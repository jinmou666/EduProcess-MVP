from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Task(Base):
    """
    题目表：存放AI生成的文本和预设的错误点（用于将来自动评分，现在仅用于展示）
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)  # 任务标题
    content = Column(Text)  # AI生成的全文内容

    # 预设的错误列表，存为JSON。例如：[{"start": 10, "end": 15, "reason": "..."}]
    preset_errors = Column(JSON, default=list)


class Submission(Base):
    """
    提交表：存放学生提交的纠错记录
    """
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    student_id = Column(String, index=True)  # 假设学生ID是字符串，如 "STU001"

    # 核心：学生的所有纠错点。
    # 结构：[{"quote": "错误文本", "rewrite": "修正文本", "citation": "理论依据", "range": [start, end]}]
    critiques = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联关系
    task = relationship("Task")