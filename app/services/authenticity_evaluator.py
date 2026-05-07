import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from app import schemas

from .llm_client import LLMClientError, chat_completion_json

RUBRIC_VERSION = "authenticity_rubric_v1"
PROMPT_VERSION = "authenticity_eval_prompt_v1"
DEMO_FALLBACK_PROMPT_VERSION = "authenticity_demo_fallback_v1"

TRANSIENT_UPSTREAM_STATUS_CODES = {429, 500, 502, 503, 504}


class AuthenticityEvaluationError(RuntimeError):
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
def load_authenticity_rubric() -> Dict[str, Any]:
    rubric_path = Path(__file__).resolve().parents[1] / "rubrics" / f"{RUBRIC_VERSION}.json"
    return json.loads(rubric_path.read_text(encoding="utf-8"))


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


def is_local_scoring_mode() -> bool:
    env_value = _read_local_env_value("AUTHENTICITY_SCORING_MODE")
    if (env_value or "").strip().lower() == "local":
        return True
    return not _is_llm_available()


def _is_demo_fallback_enabled() -> bool:
    env_value = _read_local_env_value("AUTHENTICITY_ENABLE_DEMO_FALLBACK")
    return (env_value or "true").strip().lower() in {"1", "true", "yes", "on"}


def should_use_authenticity_fallback(exc: AuthenticityEvaluationError) -> bool:
    if not _is_demo_fallback_enabled():
        return False
    if exc.upstream_status_code is None:
        return True
    return exc.upstream_status_code in TRANSIENT_UPSTREAM_STATUS_CODES


def _is_llm_available() -> bool:
    api_key = os.getenv("LLM_API_KEY")
    if api_key is None:
        env_path = Path(__file__).resolve().parents[2] / ".env"
        if env_path.exists():
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip() == "LLM_API_KEY":
                    api_key = value.strip().strip('"').strip("'")
                    break
    if not api_key:
        return False
    try:
        from .llm_client import get_llm_settings
        get_llm_settings()
        return True
    except Exception:
        return False


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


def _compute_rule_scores(task: Any, iterations: List[Any]) -> Dict[str, Any]:
    version_count = len(iterations)

    # --- iteration_evidence_base (max 16 out of 20) ---
    if version_count >= 6:
        iteration_evidence_base = 16
    elif version_count == 5:
        iteration_evidence_base = 15
    elif version_count == 4:
        iteration_evidence_base = 14
    elif version_count == 3:
        iteration_evidence_base = 13
    elif version_count == 2:
        iteration_evidence_base = 8
    elif version_count == 1:
        iteration_evidence_base = 3
    else:
        iteration_evidence_base = 0

    # --- process_transparency_rule (max 20 out of 25) ---
    completeness_scores = []
    for it in iterations:
        matrix = it.collaboration_matrix or []
        stage_count = len(matrix)
        if stage_count >= 4:
            completeness_scores.append(10)
        else:
            completeness_scores.append(round(stage_count / 4 * 10))
    completeness_total = round(sum(completeness_scores) / max(len(completeness_scores), 1))

    latest = iterations[-1] if iterations else None
    latest_matrix = (latest.collaboration_matrix or []) if latest else []

    differentiation_score = 0
    if latest_matrix:
        human_percents = [stage.get("humanPercent", 0) for stage in latest_matrix if isinstance(stage, dict)]
        if human_percents and not all(hp == human_percents[0] for hp in human_percents):
            differentiation_score = 5

    deliverable_score = 0
    if latest and latest.deliverable_payload:
        payload_stripped = latest.deliverable_payload.strip()
        if payload_stripped and payload_stripped != "未提供链接":
            deliverable_score = 5

    process_transparency_rule = min(20, completeness_total + differentiation_score + deliverable_score)

    # --- critical_engagement_rule (max 25, all LLM; rule only caps) ---
    all_reflections_short = all(
        len((it.reflection_log or "")) < 50 for it in iterations
    )
    critical_engagement_rule_cap = 0 if all_reflections_short else None

    # --- reflection_quality_rule (max 20, all LLM; rule only caps) ---
    reflection_quality_rule_cap = 0 if all_reflections_short else None

    # --- ai_collab_literacy_rule (max 6 out of 10) ---
    ai_collab_rule = 0
    if latest_matrix:
        for stage in latest_matrix:
            if not isinstance(stage, dict):
                continue
            stage_name = stage.get("stageName", "")
            human_pct = stage.get("humanPercent", 0)
            ai_pct = stage.get("aiPercent", 0)
            if stage_name in ("规划", "planning") and human_pct >= 60:
                ai_collab_rule += 2
                break
        for stage in latest_matrix:
            if not isinstance(stage, dict):
                continue
            stage_name = stage.get("stageName", "")
            human_pct = stage.get("humanPercent", 0)
            if stage_name in ("审核", "修订", "润色", "review", "revision", "polish") and human_pct >= 60:
                ai_collab_rule += 2
                break
        all_ai_high = all(
            stage.get("aiPercent", 0) >= 90
            for stage in latest_matrix
            if isinstance(stage, dict)
        )
        if all_ai_high:
            ai_collab_rule = max(0, ai_collab_rule - 1)

    tools_used_list = (latest.tools_used or []) if latest else []
    if isinstance(tools_used_list, list) and len(tools_used_list) >= 2:
        if len(set(tools_used_list)) >= 2:
            ai_collab_rule += 2

    ai_collab_rule = min(6, max(0, ai_collab_rule))

    return {
        "iteration_evidence_base": iteration_evidence_base,
        "process_transparency_rule": process_transparency_rule,
        "critical_engagement_rule_cap": critical_engagement_rule_cap,
        "reflection_quality_rule_cap": reflection_quality_rule_cap,
        "ai_collab_rule": ai_collab_rule,
        "version_count": version_count,
        "all_reflections_short": all_reflections_short,
    }


def build_local_evaluation(
        task: Any,
        iterations: List[Any],
        upstream_error_message: str = "",
        scoring_mode: str = "local",
) -> Tuple[schemas.AuthenticityEvaluationReport, Dict[str, Any]]:
    rule_scores = _compute_rule_scores(task, iterations)

    iteration_evidence_score = min(rule_scores["iteration_evidence_base"], 16)
    iteration_evidence_reason = f"规则基础分 {iteration_evidence_score}/20（版本数 {rule_scores['version_count']}）"

    process_transparency_score = rule_scores["process_transparency_rule"]
    process_transparency_reason = f"规则评分 {process_transparency_score}/25（完整度+区分度+交付物）"

    if rule_scores["critical_engagement_rule_cap"] == 0:
        critical_engagement_score = 0
        critical_engagement_reason = "所有版本反思均不足50字，规则强制0分"
    else:
        critical_engagement_score = min(
            round(25 * 0.4),
            25,
        )
        critical_engagement_reason = "本地模式保守估算分（LLM维度由规则兜底估算）"

    if rule_scores["reflection_quality_rule_cap"] == 0:
        reflection_quality_score = 0
        reflection_quality_reason = "所有版本反思均不足50字，规则强制0分"
    else:
        reflection_quality_score = min(
            round(20 * 0.4),
            20,
        )
        reflection_quality_reason = "本地模式保守估算分（LLM维度由规则兜底估算）"

    ai_collab_score = rule_scores["ai_collab_rule"]
    ai_collab_reason = f"规则评分 {ai_collab_score}/10"

    dimension_scores = [
        schemas.AuthenticityDimensionScore(
            key="iteration_evidence",
            score=iteration_evidence_score,
            max_score=20,
            reason=iteration_evidence_reason,
        ),
        schemas.AuthenticityDimensionScore(
            key="process_transparency",
            score=process_transparency_score,
            max_score=25,
            reason=process_transparency_reason,
        ),
        schemas.AuthenticityDimensionScore(
            key="critical_engagement",
            score=critical_engagement_score,
            max_score=25,
            reason=critical_engagement_reason,
        ),
        schemas.AuthenticityDimensionScore(
            key="reflection_quality",
            score=reflection_quality_score,
            max_score=20,
            reason=reflection_quality_reason,
        ),
        schemas.AuthenticityDimensionScore(
            key="ai_collab_literacy",
            score=ai_collab_score,
            max_score=10,
            reason=ai_collab_reason,
        ),
    ]

    total_score = sum(ds.score for ds in dimension_scores)

    improvements = []
    if rule_scores["version_count"] < 3:
        improvements.append("建议增加迭代版本数量至3个以上，以体现过程推进。")
    if rule_scores["all_reflections_short"]:
        improvements.append("反思内容过于简短，请补充具体修改细节与学习反思。")
    if process_transparency_score < 15:
        improvements.append("协作矩阵完整度不足或各阶段比例区分度低，建议完善各阶段人机分工。")
    latest = iterations[-1] if iterations else None
    if latest and (not latest.deliverable_payload or latest.deliverable_payload.strip() in ("", "未提供链接")):
        improvements.append("请提交交付物链接以体现过程产出。")
    if ai_collab_score < 4:
        improvements.append("人机分工合理性偏低，建议在规划与审核阶段提高人类参与度，并针对性选择工具。")
    if not improvements:
        improvements.append("整体表现稳定，建议进一步深化反思中的认知变化描述。")

    overall_feedback = (
        f"规则评分模式：版本数 {rule_scores['version_count']}，"
        f"总分 {total_score}/100。"
    )
    if upstream_error_message:
        overall_feedback = f"（因上游服务不可用，以下为规则评分）{overall_feedback}"

    report = schemas.AuthenticityEvaluationReport(
        rubric_version=RUBRIC_VERSION,
        total_score=total_score,
        overall_feedback=overall_feedback,
        dimension_scores=dimension_scores,
        improvement_advice=improvements,
    )

    input_snapshot = _build_input_snapshot(task, iterations)

    metadata = {
        "input_snapshot": input_snapshot,
        "model_name": "demo-fallback" if scoring_mode == "fallback" else "local-rule",
        "rubric_version": RUBRIC_VERSION,
        "prompt_version": DEMO_FALLBACK_PROMPT_VERSION,
        "fallback_reason": upstream_error_message or "local scoring mode",
        "scoring_mode": scoring_mode,
    }

    return report, metadata


def _build_input_snapshot(task: Any, iterations: List[Any]) -> Dict[str, Any]:
    iterations_data = []
    for it in iterations:
        iterations_data.append({
            "id": it.id,
            "version_number": it.version_number,
            "deliverable_payload": it.deliverable_payload,
            "collaboration_matrix": it.collaboration_matrix or [],
            "tools_used": it.tools_used or [],
            "reflection_log": it.reflection_log or "",
        })
    return {
        "task": {
            "id": task.id,
            "title": task.title,
            "context_description": task.context_description,
            "evaluation_criteria": task.evaluation_criteria,
        },
        "iterations": iterations_data,
        "version_count": len(iterations_data),
        "rubric": load_authenticity_rubric(),
    }


def _build_prompts(
        task: Any,
        iterations: List[Any],
        rule_scores: Dict[str, Any],
) -> Tuple[str, str]:
    rubric = load_authenticity_rubric()

    system_prompt = (
        "你是一个严谨的课程过程真实性评分引擎。"
        "你的评分目标是：评估过程是否透明、迭代是否有实质推进、学生是否保持认知主导权。"
        "AI使用多不扣分，不会解释为什么这样用才扣分。"
        "不要输出 Markdown，只输出纯 JSON。严格遵守下面给出的维度、权重和强制规则。"
    )

    iterations_data = []
    for it in iterations:
        iterations_data.append({
            "version_number": it.version_number,
            "deliverable_payload": it.deliverable_payload,
            "collaboration_matrix": it.collaboration_matrix or [],
            "tools_used": it.tools_used or [],
            "reflection_log": it.reflection_log or "",
        })

    rule_summary = (
        f"\n规则基础分如下，你只能在此基础上调整由LLM负责的部分：\n"
        f"- iteration_evidence: 规则基础分={rule_scores['iteration_evidence_base']}/20（版本数={rule_scores['version_count']}），"
        f"你可在基础分基础上根据版本间反思差异调整（0~4分加成空间）\n"
        f"- process_transparency: 规则分={rule_scores['process_transparency_rule']}/25，"
        f"你可在规则分基础上根据矩阵内容合理性调整（0~5分加成空间）\n"
        f"- critical_engagement: 完全由你评分（0~25），"
        f"{'但规则硬限制为0（所有反思不足50字）' if rule_scores['critical_engagement_rule_cap'] == 0 else '无规则基础分，请根据反思内容评估'}\n"
        f"- reflection_quality: 完全由你评分（0~20），"
        f"{'但规则硬限制为0（所有反思不足50字）' if rule_scores['reflection_quality_rule_cap'] == 0 else '无规则基础分，请根据反思质量评估'}\n"
        f"- ai_collab_literacy: 规则基础分={rule_scores['ai_collab_rule']}/10，"
        f"你可在基础分基础上根据反思中是否解释AI使用来调整（0~4分加成空间）\n"
    )

    forced_rules_text = "\n强制规则：\n" + "\n".join(f"- {r}" for r in rubric.get("forced_rules", []))

    user_prompt = f"""
请根据以下任务和数据，对真实性过程进行评分。

任务标题：{task.title}
任务说明：{task.context_description}
评分标准：{task.evaluation_criteria}

版本迭代数据：
{json.dumps(iterations_data, ensure_ascii=False, indent=2)}
{rule_summary}
{forced_rules_text}

输出必须严格为以下 JSON 格式：
{{
  "rubric_version": "authenticity_rubric_v1",
  "total_score": integer 0-100,
  "overall_feedback": "string",
  "dimension_scores": [
    {{"key": "iteration_evidence", "score": integer, "max_score": 20, "reason": "string"}},
    {{"key": "process_transparency", "score": integer, "max_score": 25, "reason": "string"}},
    {{"key": "critical_engagement", "score": integer, "max_score": 25, "reason": "string"}},
    {{"key": "reflection_quality", "score": integer, "max_score": 20, "reason": "string"}},
    {{"key": "ai_collab_literacy", "score": integer, "max_score": 10, "reason": "string"}}
  ],
  "improvement_advice": ["string"]
}}

total_score 必须等于各 dimension_scores 之和。不要输出 Markdown。
""".strip()

    return system_prompt, user_prompt


def evaluate_submission(
        task: Any,
        iterations: List[Any],
) -> Tuple[schemas.AuthenticityEvaluationReport, Dict[str, Any]]:
    if is_local_scoring_mode():
        return build_local_evaluation(
            task=task,
            iterations=iterations,
            upstream_error_message="local scoring mode enabled",
            scoring_mode="local",
        )

    input_snapshot = _build_input_snapshot(task, iterations)
    rule_scores = _compute_rule_scores(task, iterations)

    last_error = None
    last_raw_response = None
    model_name = None

    for _attempt in range(2):
        try:
            system_prompt, user_prompt = _build_prompts(task, iterations, rule_scores)
            raw_response, resolved_model = chat_completion_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            last_raw_response = raw_response
            model_name = resolved_model

            parsed_payload = json.loads(_extract_json_payload(raw_response))

            llm_total = parsed_payload.get("total_score", 0)
            llm_dims = parsed_payload.get("dimension_scores", [])

            iteration_evidence_score = rule_scores["iteration_evidence_base"]
            for dim in llm_dims:
                if dim.get("key") == "iteration_evidence":
                    adjust = int(dim.get("score", 0)) - rule_scores["iteration_evidence_base"]
                    adjust = max(0, min(4, adjust))
                    iteration_evidence_score = min(20, rule_scores["iteration_evidence_base"] + adjust)

            process_transparency_score = rule_scores["process_transparency_rule"]
            for dim in llm_dims:
                if dim.get("key") == "process_transparency":
                    adjust = int(dim.get("score", 0)) - rule_scores["process_transparency_rule"]
                    adjust = max(0, min(5, adjust))
                    process_transparency_score = min(25, rule_scores["process_transparency_rule"] + adjust)

            critical_engagement_score = 0
            for dim in llm_dims:
                if dim.get("key") == "critical_engagement":
                    critical_engagement_score = min(25, max(0, int(dim.get("score", 0))))
            if rule_scores["critical_engagement_rule_cap"] == 0:
                critical_engagement_score = 0

            reflection_quality_score = 0
            for dim in llm_dims:
                if dim.get("key") == "reflection_quality":
                    reflection_quality_score = min(20, max(0, int(dim.get("score", 0))))
            if rule_scores["reflection_quality_rule_cap"] == 0:
                reflection_quality_score = min(5, reflection_quality_score)

            ai_collab_score = rule_scores["ai_collab_rule"]
            for dim in llm_dims:
                if dim.get("key") == "ai_collab_literacy":
                    adjust = int(dim.get("score", 0)) - rule_scores["ai_collab_rule"]
                    adjust = max(0, min(4, adjust))
                    ai_collab_score = min(10, rule_scores["ai_collab_rule"] + adjust)

            dimension_scores_list = [
                schemas.AuthenticityDimensionScore(
                    key="iteration_evidence",
                    score=iteration_evidence_score,
                    max_score=20,
                    reason="",
                ),
                schemas.AuthenticityDimensionScore(
                    key="process_transparency",
                    score=process_transparency_score,
                    max_score=25,
                    reason="",
                ),
                schemas.AuthenticityDimensionScore(
                    key="critical_engagement",
                    score=critical_engagement_score,
                    max_score=25,
                    reason="",
                ),
                schemas.AuthenticityDimensionScore(
                    key="reflection_quality",
                    score=reflection_quality_score,
                    max_score=20,
                    reason="",
                ),
                schemas.AuthenticityDimensionScore(
                    key="ai_collab_literacy",
                    score=ai_collab_score,
                    max_score=10,
                    reason="",
                ),
            ]

            overall_feedback = parsed_payload.get("overall_feedback", "")
            improvement_advice = parsed_payload.get("improvement_advice", [])

            report = schemas.AuthenticityEvaluationReport(
                rubric_version=RUBRIC_VERSION,
                total_score=sum(ds.score for ds in dimension_scores_list),
                overall_feedback=overall_feedback,
                dimension_scores=dimension_scores_list,
                improvement_advice=improvement_advice,
            )

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
            raise AuthenticityEvaluationError(
                f"LLM 调用失败：{exc}",
                input_snapshot=input_snapshot,
                model_name=model_name,
                raw_response=last_raw_response,
                upstream_status_code=exc.status_code,
            ) from exc

    raise AuthenticityEvaluationError(
        f"LLM 返回结果经过 2 次尝试仍无法通过 JSON/Pydantic 校验：{last_error}",
        input_snapshot=input_snapshot,
        model_name=model_name,
        raw_response=last_raw_response,
    )