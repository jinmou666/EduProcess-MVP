import sys
import os
from datetime import datetime, timedelta

# 将项目根目录加入 python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app import models

def init_db_data():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    existing_task = db.query(models.Task).first()
    if existing_task:
        print("Data already exists. Please delete 'sql_app.db' first if you want to reset data.")
        return

    now = datetime.utcnow()

    # 任务1：旧任务
    task1 = models.Task(
        title="5G 技术描述批判",
        content="5G通信技术利用正交频分复用（OFDM）技术，这是数字信号处理的核心。它将高速数据流拆分为多个模拟子载波，从而减少传输过程中的信号干扰。OFDM的一个显著特点是其子载波之间需要设置保护频带，这在一定程度上降低了频谱效率，但保证了信号的完整性。",
        publish_date=now - timedelta(days=10),
        deadline=now + timedelta(days=2),
        preset_errors=[
            {"description": "OFDM子载波是正交的，不需要保护频带", "keyword": "需要设置保护频带"},
            {"description": "OFDM处理数字信号", "keyword": "模拟子载波"}
        ]
    )

    # 任务2：新任务
    task2 = models.Task(
        title="TCP/IP 协议栈概念辨析",
        content="在TCP/IP模型中，应用层负责数据的路由和转发。TCP协议是一种无连接、不可靠的传输协议，它通过三次握手来随意发送数据包。而IP地址负责在同一个局域网内的物理设备寻址，这通常被称为MAC地址。",
        publish_date=now - timedelta(days=2),
        deadline=now + timedelta(days=14),
        preset_errors=[]
    )

    db.add_all([task1, task2])
    db.commit()
    print("Mock data created successfully!")
    db.close()

if __name__ == "__main__":
    init_db_data()