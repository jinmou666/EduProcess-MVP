import sys
import os
from datetime import datetime, timedelta

# 绝对路径绑定（防止你再次迷失在相对路径里）
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app import models

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
    print("========================================")

    db.close()

if __name__ == "__main__":
    init_db_data()