from pydantic import BaseModel
from typing import List, Optional, Any

# --- 基础组件模型 ---

class CritiqueItem(BaseModel):
    """前端传来的单个纠错点"""
    quote: str          # 选中的错误原文
    rewrite: str        # 学生的重写
    citation: str       # 理论依据
    selection_range: List[int] # 高亮位置 [start_index, end_index]

# --- Task 相关 ---

class TaskBase(BaseModel):
    title: str
    content: str

class TaskCreate(TaskBase):
    preset_errors: List[Any] = []

class TaskOut(TaskBase):
    id: int
    # 在做题界面，通常不把 preset_errors (答案) 返回给前端，防止作弊
    # 但如果是练习模式，可能需要。这里MVP暂时不返回。

    class Config:
        orm_mode = True

# --- Submission 相关 ---

class SubmissionCreate(BaseModel):
    """学生提交时的请求体"""
    task_id: int
    student_id: str
    critiques: List[CritiqueItem]

class SubmissionOut(SubmissionCreate):
    id: int
    created_at: Any

    class Config:
        orm_mode = True