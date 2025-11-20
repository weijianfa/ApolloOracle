"""
数据库测试
"""
import pytest
import os
from bot.database.db import init_db, drop_db, get_db_session, Base, engine
from bot.models import User, Order, UserSession, Affiliate, OperationLog, SystemConfig, Prompt, ExchangeRate
from bot.config.settings import settings


@pytest.fixture(scope="function")
def test_db():
    """测试数据库fixture"""
    # 使用测试数据库
    test_db_url = "sqlite:///test_bot.db"
    original_url = settings.DATABASE_URL
    
    # 临时修改数据库URL
    settings.DATABASE_URL = test_db_url
    
    # 创建表
    Base.metadata.create_all(bind=engine)
    
    yield
    
    # 清理
    Base.metadata.drop_all(bind=engine)
    settings.DATABASE_URL = original_url
    
    # 删除测试数据库文件
    if os.path.exists("test_bot.db"):
        os.remove("test_bot.db")


def test_database_initialization(test_db):
    """测试数据库初始化"""
    # 测试表是否创建
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    expected_tables = [
        'users', 'orders', 'user_sessions', 'affiliates',
        'operation_logs', 'system_config', 'prompts', 'exchange_rates'
    ]
    
    for table in expected_tables:
        assert table in tables, f"Table {table} not found"


def test_user_model(test_db):
    """测试用户模型"""
    with get_db_session() as db:
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test",
            language_code="zh"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        assert user.id is not None
        assert user.telegram_id == 123456789
        assert user.username == "test_user"


def test_order_model(test_db):
    """测试订单模型"""
    with get_db_session() as db:
        # 先创建用户
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 创建订单
        order = Order(
            order_id="TEST_ORDER_001",
            user_id=user.id,
            product_id=1,
            product_name="测试产品",
            status="pending_payment",
            amount_usd=1.00
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        assert order.id is not None
        assert order.order_id == "TEST_ORDER_001"
        assert order.status == "pending_payment"


def test_user_session_model(test_db):
    """测试用户会话模型"""
    with get_db_session() as db:
        # 先创建用户
        user = User(
            telegram_id=123456789,
            username="test_user",
            first_name="Test"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 创建会话
        session = UserSession(
            user_id=user.id,
            session_state="selecting_product",
            session_data='{"product_id": 1}',
            product_id=1
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        assert session.id is not None
        assert session.session_state == "selecting_product"

