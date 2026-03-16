from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from fastapi.middleware.cors import CORSMiddleware

from . import models, schemas, database

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