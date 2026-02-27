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

    # 新增字段：支持任务列表显示
    publish_date = Column(DateTime, default=datetime.utcnow)
    deadline = Column(DateTime, nullable=True)


class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    student_id = Column(String, index=True)
    critiques = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    task = relationship("Task")


# --- 模块 2: 拓扑构筑 (原有) ---
class TopologyTask(Base):
    __tablename__ = "topology_tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    standard_graph = Column(JSON, nullable=True)


class TopologySubmission(Base):
    __tablename__ = "topology_submissions"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("topology_tasks.id"))
    student_id = Column(String, index=True)
    raw_flow_data = Column(JSON)
    adjacency_list = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    task = relationship("TopologyTask")