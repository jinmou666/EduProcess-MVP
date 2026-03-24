from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import json

from . import models, schemas, database

# 初始化数据库结构
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="EduProcess API System")


def call_llm(prompt: str) -> str:
    """
    Mock LLM 辅助函数。
    【架构师警告】：生产环境下，强烈建议为这里的模型请求配置 JSON 约束 (例如 OpenAI 的 response_format={"type": "json_object"})
    并设置 temperature=0.1 左右以保证确定性。
    """
    # 模拟 LLM 思考后的返回。硬编码一个合规的 JSON。
    mock_response = {
        "total_score": 75,
        "overall_feedback": "你找出了大部分明显错误，但在深层次的理论解释上还缺乏精确度。有1处预设错误被遗漏。",
        "details": [
            {
                "step1_match": "成功匹配到预设错误：'核心概念混淆'",
                "step2_score": 85,
                "step2_feedback": "纠错理由基本正确，但表述略显啰嗦。"
            },
            {
                "step1_match": "未找到预设错误：'分析方法错误'",
                "step2_score": 0,
                "step2_feedback": "未能指出文章分析逻辑的根本漏洞，扣除相应分数。"
            }
        ]
    }
    return json.dumps(mock_response, ensure_ascii=False)


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


def verify_student_and_task(db: Session, student_id: str, task_id: int, task_model: models.Base):
    student = db.query(models.Student).filter(models.Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student {student_id} not found.")
    task = db.query(task_model).filter(task_model.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found.")
    return student, task


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
def evaluate_critique_submission(task_id: int, student_id: int, db: Session = Depends(get_db)):
    """
    文本纠错评分评估引擎
    注意：此操作为同步阻塞调用。仅限MVP阶段使用。
    """
    # 1. 提取任务及老师预设的错误
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="未找到该任务 (Task not found)")
    if not task.preset_errors:
        raise HTTPException(status_code=400, detail="该任务尚未配置预设错误，无法评估。")

    # 2. 提取学生最新的纠错提交
    # 使用 order_by(desc) 确保在有多次提交时，抓取的是最新版本
    submission = db.query(models.CritiqueSubmission).filter(
        models.CritiqueSubmission.task_id == task_id,
        models.CritiqueSubmission.student_id == student_id
    ).order_by(models.CritiqueSubmission.id.desc()).first()

    if not submission:
        raise HTTPException(status_code=404, detail="未找到该学生的提交记录 (Submission not found)")
    if not submission.critiques_data:
        raise HTTPException(status_code=400, detail="提交记录中没有纠错数据 (Empty critiques data)")

    # 3. 组装复杂的 Prompt 逻辑
    prompt = f"""
你是一个极其严厉且客观的评分引擎。请将学生提交的纠错数据与老师的预设标准进行对比评估。

【老师的预设错误 (Preset Errors)】:
{json.dumps(task.preset_errors, ensure_ascii=False)}

【学生的纠错提交 (Student Critiques)】:
{json.dumps(submission.critiques_data, ensure_ascii=False)}

请执行以下逻辑并严格输出纯 JSON 格式：
- 步骤 1 (匹配)：分析学生的纠错内容，判断其是否对应了老师预设的某一个错误。如果学生指出了预设以外的“无效错误”，忽略不计。
- 步骤 2 (评分)：针对匹配上的错误，对比学生的“更正内容/理论依据”与老师的“标准更正”，给出 0-100 的质量分，并附上简短评语。
- 步骤 3 (汇总)：发现学生未找出的预设错误，重度扣分。最后计算最终的 total_score (0-100) 并给出 overall_feedback。

要求：绝对不要输出任何 Markdown 标记（例如 ```json）以及多余解释。必须输出以下结构：
{{
    "total_score": int,
    "overall_feedback": "string",
    "details": [
        {{
            "step1_match": "string",
            "step2_score": int,
            "step2_feedback": "string"
        }}
    ]
}}
    """

    # 4. 调用大模型（当前为Mock）
    llm_result_str = call_llm(prompt)

    # 5. 防御性解析 (容忍部分大模型喜欢加前缀的坏习惯)
    try:
        clean_json_str = llm_result_str.strip()
        if clean_json_str.startswith("```json"):
            clean_json_str = clean_json_str[7:]
        if clean_json_str.endswith("```"):
            clean_json_str = clean_json_str[:-3]

        evaluation_report = json.loads(clean_json_str)
    except json.JSONDecodeError:
        # 现实情况中，一旦报错你连重试机制都没有，这里只能直接阻断
        raise HTTPException(
            status_code=502,
            detail="大模型返回了无法解析的异常数据，评估引擎故障。"
        )

    # 6. 数据持久化
    # 提取总分，默认保底为 0
    submission.score = evaluation_report.get("total_score", 0)
    submission.evaluation_report = evaluation_report

    db.commit()
    db.refresh(submission)

    return submission


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
        collaboration_matrix=[stage.dict() for stage in payload.collaboration_matrix],
        tools_used=payload.tools_used,
        reflection_log=payload.reflection_log
    )
    db.add(new_iteration)
    db.commit()
    db.refresh(new_iteration)
    return new_iteration