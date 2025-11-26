import logging
import time
from typing import List, Type

from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import Engine



# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# PostgreSQL 连接配置
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}?client_encoding=utf8"

# 创建引擎
# 创建引擎（开启echo可以看到所有SQL）
engine = create_engine(
    DATABASE_URL,
    echo=False,  # 不使用SQLAlchemy的内置日志
    connect_args={'client_encoding': 'utf8'},
    pool_size=10,  # 连接池大小
    max_overflow=5,  # 最大溢出连接数
    pool_pre_ping=True,  # 连接池健康检查
    pool_recycle=3600  # 连接回收时间（秒）
)

# SQL执行监听器
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())
    #logging.info(f"\n{'='*50}\nExecuting SQL: {statement}")
    #if parameters:
    #    logging.info(f"Parameters: {parameters}")

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    #logger.info(f"Execution Time: {total:.3f}s\n{'='*50}\n")

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()


def get_all_models() -> List[Type]:
    """获取所有需要检查的模型类"""
    from models.stock import Stock
    from models.stock_history import StockHistoryD, StockHistoryW, StockHistoryM, StockHistory30M
    from models.sync_history import SyncHistory
    from models.stock_trade import StockTrade
    return [Stock, StockHistoryD, StockHistoryW, StockHistoryM, StockHistory30M, SyncHistory, StockTrade]


def check_tables(conn, tables: List[Type]) -> List[str]:
    """检查表是否存在，返回不存在的表名列表"""
    missing_tables = []
    for model in tables:
        if not engine.dialect.has_table(conn, model.__tablename__):
            missing_tables.append(model.__tablename__)
    return missing_tables


def init_db():
    """初始化数据库（只创建不存在的表）"""
    try:
        Base.metadata.create_all(bind=engine)
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Error creating database tables: {str(e)}")
        raise e


def check_db():
    """检查数据库连接和表是否存在"""
    try:
        # 检查连接
        with engine.connect() as conn:
            # 获取所有模型
            models = get_all_models()
            # 检查表是否存在
            missing_tables = check_tables(conn, models)
            if missing_tables:
                logging.info(f"Missing tables: {', '.join(missing_tables)}, creating...")
                init_db()
            else:
                logging.info("All database tables exist")
    except Exception as e:
        logging.error(f"Database check failed: {str(e)}")
        raise e