"""
用户数据模型
"""
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from bot.database.db import Base


class User(Base):
    """用户表模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default='en')
    
    # 推广员相关字段
    is_affiliate = Column(Boolean, default=False)
    affiliate_code = Column(String(20), unique=True, nullable=True)
    agreement_date = Column(DateTime, nullable=True)
    real_name = Column(String(255), nullable=True)
    contact_info = Column(String(255), nullable=True)
    payout_account = Column(Text, nullable=True)
    referred_by = Column(String(20), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"

