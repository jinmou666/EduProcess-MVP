from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

# --- 基础组件模型 (原有) ---
class CritiqueItem(BaseModel):
    quote: str
    rewrite: str
    citation: str
    selection_range: List[int]

# --- Task 相关 (原有) ---
class TaskBase(BaseModel):
    title: str
    content: Optional[str] = None

class TaskOut(TaskBase):
    id: int
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

# ==========================================
# 新增：拓扑构筑相关模型
# ==========================================

class AdjacencyItem(BaseModel):
    source: str
    target: str
    relation: str = "connects"

class TopologySubmissionCreate(BaseModel):
    """
    匹配前端 ConceptMap.tsx 发送的 payload
    """
    task_id: int
    student_id: str
    # 原始 React Flow 数据 (用于回放/重建画布)
    raw_flow_data: Dict[str, Any]
    # 清洗后的邻接表 (用于算法比对)
    adjacency_list: List[AdjacencyItem]

class TopologySubmissionOut(BaseModel):
    id: int
    status: str
    saved_file: str # 告诉前端文件存哪了
    class Config:
        orm_mode = True