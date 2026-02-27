from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime


# --- 基础组件模型 (原有) ---
class CritiqueItem(BaseModel):
    quote: str
    rewrite: str
    citation: str
    selection_range: List[int]


# --- Task 相关 (拓展) ---
class TaskBase(BaseModel):
    title: str
    content: Optional[str] = None


class TaskOut(TaskBase):
    id: int
    publish_date: Optional[datetime] = None
    deadline: Optional[datetime] = None

    class Config:
        orm_mode = True


# --- Submission 相关 (原有) ---
class SubmissionCreate(BaseModel):
    task_id: int
    student_id: str
    critiques: List[CritiqueItem]


class SubmissionOut(SubmissionCreate):
    id: int
    created_at: Any

    class Config:
        orm_mode = True


# --- 拓扑构筑相关模型 (原有) ---
class AdjacencyItem(BaseModel):
    source: str
    target: str
    relation: str = "connects"


class TopologySubmissionCreate(BaseModel):
    task_id: int
    student_id: str
    raw_flow_data: Dict[str, Any]
    adjacency_list: List[AdjacencyItem]


class TopologySubmissionOut(BaseModel):
    id: int
    status: str
    saved_file: str

    class Config:
        orm_mode = True