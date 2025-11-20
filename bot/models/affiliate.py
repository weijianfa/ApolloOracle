"""
推广员数据模型
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func
from bot.database.db import Base


class Affiliate(Base):
    """推广员表模型"""
    __tablename__ = "affiliates"
    
    id = Column(Integer, primary_key=True, index=True)
    affiliate_code = Column(String(20), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # 销售统计
    total_sales = Column(Numeric(10, 2), default=0)
    total_commission = Column(Numeric(10, 2), default=0)
    current_tier = Column(Integer, default=1)  # 1-4对应不同佣金比例
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Affiliate(code={self.affiliate_code}, sales={self.total_sales}, tier={self.current_tier})>"

