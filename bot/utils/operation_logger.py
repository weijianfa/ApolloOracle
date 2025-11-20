"""
操作日志记录工具
"""
from typing import Optional, Dict, Any
from bot.database.db import get_db_session
from bot.models.operation_log import OperationLog
from bot.utils.logger import logger
import json


def log_operation(
    operation_type: str,
    status: str,
    user_id: Optional[int] = None,
    order_id: Optional[str] = None,
    operation_detail: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> bool:
    """
    记录操作日志
    
    Args:
        operation_type: 操作类型（payment, api_call, status_change等）
        status: 操作状态（success, failed, pending）
        user_id: 用户ID（可选）
        order_id: 订单ID（可选）
        operation_detail: 操作详情（可选，字典格式）
        error_message: 错误信息（可选）
        
    Returns:
        记录是否成功
    """
    try:
        with get_db_session() as db:
            log_entry = OperationLog(
                user_id=user_id,
                order_id=order_id,
                operation_type=operation_type,
                operation_detail=json.dumps(operation_detail, ensure_ascii=False) if operation_detail else None,
                status=status,
                error_message=error_message
            )
            db.add(log_entry)
            db.commit()
            return True
    except Exception as e:
        logger.error(f"Error logging operation: {e}")
        return False

