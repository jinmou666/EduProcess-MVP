from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any, Dict
from datetime import datetime


# ==========================================
# 全局实体 Schemas
# ==========================================
class StudentBase(BaseModel):
    student_id: str
    name: str


class StudentOut(StudentBase):
    created_at: datetime

    class Config:
        orm_mode = True


# ==========================================
# 模块一：文本纠错 (Text Critique)
# ==========================================
class TaskOut(BaseModel):
    """用于前端列表展示的任务模型"""
    id: int
    title: str
    content: str
    publish_date: datetime
    deadline: Optional[datetime] = None
    preset_errors: List[Dict[str, Any]] = []

    class Config:
        orm_mode = True


class CritiqueSubmissionCreate(BaseModel):
    critiques_data: List[Dict[str, Any]] = Field(default_factory=list, description="黑盒化的全量纠错数组")


class CritiqueSubmissionOut(BaseModel):
    id: int
    task_id: int
    student_id: str
    critiques_data: List[Dict[str, Any]]
    updated_at: datetime

    score: Optional[int] = None
    evaluation_report: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


# ==========================================
# 模块二：概念拓扑图 (Topology Construction)
# ==========================================
class TopologySubmissionCreate(BaseModel):
    raw_flow_data: Dict[str, Any] = Field(..., description="前端 ReactFlow 完整状态数据")
    adjacency_list: List[Dict[str, Any]] = Field(default_factory=list, description="后端分析用的邻接表")


class TopologySubmissionOut(BaseModel):
    id: int
    task_id: int
    student_id: str
    raw_flow_data: Dict[str, Any]
    adjacency_list: List[Dict[str, Any]]
    last_saved_at: datetime

    class Config:
        orm_mode = True


# ==========================================
# 模块三：真实性任务工作台 (Authenticity Task Workspace)
# ==========================================
class CollaborationStage(BaseModel):
    stageName: str
    humanPercent: int = Field(ge=0, le=100)
    aiPercent: int = Field(ge=0, le=100)

    @validator('aiPercent')
    def check_percent_sum(cls, v, values):
        if 'humanPercent' in values and values['humanPercent'] + v != 100:
            raise ValueError('Human percent and AI percent must sum to 100')
        return v


class AuthenticityIterationCreate(BaseModel):
    deliverable_payload: str = Field(..., description="外部URL或代码仓链接")
    collaboration_matrix: List[CollaborationStage] = Field(..., description="各阶段人机贡献比例")
    tools_used: List[str] = Field(default_factory=list)
    reflection_log: str = Field(..., min_length=50, description="强制反思验证，不少于50字")


class AuthenticityIterationOut(BaseModel):
    id: int
    task_id: int
    student_id: str
    version_number: int
    created_at: datetime
    deliverable_payload: str
    collaboration_matrix: List[Dict[str, Any]]
    tools_used: List[str]
    reflection_log: str

    class Config:
        orm_mode = True