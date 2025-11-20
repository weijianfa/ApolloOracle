"""
退款处理模块
"""
from telegram import Update
from telegram.ext import ContextTypes
from bot.database.db import get_db_session
from bot.models.order import Order
from bot.models.user import User
from bot.services.payment_service import payment_service
from bot.utils.logger import logger
from bot.utils.operation_logger import log_operation
from bot.config.settings import settings


async def notify_user_refund(telegram_id: int, order: Order, reason: str):
    """
    通知用户退款
    
    Args:
        telegram_id: Telegram用户ID
        order: 订单对象
        reason: 退款原因
    """
    try:
        from telegram import Bot
        
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        
        message = (
            f"💰 退款通知 / Refund Notice\n\n"
            f"订单号 / Order ID: `{order.order_id}`\n"
            f"产品 / Product: {order.product_name}\n"
            f"退款原因 / Reason: {reason}\n\n"
            f"退款金额 / Refund Amount: ${order.amount_usd:.2f} USD\n\n"
            f"退款将在3-5个工作日内到账。\n"
            f"Refund will be processed within 3-5 business days."
        )
        
        await bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode="Markdown"
        )
        
        logger.info(f"Refund notification sent to user {telegram_id} for order {order.order_id}")
        
    except Exception as e:
        logger.error(f"Error sending refund notification: {e}")


async def process_automatic_refund(order_id: str, reason: str) -> bool:
    """
    处理自动退款
    
    Args:
        order_id: 订单ID
        reason: 退款原因
        
    Returns:
        退款是否成功
    """
    try:
        with get_db_session() as db:
            order = db.query(Order).filter(Order.order_id == order_id).first()
            if not order:
                logger.error(f"Order not found for refund: {order_id}")
                return False
            
            # 检查订单状态
            if order.status == "refunded":
                logger.warning(f"Order {order_id} already refunded")
                return True
            
            if order.status != "failed":
                logger.warning(f"Order {order_id} is not in failed status, cannot refund")
                return False
            
            # 检查是否已支付
            if order.status not in ["paid", "generating", "failed"]:
                logger.warning(f"Order {order_id} not paid, no refund needed")
                return False
            
            # 执行退款
            refund_success = payment_service.refund_order(order, reason)
            
            # 记录操作日志
            user = db.query(User).filter(User.id == order.user_id).first()
            log_operation(
                operation_type="auto_refund",
                status="success" if refund_success else "failed",
                user_id=order.user_id,
                order_id=order_id,
                operation_detail={
                    "reason": reason,
                    "refund_success": refund_success,
                    "order_status": order.status
                },
                error_message=None if refund_success else "Refund API call failed"
            )
            
            if refund_success:
                # 通知用户
                if user:
                    await notify_user_refund(user.telegram_id, order, reason)
                
                logger.info(f"Automatic refund processed for order {order_id}")
            else:
                logger.error(f"Automatic refund failed for order {order_id}")
            
            return refund_success
            
    except Exception as e:
        logger.error(f"Error processing automatic refund: {e}")
        return False

