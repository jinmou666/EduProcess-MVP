from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import time
from typing import List
from . import models, schemas, database

# 1. 数据库初始化
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="EduProcess System API")

# 2. CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 依赖项
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 辅助函数 ---
UPLOAD_DIR = "submitted_topologies"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.get("/")
def root():
    return {"message": "EduProcess Backend Online"}


# ================= 模块 1: 批判 (Critique) =================

# 新增：获取任务列表接口
@app.get("/tasks", response_model=List[schemas.TaskOut])
def get_all_critique_tasks(db: Session = Depends(get_db)):
    # 按照发布时间升序排列（越早越靠前）
    tasks = db.query(models.Task).order_by(models.Task.publish_date.asc()).all()
    return tasks

@app.get("/tasks/{task_id}", response_model=schemas.TaskOut)
def get_critique_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.post("/submit", response_model=schemas.SubmissionOut)
def submit_critique(submission: schemas.SubmissionCreate, db: Session = Depends(get_db)):
    critiques_data = [item.dict() for item in submission.critiques]
    db_obj = models.Submission(
        task_id=submission.task_id,
        student_id=submission.student_id,
        critiques=critiques_data
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


# ================= 模块 2: 拓扑 (Topology) =================

@app.post("/topology/submit", response_model=schemas.TopologySubmissionOut)
def submit_topology(submission: schemas.TopologySubmissionCreate, db: Session = Depends(get_db)):
    adj_list_data = [item.dict() for item in submission.adjacency_list]
    db_obj = models.TopologySubmission(
        task_id=submission.task_id,
        student_id=submission.student_id,
        raw_flow_data=submission.raw_flow_data,
        adjacency_list=adj_list_data
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    filename = f"topology_{submission.student_id}_task{submission.task_id}.json"
    filepath = os.path.join(UPLOAD_DIR, filename)

    raw_nodes = submission.raw_flow_data.get('nodes', [])
    concepts_list = []
    for node in raw_nodes:
        label = node.get('data', {}).get('label', 'Unknown')
        concepts_list.append(label)
    concepts_list = list(set(concepts_list))

    file_content = {
        "meta": {
            "student_id": submission.student_id,
            "task_id": submission.task_id,
            "last_updated": int(time.time()),
            "db_id": db_obj.id
        },
        "concepts": concepts_list,
        "connections": adj_list_data
    }

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(file_content, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"文件保存失败: {e}")

    return {
        "id": db_obj.id,
        "status": "success",
        "saved_file": filename
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)