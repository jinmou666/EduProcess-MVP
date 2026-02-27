import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# 获取当前文件所在目录的上一级目录（即项目根目录，EduProcess-MVP-xxx）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 强制将数据库文件绑定在根目录下
DB_PATH = os.path.join(BASE_DIR, "sql_app.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# SQLite 需要 check_same_thread=False
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()