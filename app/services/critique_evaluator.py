import json
import os
import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from app import schemas

from .llm_client import LLMClientError, chat_completion_json

RUBRIC_VERSION = "critique_rubric_v1"
PROMPT_VERSION = "critique_eval_prompt_v1"
DEMO_FALLBACK_PROMPT_VERSION = "critique_demo_fallback_v1"
TRANSIENT_UPSTREAM_STATUS_CODES = {429, 500, 502, 503, 504}


class CritiqueEvaluationError(RuntimeError):
    def __init__(
            self,
            message: str,
            *,
            input_snapshot: Dict[str, Any],
            model_name: Optional[str] = None,
            raw_response: Optional[str] = None,
            upstream_status_code: Optional[int] = None,
    ):
        super().__init__(message)
        self.input_snapshot = input_snapshot
        self.model_name = model_name
        self.raw_response = raw_response
        self.upstream_status_code = upstream_status_code


@lru_cache(maxsize=1)
def load_critique_rubric() -> Dict[str, Any]:
    rubric_path = Path(__file__).resolve().parents[1] / "rubrics" / f"{RUBRIC_VERSION}.json"
    return json.loads(rubric_path.read_text(encoding="utf-8"))


def _build_input_snapshot(task: Any, submission: Any) -> Dict[str, Any]:
    return {
        "task": {
            "title": task.title,
            "content": task.content,
            "preset_errors": task.preset_errors or [],
        },
        "submission": {
            "id": submission.id,
            "task_id": submission.task_id,
            "student_id": submission.student_id,
            "critiques_data": submission.critiques_data or [],
        },
        "rubric": load_critique_rubric(),
    }


def _build_prompts(input_snapshot: Dict[str, Any]) -> Tuple[str, str]:
    system_prompt = (
        "你是一个严谨的课程批判评分引擎，只评估学生是否识别并纠正教师预设错误。"
        "不要评价文章文采，不要输出 Markdown，不要输出额外解释。"
        "你必须返回一个可被 JSON 直接解析的对象，并严格遵守输入 rubric 的维度、权重、强制规则和输出结构。"
    )

    user_prompt = f"""
请根据下面的评分输入快照进行评分，并严格返回单个 JSON 对象。

评分目标：评"是否识别并纠正预设错误"，不是评整篇文章写得漂不漂亮。

固定评分维度与满分：
- coverage: 35
- correction_accuracy: 30
- reasoning_quality: 20
- alignment_precision: 10
- noise_control: 5

输出必须至少包含这些字段：
- rubric_version
- total_score
- overall_feedback
- dimension_scores
- details
- missed_error_ids
- invalid_critiques
- improvement_advice

details 中每一项都必须保留旧字段：
- step1_match
- step2_score
- step2_feedback

重要：在 step1_match、step2_feedback、overall_feedback、improvement_advice 等所有面向学生的文字中，必须明确指出预设错误的具体内容（如原文错误表述「wrong_text」和核心概念「core_concept」），不要只写 error_id 编号（如"e1"）。例如应写"预设错误「需要设置保护频带」"而不是"预设错误 e1"。

输入快照如下：
{json.dumps(input_snapshot, ensure_ascii=False, indent=2)}
""".strip()

    return system_prompt, user_prompt


def _extract_json_payload(raw_text: str) -> str:
    clean_text = raw_text.strip()
    if clean_text.startswith("```"):
        clean_text = clean_text.strip("`")
        if clean_text.startswith("json"):
            clean_text = clean_text[4:]
        clean_text = clean_text.strip()

    start = clean_text.find("{")
    end = clean_text.rfind("}")
    if start != -1 and end != -1 and end >= start:
        return clean_text[start:end + 1]
    return clean_text


def _is_demo_fallback_enabled() -> bool:
    env_value = _read_local_env_value("CRITIQUE_ENABLE_DEMO_FALLBACK")
    return (env_value or "false").strip().lower() in {"1", "true", "yes", "on"}


def is_local_scoring_mode() -> bool:
    env_value = _read_local_env_value("CRITIQUE_SCORING_MODE")
    return (env_value or "llm").strip().lower() == "local"


def _read_local_env_value(key_name: str) -> Optional[str]:
    env_value = os.getenv(key_name)
    if env_value is None:
        env_path = Path(__file__).resolve().parents[2] / ".env"
        if env_path.exists():
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip() == key_name:
                    env_value = value.strip().strip('"').strip("'")
                    break
    return env_value


def should_use_demo_fallback(exc: CritiqueEvaluationError) -> bool:
    return _is_demo_fallback_enabled() and exc.upstream_status_code in TRANSIENT_UPSTREAM_STATUS_CODES


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    value = str(value).lower()
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value)
    return value


def _similarity(left: Any, right: Any) -> float:
    left_text = _normalize_text(left)
    right_text = _normalize_text(right)
    if not left_text or not right_text:
        return 0.0

    min_len = min(len(left_text), len(right_text))
    if min_len >= 2 and (left_text in right_text or right_text in left_text):
        return 1.0

    seq_ratio = SequenceMatcher(None, left_text, right_text).ratio()
    left_chars = set(left_text)
    right_chars = set(right_text)
    char_ratio = len(left_chars & right_chars) / max(len(left_chars | right_chars), 1)
    return max(seq_ratio, char_ratio)


def _safe_mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _extract_selected_text(task_content: str, critique: Dict[str, Any]) -> str:
    quote_text = critique.get("quote")
    if isinstance(quote_text, str) and quote_text.strip():
        return quote_text

    selection_range = critique.get("selection_range")
    if not isinstance(selection_range, list) or len(selection_range) != 2:
        return ""

    start, end = selection_range
    if not isinstance(start, int) or not isinstance(end, int):
        return ""

    start = max(0, min(start, len(task_content)))
    end = max(start, min(end, len(task_content)))
    return task_content[start:end]


def _candidate_metrics(task_content: str, critique: Dict[str, Any], error_item: Dict[str, Any]) -> Dict[str, Any]:
    selected_text = _extract_selected_text(task_content, critique)
    rewrite_text = critique.get("rewrite") or ""
    citation_text = critique.get("citation") or ""
    wrong_text = error_item.get("wrong_text") or ""
    standard_correction = error_item.get("standard_correction") or ""
    core_concept = error_item.get("core_concept") or ""

    quote_similarity = _similarity(selected_text, wrong_text)
    rewrite_similarity = max(
        _similarity(rewrite_text, standard_correction),
        _similarity(rewrite_text, core_concept),
    )
    citation_similarity = max(
        _similarity(citation_text, standard_correction),
        _similarity(citation_text, core_concept),
    )
    cross_similarity = max(
        _similarity(f"{selected_text}{rewrite_text}", wrong_text),
        _similarity(f"{rewrite_text}{citation_text}", core_concept),
    )

    match_confidence = (
        0.5 * quote_similarity
        + 0.3 * rewrite_similarity
        + 0.1 * citation_similarity
        + 0.1 * cross_similarity
    )
    citation_present = bool(_normalize_text(citation_text))

    alignment_quality = min(100, max(0, round(25 + quote_similarity * 75)))
    correction_quality = min(100, max(0, round(20 + rewrite_similarity * 80)))
    if citation_present:
        reasoning_quality = min(100, max(0, round(25 + citation_similarity * 75)))
    else:
        reasoning_quality = 20

    pair_score = min(
        100,
        max(
            0,
            round(0.45 * correction_quality + 0.35 * reasoning_quality + 0.2 * alignment_quality),
        ),
    )

    return {
        "selected_text": selected_text,
        "rewrite_text": rewrite_text,
        "citation_text": citation_text,
        "quote_similarity": quote_similarity,
        "rewrite_similarity": rewrite_similarity,
        "citation_similarity": citation_similarity,
        "match_confidence": match_confidence,
        "alignment_quality": alignment_quality,
        "correction_quality": correction_quality,
        "reasoning_quality": reasoning_quality,
        "citation_present": citation_present,
        "pair_score": pair_score,
    }


def _build_step2_feedback(metrics: Dict[str, Any]) -> str:
    notes = []

    if metrics["correction_quality"] >= 80:
        notes.append("更正方向基本准确")
    elif metrics["correction_quality"] >= 55:
        notes.append("更正方向部分正确，但精度一般")
    else:
        notes.append("更正内容与标准修正仍有明显偏差")

    if metrics["citation_present"]:
        if metrics["reasoning_quality"] >= 75:
            notes.append("理论依据能支撑主要判断")
        else:
            notes.append("理论依据较浅，建议补充原理说明")
    else:
        notes.append("缺少 citation，理论依据支撑不足")

    if metrics["alignment_quality"] < 60:
        notes.append("错误片段定位还不够精准")

    return "；".join(notes) + "。"


def build_demo_fallback_evaluation(
        task: Any,
        submission: Any,
        upstream_error_message: str,
        scoring_mode: str = "fallback",
) -> Tuple[schemas.CritiqueEvaluationReport, Dict[str, Any]]:
    input_snapshot = _build_input_snapshot(task, submission)
    preset_errors = task.preset_errors or []
    critiques = submission.critiques_data or []
    task_content = task.content or ""

    candidate_pairs = []
    best_candidate_by_critique: Dict[int, Dict[str, Any]] = {}
    for critique_index, critique in enumerate(critiques):
        for error_index, error_item in enumerate(preset_errors):
            metrics = _candidate_metrics(task_content, critique, error_item)
            candidate = {
                "critique_index": critique_index,
                "error_index": error_index,
                "error_id": error_item.get("error_id") or f"error_{error_index + 1}",
                "metrics": metrics,
                "quality_rank": (
                    metrics["match_confidence"],
                    metrics["pair_score"],
                    metrics["correction_quality"],
                ),
            }
            candidate_pairs.append(candidate)
            if critique_index not in best_candidate_by_critique or candidate["quality_rank"] > best_candidate_by_critique[critique_index]["quality_rank"]:
                best_candidate_by_critique[critique_index] = candidate

    candidate_pairs.sort(key=lambda item: item["quality_rank"], reverse=True)

    accepted_pairs = []
    assigned_critique_indexes = set()
    assigned_error_indexes = set()
    match_threshold = 0.38

    for candidate in candidate_pairs:
        if candidate["metrics"]["match_confidence"] < match_threshold:
            continue
        if candidate["critique_index"] in assigned_critique_indexes:
            continue
        if candidate["error_index"] in assigned_error_indexes:
            continue

        accepted_pairs.append(candidate)
        assigned_critique_indexes.add(candidate["critique_index"])
        assigned_error_indexes.add(candidate["error_index"])

    accepted_by_error_index = {item["error_index"]: item for item in accepted_pairs}

    details = []
    invalid_critiques = []
    improvement_advice = []
    is_local_mode = scoring_mode == "local"
    match_prefix = "规则评分：" if is_local_mode else "演示级回退评分："

    for error_index, error_item in enumerate(preset_errors):
        error_id = error_item.get("error_id") or f"error_{error_index + 1}"
        accepted = accepted_by_error_index.get(error_index)
        if accepted:
            metrics = accepted["metrics"]
            wrong_text = error_item.get("wrong_text", "")
            core_concept = error_item.get("core_concept", "")
            standard_correction = error_item.get("standard_correction", "")
            wrong_text_brief = f"「{wrong_text[:30]}{'…' if len(wrong_text) > 30 else ''}」" if wrong_text else ""
            step1_msg = (
                f"{match_prefix}匹配到预设错误 {wrong_text_brief}（{core_concept}），"
                f"学生定位片段「{metrics['selected_text'][:30]}{'…' if len(metrics['selected_text']) > 30 else ''}」"
                f"与预设错误匹配度约 {round(metrics['match_confidence'] * 100)}%。"
            )
            detail_feedback = _build_step2_feedback(metrics)
            if standard_correction:
                detail_feedback += f"；标准更正：{standard_correction}"
            details.append(
                schemas.CritiqueEvaluationDetail(
                    error_id=error_id,
                    matched=True,
                    step1_match=step1_msg,
                    step2_score=metrics["pair_score"],
                    step2_feedback=detail_feedback,
                )
            )
        else:
            wrong_text = error_item.get("wrong_text", "")
            core_concept = error_item.get("core_concept") or "相关理论点"
            standard_correction = error_item.get("standard_correction", "")
            wrong_text_brief = f"「{wrong_text[:30]}{'…' if len(wrong_text) > 30 else ''}」" if wrong_text else ""
            step1_msg = f"{match_prefix}未识别到预设错误 {wrong_text_brief}（{core_concept}）。"
            miss_advice = f"建议识别并更正{wrong_text_brief}，围绕「{core_concept}」补充理论依据。"
            if standard_correction:
                miss_advice += f" 参考更正：{standard_correction}"
            details.append(
                schemas.CritiqueEvaluationDetail(
                    error_id=error_id,
                    matched=False,
                    step1_match=step1_msg,
                    step2_score=0,
                    step2_feedback=miss_advice,
                )
            )
        for critique_index, critique in enumerate(critiques):
            if critique_index in assigned_critique_indexes:
                continue

            best_candidate = best_candidate_by_critique.get(critique_index)
            if best_candidate is None or best_candidate["metrics"]["match_confidence"] < match_threshold:
                reason = "未能匹配到任何预设错误，不计分。"
            else:
                best_error_item = preset_errors[best_candidate["error_index"]] if best_candidate["error_index"] < len(preset_errors) else {}
                best_wrong = best_error_item.get("wrong_text", "")
                best_brief = f"「{best_wrong[:30]}{'…' if len(best_wrong) > 30 else ''}」" if best_wrong else ""
                reason = f"与更高质量的纠错重复命中预设错误 {best_brief}，按规则不重复计分。"

            invalid_critiques.append(
                {
                    "critique_index": critique_index,
                    "quote": critique.get("quote") or _extract_selected_text(task_content, critique),
                    "reason": reason,
                }
            )

    matched_metrics = [item["metrics"] for item in accepted_pairs]
    matched_count = len(accepted_pairs)
    total_errors = len(preset_errors)
    missed_error_ids = [
        (error_item.get("error_id") or f"error_{index + 1}")
        for index, error_item in enumerate(preset_errors)
        if index not in accepted_by_error_index
    ]

    avg_match_confidence = _safe_mean([item["match_confidence"] for item in matched_metrics])
    avg_correction_quality = _safe_mean([item["correction_quality"] for item in matched_metrics])
    avg_reasoning_quality = _safe_mean([item["reasoning_quality"] for item in matched_metrics])
    avg_alignment_quality = _safe_mean([item["alignment_quality"] for item in matched_metrics])

    if total_errors == 0 or matched_count == 0:
        coverage_score = 0
    elif matched_count == total_errors:
        coverage_score = min(35, max(32, 32 + round(avg_match_confidence * 3)))
    elif matched_count == total_errors - 1:
        coverage_score = min(31, max(20, 20 + round(avg_match_confidence * 11)))
    else:
        coverage_score = min(19, round((matched_count / total_errors) * 19))

    correction_accuracy_score = min(30, round((avg_correction_quality / 100) * 30))
    reasoning_quality_score = min(20, round((avg_reasoning_quality / 100) * 20))
    if matched_metrics and all(not item["citation_present"] for item in matched_metrics):
        reasoning_quality_score = min(reasoning_quality_score, 8)
    alignment_precision_score = min(10, round((avg_alignment_quality / 100) * 10))

    invalid_count = len(invalid_critiques)
    if invalid_count == 0:
        noise_control_score = 5
    elif invalid_count == 1:
        noise_control_score = 4
    elif invalid_count == 2:
        noise_control_score = 2
    else:
        noise_control_score = 1

    dimension_scores = [
        schemas.CritiqueDimensionScore(
            key="coverage",
            score=coverage_score,
            max_score=35,
            reason=f"命中 {matched_count}/{total_errors} 个预设错误。",
        ),
        schemas.CritiqueDimensionScore(
            key="correction_accuracy",
            score=correction_accuracy_score,
            max_score=30,
            reason="依据 rewrite 与标准更正的接近程度给出评分。",
        ),
        schemas.CritiqueDimensionScore(
            key="reasoning_quality",
            score=reasoning_quality_score,
            max_score=20,
            reason="依据 citation 是否存在以及与核心原理的接近程度评分。",
        ),
        schemas.CritiqueDimensionScore(
            key="alignment_precision",
            score=alignment_precision_score,
            max_score=10,
            reason="依据 quote 或 selection_range 与 wrong_text 的重合度评分。",
        ),
        schemas.CritiqueDimensionScore(
            key="noise_control",
            score=noise_control_score,
            max_score=5,
            reason=f"检测到 {invalid_count} 条无效或重复 critique。",
        ),
    ]

    if missed_error_ids:
        for error_item in preset_errors:
            error_id = error_item.get("error_id") or ""
            if error_id in missed_error_ids:
                core_concept = error_item.get("core_concept") or "相关理论点"
                wrong_text = error_item.get("wrong_text", "")
                wrong_brief = f"「{wrong_text[:30]}…」" if len(wrong_text) > 30 else f"「{wrong_text}」" if wrong_text else ""
                improvement_advice.append(f"补充对 {wrong_brief} 的识别，并说明「{core_concept}」的正确原理。")

    if matched_metrics and any(not item["citation_present"] for item in matched_metrics):
        improvement_advice.append("为每条有效纠错补充 citation，明确说明为什么错以及正确原理。")

    if invalid_critiques:
        improvement_advice.append("减少重复或伪错误 critique，只保留与教师预设错误直接相关的内容。")

    if matched_metrics and avg_alignment_quality < 75:
        improvement_advice.append("框选更短、更准的错误片段，提升定位精度。")

    if not improvement_advice:
        improvement_advice.append("整体表现稳定，下一步可继续补强理论依据的深度与表述精度。")

    improvement_advice = improvement_advice[:4]

    total_score = sum(item.score for item in dimension_scores)
    if is_local_mode:
        overall_feedback = (
            f"本次命中 {matched_count}/{total_errors} 个预设错误，"
            f"总分 {total_score}/100。"
        )
    else:
        overall_feedback = (
            f"当前上游评分服务暂不可用，已切换为演示级规则评分。"
            f"本次命中 {matched_count}/{total_errors} 个预设错误，"
            f"总分 {total_score}/100。"
        )
    if missed_error_ids:
        overall_feedback += "你已识别部分关键错误，但仍有预设错误遗漏。"
    elif invalid_critiques:
        overall_feedback += "主要错误基本覆盖，但存在重复或无效 critique。"
    else:
        overall_feedback += "主要错误覆盖较完整，后续可继续加强理论依据的说理深度。"

    report = schemas.CritiqueEvaluationReport(
        rubric_version=RUBRIC_VERSION,
        total_score=total_score,
        overall_feedback=overall_feedback,
        dimension_scores=dimension_scores,
        details=details,
        missed_error_ids=missed_error_ids,
        invalid_critiques=invalid_critiques,
        improvement_advice=improvement_advice,
    )

    return report, {
        "input_snapshot": input_snapshot,
        "model_name": "demo-fallback",
        "rubric_version": RUBRIC_VERSION,
        "prompt_version": DEMO_FALLBACK_PROMPT_VERSION,
        "fallback_reason": upstream_error_message,
        "scoring_mode": scoring_mode,
    }


def evaluate_submission(task: Any, submission: Any) -> Tuple[schemas.CritiqueEvaluationReport, Dict[str, Any]]:
    input_snapshot = _build_input_snapshot(task, submission)
    system_prompt, user_prompt = _build_prompts(input_snapshot)

    last_error = None
    last_raw_response = None
    model_name = None

    for _attempt in range(2):
        try:
            raw_response, model_name = chat_completion_json(system_prompt=system_prompt, user_prompt=user_prompt)
            last_raw_response = raw_response
            parsed_payload = json.loads(_extract_json_payload(raw_response))
            report = schemas.CritiqueEvaluationReport.parse_obj(parsed_payload)
            return report, {
                "input_snapshot": input_snapshot,
                "model_name": model_name,
                "rubric_version": RUBRIC_VERSION,
                "prompt_version": PROMPT_VERSION,
            }
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            continue
        except LLMClientError as exc:
            raise CritiqueEvaluationError(
                f"LLM 调用失败：{exc}",
                input_snapshot=input_snapshot,
                model_name=model_name,
                raw_response=last_raw_response,
                upstream_status_code=exc.status_code,
            ) from exc

    raise CritiqueEvaluationError(
        f"LLM 返回结果经过 2 次尝试仍无法通过 JSON/Pydantic 校验：{last_error}",
        input_snapshot=input_snapshot,
        model_name=model_name,
        raw_response=last_raw_response,
    )
