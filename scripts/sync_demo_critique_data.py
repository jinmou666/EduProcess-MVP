import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models
from app.services.critique_evaluator import build_demo_fallback_evaluation


def build_selection_range(text: str, snippet: str):
    start = text.find(snippet)
    if start == -1:
        raise ValueError(f"Snippet not found in task content: {snippet}")
    return [start, start + len(snippet)]


def upsert_submission(db, task, student_id, critiques_data):
    submission = db.query(models.CritiqueSubmission).filter(
        models.CritiqueSubmission.task_id == task.id,
        models.CritiqueSubmission.student_id == student_id,
    ).order_by(models.CritiqueSubmission.id.desc()).first()

    if submission is None:
        submission = models.CritiqueSubmission(
            task_id=task.id,
            student_id=student_id,
            critiques_data=critiques_data,
        )
        db.add(submission)
        db.flush()
    else:
        submission.critiques_data = critiques_data

    report, metadata = build_demo_fallback_evaluation(
        task,
        submission,
        "seeded local critique example",
        scoring_mode="local",
    )
    submission.score = report.total_score
    submission.evaluation_report = report.model_dump()
    db.flush()

    db.add(models.EvaluationRecord(
        student_id=student_id,
        module_type="critique",
        target_id=submission.id,
        status="success_local",
        rubric_version=metadata["rubric_version"],
        prompt_version=metadata["prompt_version"],
        model_name=metadata["model_name"],
        input_snapshot_json=metadata["input_snapshot"],
        result_json={
            "report": report.model_dump(),
            "fallback_reason": metadata["fallback_reason"],
        },
        total_score=report.total_score,
    ))
    return submission


def main():
    db = SessionLocal()
    now = datetime.utcnow()

    try:
        task_1 = db.query(models.Task).filter(models.Task.id == 1).first()
        task_2 = db.query(models.Task).filter(models.Task.id == 2).first()
        task_3 = db.query(models.Task).filter(models.Task.id == 3).first()

        if task_1 is None or task_2 is None:
            raise RuntimeError("Tasks 1 and 2 must exist before syncing demo critique data.")

        task_3_content = "在 TCP/IP 协议中，HTTP 属于网络层协议，主要负责路由转发。此外，DNS 服务器只能把域名解析成 IPv4 地址，不能返回 IPv6 记录。"
        task_3_errors = [
            {
                "error_id": "e1",
                "wrong_text": "HTTP 属于网络层协议",
                "standard_correction": "HTTP 属于应用层协议，依赖 TCP 在传输层提供可靠传输服务。",
                "core_concept": "HTTP 所处层级与 TCP/IP 分层",
            },
            {
                "error_id": "e2",
                "wrong_text": "DNS 服务器只能把域名解析成 IPv4 地址，不能返回 IPv6 记录",
                "standard_correction": "DNS 既可以返回 IPv4 的 A 记录，也可以返回 IPv6 的 AAAA 记录，并不局限于 IPv4。",
                "core_concept": "DNS 记录类型与 IPv6 解析",
            },
        ]

        if task_3 is None:
            task_3 = models.Task(
                id=3,
                title="TCP/IP 与 DNS 描述批判",
                content=task_3_content,
                publish_date=now - timedelta(days=1),
                deadline=now + timedelta(days=5),
                preset_errors=task_3_errors,
            )
            db.add(task_3)
            db.flush()
        else:
            task_3.title = "TCP/IP 与 DNS 描述批判"
            task_3.content = task_3_content
            task_3.deadline = now + timedelta(days=5)
            task_3.preset_errors = task_3_errors

        task_1_critiques = [
            {
                "quote": "模拟子载波",
                "rewrite": "OFDM 处理的是数字数据流，不是模拟子载波。",
                "citation": "OFDM 属于数字通信中的多载波调制技术。",
                "selection_range": build_selection_range(task_1.content, "模拟子载波"),
            },
            {
                "quote": "需要设置保护频带",
                "rewrite": "OFDM 子载波保持正交，不需要传统保护频带，这也是其频谱效率更高的原因。",
                "citation": "子载波正交后可在频域重叠而互不干扰。",
                "selection_range": build_selection_range(task_1.content, "需要设置保护频带"),
            },
        ]

        task_2_critiques = [
            {
                "quote": "大语言模型（LLM）已经等同于AI智能体（Agent）",
                "rewrite": "LLM 不等同于 Agent，LLM 更像是 Agent 的语言与推理核心。",
                "citation": "完整 Agent 还需要记忆、规划和行动模块。",
                "selection_range": build_selection_range(task_2.content, "大语言模型（LLM）已经等同于AI智能体（Agent）"),
            },
            {
                "quote": "可以直接通过其内部的参数权重，在软件系统中自主执行",
                "rewrite": "模型参数本身不能直接执行外部任务，通常还要依赖工具调用或执行器。",
                "citation": "Agent 通过 Tool Calling 把文本决策转成系统动作。",
                "selection_range": build_selection_range(task_2.content, "可以直接通过其内部的参数权重，在软件系统中自主执行"),
            },
            {
                "quote": "记忆系统仅仅依赖于模型预训练时的上下文窗口大小",
                "rewrite": "现代 Agent 还可通过向量数据库或 RAG 做跨会话长期记忆。",
                "citation": "长期记忆通常外挂存储与检索，而不是只靠上下文窗口。",
                "selection_range": build_selection_range(task_2.content, "记忆系统仅仅依赖于模型预训练时的上下文窗口大小"),
            },
        ]

        task_3_critiques = [
            {
                "quote": "HTTP 属于网络层协议",
                "rewrite": "HTTP 属于应用层协议，依赖 TCP 在传输层提供可靠传输服务。",
                "citation": "HTTP 所处层级与 TCP/IP 分层",
                "selection_range": build_selection_range(task_3.content, "HTTP 属于网络层协议"),
            },
            {
                "quote": "DNS 服务器只能把域名解析成 IPv4 地址，不能返回 IPv6 记录",
                "rewrite": "DNS 既可以返回 IPv4 的 A 记录，也可以返回 IPv6 的 AAAA 记录，并不局限于 IPv4。",
                "citation": "DNS 记录类型与 IPv6 解析",
                "selection_range": build_selection_range(task_3.content, "DNS 服务器只能把域名解析成 IPv4 地址，不能返回 IPv6 记录"),
            },
        ]

        results = {
            1: upsert_submission(db, task_1, "20230001", task_1_critiques).score,
            2: upsert_submission(db, task_2, "20230001", task_2_critiques).score,
            3: upsert_submission(db, task_3, "20230001", task_3_critiques).score,
        }

        db.commit()
        print({
            "task_scores": results,
            "task_3_deadline": str(task_3.deadline),
        })
    finally:
        db.close()


if __name__ == "__main__":
    main()
