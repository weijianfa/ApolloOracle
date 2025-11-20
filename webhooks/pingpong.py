"""
PingPong支付Webhook处理器
"""
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
import json
from bot.services.payment_service import payment_service
from bot.utils.logger import logger
from bot.utils.operation_logger import log_operation
from bot.database.db import get_db_session
from bot.models.order import Order

router = APIRouter()


@router.post("/webhook/pingpong")
async def pingpong_webhook(
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature")
):
    """
    处理PingPong支付Webhook
    
    Args:
        request: FastAPI请求对象
        x_signature: 请求签名（从Header获取）
        
    Returns:
        Webhook响应
    """
    try:
        # 获取请求体
        payload = await request.json()
        
        # 验证签名
        if not x_signature:
            logger.warning("No signature in webhook request")
            raise HTTPException(status_code=401, detail="Missing signature")
        
        # 处理支付Webhook
        success = payment_service.process_payment_webhook(payload, x_signature)
        
        if success:
            # [步骤1] 支付成功验证完成
            # 根据PRD文档"2.调用时机与流程"：支付成功并通过PingPong Webhook验证后，触发后续流程
            # 后续流程将首先调用八字接口，然后将八字数据作为核心依据传递给AI生成层
            order_id = payload.get("order_id")
            if order_id and payload.get("status") == "paid":
                logger.info(f"[步骤1完成] 支付成功验证完成，开始触发订单处理流程 for order {order_id}")
                # 立即通知用户支付成功，并告知正在生成报告
                await notify_user_payment_success(order_id)
                # 然后触发订单处理流程
                await trigger_order_processing(order_id)
            
            return {"status": "success", "message": "Webhook processed"}
        else:
            logger.warning(f"Failed to process webhook for order {payload.get('order_id')}")
            raise HTTPException(status_code=400, detail="Failed to process webhook")
            
    except Exception as e:
        logger.error(f"Error processing PingPong webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def notify_user_payment_success(order_id: str):
    """
    通知用户支付成功，并告知正在生成报告
    
    Args:
        order_id: 订单ID
    """
    try:
        from bot.database.db import get_db_session
        from bot.models.order import Order
        from bot.models.user import User
        from bot.config.settings import settings
        from bot.utils.i18n import get_user_language, translate
        from telegram import Bot
        
        with get_db_session() as db:
            order = db.query(Order).filter(Order.order_id == order_id).first()
            if not order:
                logger.error(f"Order not found for payment success notification: {order_id}")
                return
            
            user = db.query(User).filter(User.id == order.user_id).first()
            if not user:
                logger.error(f"User not found for order {order_id}")
                return
            
            # 获取用户语言
            user_lang = get_user_language(user.language_code)
            
            # 构建通知消息
            payment_success_text = translate("payment.success", user_lang)
            generating_text = translate("payment.generating", user_lang)
            order_id_text = translate("payment.order_id", user_lang)
            product_text = translate("payment.product", user_lang)
            amount_text = translate("payment.amount_label", user_lang)
            wait_text = translate("payment.wait", user_lang)
            
            message = (
                f"✅ {payment_success_text}\n\n"
                f"{order_id_text}: `{order_id}`\n"
                f"{product_text}: {order.product_name}\n"
                f"{amount_text}: ${float(order.amount_usd):.2f} USD\n\n"
                f"🔄 {generating_text}\n"
                f"{wait_text}"
            )
            
            # 发送消息给用户
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            await bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="Markdown"
            )
            
            logger.info(f"Payment success notification sent to user {user.telegram_id} for order {order_id}")
            
    except Exception as e:
        logger.error(f"Error sending payment success notification: {e}", exc_info=True)


async def trigger_order_processing(order_id: str):
    """
    触发订单后续处理流程
    
    根据PRD文档"2.调用时机与流程"的要求：
    1. 支付成功验证（已完成）
    2. 首先调用八字接口（缘分居API）- 获取结构化数据
    3. 将八字数据作为核心依据传递给AI生成层
    4. AI生成报告并发送给用户
    
    Args:
        order_id: 订单ID
    """
    try:
        from bot.services.order_processor import order_processor
        
        # 异步处理订单
        success = await order_processor.process_paid_order(order_id)
        
        if success:
            logger.info(f"Order {order_id} processing started successfully")
        else:
            logger.error(f"Order {order_id} processing failed")
            
    except Exception as e:
        logger.error(f"Error triggering order processing: {e}")

