from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


# --- 模块 1: 内容批判 (原有) ---
class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    preset_errors = Column(JSON, default=list)


class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    student_id = Column(String, index=True)
    critiques = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    task = relationship("Task")


# --- 模块 2: 拓扑构筑 (新增) ---
class TopologyTask(Base):
    """
    拓扑任务表：例如 "构建一个包含核心层、汇聚层、接入层的校园网"
    """
    __tablename__ = "topology_tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)  # 任务描述
    # 预设的标准答案（用于自动对比），存邻接表或标准JSON
    standard_graph = Column(JSON, nullable=True)


class TopologySubmission(Base):
    """
    拓扑提交表：存学生画的图
    """
    __tablename__ = "topology_submissions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("topology_tasks.id"))
    student_id = Column(String, index=True)

    # 核心数据：前端传来的 ReactFlow 原始数据（用于回放）
    raw_flow_data = Column(JSON)

    # 分析数据：前端转换好的“邻接表”（用于评分）
    # 格式示例: [{"source": "CoreSwitch", "target": "Firewall", "relation": "connects"}]
    adjacency_list = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("TopologyTask")