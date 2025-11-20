"""
定时任务调度器
"""
import asyncio
from datetime import datetime
from bot.services.payment_service import payment_service
from bot.utils.logger import logger
from bot.utils.session_manager import cleanup_expired_sessions


async def check_payment_timeouts():
    """
    检查支付超时的订单（每5分钟执行一次）
    """
    while True:
        try:
            count = payment_service.check_payment_timeout()
            if count > 0:
                logger.info(f"Cleaned up {count} timeout orders")
        except Exception as e:
            logger.error(f"Error checking payment timeouts: {e}")
        
        # 等待5分钟
        await asyncio.sleep(300)


async def cleanup_sessions():
    """
    清理过期的会话（每小时执行一次）
    """
    while True:
        try:
            count = cleanup_expired_sessions()
            if count > 0:
                logger.info(f"Cleaned up {count} expired sessions")
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
        
        # 等待1小时
        await asyncio.sleep(3600)


async def start_background_tasks():
    """
    启动所有后台任务
    """
    logger.info("Starting background tasks...")
    
    # 启动支付超时检查任务
    asyncio.create_task(check_payment_timeouts())
    
    # 启动会话清理任务
    asyncio.create_task(cleanup_sessions())
    
    logger.info("Background tasks started")

