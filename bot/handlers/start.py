"""
/start 命令处理器
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config.products import get_all_products
from bot.utils.logger import logger
from bot.utils.i18n import get_user_language, translate
from bot.database.db import get_db_session
from bot.models.user import User
from bot.models.user_session import UserSession
from sqlalchemy.orm import Session


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理 /start 命令
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
    """
    user = update.effective_user
    
    # 检查是否有推广链接参数
    referral_code = None
    if context.args and len(context.args) > 0:
        ref_arg = context.args[0]
        if ref_arg.startswith("ref_"):
            referral_code = ref_arg[4:]  # 去掉 "ref_" 前缀
            logger.info(f"User {user.id} came from referral: {referral_code}")
    
    # 保存或更新用户信息，并在会话内提取需要的值
    user_language_code = user.language_code or 'en'
    with get_db_session() as db:
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        if not db_user:
            # 创建新用户
            db_user = User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                language_code=user_language_code,
                referred_by=referral_code
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            logger.info(f"New user created: {user.id}")
        else:
            # 更新用户信息
            db_user.username = user.username
            db_user.first_name = user.first_name
            # 在会话内获取当前语言代码
            current_language_code = db_user.language_code or user_language_code
            db_user.language_code = user.language_code or current_language_code
            # 在会话内提取语言代码
            user_language_code = db_user.language_code
            if referral_code and not db_user.referred_by:
                db_user.referred_by = referral_code
            db.commit()
    
    # 清除之前的会话状态
    context.user_data.clear()
    
    # 清除数据库会话（确保没有残留的会话数据）
    from bot.utils.session_manager import clear_session
    try:
        clear_session(user.id)
        logger.info(f"[start_command] Cleared session for user {user.id}")
    except Exception as e:
        logger.warning(f"[start_command] Failed to clear session for user {user.id}: {e}")
        # 会话清除失败不影响继续流程
    
    # 获取用户语言（使用在会话内提取的值）
    user_lang = get_user_language(user_language_code)
    
    # 构建欢迎消息（使用i18n）
    welcome_title = translate("welcome.title", user_lang)
    welcome_greeting = translate("welcome.greeting", user_lang, name=user.first_name)
    select_service = translate("welcome.select_service", user_lang)
    disclaimer = translate("welcome.disclaimer", user_lang)
    
    welcome_text = (
        f"{welcome_title}\n\n"
        f"{welcome_greeting}\n\n"
        f"{select_service}\n\n"
        f"{disclaimer}"
    )
    
    # 创建产品菜单按钮
    products = get_all_products()
    keyboard = []
    
    # 每行显示2个产品按钮
    for i in range(0, len(products), 2):
        row = []
        for j in range(2):
            if i + j < len(products):
                product = products[i + j]
                # 显示产品名称（免费产品不显示价格信息）
                if product.price_usd == 0.00:
                    button_text = product.name_zh
                else:
                    button_text = f"{product.name_zh} ${product.price_usd}"
                row.append(
                    InlineKeyboardButton(
                        button_text,
                        callback_data=f"product_{product.id}"
                    )
                )
        keyboard.append(row)
    
    # 添加帮助按钮
    help_btn_text = translate("common.help_btn", user_lang)
    keyboard.append([
        InlineKeyboardButton(help_btn_text, callback_data="help")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup
    )
    
    logger.info(f"User {user.id} started the bot")


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理帮助按钮回调
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
    """
    query = update.callback_query
    await query.answer()
    
    # 获取用户语言
    user = query.from_user
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
    
    await query.edit_message_text(help_text)

