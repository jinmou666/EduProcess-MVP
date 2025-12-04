import sys
import os

# 将项目根目录加入 python path，防止找不到 app 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app import models


def init_db_data():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 检查是否已有数据，防止重复插入
    existing_task = db.query(models.Task).filter(models.Task.id == 1).first()
    if existing_task:
        print("Data already exists. Skipping.")
        return


    # 错误1: "OFDM技术将高速数据流拆分为多个模拟子载波" -> 应该是正交的、数字调制的概念混淆
    # 错误2: "3G网络利用正交频分复用" -> 主要是4G/5G，3G主要是CDMA
    # 错误3: "子载波之间需要设置保护频带" -> OFDM的优势就是利用正交性取消了保护频带(Guard Band)的需求(除了CP)

    ai_content = (
        "5G通信技术利用正交频分复用（OFDM）技术，这是数字信号处理的核心。"
        "它将高速数据流拆分为多个模拟子载波，从而减少传输过程中的信号干扰。"
        "OFDM的一个显著特点是其子载波之间需要设置保护频带，这在一定程度上降低了频谱效率，"
        "但保证了信号的完整性。"
    )

    task = models.Task(
        title="5G 技术描述批判",
        content=ai_content,
        preset_errors=[
            {
                "description": "OFDM子载波是正交的，不需要保护频带(guard band)，这是它的主要优势。",
                "keyword": "需要设置保护频带"
            },
            {
                "description": "OFDM主要处理数字信号，子载波也是数字调制后的表现形式。",
                "keyword": "模拟子载波"
            }
        ]
    )

    db.add(task)
    db.commit()
    print("Mock data created successfully!")
    print(f"Task ID: {task.id}")
    print(f"Content Preview: {task.content[:50]}...")
    db.close()


if __name__ == "__main__":
    init_db_data()