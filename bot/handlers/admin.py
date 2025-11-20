"""
管理员命令处理器
Admin Command Handlers
"""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from bot.config.settings import settings
from bot.utils.logger import logger
from bot.services.monitor_service import monitor_service
from bot.database.db import get_db_session
from bot.models.order import Order
from bot.models.user import User
from bot.models.affiliate import Affiliate
from bot.utils.i18n import get_user_language, translate
from datetime import datetime, timedelta
from sqlalchemy import func, desc


async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理 /health 命令（管理员查看系统健康状态）
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
    """
    user = update.effective_user
    
    # 检查是否为管理员
    if user.id != settings.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ 此命令仅限管理员使用 / This command is for administrators only")
        return
    
    # 设置Bot实例（如果还没有设置）
    if not monitor_service.bot:
        monitor_service.set_bot(context.bot)
    
    # 获取系统健康状态
    try:
        health = await monitor_service.get_system_health()
        
        if not health:
            await update.message.reply_text("❌ 无法获取系统健康状态 / Unable to get system health")
            return
        
        # 获取用户语言
        user_lang = get_user_language(user.language_code)
        
        # 构建健康报告消息（使用i18n）
        title = translate("admin.health.title", user_lang)
        report = (
            f"{title}\n\n"
            f"⏰ 时间 / Time: {health.get('timestamp', 'N/A')}\n\n"
            f"💳 支付成功率 / Payment Success Rate: {health.get('payment_success_rate', 0) * 100:.2f}%\n"
            f"   成功 / Success: {health.get('payment_stats', {}).get('success', 0)}\n"
            f"   总数 / Total: {health.get('payment_stats', {}).get('total', 0)}\n\n"
            f"🤖 AI调用成功率 / AI Call Success Rate: {health.get('ai_success_rate', 0) * 100:.2f}%\n"
            f"   成功 / Success: {health.get('ai_stats', {}).get('success', 0)}\n"
            f"   总数 / Total: {health.get('ai_stats', {}).get('total', 0)}\n\n"
            f"❌ 总体失败率 / Overall Failure Rate: {health.get('overall_failure_rate', 0) * 100:.2f}%\n"
            f"   失败 / Failed: {health.get('failure_stats', {}).get('failed', 0)}\n"
            f"   总数 / Total: {health.get('failure_stats', {}).get('total', 0)}\n"
        )
        
        # 添加API响应时间
        api_times = health.get('api_response_times', {})
        if api_times:
            report += "\n⏱️ API响应时间 / API Response Times:\n"
            for api_name, avg_time in api_times.items():
                report += f"   {api_name}: {avg_time:.2f}秒 / {avg_time:.2f}s\n"
        else:
            report += "\n⏱️ API响应时间 / API Response Times: 暂无数据 / No data\n"
        
        await update.message.reply_text(report)
        
    except Exception as e:
        logger.error(f"Error in health command: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 获取健康状态时发生错误 / Error getting health status: {e}")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理 /stats 命令（管理员查看订单统计）
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
    """
    user = update.effective_user
    
    # 检查是否为管理员
    if user.id != settings.ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ 此命令仅限管理员使用 / This command is for administrators only")
        return
    
    try:
        with get_db_session() as db:
            # 总订单数
            total_orders = db.query(func.count(Order.id)).scalar() or 0
            
            # 各状态订单数
            pending = db.query(func.count(Order.id)).filter(Order.status == "pending_payment").scalar() or 0
            paid = db.query(func.count(Order.id)).filter(Order.status == "paid").scalar() or 0
            generating = db.query(func.count(Order.id)).filter(Order.status == "generating").scalar() or 0
            completed = db.query(func.count(Order.id)).filter(Order.status == "completed").scalar() or 0
            failed = db.query(func.count(Order.id)).filter(Order.status == "failed").scalar() or 0
            
            # 总销售额
            total_sales = db.query(func.sum(Order.amount_usd)).filter(Order.status == "completed").scalar() or 0
            total_sales = float(total_sales) if total_sales else 0.0
            
            # 今日订单
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_orders = db.query(func.count(Order.id)).filter(Order.created_at >= today_start).scalar() or 0
            today_sales = db.query(func.sum(Order.amount_usd)).filter(
                Order.status == "completed",
                Order.created_at >= today_start
            ).scalar() or 0
            today_sales = float(today_sales) if today_sales else 0.0
            
            # 总用户数
            total_users = db.query(func.count(User.id)).scalar() or 0
            
            # 推广员数
            total_affiliates = db.query(func.count(Affiliate.id)).scalar() or 0
            
            # 获取用户语言
            user_lang = get_user_language(user.language_code)
            
            # 构建统计报告（使用i18n）
            title = translate("admin.stats.title", user_lang)
            report = (
                f"{title}\n\n"
                f"📦 {translate('admin.stats.total_orders', user_lang)}: {total_orders}\n"
                f"   ⏳ {translate('admin.stats.pending', user_lang)}: {pending}\n"
                f"   💳 {translate('admin.stats.paid', user_lang)}: {paid}\n"
                f"   🔄 {translate('admin.stats.generating', user_lang)}: {generating}\n"
                f"   ✅ {translate('admin.stats.completed', user_lang)}: {completed}\n"
                f"   ❌ {translate('admin.stats.failed', user_lang)}: {failed}\n\n"
                f"💰 {translate('admin.stats.total_sales', user_lang)}: ${total_sales:.2f}\n"
                f"📅 {translate('admin.stats.today_orders', user_lang)}: {today_orders}\n"
                f"💰 {translate('admin.stats.today_sales', user_lang)}: ${today_sales:.2f}\n\n"
                f"👥 {translate('admin.stats.total_users', user_lang)}: {total_users}\n"
                f"📢 {translate('admin.stats.total_affiliates', user_lang)}: {total_affiliates}"
            )
            
            await update.message.reply_text(report)
            
    except Exception as e:
        logger.error(f"Error in stats command: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 获取统计信息时发生错误 / Error getting statistics: {e}")


async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理 /orders 命令（管理员查看最近订单）
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
    """
    user = update.effective_user
    
    # 检查是否为管理员
    if user.id != settings.ADMIN_TELEGRAM_ID:
        user_lang = get_user_language(user.language_code)
        error_text = translate("admin.unauthorized", user_lang)
        await update.message.reply_text(error_text)
        return
    
    try:
        limit = 10
        if context.args and len(context.args) > 0:
            try:
                limit = int(context.args[0])
                limit = min(max(limit, 1), 50)  # 限制在1-50之间
            except ValueError:
                pass
        
        with get_db_session() as db:
            # 获取最近订单
            recent_orders = db.query(Order).order_by(desc(Order.created_at)).limit(limit).all()
            
            if not recent_orders:
                user_lang = get_user_language(user.language_code)
                no_orders_text = translate("admin.orders.no_orders", user_lang)
                await update.message.reply_text(no_orders_text)
                return
            
            # 获取用户语言
            user_lang = get_user_language(user.language_code)
            
            # 构建订单列表（使用i18n）
            title = translate("admin.orders.title", user_lang, count=len(recent_orders))
            report = f"{title}\n\n"
            
            for i, order in enumerate(recent_orders, 1):
                status_emoji = {
                    "pending_payment": "⏳",
                    "paid": "💳",
                    "generating": "🔄",
                    "completed": "✅",
                    "failed": "❌"
                }.get(order.status, "❓")
                
                product_label = translate("admin.orders.product", user_lang)
                amount_label = translate("admin.orders.amount", user_lang)
                status_label = translate("admin.orders.status", user_lang)
                time_label = translate("admin.orders.time", user_lang)
                
                report += (
                    f"{i}. {status_emoji} {order.order_id}\n"
                    f"   {product_label}: {order.product_name}\n"
                    f"   {amount_label}: ${order.amount_usd:.2f}\n"
                    f"   {status_label}: {order.status}\n"
                    f"   {time_label}: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                )
            
            await update.message.reply_text(report)
            
    except Exception as e:
        logger.error(f"Error in orders command: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 获取订单列表时发生错误 / Error getting orders: {e}")


async def affiliates_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理 /affiliates 命令（管理员查看推广员列表）
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
    """
    user = update.effective_user
    
    # 检查是否为管理员
    if user.id != settings.ADMIN_TELEGRAM_ID:
        user_lang = get_user_language(user.language_code)
        error_text = translate("admin.unauthorized", user_lang)
        await update.message.reply_text(error_text)
        return
    
    try:
        limit = 10
        if context.args and len(context.args) > 0:
            try:
                limit = int(context.args[0])
                limit = min(max(limit, 1), 50)  # 限制在1-50之间
            except ValueError:
                pass
        
        with get_db_session() as db:
            # 获取推广员列表（按销售额排序）
            affiliates = db.query(Affiliate).order_by(desc(Affiliate.total_sales)).limit(limit).all()
            
            if not affiliates:
                user_lang = get_user_language(user.language_code)
                no_affiliates_text = translate("admin.affiliates.no_affiliates", user_lang)
                await update.message.reply_text(no_affiliates_text)
                return
            
            # 获取用户语言
            user_lang = get_user_language(user.language_code)
            
            # 构建推广员列表（使用i18n）
            title = translate("admin.affiliates.title", user_lang, count=len(affiliates))
            report = f"{title}\n\n"
            
            for i, affiliate in enumerate(affiliates, 1):
                # 获取用户信息
                db_user = db.query(User).filter(User.id == affiliate.user_id).first()
                username = db_user.username if db_user else "N/A"
                
                user_label = translate("admin.affiliates.user", user_lang)
                sales_label = translate("admin.affiliates.sales", user_lang)
                commission_label = translate("admin.affiliates.commission", user_lang)
                tier_label = translate("admin.affiliates.tier", user_lang)
                
                report += (
                    f"{i}. {affiliate.affiliate_code}\n"
                    f"   {user_label}: @{username}\n"
                    f"   {sales_label}: ${float(affiliate.total_sales):.2f}\n"
                    f"   {commission_label}: ${float(affiliate.total_commission):.2f}\n"
                    f"   {tier_label}: {affiliate.current_tier}\n\n"
                )
            
            await update.message.reply_text(report)
            
    except Exception as e:
        logger.error(f"Error in affiliates command: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 获取推广员列表时发生错误 / Error getting affiliates: {e}")


def register_admin_handlers(application):
    """
    注册管理员命令处理器
    
    Args:
        application: Telegram Application实例
    """
    # 只在配置了管理员ID时注册
    if settings.ADMIN_TELEGRAM_ID:
        application.add_handler(CommandHandler("health", health_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("orders", orders_command))
        application.add_handler(CommandHandler("affiliates", affiliates_command))
        logger.info("Admin handlers registered (health, stats, orders, affiliates)")
    else:
        logger.warning("ADMIN_TELEGRAM_ID not configured, admin handlers not registered")

