from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from . import models, schemas, database

# 初始化数据库表（如果不存在则创建）
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="EduProcess AI Critique API")

# --- 关键：配置 CORS ---
# 如果不配这个，你的前端浏览器会拦截请求。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，演示期间图省事。生产环境要改。
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 接口实现 ---

@app.get("/")
def read_root():
    return {"message": "EduProcess Backend is Running. Focus on the critique module."}


@app.get("/tasks/{task_id}", response_model=schemas.TaskOut)
def get_task(task_id: int, db: Session = Depends(database.get_db)):
    """
    获取指定ID的题目内容。
    """
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/submit", response_model=schemas.SubmissionOut)
def submit_critique(submission: schemas.SubmissionCreate, db: Session = Depends(database.get_db)):
    """
    接收学生的纠错提交。
    """
    # 验证任务是否存在
    task = db.query(models.Task).filter(models.Task.id == submission.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 将Pydantic模型转为JSON兼容的字典列表
    critiques_data = [item.dict() for item in submission.critiques]

    db_submission = models.Submission(
        task_id=submission.task_id,
        student_id=submission.student_id,
        critiques=critiques_data
    )

    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)

    return db_submission


if __name__ == "__main__":
    # 方便直接右键运行 main.py 调试
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)