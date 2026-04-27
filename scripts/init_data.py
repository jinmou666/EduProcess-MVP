import sys
import os
from datetime import datetime, timedelta

# 绝对路径绑定（防止你再次迷失在相对路径里）
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app import models
from app.services.critique_evaluator import build_demo_fallback_evaluation


def build_selection_range(text: str, snippet: str):
    start = text.find(snippet)
    if start == -1:
        raise ValueError(f"Snippet not found in task content: {snippet}")
    return [start, start + len(snippet)]


def seed_critique_submission(db, task, student_id, critiques_data, status="success_local"):
    submission = models.CritiqueSubmission(
        task_id=task.id,
        student_id=student_id,
        critiques_data=critiques_data,
    )
    report, metadata = build_demo_fallback_evaluation(
        task,
        submission,
        "seeded local critique example",
        scoring_mode="local",
    )
    submission.score = report.total_score
    submission.evaluation_report = report.dict()
    db.add(submission)
    db.flush()

    db.add(models.EvaluationRecord(
        student_id=student_id,
        module_type="critique",
        target_id=submission.id,
        status=status,
        rubric_version=metadata["rubric_version"],
        prompt_version=metadata["prompt_version"],
        model_name=metadata["model_name"],
        input_snapshot_json=metadata["input_snapshot"],
        result_json={
            "report": report.dict(),
            "fallback_reason": metadata["fallback_reason"],
        },
        total_score=report.total_score,
    ))

    return submission

def init_db_data():
    # 强制建表
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 防呆设计：检查是否已经有这个学生了
    existing_student = db.query(models.Student).filter(models.Student.student_id == "20230001").first()
    if existing_student:
        print("❌ 数据库中已存在测试数据！")
        print("请立刻去项目根目录，手动删除 'sql_app.db' 文件，然后再重新运行本脚本！")
        db.close()
        return

    print("开始注入核心测试数据...")
    now = datetime.utcnow()

    # ==================================================
    # 1. 注入学生实体 (全局数据锚点)
    # ==================================================
    student = models.Student(
        student_id="20230001",
        name="测试用户_MVP"
    )
    db.add(student)

    # ==================================================
    # 2. 注入模块一：文本纠错任务
    # ==================================================
    critique_task = models.Task(
        id=1,  # 强制硬编码 ID 为 1
        title="5G 技术描述批判",
        content="5G通信技术利用正交频分复用（OFDM）技术，这是数字信号处理的核心。它将高速数据流拆分为多个模拟子载波，从而减少传输过程中的信号干扰。OFDM的一个显著特点是其子载波之间需要设置保护频带，这在一定程度上降低了频谱效率，但保证了信号的完整性。",
        publish_date=now - timedelta(days=10),
        deadline=now + timedelta(days=2),
        preset_errors=[
            {
                "error_id": "e1",
                "wrong_text": "需要设置保护频带",
                "standard_correction": "OFDM的子载波是严格正交的，因此不需要设置传统的保护频带，这正是其能够大幅提升频谱效率的核心原理。",
                "core_concept": "OFDM正交性原理与频谱效率"
            },
            {
                "error_id": "e2",
                "wrong_text": "模拟子载波",
                "standard_correction": "OFDM是数字通信系统的核心技术，它处理并传输的是数字数据流，而非模拟信号。",
                "core_concept": "数字信号处理基础"
            }
        ]
    )
    db.add(critique_task)

    critique_task_2 = models.Task(
        id=2,
        title="大语言模型(LLM)与AI智能体(Agent)概念辨析",
        content="当前，大语言模型（LLM）已经等同于AI智能体（Agent）。LLM可以直接通过其内部的参数权重，在软件系统中自主执行如发送邮件、预订机票等复杂任务。此外，智能体的记忆能力是固定的，其记忆系统仅仅依赖于模型预训练时的上下文窗口大小，无法在多轮交互中实现真正的长期记忆跨度。",
        publish_date=now - timedelta(days=5),
        deadline=now + timedelta(days=7),
        preset_errors=[
            {
                "error_id": "e1",
                "wrong_text": "大语言模型（LLM）已经等同于AI智能体（Agent）",
                "standard_correction": "LLM不等同于Agent。LLM通常只作为Agent的“大脑”提供推理和自然语言处理能力，而一个完整的Agent还需要包含感知模块、记忆模块以及规划和行动（Action/Tool Use）模块。",
                "core_concept": "LLM与Agent的架构区别"
            },
            {
                "error_id": "e2",
                "wrong_text": "可以直接通过其内部的参数权重，在软件系统中自主执行",
                "standard_correction": "单纯的参数权重只能生成文本。要执行现实系统中的任务，Agent必须依赖外部的“工具调用（Tool Calling）”机制或执行器（Actuators）将其生成的指令转化为API请求或物理动作。",
                "core_concept": "Agent的行动力/工具调用逻辑"
            },
            {
                "error_id": "e3",
                "wrong_text": "记忆系统仅仅依赖于模型预训练时的上下文窗口大小",
                "standard_correction": "虽然短期记忆受限于上下文窗口，但现代Agent架构通过外挂向量数据库（Vector Database）或记忆检索增强（RAG）技术，已经能够实现跨会话的、可扩展的长期记忆（Long-term Memory）。",
                "core_concept": "智能体的长短期记忆机制"
            }
        ]
    )
    db.add(critique_task_2)

    critique_task_3_content = "在 TCP/IP 协议中，HTTP 属于网络层协议，主要负责路由转发。此外，DNS 服务器只能把域名解析成 IPv4 地址，不能返回 IPv6 记录。"
    critique_task_3 = models.Task(
        id=3,
        title="TCP/IP 与 DNS 描述批判",
        content=critique_task_3_content,
        publish_date=now - timedelta(days=1),
        deadline=now + timedelta(days=5),
        preset_errors=[
            {
                "error_id": "e1",
                "wrong_text": "HTTP 属于网络层协议",
                "standard_correction": "HTTP 属于应用层协议，依赖 TCP 在传输层提供可靠传输服务。",
                "core_concept": "HTTP 所处层级与 TCP/IP 分层"
            },
            {
                "error_id": "e2",
                "wrong_text": "DNS 服务器只能把域名解析成 IPv4 地址，不能返回 IPv6 记录",
                "standard_correction": "DNS 既可以返回 IPv4 的 A 记录，也可以返回 IPv6 的 AAAA 记录，并不局限于 IPv4。",
                "core_concept": "DNS 记录类型与 IPv6 解析"
            }
        ]
    )
    db.add(critique_task_3)

    task_1_critiques = [
        {
            "quote": "模拟子载波",
            "rewrite": "OFDM 处理的是数字数据流，不是模拟子载波。",
            "citation": "OFDM 属于数字通信中的多载波调制技术。",
            "selection_range": build_selection_range(critique_task.content, "模拟子载波")
        },
        {
            "quote": "需要设置保护频带",
            "rewrite": "OFDM 子载波保持正交，不需要传统保护频带，这也是其频谱效率更高的原因。",
            "citation": "子载波正交后可在频域重叠而互不干扰。",
            "selection_range": build_selection_range(critique_task.content, "需要设置保护频带")
        }
    ]
    seed_critique_submission(db, critique_task, "20230001", task_1_critiques)

    task_2_critiques = [
        {
            "quote": "大语言模型（LLM）已经等同于AI智能体（Agent）",
            "rewrite": "LLM 不等同于 Agent，LLM 更像是 Agent 的语言与推理核心。",
            "citation": "完整 Agent 还需要记忆、规划和行动模块。",
            "selection_range": build_selection_range(critique_task_2.content, "大语言模型（LLM）已经等同于AI智能体（Agent）")
        },
        {
            "quote": "可以直接通过其内部的参数权重，在软件系统中自主执行",
            "rewrite": "模型参数本身不能直接执行外部任务，通常还要依赖工具调用或执行器。",
            "citation": "Agent 通过 Tool Calling 把文本决策转成系统动作。",
            "selection_range": build_selection_range(critique_task_2.content, "可以直接通过其内部的参数权重，在软件系统中自主执行")
        },
        {
            "quote": "记忆系统仅仅依赖于模型预训练时的上下文窗口大小",
            "rewrite": "现代 Agent 还可通过向量数据库或 RAG 做跨会话长期记忆。",
            "citation": "长期记忆通常外挂存储与检索，而不是只靠上下文窗口。",
            "selection_range": build_selection_range(critique_task_2.content, "记忆系统仅仅依赖于模型预训练时的上下文窗口大小")
        }
    ]
    seed_critique_submission(db, critique_task_2, "20230001", task_2_critiques)

    task_3_critiques = [
        {
            "quote": "HTTP 属于网络层协议",
            "rewrite": "HTTP 属于应用层协议，依赖 TCP 在传输层提供可靠传输服务。",
            "citation": "HTTP 所处层级与 TCP/IP 分层",
            "selection_range": build_selection_range(critique_task_3_content, "HTTP 属于网络层协议")
        },
        {
            "quote": "DNS 服务器只能把域名解析成 IPv4 地址，不能返回 IPv6 记录",
            "rewrite": "DNS 既可以返回 IPv4 的 A 记录，也可以返回 IPv6 的 AAAA 记录，并不局限于 IPv4。",
            "citation": "DNS 记录类型与 IPv6 解析",
            "selection_range": build_selection_range(critique_task_3_content, "DNS 服务器只能把域名解析成 IPv4 地址，不能返回 IPv6 记录")
        }
    ]
    seed_critique_submission(db, critique_task_3, "20230001", task_3_critiques)

    # ==================================================
    # 3. 注入模块二：拓扑构筑任务
    # ==================================================
    topology_task = models.TopologyTask(
        id=1,  # 强制硬编码 ID 为 1
        title="计算机网络基础概念关联",
        description="请将左侧的概念节点拖拽到画板中，并根据它们在 OSI 七层模型中的逻辑关联进行连线。",
        standard_graph={"nodes": [], "edges": []}
    )
    db.add(topology_task)

    # ==================================================
    # 4. 注入模块三：真实性任务
    # ==================================================
    authenticity_task = models.AuthenticityTask(
        id=1,  # 强制硬编码 ID 为 1
        title="AI技术在自动驾驶领域应用风险的商业分析报告",
        context_description="本任务要求你完成一篇关于“AI技术在自动驾驶领域应用风险”的商业分析报告。你需要提交不少于3000字的文档，并附带数据支撑。",
        evaluation_criteria="1. 过程透明：严禁一键生成，必须展示至少3次迭代过程。\n2. 人机边界：在数据支撑阶段要求极高的人工审核比例（避免AI幻觉）。\n3. 反思深度：评估你发现并纠正AI错误的能力。"
    )
    db.add(authenticity_task)

    # 提交所有数据
    db.commit()
    print("✅ 测试数据注入成功！")
    print("========================================")
    print("【系统前端对接凭证】")
    print("请确保前端在发起 Fetch 请求时，URL 和 Payload 严格使用以下参数：")
    print("学生身份 (student_id) : '20230001'")
    print("全局任务 (task_id)    : 1")
    print("若要启用真实 LLM 评分，请先在项目根目录配置 .env 中的 LLM_API_KEY / LLM_MODEL_NAME。")
    print("========================================")

    db.close()

if __name__ == "__main__":
    init_db_data()
