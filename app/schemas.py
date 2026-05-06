from pydantic import BaseModel, ConfigDict, Field, root_validator, validator
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

    model_config = ConfigDict(from_attributes=True)


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
    preset_errors: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CritiqueSubmissionCreate(BaseModel):
    critiques_data: List[Dict[str, Any]] = Field(default_factory=list, description="黑盒化的全量纠错数组")


class CritiqueDimensionScore(BaseModel):
    key: str
    score: int = Field(ge=0)
    max_score: int = Field(ge=0)
    reason: str = ""


class CritiqueEvaluationDetail(BaseModel):
    error_id: Optional[str] = None
    matched: bool = False
    step1_match: str
    step2_score: int = Field(ge=0, le=100)
    step2_feedback: str


class CritiqueEvaluationReport(BaseModel):
    rubric_version: str
    total_score: int = Field(ge=0, le=100)
    overall_feedback: str
    dimension_scores: List[CritiqueDimensionScore]
    details: List[CritiqueEvaluationDetail]
    missed_error_ids: List[str] = Field(default_factory=list)
    invalid_critiques: List[Dict[str, Any]] = Field(default_factory=list)
    improvement_advice: List[str] = Field(default_factory=list)

    @validator("rubric_version")
    def validate_rubric_version(cls, value):
        if value != "critique_rubric_v1":
            raise ValueError("rubric_version must be critique_rubric_v1")
        return value

    @validator("dimension_scores")
    def validate_dimension_scores(cls, value):
        expected_max_scores = {
            "coverage": 35,
            "correction_accuracy": 30,
            "reasoning_quality": 20,
            "alignment_precision": 10,
            "noise_control": 5,
        }

        received = {}
        for item in value:
            if item.key not in expected_max_scores:
                raise ValueError(f"Unsupported dimension key: {item.key}")
            if item.max_score != expected_max_scores[item.key]:
                raise ValueError(f"Dimension {item.key} max_score must be {expected_max_scores[item.key]}")
            if item.score > item.max_score:
                raise ValueError(f"Dimension {item.key} score cannot exceed max_score")
            if item.key in received:
                raise ValueError(f"Duplicate dimension key: {item.key}")
            received[item.key] = item.score

        if set(received.keys()) != set(expected_max_scores.keys()):
            raise ValueError("dimension_scores must contain all fixed critique dimensions")

        return value

    @root_validator(skip_on_failure=True)
    def validate_total_score(cls, values):
        dimension_scores = values.get("dimension_scores") or []
        if dimension_scores:
            dimension_total = sum(item.score for item in dimension_scores)
            if values.get("total_score") != dimension_total:
                raise ValueError("total_score must equal the sum of dimension_scores")
        return values


class CritiqueSubmissionOut(BaseModel):
    id: int
    task_id: int
    student_id: str
    critiques_data: List[Dict[str, Any]]
    updated_at: datetime

    score: Optional[int] = None
    evaluation_report: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 模块三：真实性任务工作台 (Authenticity Task Workspace)
# ==========================================
class CollaborationStage(BaseModel):
    stageName: str
    humanPercent: int = Field(ge=0, le=100)
    aiPercent: int = Field(ge=0, le=100)
    tools: List[str] = Field(default_factory=list)

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

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 模块三：真实性任务评分 (Authenticity Evaluation)
# ==========================================
class AuthenticityDimensionScore(BaseModel):
    key: str
    score: int = Field(ge=0)
    max_score: int = Field(ge=0)
    reason: str = ""


class AuthenticityEvaluationReport(BaseModel):
    rubric_version: str
    total_score: int = Field(ge=0, le=100)
    overall_feedback: str
    dimension_scores: List[AuthenticityDimensionScore]
    improvement_advice: List[str] = Field(default_factory=list)

    @validator("rubric_version")
    def validate_rubric_version(cls, value):
        if value != "authenticity_rubric_v1":
            raise ValueError("rubric_version must be authenticity_rubric_v1")
        return value

    @validator("dimension_scores")
    def validate_dimension_scores(cls, value):
        expected = {
            "iteration_evidence": 20,
            "process_transparency": 25,
            "critical_engagement": 25,
            "reflection_quality": 20,
            "ai_collab_literacy": 10,
        }
        received = {}
        for item in value:
            if item.key not in expected:
                raise ValueError(f"Unsupported dimension key: {item.key}")
            if item.max_score != expected[item.key]:
                raise ValueError(f"{item.key} max_score must be {expected[item.key]}")
            if item.score > item.max_score:
                raise ValueError(f"{item.key} score cannot exceed max_score")
            if item.key in received:
                raise ValueError(f"Duplicate dimension key: {item.key}")
            received[item.key] = item.score
        if set(received.keys()) != set(expected.keys()):
            raise ValueError("dimension_scores must contain all 5 authenticity dimensions")
        return value

    @root_validator(skip_on_failure=True)
    def validate_total_score(cls, values):
        dimension_scores = values.get("dimension_scores") or []
        if dimension_scores:
            total = sum(item.score for item in dimension_scores)
            if values.get("total_score") != total:
                raise ValueError("total_score must equal sum of dimension_scores")
        return values


# ==========================================
# 仪表盘聚合 (Dashboard)
# ==========================================
class DashboardCritiqueTaskStatus(BaseModel):
    task_id: int
    task_title: str
    status: str
    total_score: Optional[int] = None
    evaluated_at: Optional[datetime] = None


class DashboardAuthenticityTaskStatus(BaseModel):
    task_id: int
    task_title: str
    status: str
    iteration_count: int = 0
    iteration_hint: str = ""
    total_score: Optional[int] = None
    evaluated_at: Optional[datetime] = None


class DashboardModuleScore(BaseModel):
    status: str
    total_score: Optional[int] = None
    dimension_scores: List[Dict[str, Any]] = Field(default_factory=list)
    improvement_advice: List[str] = Field(default_factory=list)
    evaluated_at: Optional[datetime] = None


class DashboardResponse(BaseModel):
    student_id: str
    student_name: str
    composite_score: Optional[int] = None
    critique_weight: float = 0.4
    authenticity_weight: float = 0.6
    critique: DashboardModuleScore
    critique_tasks: List[DashboardCritiqueTaskStatus] = Field(default_factory=list)
    authenticity: DashboardModuleScore
    authenticity_tasks: List[DashboardAuthenticityTaskStatus] = Field(default_factory=list)
    concept_status: str = "not_started"
