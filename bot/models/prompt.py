"""
提示词数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from bot.database.db import Base


class Prompt(Base):
    """提示词表模型"""
    __tablename__ = "prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    language = Column(String(10), nullable=False, index=True)  # en, zh
    prompt_template = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Prompt(product_id={self.product_id}, language={self.language}, version={self.version})>"

