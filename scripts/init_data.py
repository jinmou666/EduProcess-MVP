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
            {"description": "OFDM子载波是正交的，不需要保护频带", "keyword": "需要设置保护频带"},
            {"description": "OFDM处理数字信号", "keyword": "模拟子载波"}
        ]
    )
    db.add(critique_task)

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