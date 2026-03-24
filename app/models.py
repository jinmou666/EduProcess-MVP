from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


# ==========================================
# 全局核心实体
# ==========================================
class Student(Base):
    __tablename__ = "students"

    # 业务主键，由学校或系统分配的学号/唯一ID
    student_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 反向关系映射（便于从学生对象直接查询其所有提交记录）
    critique_submissions = relationship("CritiqueSubmission", back_populates="student")
    topology_submissions = relationship("TopologySubmission", back_populates="student")
    authenticity_iterations = relationship("AuthenticityIteration", back_populates="student")


# ==========================================
# 模块一：文本纠错 (Text Critique)
# ==========================================
class Task(Base):
    """通用/纠错任务表"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    related_chapter = Column(String, nullable=True)
    publish_date = Column(DateTime, default=datetime.utcnow)
    deadline = Column(DateTime, nullable=True)
    preset_errors = Column(JSON, default=list)


class CritiqueSubmission(Base):
    """纠错提交记录（全量快照覆写模式）"""
    __tablename__ = "critique_submissions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    student_id = Column(String, ForeignKey("students.student_id"), nullable=False, index=True)

    # 黑盒化数据结构
    critiques_data = Column(JSON, default=list)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    score = Column(Integer, nullable=True, comment="LLM给出的最终总分")
    evaluation_report = Column(JSON, nullable=True, comment="LLM返回的详细匹配与打分报告(JSON)")

    # 关系映射
    student = relationship("Student", back_populates="critique_submissions")
    task = relationship("Task")


# ==========================================
# 模块二：概念拓扑图构筑 (Topology Construction)
# ==========================================
class TopologyTask(Base):
    """拓扑任务表"""
    __tablename__ = "topology_tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    standard_graph = Column(JSON, nullable=True)


class TopologySubmission(Base):
    """拓扑提交记录（画布状态持久化模式）"""
    __tablename__ = "topology_submissions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("topology_tasks.id"), nullable=False, index=True)
    student_id = Column(String, ForeignKey("students.student_id"), nullable=False, index=True)

    raw_flow_data = Column(JSON, nullable=False)
    adjacency_list = Column(JSON, nullable=False)
    last_saved_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系映射
    student = relationship("Student", back_populates="topology_submissions")
    task = relationship("TopologyTask")


# ==========================================
# 模块三：真实性任务工作台 (Authenticity Task Workspace)
# ==========================================
class AuthenticityTask(Base):
    """真实性任务表"""
    __tablename__ = "authenticity_tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    context_description = Column(Text, nullable=False)
    evaluation_criteria = Column(Text, nullable=False)


class AuthenticityIteration(Base):
    """真实性任务迭代记录（版本控制模式）"""
    __tablename__ = "authenticity_iterations"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("authenticity_tasks.id"), nullable=False, index=True)
    student_id = Column(String, ForeignKey("students.student_id"), nullable=False, index=True)

    version_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 负载数据 (按要求降维采用 JSON 存储)
    deliverable_payload = Column(String, nullable=False)
    collaboration_matrix = Column(JSON, nullable=False)
    tools_used = Column(JSON, default=list)
    reflection_log = Column(Text, nullable=False)

    # 关系映射
    student = relationship("Student", back_populates="authenticity_iterations")
    task = relationship("AuthenticityTask")