"""
用户会话状态模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from bot.database.db import Base


class UserSession(Base):
    """用户会话状态表模型"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # 会话状态
    session_state = Column(String(50), nullable=True)  # 当前对话状态
    session_data = Column(Text, nullable=True)  # JSON格式存储临时数据
    product_id = Column(Integer, nullable=True)  # 当前选择的产品ID
    
    # 过期时间
    expires_at = Column(DateTime, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, state={self.session_state})>"

