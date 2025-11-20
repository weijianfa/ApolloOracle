"""
订单数据模型
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from bot.database.db import Base


class Order(Base):
    """订单表模型"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 产品信息
    product_id = Column(Integer, nullable=False)
    product_name = Column(String(255), nullable=True)
    
    # 订单状态
    status = Column(String(20), nullable=False, index=True)  
    # 状态值: pending_payment, paid, generating, completed, failed, refunded
    
    # 价格信息
    amount_usd = Column(Numeric(10, 2), nullable=True)
    amount_local = Column(Numeric(10, 2), nullable=True)
    local_currency = Column(String(10), nullable=True)
    exchange_rate = Column(Numeric(10, 6), nullable=True)
    
    # 支付信息
    payment_method = Column(String(50), nullable=True)
    payment_id = Column(String(100), nullable=True)
    
    # 数据存储
    user_input = Column(Text, nullable=True)  # JSON格式
    bazi_data = Column(Text, nullable=True)  # JSON格式
    ai_report = Column(Text, nullable=True)
    
    # 推广员信息
    affiliate_code = Column(String(20), nullable=True)
    commission_rate = Column(Numeric(5, 2), nullable=True)
    commission_amount = Column(Numeric(10, 2), nullable=True)
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Order(id={self.id}, order_id={self.order_id}, status={self.status})>"

