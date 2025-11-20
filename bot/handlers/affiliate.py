"""
推广员相关处理器
Affiliate Handler
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from bot.services.affiliate_service import affiliate_service
from bot.utils.logger import logger
from bot.utils.i18n import get_user_language, translate
from bot.database.db import get_db_session
from bot.models.user import User
from bot.config.settings import settings

# 对话状态定义
(
    VIEWING_AGREEMENT,
    ENTERING_NAME,
    ENTERING_CONTACT,
    ENTERING_ACCOUNT,
) = range(4)


async def apply_affiliate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    处理 /apply_affiliate 命令
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
    
    Returns:
        下一个对话状态
    """
    user = update.effective_user
    
    # 获取用户语言
    user_lang = get_user_language(user.language_code)
    
    # 检查用户是否已经是推广员
    with get_db_session() as db:
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        if not db_user:
            await update.message.reply_text(translate("error.general", user_lang, error="User not found"))
            return ConversationHandler.END
        
        if db_user.is_affiliate:
            # 已经是推广员，显示推广码和链接
            affiliate = affiliate_service.get_affiliate_by_user_id(db_user.id)
            if affiliate:
                # 获取bot用户名（从bot信息获取）
                try:
                    bot_info = await context.bot.get_me()
                    bot_username = bot_info.username
                except:
                    bot_username = "your_bot"  # 默认值
                
                referral_link = affiliate_service.generate_referral_link(affiliate.affiliate_code, bot_username)
                already_text = translate("affiliate.apply.already", user_lang, code=affiliate.affiliate_code)
                await update.message.reply_text(f"{already_text}\n\n{referral_link}")
            else:
                await update.message.reply_text(translate("affiliate.apply.failed", user_lang))
            return ConversationHandler.END
    
    # 显示推广员协议
    title = translate("affiliate.apply.title", user_lang)
    description = translate("affiliate.apply.description", user_lang)
    agreement = translate("affiliate.apply.agreement", user_lang)
    
    agreement_text = (
        f"{title}\n\n"
        f"{description}\n\n"
        f"{agreement}"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(
                translate("affiliate.apply.confirm", user_lang),
                callback_data="affiliate_agree"
            ),
            InlineKeyboardButton(
                translate("affiliate.apply.cancel", user_lang),
                callback_data="affiliate_cancel"
            )
        ]
    ]
    
    await update.message.reply_text(
        agreement_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return VIEWING_AGREEMENT


async def affiliate_agree_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理同意协议回调"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_lang = get_user_language(user.language_code)
    
    # 清除协议消息的按钮
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except:
        pass
    
    # 开始收集信息
    name_prompt = translate("affiliate.apply.input_name", user_lang)
    await query.message.reply_text(name_prompt)
    
    return ENTERING_NAME


async def affiliate_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理取消申请回调"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_lang = get_user_language(user.language_code)
    
    cancel_text = translate("common.cancel", user_lang)
    await query.edit_message_text(cancel_text)
    
    return ConversationHandler.END


async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理姓名输入"""
    user = update.effective_user
    user_lang = get_user_language(user.language_code)
    
    real_name = update.message.text.strip()
    
    if len(real_name) < 2:
        await update.message.reply_text(translate("input.invalid", user_lang))
        return ENTERING_NAME
    
    # 保存姓名
    context.user_data["affiliate_real_name"] = real_name
    
    # 请求联系方式
    contact_prompt = translate("affiliate.apply.input_contact", user_lang)
    await update.message.reply_text(contact_prompt)
    
    return ENTERING_CONTACT


async def handle_contact_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理联系方式输入"""
    user = update.effective_user
    user_lang = get_user_language(user.language_code)
    
    contact_info = update.message.text.strip()
    
    if len(contact_info) < 3:
        await update.message.reply_text(translate("input.invalid", user_lang))
        return ENTERING_CONTACT
    
    # 保存联系方式
    context.user_data["affiliate_contact"] = contact_info
    
    # 请求收款账户
    account_prompt = translate("affiliate.apply.input_account", user_lang)
    await update.message.reply_text(account_prompt)
    
    return ENTERING_ACCOUNT


async def handle_account_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理收款账户输入"""
    user = update.effective_user
    user_lang = get_user_language(user.language_code)
    
    payout_account = update.message.text.strip()
    
    if len(payout_account) < 3:
        await update.message.reply_text(translate("input.invalid", user_lang))
        return ENTERING_ACCOUNT
    
    # 获取保存的信息
    real_name = context.user_data.get("affiliate_real_name")
    contact_info = context.user_data.get("affiliate_contact")
    
    if not real_name or not contact_info:
        await update.message.reply_text(translate("error.general", user_lang, error="Missing information"))
        context.user_data.clear()
        return ConversationHandler.END
    
    # 注册推广员
    with get_db_session() as db:
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        if not db_user:
            await update.message.reply_text(translate("error.general", user_lang, error="User not found"))
            context.user_data.clear()
            return ConversationHandler.END
        
        affiliate_code = affiliate_service.register_affiliate(
            user_id=db_user.id,
            real_name=real_name,
            contact_info=contact_info,
            payout_account=payout_account
        )
        
        if affiliate_code:
            # 获取bot用户名
            try:
                bot_info = await context.bot.get_me()
                bot_username = bot_info.username
            except:
                bot_username = "your_bot"
            
            referral_link = affiliate_service.generate_referral_link(affiliate_code, bot_username)
            
            success_text = translate("affiliate.apply.success", user_lang, code=affiliate_code, link=referral_link)
            await update.message.reply_text(success_text)
            
            # 通知管理员
            try:
                if settings.ADMIN_TELEGRAM_ID:
                    await context.bot.send_message(
                        chat_id=settings.ADMIN_TELEGRAM_ID,
                        text=(
                            f"📢 新推广员注册\n\n"
                            f"用户ID: {user.id}\n"
                            f"用户名: @{user.username or 'N/A'}\n"
                            f"真实姓名: {real_name}\n"
                            f"联系方式: {contact_info}\n"
                            f"推广码: {affiliate_code}"
                        )
                    )
            except Exception as e:
                logger.warning(f"Failed to notify admin about new affiliate: {e}")
        else:
            await update.message.reply_text(translate("affiliate.apply.failed", user_lang))
    
    context.user_data.clear()
    return ConversationHandler.END


async def affiliate_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理 /affiliate_stats 命令（查看推广员统计）
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
    """
    user = update.effective_user
    user_lang = get_user_language(user.language_code)
    
    with get_db_session() as db:
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        if not db_user:
            await update.message.reply_text(translate("error.general", user_lang, error="User not found"))
            return
        
        if not db_user.is_affiliate:
            not_affiliate_text = translate("affiliate.stats.not_affiliate", user_lang)
            await update.message.reply_text(not_affiliate_text)
            return
        
        # 获取统计信息
        stats = affiliate_service.get_affiliate_stats(db_user.id)
        if not stats:
            await update.message.reply_text(translate("error.general", user_lang, error="Failed to get stats"))
            return
        
        # 获取bot用户名
        try:
            bot_info = await context.bot.get_me()
            bot_username = bot_info.username
        except:
            bot_username = "your_bot"
        
        referral_link = affiliate_service.generate_referral_link(stats["affiliate_code"], bot_username)
        
        # 构建统计信息文本
        title = translate("affiliate.stats.title", user_lang)
        code_text = translate("affiliate.stats.code", user_lang, code=stats["affiliate_code"])
        sales_text = translate("affiliate.stats.sales", user_lang, sales=f"{stats['total_sales']:.2f}")
        commission_text = translate("affiliate.stats.commission", user_lang, commission=f"{stats['total_commission']:.2f}")
        tier_text = translate("affiliate.stats.tier", user_lang, tier=stats["current_tier"], rate=f"{stats['current_rate']*100:.0f}")
        link_text = translate("affiliate.stats.link", user_lang, link=referral_link)
        
        stats_text = (
            f"{title}\n\n"
            f"{code_text}\n"
            f"{sales_text}\n"
            f"{commission_text}\n"
            f"{tier_text}\n"
        )
        
        if stats.get("next_tier_sales") and stats["next_tier_sales"] > 0:
            next_tier_text = translate("affiliate.stats.next_tier", user_lang, amount=f"{stats['next_tier_sales']:.2f}")
            stats_text += f"{next_tier_text}\n"
        
        if stats.get("bonus_eligible"):
            bonus_text = translate("affiliate.stats.bonus", user_lang)
            stats_text += f"\n{bonus_text}\n"
        
        stats_text += f"\n{link_text}"
        
        await update.message.reply_text(stats_text)


def create_affiliate_conversation_handler() -> ConversationHandler:
    """
    创建推广员申请对话处理器
    
    Returns:
        ConversationHandler实例
    """
    return ConversationHandler(
        entry_points=[CommandHandler("apply_affiliate", apply_affiliate_command)],
        states={
            VIEWING_AGREEMENT: [
                CallbackQueryHandler(affiliate_agree_callback, pattern="^affiliate_agree$"),
                CallbackQueryHandler(affiliate_cancel_callback, pattern="^affiliate_cancel$"),
            ],
            ENTERING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input),
            ],
            ENTERING_CONTACT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contact_input),
            ],
            ENTERING_ACCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account_input),
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        per_message=False
    )

