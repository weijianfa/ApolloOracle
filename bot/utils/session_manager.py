"""
会话状态管理工具
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
from bot.database.db import get_db_session
from bot.models.user_session import UserSession
from bot.models.user import User


def save_session(user_id: int, state: str, data: Dict[str, Any], product_id: Optional[int] = None) -> None:
    """
    保存用户会话状态
    
    Args:
        user_id: Telegram用户ID
        state: 会话状态
        data: 会话数据
        product_id: 产品ID
    """
    with get_db_session() as db:
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            return
        
        session = db.query(UserSession).filter(UserSession.user_id == db_user.id).first()
        if not session:
            session = UserSession(user_id=db_user.id)
            db.add(session)
        
        session.session_state = state
        session.session_data = json.dumps(data)
        session.product_id = product_id
        session.expires_at = datetime.now() + timedelta(minutes=30)  # 30分钟过期
        db.commit()


def load_session(user_id: int) -> Optional[Dict[str, Any]]:
    """
    加载用户会话状态
    
    Args:
        user_id: Telegram用户ID
        
    Returns:
        会话数据字典，如果不存在或已过期则返回None
    """
    with get_db_session() as db:
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            return None
        
        session = db.query(UserSession).filter(UserSession.user_id == db_user.id).first()
        if not session:
            return None
        
        # 检查是否过期
        if session.expires_at and session.expires_at < datetime.now():
            db.delete(session)
            db.commit()
            return None
        
        return {
            "state": session.session_state,
            "data": json.loads(session.session_data) if session.session_data else {},
            "product_id": session.product_id
        }


def clear_session(user_id: int) -> None:
    """
    清除用户会话状态
    
    Args:
        user_id: Telegram用户ID
    """
    with get_db_session() as db:
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            return
        
        session = db.query(UserSession).filter(UserSession.user_id == db_user.id).first()
        if session:
            db.delete(session)
            db.commit()


def cleanup_expired_sessions() -> int:
    """
    清理过期的会话
    
    Returns:
        清理的会话数量
    """
    count = 0
    with get_db_session() as db:
        expired_sessions = db.query(UserSession).filter(
            UserSession.expires_at < datetime.now()
        ).all()
        
        for session in expired_sessions:
            db.delete(session)
            count += 1
        
        db.commit()
    
    return count

