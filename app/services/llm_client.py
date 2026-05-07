import json
import os
import socket
import ssl
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, request


class LLMClientError(RuntimeError):
    def __init__(self, message: str, *, status_code: Optional[int] = None, error_code: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


_ENV_LOADED = False


def _load_local_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return

    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)

    _ENV_LOADED = True


def _parse_model_list(raw_value: Optional[str]) -> List[str]:
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def get_llm_settings() -> Dict[str, Any]:
    _load_local_env()

    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMClientError("Missing LLM_API_KEY or OPENAI_API_KEY in environment.")

    return {
        "api_key": api_key,
        "base_url": (os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/"),
        "model_name": os.getenv("LLM_MODEL_NAME") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini",
        "fallback_models": _parse_model_list(os.getenv("LLM_FALLBACK_MODELS")),
        "timeout_seconds": int(os.getenv("LLM_TIMEOUT_SECONDS", "90")),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.1")),
    }


# Network-level exceptions that should be treated as transient upstream failures
_TRANSIENT_NETWORK_EXCEPTIONS = (socket.timeout, ConnectionError, ConnectionResetError, ssl.SSLError, OSError)


def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout_seconds: int) -> Dict[str, Any]:
    req = request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8", errors="replace")
        try:
            error_payload = json.loads(raw_body)
        except json.JSONDecodeError:
            error_payload = None

        message = raw_body
        error_code = None
        if isinstance(error_payload, dict):
            error_obj = error_payload.get("error")
            if isinstance(error_obj, dict):
                message = error_obj.get("message") or raw_body
                error_code = error_obj.get("code") or error_obj.get("type")
            else:
                message = error_payload.get("message") or raw_body

        raise LLMClientError(
            f"LLM request failed ({exc.code}): {message}",
            status_code=exc.code,
            error_code=error_code,
        ) from exc
    except error.URLError as exc:
        # URLError (DNS failure, connection refused, etc.) → treat as 502 upstream
        raise LLMClientError(
            f"LLM request failed (URL error): {exc.reason}",
            status_code=502,
            error_code=None,
        ) from exc
    except _TRANSIENT_NETWORK_EXCEPTIONS as exc:
        # socket.timeout, ConnectionError, etc. → treat as 504 upstream
        raise LLMClientError(
            f"LLM request failed (network error): {type(exc).__name__}: {exc}",
            status_code=504,
            error_code=None,
        ) from exc


def _extract_message_content(response_json: Dict[str, Any]) -> str:
    choices = response_json.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LLMClientError("LLM response missing choices.")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise LLMClientError("LLM response missing message payload.")

    content = message.get("content")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
        if parts:
            return "".join(parts)

    raise LLMClientError("LLM response missing text content.")


def _is_transient_llm_error(exc: LLMClientError) -> bool:
    return exc.status_code in {429, 500, 502, 503, 504} or exc.error_code in {
        "service_unavailable_error",
        "no_available_providers",
        "rate_limit_exceeded",
    }


def _post_json_with_retry(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout_seconds: int) -> Dict[str, Any]:
    last_error = None
    for attempt in range(2):
        try:
            return _post_json(url=url, headers=headers, payload=payload, timeout_seconds=timeout_seconds)
        except LLMClientError as exc:
            last_error = exc
            if attempt == 1 or not _is_transient_llm_error(exc):
                raise
            time.sleep(1.0)

    if last_error is not None:
        raise last_error
    raise LLMClientError("LLM request failed without a captured error.")  # pragma: no cover


def _candidate_models(settings: Dict[str, Any]) -> List[str]:
    seen = set()
    ordered = []
    for model_name in [settings["model_name"], *settings.get("fallback_models", [])]:
        if model_name and model_name not in seen:
            seen.add(model_name)
            ordered.append(model_name)
    return ordered


def chat_completion_json(system_prompt: str, user_prompt: str) -> Tuple[str, str]:
    settings = get_llm_settings()
    url = f"{settings['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings['api_key']}",
        "Content-Type": "application/json",
    }

    last_error = None

    for model_name in _candidate_models(settings):
        base_payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": settings["temperature"],
        }

        payload_with_json_mode = dict(base_payload)
        payload_with_json_mode["response_format"] = {"type": "json_object"}

        try:
            response_json = _post_json_with_retry(
                url=url,
                headers=headers,
                payload=payload_with_json_mode,
                timeout_seconds=settings["timeout_seconds"],
            )
            resolved_model = response_json.get("model") or model_name
            return _extract_message_content(response_json), resolved_model
        except LLMClientError as exc:
            if "response_format" not in str(exc):
                last_error = exc
            else:
                try:
                    response_json = _post_json_with_retry(
                        url=url,
                        headers=headers,
                        payload=base_payload,
                        timeout_seconds=settings["timeout_seconds"],
                    )
                    resolved_model = response_json.get("model") or model_name
                    return _extract_message_content(response_json), resolved_model
                except LLMClientError as fallback_exc:
                    last_error = fallback_exc

    if last_error is not None:
        raise last_error

    raise LLMClientError("No LLM model candidates configured.")
