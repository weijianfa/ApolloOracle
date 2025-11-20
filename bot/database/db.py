"""
数据库连接和会话管理
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from bot.config.settings import settings
from bot.utils.logger import logger

# 创建基础模型类
Base = declarative_base()

# 数据库引擎配置
engine_kwargs = {
    "echo": settings.is_development(),  # 开发环境显示SQL
    "pool_pre_ping": True,  # 连接池健康检查
}

# SQLite特殊配置
if "sqlite" in settings.DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    # SQLite不支持连接池，使用NullPool
    engine_kwargs["poolclass"] = None
else:
    # PostgreSQL等数据库使用连接池
    engine_kwargs["poolclass"] = QueuePool
    engine_kwargs["pool_size"] = 5  # 连接池大小
    engine_kwargs["max_overflow"] = 10  # 最大溢出连接数
    engine_kwargs["pool_recycle"] = 3600  # 连接回收时间（秒）

# 创建数据库引擎
engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    获取数据库会话（用于依赖注入）
    
    Yields:
        Session: 数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """
    获取数据库会话（上下文管理器）
    
    Yields:
        Session: 数据库会话
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()


def init_db():
    """
    初始化数据库（创建所有表）
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def drop_db():
    """
    删除所有表（谨慎使用！）
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables dropped")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise

