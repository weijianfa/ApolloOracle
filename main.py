"""
阿波罗神谕 Telegram Bot - 主入口文件
Apollo Oracle Telegram Bot - Main Entry Point
"""
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.error import Conflict, NetworkError, TimedOut
from bot.config.settings import settings
from bot.utils.logger import setup_logger
from bot.handlers.start import start_command, help_callback
from bot.handlers.product import create_product_conversation_handler

# 设置日志
logger = setup_logger("bot")

# 配置python-telegram-bot的日志级别
logging.getLogger("httpx").setLevel(logging.WARNING)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理 /help 命令
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
    """
    from bot.utils.i18n import get_user_language, translate
    
    # 获取用户语言
    user = update.effective_user
    user_lang = get_user_language(user.language_code)
    
    # 构建帮助文本（使用i18n）
    help_title = translate("help.title", user_lang)
    commands_label = translate("help.commands", user_lang)
    start_cmd = translate("help.start", user_lang)
    help_cmd = translate("help.help", user_lang)
    cancel_cmd = translate("help.cancel", user_lang)
    instructions_label = translate("help.instructions", user_lang)
    step1 = translate("help.step1", user_lang)
    step2 = translate("help.step2", user_lang)
    step3 = translate("help.step3", user_lang)
    step4 = translate("help.step4", user_lang)
    contact = translate("help.contact", user_lang)
    
    help_text = (
        f"{help_title}\n\n"
        f"{commands_label}\n"
        f"{start_cmd}\n"
        f"{help_cmd}\n"
        f"{cancel_cmd}\n\n"
        f"{instructions_label}\n"
        f"{step1}\n"
        f"{step2}\n"
        f"{step3}\n"
        f"{step4}\n\n"
        f"{contact}"
    )
    
    await update.message.reply_text(help_text)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理 /cancel 命令
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
    """
    from bot.handlers.product import cancel_order
    from bot.utils.i18n import get_user_language, translate
    
    # 清除用户数据
    context.user_data.clear()
    
    # 清除数据库会话
    from bot.utils.session_manager import clear_session
    user = update.effective_user
    clear_session(user.id)
    
    # 获取用户语言
    user_lang = get_user_language(user.language_code)
    cancel_text = translate("common.cancel", user_lang)
    
    await update.message.reply_text(cancel_text)


def main():
    """
    主函数 - 启动Bot
    """
    # 验证配置
    try:
        settings.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    # 在启动Polling之前，先清除可能存在的webhook
    # 使用post_init回调来清除webhook，避免事件循环冲突
    async def post_init(application: Application) -> None:
        """应用初始化后的回调，用于清除webhook和启动后台任务"""
        try:
            bot = application.bot
            webhook_info = await bot.get_webhook_info()
            if webhook_info.url:
                logger.info(f"Found existing webhook: {webhook_info.url}, deleting...")
                await bot.delete_webhook(drop_pending_updates=True)
                logger.info("Webhook cleared successfully")
            else:
                logger.info("No webhook found, ready for polling")
        except Exception as e:
            logger.warning(f"Error while clearing webhook: {e}. Continuing anyway...")
        
        # 初始化监控服务并启动后台任务
        try:
            from bot.services.monitor_service import monitor_service
            from bot.utils.monitor_task import start_monitoring_task
            monitor_service.set_bot(application.bot)
            # 在后台启动监控任务
            asyncio.create_task(start_monitoring_task(application))
            logger.info("Background monitoring task started")
        except Exception as e:
            logger.warning(f"Failed to start monitoring task: {e}. Continuing anyway...")
    
    # 创建应用，并设置post_init回调（仅在开发环境）
    builder = Application.builder().token(settings.TELEGRAM_BOT_TOKEN)
    if settings.is_development():
        builder = builder.post_init(post_init)
    else:
        # 生产环境也需要启动监控任务
        async def prod_post_init(application: Application) -> None:
            """生产环境初始化回调"""
            try:
                from bot.services.monitor_service import monitor_service
                from bot.utils.monitor_task import start_monitoring_task
                monitor_service.set_bot(application.bot)
                asyncio.create_task(start_monitoring_task(application))
                logger.info("Background monitoring task started (production)")
            except Exception as e:
                logger.warning(f"Failed to start monitoring task: {e}. Continuing anyway...")
        builder = builder.post_init(prod_post_init)
    application = builder.build()
    
    # 注册命令处理器
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    # 注册回调处理器
    application.add_handler(CallbackQueryHandler(help_callback, pattern=r"^help$"))
    
    # 注册产品对话处理器
    application.add_handler(create_product_conversation_handler())
    
    # 注册支付处理器
    from bot.handlers.payment import register_payment_handlers
    register_payment_handlers(application)
    
    # 注册推广员处理器
    from bot.handlers.affiliate import create_affiliate_conversation_handler, affiliate_stats_command
    application.add_handler(create_affiliate_conversation_handler())
    application.add_handler(CommandHandler("affiliate_stats", affiliate_stats_command))
    
    # 注册管理员处理器
    from bot.handlers.admin import register_admin_handlers
    register_admin_handlers(application)
    
    # 初始化数据库
    try:
        from bot.database.db import init_db
        init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return
    
    # 添加错误处理器
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理所有未捕获的异常"""
        logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
        
        # 如果是Conflict错误，提供更友好的提示
        if isinstance(context.error, Conflict):
            logger.error(
                "Conflict error detected. This usually means:\n"
                "1. Another bot instance is running with the same token\n"
                "2. A previous instance didn't shut down properly\n"
                "3. The bot is running elsewhere (e.g., on a server)\n\n"
                "Solution: Stop all other instances and wait a few seconds before restarting."
            )
    
    application.add_error_handler(error_handler)
    
    # 启动Bot
    logger.info("Bot starting...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Log level: {settings.LOG_LEVEL}")
    
    if settings.is_development():
        # 开发环境使用Polling模式
        logger.info("Using Polling mode (development)")
        
        # 启动Polling
        try:
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                close_loop=False  # 允许在开发环境中正常关闭
            )
        except KeyboardInterrupt:
            # 用户按下 Ctrl+C，优雅关闭
            logger.info("Received KeyboardInterrupt, shutting down gracefully...")
            print("\n🛑 Shutting down bot...")
            logger.info("Bot stopped by user (Ctrl+C)")
            # 不重新抛出异常，允许程序正常退出
        except Conflict as e:
            logger.error(
                f"Conflict error: {e}\n\n"
                "This means another bot instance is running with the same token.\n"
                "Please:\n"
                "1. Stop all other bot instances\n"
                "2. Wait a few seconds\n"
                "3. Try again\n\n"
                "If the problem persists, you may need to:\n"
                "- Check if the bot is running on a server\n"
                "- Check for background processes\n"
                "- Restart your computer if necessary"
            )
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise
    else:
        # 生产环境使用Webhook模式
        logger.info("Using Webhook mode (production)")
        logger.info(f"Webhook URL: {settings.WEBHOOK_URL}")
        application.run_webhook(
            listen=settings.WEBHOOK_LISTEN,
            port=settings.WEBHOOK_PORT,
            url_path="webhook",
            webhook_url=settings.WEBHOOK_URL,
            cert=settings.SSL_CERT_PATH if settings.SSL_CERT_PATH else None
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # 捕获顶层 KeyboardInterrupt，确保优雅退出
        logger.info("Bot stopped by user (Ctrl+C)")
        print("\n✅ Bot stopped gracefully. Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise

