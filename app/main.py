from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Any, Dict, List, Optional
from pathlib import Path
import os
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

from . import models, schemas, database
from .services.critique_evaluator import (
    PROMPT_VERSION as CRITIQUE_PROMPT_VERSION,
    RUBRIC_VERSION as CRITIQUE_RUBRIC_VERSION,
    CritiqueEvaluationError,
    build_demo_fallback_evaluation,
    evaluate_submission as run_critique_evaluation,
    is_local_scoring_mode,
    should_use_demo_fallback,
)
from .services.authenticity_evaluator import (
    RUBRIC_VERSION as AUTHENTICITY_RUBRIC_VERSION,
    PROMPT_VERSION as AUTHENTICITY_PROMPT_VERSION,
    AuthenticityEvaluationError,
    build_local_evaluation as build_authenticity_local_evaluation,
    evaluate_submission as evaluate_authenticity_submission,
    is_local_scoring_mode as is_authenticity_local_scoring_mode,
    should_use_authenticity_fallback,
)

# 初始化数据库结构
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="EduProcess API System")


# !!! 别忘了 CORS，否则前端跨域会被拦截 !!!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_student_and_task(db: Session, student_id: str, task_id: int, task_model: Any):
    student = db.query(models.Student).filter(models.Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student {student_id} not found.")
    task = db.query(task_model).filter(task_model.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found.")
    return student, task


def create_evaluation_record(
        db: Session,
        *,
        student_id: str,
        module_type: str,
        target_id: int,
        status: str,
        rubric_version: str,
        prompt_version: str,
        input_snapshot_json: Optional[Dict[str, Any]] = None,
        result_json: Optional[Dict[str, Any]] = None,
        total_score: Optional[int] = None,
        model_name: Optional[str] = None,
):
    record = models.EvaluationRecord(
        student_id=student_id,
        module_type=module_type,
        target_id=target_id,
        status=status,
        rubric_version=rubric_version,
        prompt_version=prompt_version,
        model_name=model_name,
input_snapshot_json=input_snapshot_json or {},
        result_json=result_json,
        total_score=total_score,
    )
    db.add(record)
    return record


def _read_env_value(key_name: str) -> Optional[str]:
    env_value = os.getenv(key_name)
    if env_value is None:
        env_path = Path(__file__).resolve().parents[1] / ".env"
        if env_path.exists():
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == key_name:
                    return v.strip().strip('"').strip("'")
    return env_value


SUCCESS_STATUSES = {"success", "success_local", "success_fallback"}


# ==========================================
# 仪表盘聚合接口
# ==========================================
@app.get("/api/dashboard/{student_id}", response_model=schemas.DashboardResponse)
def get_dashboard(student_id: str, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found.")

    critique_weight = float(_read_env_value("CRITIQUE_WEIGHT") or "0.4")
    authenticity_weight = float(_read_env_value("AUTHENTICITY_WEIGHT") or "0.6")

    # --- 批判模块 ---
    critique_tasks_status: List[schemas.DashboardCritiqueTaskStatus] = []
    best_critique_score: Optional[int] = None
    best_critique_eval_at: Optional[Any] = None
    critique_dim_scores: List[Dict[str, Any]] = []
    critique_advice: List[str] = []
    critique_module_status = "not_started"

    all_critique_tasks = db.query(models.Task).order_by(models.Task.id.asc()).all()
    for task in all_critique_tasks:
        task_status = "not_started"
        task_score: Optional[int] = None
        task_eval_at = None

        submission = db.query(models.CritiqueSubmission).filter(
            models.CritiqueSubmission.task_id == task.id,
            models.CritiqueSubmission.student_id == student_id,
        ).first()

        if submission:
            eval_record = db.query(models.EvaluationRecord).filter(
                models.EvaluationRecord.student_id == student_id,
                models.EvaluationRecord.module_type == "critique",
                models.EvaluationRecord.target_id == submission.id,
                models.EvaluationRecord.status.in_(SUCCESS_STATUSES),
            ).order_by(models.EvaluationRecord.created_at.desc()).first()

            if eval_record:
                task_status = "evaluated"
                task_score = eval_record.total_score
                task_eval_at = eval_record.created_at
            else:
                task_status = "submitted"

        critique_tasks_status.append(schemas.DashboardCritiqueTaskStatus(
            task_id=task.id,
            task_title=task.title,
            status=task_status,
            total_score=task_score,
            evaluated_at=task_eval_at,
        ))

    evaluated_crit_task = [t for t in critique_tasks_status if t.status == "evaluated"]
    if evaluated_crit_task:
        critique_module_status = "evaluated"
        avg_crit_score = round(sum(t.total_score or 0 for t in evaluated_crit_task) / len(evaluated_crit_task))
        best_critique_score = avg_crit_score
        best_critique_eval_at = max(evaluated_crit_task, key=lambda t: t.evaluated_at or datetime.min).evaluated_at

        dim_score_map: Dict[str, List[int]] = {}
        crit_advice_set: set = set()
        for et in evaluated_crit_task:
            sub = db.query(models.CritiqueSubmission).filter(
                models.CritiqueSubmission.task_id == et.task_id,
                models.CritiqueSubmission.student_id == student_id,
            ).first()
            if sub:
                rec = db.query(models.EvaluationRecord).filter(
                    models.EvaluationRecord.student_id == student_id,
                    models.EvaluationRecord.module_type == "critique",
                    models.EvaluationRecord.target_id == sub.id,
                    models.EvaluationRecord.status.in_(SUCCESS_STATUSES),
                ).order_by(models.EvaluationRecord.created_at.desc()).first()
                if rec and rec.result_json:
                    result = rec.result_json
                    for ds in result.get("dimension_scores", []):
                        dim_score_map.setdefault(ds.get("key", ""), []).append(ds.get("score", 0))
                    for adv in result.get("improvement_advice", []):
                        if adv:
                            crit_advice_set.add(adv)
        if dim_score_map:
            critique_dim_scores = []
            dim_max_scores = {"coverage": 35, "correction_accuracy": 30, "reasoning_quality": 20, "alignment_precision": 10, "noise_control": 5}
            for key in dim_max_scores:
                scores = dim_score_map.get(key, [])
                avg = round(sum(scores) / len(scores)) if scores else 0
                critique_dim_scores.append({"key": key, "score": avg, "max_score": dim_max_scores[key], "reason": ""})
        critique_advice = list(crit_advice_set)[:5]
    elif any(t.status == "submitted" for t in critique_tasks_status):
        critique_module_status = "submitted"

    critique_module_score = schemas.DashboardModuleScore(
        status=critique_module_status,
        total_score=best_critique_score,
        dimension_scores=critique_dim_scores,
        improvement_advice=critique_advice,
        evaluated_at=best_critique_eval_at,
    )

    # --- 真实性模块 ---
    authenticity_tasks_status: List[schemas.DashboardAuthenticityTaskStatus] = []
    best_auth_score: Optional[int] = None
    best_auth_eval_at: Optional[Any] = None
    auth_dim_scores: List[Dict[str, Any]] = []
    auth_advice: List[str] = []
    auth_module_status = "not_started"

    all_auth_tasks = db.query(models.AuthenticityTask).order_by(models.AuthenticityTask.id.asc()).all()
    for task in all_auth_tasks:
        it_count = db.query(models.AuthenticityIteration).filter(
            models.AuthenticityIteration.task_id == task.id,
            models.AuthenticityIteration.student_id == student_id,
        ).count()

        if it_count < 3:
            it_hint = f"建议至少提交3个版本再评估（当前{it_count}个）"
        else:
            it_hint = "迭代数已满足最低要求"

        task_status = "not_started"
        task_score: Optional[int] = None
        task_eval_at = None

        if it_count > 0:
            eval_record = db.query(models.EvaluationRecord).filter(
                models.EvaluationRecord.student_id == student_id,
                models.EvaluationRecord.module_type == "authenticity",
                models.EvaluationRecord.target_id == task.id,
                models.EvaluationRecord.status.in_(SUCCESS_STATUSES),
            ).order_by(models.EvaluationRecord.created_at.desc()).first()

            if eval_record:
                task_status = "evaluated"
                task_score = eval_record.total_score
                task_eval_at = eval_record.created_at
            else:
                task_status = "submitted"

        authenticity_tasks_status.append(schemas.DashboardAuthenticityTaskStatus(
            task_id=task.id,
            task_title=task.title,
            status=task_status,
            iteration_count=it_count,
            iteration_hint=it_hint,
            total_score=task_score,
            evaluated_at=task_eval_at,
        ))

    evaluated_auth_task = [t for t in authenticity_tasks_status if t.status == "evaluated"]
    if evaluated_auth_task:
        auth_module_status = "evaluated"
        avg_auth_score = round(sum(t.total_score or 0 for t in evaluated_auth_task) / len(evaluated_auth_task))
        best_auth_score = avg_auth_score
        best_auth_eval_at = max(evaluated_auth_task, key=lambda t: t.evaluated_at or datetime.min).evaluated_at

        auth_dim_map: Dict[str, List[int]] = {}
        auth_advice_set: set = set()
        for et in evaluated_auth_task:
            rec = db.query(models.EvaluationRecord).filter(
                models.EvaluationRecord.student_id == student_id,
                models.EvaluationRecord.module_type == "authenticity",
                models.EvaluationRecord.target_id == et.task_id,
                models.EvaluationRecord.status.in_(SUCCESS_STATUSES),
            ).order_by(models.EvaluationRecord.created_at.desc()).first()
            if rec and rec.result_json:
                result = rec.result_json
                for ds in result.get("dimension_scores", []):
                    auth_dim_map.setdefault(ds.get("key", ""), []).append(ds.get("score", 0))
                for adv in result.get("improvement_advice", []):
                    if adv:
                        auth_advice_set.add(adv)
        if auth_dim_map:
            auth_dim_scores = []
            auth_max_scores = {"iteration_evidence": 20, "process_transparency": 25, "critical_engagement": 25, "reflection_quality": 20, "ai_collab_literacy": 10}
            for key in auth_max_scores:
                scores = auth_dim_map.get(key, [])
                avg = round(sum(scores) / len(scores)) if scores else 0
                auth_dim_scores.append({"key": key, "score": avg, "max_score": auth_max_scores[key], "reason": ""})
        auth_advice = list(auth_advice_set)[:5]
    elif any(t.status == "submitted" for t in authenticity_tasks_status):
        auth_module_status = "submitted"

    auth_module_score = schemas.DashboardModuleScore(
        status=auth_module_status,
        total_score=best_auth_score,
        dimension_scores=auth_dim_scores,
        improvement_advice=auth_advice,
        evaluated_at=best_auth_eval_at,
    )

    # --- 拓扑模块 ---
    topology_exists = db.query(models.TopologySubmission).filter(
        models.TopologySubmission.student_id == student_id,
    ).first() is not None
    concept_status = "submitted" if topology_exists else "not_started"

    # --- 加权总分 ---
    composite_score = None
    if best_critique_score is not None and best_auth_score is not None:
        composite_score = round(best_critique_score * critique_weight + best_auth_score * authenticity_weight)

    return schemas.DashboardResponse(
        student_id=student_id,
        student_name=student.name,
        composite_score=composite_score,
        critique_weight=critique_weight,
        authenticity_weight=authenticity_weight,
        critique=critique_module_score,
        critique_tasks=critique_tasks_status,
        authenticity=auth_module_score,
        authenticity_tasks=authenticity_tasks_status,
        concept_status=concept_status,
    )


# ==========================================
# 模块一：文本纠错 (快照覆写模式)
# ==========================================

# 【新增：补回前端需要的任务列表接口】
@app.get("/tasks", response_model=List[schemas.TaskOut])
def get_all_critique_tasks(db: Session = Depends(get_db)):
    """获取所有待批判的任务列表"""
    tasks = db.query(models.Task).order_by(models.Task.publish_date.asc()).all()
    return tasks


@app.get("/critique/{task_id}/{student_id}", response_model=schemas.CritiqueSubmissionOut)
def get_critique_submission(task_id: int, student_id: str, db: Session = Depends(get_db)):
    """拉取最新纠错记录，不存在则报404或由前端处理"""
    submission = db.query(models.CritiqueSubmission).filter(
        models.CritiqueSubmission.task_id == task_id,
        models.CritiqueSubmission.student_id == student_id
    ).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")
    return submission


@app.put("/critique/{task_id}/{student_id}", response_model=schemas.CritiqueSubmissionOut)
def upsert_critique_submission(
        task_id: int,
        student_id: str,
        payload: schemas.CritiqueSubmissionCreate,
        db: Session = Depends(get_db)
):
    """执行快照覆写逻辑"""
    verify_student_and_task(db, student_id, task_id, models.Task)

    submission = db.query(models.CritiqueSubmission).filter(
        models.CritiqueSubmission.task_id == task_id,
        models.CritiqueSubmission.student_id == student_id
    ).first()

    if submission:
        submission.critiques_data = payload.critiques_data
        submission.score = None
        submission.evaluation_report = None
    else:
        submission = models.CritiqueSubmission(
            task_id=task_id,
            student_id=student_id,
            critiques_data=payload.critiques_data
        )
        db.add(submission)

    db.commit()
    db.refresh(submission)
    return submission


@app.post("/api/tasks/{task_id}/evaluate/{student_id}", response_model=schemas.CritiqueSubmissionOut)
def evaluate_critique_submission(task_id: int, student_id: str, db: Session = Depends(get_db)):
    """
    文本纠错评分评估引擎
    注意：此操作为同步阻塞调用。仅限MVP阶段使用。
    """
    submission = None
    task = None
    target_id = task_id
    input_snapshot: Dict[str, Any] = {
        "task": {"id": task_id},
        "submission": {"student_id": student_id},
    }
    model_name: Optional[str] = None

    try:
        _, task = verify_student_and_task(db, student_id, task_id, models.Task)
        input_snapshot["task"].update({
            "title": task.title,
            "content": task.content,
            "preset_errors": task.preset_errors or [],
        })

        if not task.preset_errors:
            raise HTTPException(status_code=400, detail="该任务尚未配置预设错误，无法评估。")

        submission = db.query(models.CritiqueSubmission).filter(
            models.CritiqueSubmission.task_id == task_id,
            models.CritiqueSubmission.student_id == student_id,
        ).order_by(models.CritiqueSubmission.id.desc()).first()

        if not submission:
            raise HTTPException(status_code=404, detail="未找到该学生的提交记录 (Submission not found)")
        if not submission.critiques_data:
            raise HTTPException(status_code=400, detail="提交记录中没有纠错数据 (Empty critiques data)")

        # 缓存直返：已有评估结果则直接返回，不调 LLM
        if submission.evaluation_report is not None and submission.score is not None:
            return submission

        target_id = submission.id
        input_snapshot["submission"].update({
            "id": submission.id,
            "task_id": submission.task_id,
            "critiques_data": submission.critiques_data,
        })

        if is_local_scoring_mode():
            report, metadata = build_demo_fallback_evaluation(
                task=task,
                submission=submission,
                upstream_error_message="local scoring mode enabled",
                scoring_mode="local",
            )
            input_snapshot = metadata["input_snapshot"]
            model_name = metadata["model_name"]

            submission.score = report.total_score
            submission.evaluation_report = report.model_dump()

            create_evaluation_record(
                db,
                student_id=student_id,
                module_type="critique",
                target_id=target_id,
                status="success_local",
                rubric_version=metadata["rubric_version"],
                prompt_version=metadata["prompt_version"],
                model_name=model_name,
                input_snapshot_json=input_snapshot,
                result_json={
                    "report": report.model_dump(),
                    "fallback_reason": metadata["fallback_reason"],
                },
                total_score=report.total_score,
            )

            db.commit()
            db.refresh(submission)
            return submission

        report, metadata = run_critique_evaluation(task=task, submission=submission)
        input_snapshot = metadata["input_snapshot"]
        model_name = metadata["model_name"]

        submission.score = report.total_score
        submission.evaluation_report = report.model_dump()

        create_evaluation_record(
            db,
            student_id=student_id,
            module_type="critique",
            target_id=target_id,
            status="success",
            rubric_version=metadata["rubric_version"],
            prompt_version=metadata["prompt_version"],
            model_name=model_name,
            input_snapshot_json=input_snapshot,
            result_json=report.model_dump(),
            total_score=report.total_score,
        )

        db.commit()
        db.refresh(submission)
        return submission
    except HTTPException as exc:
        db.rollback()
        create_evaluation_record(
            db,
            student_id=student_id,
            module_type="critique",
            target_id=target_id,
            status="failed",
            rubric_version=CRITIQUE_RUBRIC_VERSION,
            prompt_version=CRITIQUE_PROMPT_VERSION,
            model_name=model_name,
            input_snapshot_json=input_snapshot,
            result_json={"error": exc.detail},
            total_score=None,
        )
        db.commit()
        raise
    except CritiqueEvaluationError as exc:
        db.rollback()
        if task is not None and submission is not None and should_use_demo_fallback(exc):
            report, metadata = build_demo_fallback_evaluation(
                task=task,
                submission=submission,
                upstream_error_message=str(exc),
                scoring_mode="fallback",
            )

            submission.score = report.total_score
            submission.evaluation_report = report.model_dump()

            create_evaluation_record(
                db,
                student_id=student_id,
                module_type="critique",
                target_id=target_id,
                status="success_fallback",
                rubric_version=metadata["rubric_version"],
                prompt_version=metadata["prompt_version"],
                model_name=metadata["model_name"],
                input_snapshot_json=metadata["input_snapshot"],
                result_json={
                    "report": report.model_dump(),
                    "fallback_reason": metadata["fallback_reason"],
                },
                total_score=report.total_score,
            )

            db.commit()
            db.refresh(submission)
            return submission

        create_evaluation_record(
            db,
            student_id=student_id,
            module_type="critique",
            target_id=target_id,
            status="failed",
            rubric_version=CRITIQUE_RUBRIC_VERSION,
            prompt_version=CRITIQUE_PROMPT_VERSION,
            model_name=exc.model_name or model_name,
            input_snapshot_json=exc.input_snapshot or input_snapshot,
            result_json={"error": str(exc), "raw_response": exc.raw_response},
            total_score=None,
        )
        db.commit()
        raise HTTPException(status_code=exc.upstream_status_code or 502, detail=f"批判评分失败：{exc}")
    except Exception as exc:
        db.rollback()
        create_evaluation_record(
            db,
            student_id=student_id,
            module_type="critique",
            target_id=target_id,
            status="failed",
            rubric_version=CRITIQUE_RUBRIC_VERSION,
            prompt_version=CRITIQUE_PROMPT_VERSION,
            model_name=model_name,
            input_snapshot_json=input_snapshot,
            result_json={"error": str(exc)},
            total_score=None,
        )
        db.commit()
        raise HTTPException(status_code=500, detail=f"评分服务异常：{exc}")


# ... （下方保留模块二和模块三的原有代码，注意不要删掉它们！）...
# ==========================================
# 模块二：概念拓扑图 (画布状态持久化)
# ==========================================
@app.get("/topology/{task_id}/{student_id}", response_model=schemas.TopologySubmissionOut)
def get_topology_submission(task_id: int, student_id: str, db: Session = Depends(get_db)):
    submission = db.query(models.TopologySubmission).filter(
        models.TopologySubmission.task_id == task_id,
        models.TopologySubmission.student_id == student_id
    ).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topology submission not found.")
    return submission


@app.put("/topology/{task_id}/{student_id}", response_model=schemas.TopologySubmissionOut)
def upsert_topology_submission(
        task_id: int,
        student_id: str,
        payload: schemas.TopologySubmissionCreate,
        db: Session = Depends(get_db)
):
    verify_student_and_task(db, student_id, task_id, models.TopologyTask)

    submission = db.query(models.TopologySubmission).filter(
        models.TopologySubmission.task_id == task_id,
        models.TopologySubmission.student_id == student_id
    ).first()

    if submission:
        submission.raw_flow_data = payload.raw_flow_data
        submission.adjacency_list = payload.adjacency_list
    else:
        submission = models.TopologySubmission(
            task_id=task_id,
            student_id=student_id,
            raw_flow_data=payload.raw_flow_data,
            adjacency_list=payload.adjacency_list
        )
        db.add(submission)

    db.commit()
    db.refresh(submission)
    return submission


# ==========================================
# 模块三：真实性任务工作台 (迭代版本控制)
# ==========================================
@app.get("/authenticity/{task_id}/{student_id}", response_model=List[schemas.AuthenticityIterationOut])
def list_authenticity_iterations(task_id: int, student_id: str, db: Session = Depends(get_db)):
    iterations = db.query(models.AuthenticityIteration).filter(
        models.AuthenticityIteration.task_id == task_id,
        models.AuthenticityIteration.student_id == student_id
    ).order_by(models.AuthenticityIteration.version_number.desc()).all()
    return iterations


@app.post("/authenticity/{task_id}/{student_id}", response_model=schemas.AuthenticityIterationOut)
def create_authenticity_iteration(
        task_id: int,
        student_id: str,
        payload: schemas.AuthenticityIterationCreate,
        db: Session = Depends(get_db)
):
    verify_student_and_task(db, student_id, task_id, models.AuthenticityTask)
    max_version = db.query(func.max(models.AuthenticityIteration.version_number)).filter(
        models.AuthenticityIteration.task_id == task_id,
        models.AuthenticityIteration.student_id == student_id
    ).scalar()
    next_version = 1 if max_version is None else max_version + 1

    new_iteration = models.AuthenticityIteration(
        task_id=task_id,
        student_id=student_id,
        version_number=next_version,
        deliverable_payload=payload.deliverable_payload,
        collaboration_matrix=[stage.model_dump() for stage in payload.collaboration_matrix],
        tools_used=payload.tools_used,
        reflection_log=payload.reflection_log
    )
    db.add(new_iteration)
    db.commit()
    db.refresh(new_iteration)
    return new_iteration


@app.post("/api/authenticity/{task_id}/evaluate/{student_id}", response_model=schemas.AuthenticityEvaluationReport)
def evaluate_authenticity_submission_endpoint(task_id: int, student_id: str, db: Session = Depends(get_db)):
    """
    真实性任务自动评分
    """
    target_id = task_id
    task = None
    iterations = None
    input_snapshot: Dict[str, Any] = {
        "task": {"id": task_id},
        "iterations_summary": {"student_id": student_id},
    }
    model_name: Optional[str] = None

    try:
        _, task = verify_student_and_task(db, student_id, task_id, models.AuthenticityTask)
        input_snapshot["task"].update({
            "title": task.title,
            "context_description": task.context_description,
            "evaluation_criteria": task.evaluation_criteria,
        })

        iterations = db.query(models.AuthenticityIteration).filter(
            models.AuthenticityIteration.task_id == task_id,
            models.AuthenticityIteration.student_id == student_id,
        ).order_by(models.AuthenticityIteration.version_number.asc()).all()

        if not iterations:
            raise HTTPException(status_code=400, detail="该学生此任务无迭代记录，无法评分。")

        # 缓存直返：比对 version_count，一致则返回已有评分结果
        current_version_count = len(iterations)
        latest_eval = db.query(models.EvaluationRecord).filter(
            models.EvaluationRecord.student_id == student_id,
            models.EvaluationRecord.module_type == "authenticity",
            models.EvaluationRecord.status.in_(["success", "success_local", "success_fallback"]),
        ).order_by(models.EvaluationRecord.created_at.desc()).first()

        if latest_eval and latest_eval.result_json:
            cached_snapshot = latest_eval.input_snapshot_json or {}
            cached_versions = cached_snapshot.get("version_count", len(cached_snapshot.get("iterations", [])))
            if cached_versions == current_version_count and current_version_count > 0:
                return latest_eval.result_json

        if is_authenticity_local_scoring_mode():
            report, metadata = build_authenticity_local_evaluation(
                task=task,
                iterations=iterations,
                upstream_error_message="local scoring mode enabled",
                scoring_mode="local",
            )
            input_snapshot = metadata["input_snapshot"]
            model_name = metadata["model_name"]

            create_evaluation_record(
                db,
                student_id=student_id,
                module_type="authenticity",
                target_id=target_id,
                status="success_local",
                rubric_version=metadata["rubric_version"],
                prompt_version=metadata["prompt_version"],
                model_name=model_name,
                input_snapshot_json=input_snapshot,
                result_json=report.model_dump(),
                total_score=report.total_score,
            )

            db.commit()
            return report.model_dump()

        report, metadata = evaluate_authenticity_submission(task=task, iterations=iterations)
        input_snapshot = metadata["input_snapshot"]
        model_name = metadata["model_name"]

        create_evaluation_record(
            db,
            student_id=student_id,
            module_type="authenticity",
            target_id=target_id,
            status="success",
            rubric_version=metadata["rubric_version"],
            prompt_version=metadata["prompt_version"],
            model_name=model_name,
            input_snapshot_json=input_snapshot,
            result_json=report.model_dump(),
            total_score=report.total_score,
        )

        db.commit()
        return report.model_dump()

    except HTTPException as exc:
        db.rollback()
        create_evaluation_record(
            db,
            student_id=student_id,
            module_type="authenticity",
            target_id=target_id,
            status="failed",
            rubric_version=AUTHENTICITY_RUBRIC_VERSION,
            prompt_version=AUTHENTICITY_PROMPT_VERSION,
            model_name=model_name,
            input_snapshot_json=input_snapshot,
            result_json={"error": exc.detail},
            total_score=None,
        )
        db.commit()
        raise
    except AuthenticityEvaluationError as exc:
        db.rollback()
        if task is not None and iterations is not None and should_use_authenticity_fallback(exc):
            report, metadata = build_authenticity_local_evaluation(
                task=task,
                iterations=iterations,
                upstream_error_message=str(exc),
                scoring_mode="fallback",
            )

            create_evaluation_record(
                db,
                student_id=student_id,
                module_type="authenticity",
                target_id=target_id,
                status="success_fallback",
                rubric_version=metadata["rubric_version"],
                prompt_version=metadata["prompt_version"],
                model_name=metadata["model_name"],
                input_snapshot_json=metadata["input_snapshot"],
                result_json=report.model_dump(),
                total_score=report.total_score,
            )

            db.commit()
            return report.model_dump()

        create_evaluation_record(
            db,
            student_id=student_id,
            module_type="authenticity",
            target_id=target_id,
            status="failed",
            rubric_version=AUTHENTICITY_RUBRIC_VERSION,
            prompt_version=AUTHENTICITY_PROMPT_VERSION,
            model_name=exc.model_name or model_name,
            input_snapshot_json=exc.input_snapshot or input_snapshot,
            result_json={"error": str(exc), "raw_response": exc.raw_response},
            total_score=None,
        )
        db.commit()
        raise HTTPException(status_code=exc.upstream_status_code or 502, detail=f"真实性评分失败：{exc}")
    except Exception as exc:
        db.rollback()
        create_evaluation_record(
            db,
            student_id=student_id,
            module_type="authenticity",
            target_id=target_id,
            status="failed",
            rubric_version=AUTHENTICITY_RUBRIC_VERSION,
            prompt_version=AUTHENTICITY_PROMPT_VERSION,
            model_name=model_name,
            input_snapshot_json=input_snapshot,
            result_json={"error": str(exc)},
            total_score=None,
        )
        db.commit()
        raise HTTPException(status_code=500, detail=f"评分服务异常：{exc}")
