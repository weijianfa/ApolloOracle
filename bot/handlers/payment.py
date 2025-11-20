"""
支付相关处理器
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler
from bot.services.payment_service import payment_service
from bot.utils.logger import logger
from bot.utils.i18n import get_user_language, translate
from bot.database.db import get_db_session
from bot.models.order import Order
from bot.models.user import User
from bot.config.settings import settings
import json
from bot.utils.session_manager import clear_session


async def confirm_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    处理确认订单回调
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
    """
    query = update.callback_query
    user = query.from_user
    
    # 尝试回答回调查询（如果查询已过期，捕获异常）
    try:
        await query.answer()
    except Exception as e:
        # 查询可能已过期，但仍然继续处理用户的意图
        logger.warning(f"Callback query answer failed (may be expired): {e}")
        # 获取用户语言
        user_lang = get_user_language(user.language_code)
        # 发送新消息告知用户
        try:
            expired_text = translate("order.expired", user_lang)
            restart_text = translate("order.expired_restart", user_lang)
            await query.message.reply_text(f"{expired_text}\n\n{restart_text}")
        except:
            pass
        # 清除会话数据
        context.user_data.clear()
        clear_session(user.id)
        return ConversationHandler.END
    
    # 用户已经做出确认，立刻移除“确认/取消”按钮，避免重复点击
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception as e:
        logger.warning(f"Failed to remove confirmation buttons: {e}")
    
    # 获取用户数据
    product = context.user_data.get("product")
    input_data = context.user_data.get("input_data", {})
    product_id = context.user_data.get("product_id")
    
    # 获取用户语言
    user_lang = get_user_language(user.language_code)
    
    if not product or not product_id:
        error_text = translate("order.info_lost", user_lang)
        await query.edit_message_text(error_text)
        context.user_data.clear()
        clear_session(user.id)
        return ConversationHandler.END
    
    try:
        # 获取数据库用户
        with get_db_session() as db:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                error_text = translate("order.user_error", user_lang)
                await query.edit_message_text(error_text)
                context.user_data.clear()
                clear_session(user.id)
                return ConversationHandler.END
            
            # 获取推广员代码（从用户的referred_by字段获取，仅在首次支付时绑定）
            affiliate_code = None
            if hasattr(db_user, 'referred_by') and db_user.referred_by:
                # 检查用户是否已有已完成的订单（如果有，说明不是首次支付，不再绑定推广关系）
                existing_completed_order = db.query(Order).filter(
                    Order.user_id == db_user.id,
                    Order.status == "completed"
                ).first()
                
                if not existing_completed_order:
                    # 首次支付，绑定推广关系
                    affiliate_code = db_user.referred_by
                    logger.info(f"Binding affiliate code {affiliate_code} to user {db_user.id} for first payment")
                else:
                    logger.info(f"User {db_user.id} already has completed orders, not binding new affiliate code")
            
            # 创建订单（返回order_id字符串）
            order_id = payment_service.create_order(
                user_id=db_user.id,
                product_id=product_id,
                product_name=product.name_zh,
                amount_usd=float(product.price_usd),
                user_input=input_data,
                affiliate_code=affiliate_code
            )
            
            if not order_id:
                error_text = translate("order.failed", user_lang)
                await query.edit_message_text(error_text)
                context.user_data.clear()
                clear_session(user.id)
                return ConversationHandler.END
            
            # 在当前会话中查询订单对象（用于后续操作）
            db_order = db.query(Order).filter(Order.order_id == order_id).first()
            if not db_order:
                error_text = translate("order.query_failed", user_lang)
                await query.edit_message_text(error_text)
                context.user_data.clear()
                clear_session(user.id)
                return ConversationHandler.END
            
            # 检查是否为免费产品（每日塔罗）
            if product.price_usd == 0.00:
                # 免费产品，直接处理订单，无需支付
                # db_order 已经在上面查询过了
                
                # 保存必要的值
                user_id = db_user.id
                product_name_zh = product.name_zh
                product_name_en = product.name_en
                
                logger.info(f"Free product detected, processing order {order_id} directly")
                
                # 更新订单状态为已支付（免费产品）
                db_order.status = "paid"
                db.commit()
                
                # 注意：db.commit() 后，order 对象可能已脱离会话，使用保存的变量
                
                # 显示处理中消息（使用i18n）
                processing_msg = translate("payment.free_processing_msg", user_lang, 
                                         product_zh=product_name_zh, 
                                         product_en=product_name_en, 
                                         order_id=order_id)
                await query.edit_message_text(processing_msg)
                
                # 清除会话数据
                context.user_data.clear()
                clear_session(user.id)
                
                # 直接触发订单处理流程
                from bot.services.order_processor import order_processor
                import asyncio
                
                # 在后台任务中处理订单（使用保存的 order_id）
                # 添加异常处理，确保后台任务的异常能被捕获和记录
                async def process_order_with_error_handling(order_id: str):
                    """包装订单处理，添加异常处理"""
                    try:
                        logger.info(f"Background task started for order {order_id}")
                        success = await order_processor.process_paid_order(order_id)
                        if success:
                            logger.info(f"Background task completed successfully for order {order_id}")
                        else:
                            logger.error(f"Background task failed for order {order_id} (process_paid_order returned False)")
                            # 获取订单信息以便通知用户
                            try:
                                with get_db_session() as db:
                                    order = db.query(Order).filter(Order.order_id == order_id).first()
                                    if order:
                                        # 通知用户处理失败
                                        await order_processor._notify_user_generation_failed(
                                            telegram_id=db.query(User).filter(User.id == order.user_id).first().telegram_id,
                                            order_id=order_id,
                                            product_name=order.product_name,
                                            is_free_product=(order.amount_usd == 0.0)
                                        )
                            except Exception as notify_error:
                                logger.error(f"Failed to notify user after background task failure: {notify_error}")
                    except Exception as e:
                        logger.error(f"Unhandled exception in background task for order {order_id}: {e}", exc_info=True)
                        # 更新订单状态为失败并通知用户
                        try:
                            with get_db_session() as db:
                                order = db.query(Order).filter(Order.order_id == order_id).first()
                                if order:
                                    order.status = "failed"
                                    order.error_message = f"Background task error: {str(e)}"
                                    db.commit()
                                    
                                    # 通知用户
                                    user = db.query(User).filter(User.id == order.user_id).first()
                                    if user:
                                        await order_processor._notify_user_generation_failed(
                                            telegram_id=user.telegram_id,
                                            order_id=order_id,
                                            product_name=order.product_name,
                                            is_free_product=(order.amount_usd == 0.0)
                                        )
                        except Exception as db_error:
                            logger.error(f"Failed to update order status after background task error: {db_error}", exc_info=True)
                
                # 启动后台任务
                asyncio.create_task(process_order_with_error_handling(order_id))
                
                logger.info(f"Free order {order_id} processing started for user {user_id}")
                return ConversationHandler.END
            
            # 付费产品，创建支付链接
            # 注意：这里需要根据实际部署的URL调整
            return_url = f"{settings.WEBHOOK_URL}/payment/success" if settings.WEBHOOK_URL else "https://t.me/your_bot"
            cancel_url = f"{settings.WEBHOOK_URL}/payment/cancel" if settings.WEBHOOK_URL else "https://t.me/your_bot"
            
            # 使用 db_order（在当前会话中）创建支付链接
            payment_url = payment_service.create_payment_link(
                order=db_order,
                return_url=return_url,
                cancel_url=cancel_url
            )
            
            if not payment_url:
                # 更新订单状态为失败（使用db_order，它在当前会话中）
                db_order.status = "failed"
                db_order.error_message = "Failed to create payment link"
                db.commit()
                
                error_text = translate("error.general", user_lang, error="Failed to create payment link")
                await query.edit_message_text(error_text)
                context.user_data.clear()
                clear_session(user.id)
                return ConversationHandler.END
            
            # 显示支付信息（使用i18n）
            payment_info = translate("payment.info", user_lang)
            order_id_label = translate("report.order_id", user_lang, order_id=order_id)
            product_label = translate("product.product_name", user_lang, name=f"{product.name_zh} / {product.name_en}")
            amount_label = translate("payment.amount", user_lang, amount=product.price_usd)
            link_label = translate("payment.link", user_lang)
            timeout_label = translate("payment.timeout", user_lang)
            
            payment_text = (
                f"{payment_info}\n\n"
                f"{order_id_label}\n"
                f"{product_label}\n"
                f"{amount_label}\n\n"
                f"{link_label}\n\n"
                f"⚠️ {timeout_label}"
            )
            
            pay_now_text = "💳 立即支付 / Pay Now" if user_lang == 'zh' else "💳 Pay Now"
            cancel_order_text = translate("product.cancel_order", user_lang)
            keyboard = [
                [InlineKeyboardButton(pay_now_text, url=payment_url)],
                [InlineKeyboardButton(cancel_order_text, callback_data="cancel_order")]
            ]
            
            if payment_service.is_mock_mode():
                mock_success_text = translate("payment.mock_success", user_lang)
                mock_failed_text = translate("payment.mock_failed", user_lang)
                mock_info = "\n\n🧪 当前运行在模拟支付模式，点击下方按钮可直接模拟支付结果。\n🧪 Mock payment mode is active. Use the buttons below to simulate the outcome." if user_lang == 'zh' else "\n\n🧪 Mock payment mode is active. Use the buttons below to simulate the outcome."
                payment_text += mock_info
                keyboard.append([
                    InlineKeyboardButton(mock_success_text, callback_data=f"mock_pay_success:{order_id}"),
                    InlineKeyboardButton(mock_failed_text, callback_data=f"mock_pay_failed:{order_id}")
                ])
            
            await query.edit_message_text(
                payment_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # 清除会话数据
            context.user_data.clear()
            clear_session(user.id)
            
            # 使用已保存的 order_id（db_order 在当前会话中）
            logger.info(f"Order {order_id} created for user {db_user.id}")
            return ConversationHandler.END
            
    except Exception as e:
        logger.error(f"Error in confirm_order_callback: {e}", exc_info=True)
        error_text = translate("error.general", user_lang, error="Error processing order")
        await query.edit_message_text(error_text)
        context.user_data.clear()
        clear_session(user.id)
        return ConversationHandler.END


async def check_payment_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    检查支付状态（用户主动查询）
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
    """
    user = update.effective_user
    
    try:
        with get_db_session() as db:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ 用户信息错误 / User information error")
                return
            
            # 查找用户最近的订单
            recent_order = db.query(Order).filter(
                Order.user_id == db_user.id
            ).order_by(Order.created_at.desc()).first()
            
            if not recent_order:
                await update.message.reply_text(
                    "📋 您还没有订单 / You have no orders yet"
                )
                return
            
            # 显示订单状态
            status_texts = {
                "pending_payment": "⏳ 等待支付 / Pending Payment",
                "paid": "✅ 已支付 / Paid",
                "generating": "🔄 正在生成报告 / Generating Report",
                "completed": "✅ 已完成 / Completed",
                "failed": "❌ 失败 / Failed",
                "refunded": "💰 已退款 / Refunded"
            }
            
            status_text = status_texts.get(recent_order.status, recent_order.status)
            
            order_info = (
                f"📋 订单信息 / Order Information\n\n"
                f"订单号 / Order ID: {recent_order.order_id}\n"
                f"产品 / Product: {recent_order.product_name}\n"
                f"金额 / Amount: ${recent_order.amount_usd} USD\n"
                f"状态 / Status: {status_text}\n"
                f"创建时间 / Created: {recent_order.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            await update.message.reply_text(order_info)
            
    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        await update.message.reply_text(
            "❌ 查询订单状态时发生错误 / Error checking order status"
        )


async def mock_payment_result_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    模拟支付按钮回调（开发环境）
    """
    query = update.callback_query
    await query.answer()
    
    if not payment_service.is_mock_mode():
        await query.edit_message_text("❌ 模拟支付模式未启用 / Mock payment mode is disabled")
        return
    
    try:
        data = query.data.split(":")
        if len(data) != 2:
            await query.edit_message_text("❌ 无效的模拟支付参数 / Invalid mock payment parameters")
            return
        
        action, order_id = data[0], data[1]
        status = "paid" if action == "mock_pay_success" else "failed"
        
        with get_db_session() as db:
            order = db.query(Order).filter(Order.order_id == order_id).first()
            if not order:
                await query.edit_message_text("❌ 未找到订单 / Order not found")
                return
            
            user = db.query(User).filter(User.id == order.user_id).first()
            if not user or user.telegram_id != query.from_user.id:
                await query.edit_message_text("❌ 只能模拟自身订单的支付 / You can only simulate payments for your own orders")
                return
        
        info_text = "✅ 模拟支付成功，正在生成报告..." if status == "paid" else "⚠️ 模拟支付失败，订单已标记为失败"
        await query.edit_message_text(
            f"{info_text}\n\nOrder ID: {order_id}"
        )
        
        error_message = None if status == "paid" else "Mock payment failure"
        await payment_service.simulate_mock_payment(order_id, status=status, error_message=error_message)
        
    except Exception as e:
        logger.error(f"Error in mock_payment_result_callback: {e}", exc_info=True)
        await query.edit_message_text("❌ 模拟支付时发生错误 / Error during mock payment simulation")


def register_payment_handlers(application):
    """
    注册支付相关处理器
    
    Args:
        application: Telegram应用实例
    """
    from bot.config.settings import settings
    
    # 注册确认订单回调
    application.add_handler(
        CallbackQueryHandler(confirm_order_callback, pattern=r"^confirm_order$")
    )
    
    application.add_handler(
        CallbackQueryHandler(mock_payment_result_callback, pattern=r"^mock_pay_(success|failed):")
    )

