"""
系统配置数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from bot.database.db import Base


class SystemConfig(Base):
    """系统配置表模型"""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(Text, nullable=False)
    config_type = Column(String(20), default='string')  # string, int, float, bool, json
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(100), nullable=True)
    
    def __repr__(self):
        return f"<SystemConfig(key={self.config_key}, type={self.config_type})>"

