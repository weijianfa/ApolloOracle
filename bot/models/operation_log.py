"""
操作日志数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from bot.database.db import Base


class OperationLog(Base):
    """操作日志表模型"""
    __tablename__ = "operation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=True, index=True)
    
    # 操作信息
    operation_type = Column(String(50), nullable=False, index=True)
    # 操作类型: payment, api_call, status_change, refund, etc.
    operation_detail = Column(Text, nullable=True)  # JSON格式存储详细信息
    status = Column(String(20), nullable=True)  # success, failed, pending
    error_message = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<OperationLog(type={self.operation_type}, status={self.status}, created_at={self.created_at})>"


# 创建索引（在Alembic迁移中创建）
# Index('idx_operation_logs_user_id', OperationLog.user_id)
# Index('idx_operation_logs_order_id', OperationLog.order_id)
# Index('idx_operation_logs_created_at', OperationLog.created_at)

