"""
汇率缓存数据模型
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from bot.database.db import Base


class ExchangeRate(Base):
    """汇率缓存表模型"""
    __tablename__ = "exchange_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    base_currency = Column(String(10), default='USD', nullable=False)
    target_currency = Column(String(10), nullable=False, index=True)
    rate = Column(Numeric(10, 6), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 唯一约束：同一基础货币和目标货币只能有一条记录
    __table_args__ = (
        UniqueConstraint('base_currency', 'target_currency', name='uq_base_target_currency'),
    )
    
    def __repr__(self):
        return f"<ExchangeRate({self.base_currency}->{self.target_currency}={self.rate})>"

