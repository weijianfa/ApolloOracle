"""
产品选择和对话流程处理器
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from bot.config.products import get_product, ZODIAC_SIGNS, CHINESE_ZODIAC
from bot.utils.logger import logger
from bot.utils.i18n import get_user_language, translate
from bot.utils.validators import (
    validate_date, validate_time, validate_name, 
    validate_zodiac, validate_chinese_zodiac, validate_gender, normalize_gender
)
from bot.database.db import get_db_session
from bot.models.user_session import UserSession
from bot.models.user import User
import json
from datetime import datetime, timedelta

# 对话状态定义
(
    SELECTING_PRODUCT,
    INPUTTING_DATA,
    CONFIRMING_ORDER,
) = range(3)


async def _remove_instruction_message(context: ContextTypes.DEFAULT_TYPE, bot):
    """
    移除“请按提示输入所需信息”指引消息，避免在完成输入后仍然显示
    """
    message_id = context.user_data.pop("instruction_message_id", None)
    chat_id = context.user_data.pop("instruction_chat_id", None)
    
    if not message_id or not chat_id:
        return
    
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.warning(f"Failed to remove instruction message: {e}")


async def product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    处理产品选择回调
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
        
    Returns:
        下一个对话状态
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # 解析产品ID
        product_id = int(query.data.split("_")[1])
        product = get_product(product_id)
        user = query.from_user
        
        if not product:
            # 获取用户语言
            user_lang = get_user_language(user.language_code)
            error_text = translate("product.not_found", user_lang)
            await query.edit_message_text(error_text)
            return ConversationHandler.END
        
        # 清除之前的会话数据（避免残留数据影响新订单）
        context.user_data.clear()
        
        # 保存产品ID到上下文
        context.user_data["product_id"] = product_id
        context.user_data["product"] = product
        context.user_data["input_data"] = {}
        
        # 保存会话状态到数据库
        from bot.utils.session_manager import save_session
        try:
            save_session(user.id, "selecting_product", {"product_id": product_id}, product_id)
            logger.info(f"[product_callback] Session saved for user {user.id}, product {product_id}")
        except Exception as session_error:
            logger.error(f"[product_callback] Failed to save session for user {user.id}: {session_error}", exc_info=True)
            # 会话保存失败不影响继续流程
    
        # 显示产品信息
        # 构建产品介绍文本
        product_text = f"📦 {product.name_zh} / {product.name_en}\n"
        # 免费产品不显示价格
        if product.price_usd > 0.00:
            product_text += f"💰 价格 / Price: ${product.price_usd}\n"
        product_text += f"📝 {product.description_zh}\n"
        product_text += f"{product.description_en}\n\n"
        
        # 获取用户语言
        user_lang = get_user_language(user.language_code)
        
        # 如果不需要输入，直接进入确认
        if not product.input_fields:
            confirm_text = translate("product.confirm_order", user_lang)
            cancel_text = translate("product.cancel_order", user_lang)
            keyboard = [
                [
                    InlineKeyboardButton(confirm_text, callback_data="confirm_order"),
                    InlineKeyboardButton(cancel_text, callback_data="cancel_order")
                ]
            ]
            await query.edit_message_text(
                product_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return CONFIRMING_ORDER
        
        # 需要输入信息
        input_required_text = translate("product.input_required", user_lang)
        product_text += f"{input_required_text}\n\n"
        
        # 显示需要输入的字段
        field_names = {
            "zodiac": "星座 / Zodiac Sign",
            "name": "姓名 / Name",
            "gender": "性别 / Gender",
            "birthday": "出生日期 / Birthday (YYYY-MM-DD)",
            "birth_time": "出生时间 / Birth Time (HH:MM)",
            "zodiac_a": "第一个人的生肖 / First Person's Zodiac",
            "zodiac_b": "第二个人的生肖 / Second Person's Zodiac",
            "gender_a": "第一个人的性别 / First Person's Gender",
            "gender_b": "第二个人的性别 / Second Person's Gender",
        }
        
        needed_fields = []
        for field in product.input_fields:
            if field not in context.user_data["input_data"]:
                needed_fields.append(field)
                product_text += f"• {field_names.get(field, field)}\n"
        
        # 开始输入流程
        context.user_data["needed_fields"] = needed_fields
        context.user_data["current_field_index"] = 0
        
        instruction_message = await query.edit_message_text(product_text)
        context.user_data["instruction_message_id"] = instruction_message.message_id
        context.user_data["instruction_chat_id"] = instruction_message.chat_id
        
        # 发送第一个输入提示
        return await prompt_next_input(update, context)
    
    except Exception as e:
        logger.error(f"[product_callback] Error processing product selection: {e}", exc_info=True)
        try:
            await query.edit_message_text(
                "❌ 处理产品选择时发生错误，请稍后重试 / Error processing product selection, please try again later"
            )
        except:
            pass
        # 清除会话数据
        context.user_data.clear()
        if update.callback_query:
            user = update.callback_query.from_user
            from bot.utils.session_manager import clear_session
            clear_session(user.id)
        return ConversationHandler.END


async def prompt_next_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    提示下一个输入
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
        
    Returns:
        对话状态
    """
    needed_fields = context.user_data.get("needed_fields", [])
    current_index = context.user_data.get("current_field_index", 0)
    
    logger.info(f"[prompt_next_input] needed_fields={needed_fields}, current_index={current_index}, len={len(needed_fields)}")
    
    if current_index >= len(needed_fields):
        # 所有输入完成，进入确认
        logger.info(f"[prompt_next_input] All fields completed, showing confirmation")
        return await show_confirmation(update, context)
    
    current_field = needed_fields[current_index]
    product = context.user_data.get("product")
    
    # 优先使用 update.message.chat.id（如果存在），然后尝试其他方式
    chat_id = None
    if update.message and update.message.chat:
        chat_id = update.message.chat.id
        logger.debug(f"[prompt_next_input] Using chat_id from update.message.chat.id: {chat_id}")
    elif update.effective_chat and update.effective_chat.id:
        chat_id = update.effective_chat.id
        logger.debug(f"[prompt_next_input] Using chat_id from update.effective_chat.id: {chat_id}")
    elif update.effective_user and update.effective_user.id:
        chat_id = update.effective_user.id
        logger.debug(f"[prompt_next_input] Using chat_id from update.effective_user.id: {chat_id}")
    
    if not chat_id:
        logger.error(f"[prompt_next_input] Unable to determine chat_id. update.message={update.message}, update.effective_chat={update.effective_chat}, update.effective_user={update.effective_user}")
        return INPUTTING_DATA
    
    logger.info(f"[prompt_next_input] Prompting user {chat_id} for field: {current_field} (index {current_index})")
    
    # 获取用户语言
    user = update.effective_user
    from bot.database.db import get_db_session
    from bot.models.user import User as DBUser
    user_lang = 'en'
    with get_db_session() as db:
        db_user = db.query(DBUser).filter(DBUser.telegram_id == user.id).first()
        if db_user:
            user_lang = get_user_language(db_user.language_code or user.language_code)
        else:
            user_lang = get_user_language(user.language_code)
    
    # 根据字段类型显示不同的输入提示
    logger.info(f"[prompt_next_input] Processing field type: {current_field}")
    if current_field == "gender" or current_field.endswith("_gender"):
        # 性别选择 - 使用键盘按钮
        logger.info(f"[prompt_next_input] Building gender selection keyboard for chat {chat_id}")
        cancel_btn_text = translate("common.cancel_btn", user_lang)
        keyboard = [
            [KeyboardButton("👨 男 / Male"), KeyboardButton("👩 女 / Female")],
            [KeyboardButton(cancel_btn_text)]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        prompt_text = translate("input.gender_select", user_lang)
        logger.info(f"[prompt_next_input] Sending gender selection prompt to chat {chat_id}")
        try:
            await context.bot.send_message(chat_id=chat_id, text=prompt_text, reply_markup=reply_markup)
            logger.info(f"[prompt_next_input] Successfully sent gender selection prompt")
        except Exception as e:
            logger.error(f"[prompt_next_input] Failed to send gender selection prompt: {e}", exc_info=True)
    
    elif current_field == "zodiac":
        # 星座选择 - 使用内联键盘
        logger.info(f"[prompt_next_input] Building zodiac selection keyboard for chat {chat_id}")
        keyboard = []
        for i in range(0, len(ZODIAC_SIGNS), 3):
            row = []
            for j in range(3):
                if i + j < len(ZODIAC_SIGNS):
                    sign = ZODIAC_SIGNS[i + j]
                    row.append(
                        InlineKeyboardButton(
                            f"{sign[2]} {sign[0]}",
                            callback_data=f"input_zodiac_{sign[0]}"
                        )
                    )
            keyboard.append(row)
        cancel_btn_text = translate("common.cancel_btn", user_lang)
        keyboard.append([InlineKeyboardButton(cancel_btn_text, callback_data="cancel_order")])
        
        prompt_text = translate("input.zodiac", user_lang)
        logger.info(f"[prompt_next_input] Sending zodiac selection prompt to chat {chat_id}")
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=prompt_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            logger.info(f"[prompt_next_input] Successfully sent zodiac selection prompt")
        except Exception as e:
            logger.error(f"[prompt_next_input] Failed to send zodiac selection prompt: {e}", exc_info=True)
        return INPUTTING_DATA
    
    elif current_field.startswith("zodiac_"):
        # 生肖选择 - 使用内联键盘
        logger.info(f"[prompt_next_input] Building Chinese zodiac selection keyboard for chat {chat_id}, field: {current_field}")
        keyboard = []
        for i in range(0, len(CHINESE_ZODIAC), 4):
            row = []
            for j in range(4):
                if i + j < len(CHINESE_ZODIAC):
                    zodiac = CHINESE_ZODIAC[i + j]
                    row.append(
                        InlineKeyboardButton(
                            f"{zodiac[2]} {zodiac[1]}",
                            callback_data=f"input_chinese_zodiac_{current_field}_{zodiac[1]}"
                        )
                    )
            keyboard.append(row)
        cancel_btn_text = translate("common.cancel_btn", user_lang)
        keyboard.append([InlineKeyboardButton(cancel_btn_text, callback_data="cancel_order")])
        
        person_key = "zodiac_person_a" if "a" in current_field else "zodiac_person_b"
        person = translate(f"input.{person_key}", user_lang)
        zodiac_key = "zodiac_a" if "a" in current_field else "zodiac_b"
        base_prompt = translate(f"input.{zodiac_key}", user_lang)
        prompt_text = base_prompt.replace("第一个", person).replace("第二个", person).replace("first", person).replace("second", person)
        logger.info(f"[prompt_next_input] Sending Chinese zodiac selection prompt to chat {chat_id}")
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=prompt_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            logger.info(f"[prompt_next_input] Successfully sent Chinese zodiac selection prompt")
        except Exception as e:
            logger.error(f"[prompt_next_input] Failed to send Chinese zodiac selection prompt: {e}", exc_info=True)
        return INPUTTING_DATA
    
    else:
        # 文本输入
        field_key_map = {
            "name": "input.name",
            "birthday": "input.birthday",
            "birth_time": "input.birth_time",
        }
        
        prompt_key = field_key_map.get(current_field, None)
        if prompt_key:
            prompt_text = translate(prompt_key, user_lang)
        else:
            prompt_text = f"请输入 {current_field}:" if user_lang == 'zh' else f"Please enter {current_field}:"
        logger.info(f"[prompt_next_input] Sending text prompt for field '{current_field}' to chat {chat_id}")
        try:
            await context.bot.send_message(chat_id=chat_id, text=prompt_text)
            logger.info(f"[prompt_next_input] Successfully sent prompt for field '{current_field}'")
        except Exception as e:
            logger.error(f"[prompt_next_input] Failed to send prompt for field '{current_field}': {e}", exc_info=True)
    
    return INPUTTING_DATA


async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    处理用户输入
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
        
    Returns:
        对话状态
    """
    needed_fields = context.user_data.get("needed_fields", [])
    current_index = context.user_data.get("current_field_index", 0)
    
    if current_index >= len(needed_fields):
        return await show_confirmation(update, context)
    
    # 第一次输入时移除指引消息
    await _remove_instruction_message(context, context.bot)
    
    current_field = needed_fields[current_index]
    user_input = update.message.text.strip()
    
    # 验证输入
    is_valid = False
    error_msg = None
    
    if current_field in ["gender", "gender_a", "gender_b"]:
        is_valid, error_msg = validate_gender(user_input)
        if is_valid:
            context.user_data["input_data"][current_field] = normalize_gender(user_input)
    elif current_field == "name":
        is_valid, error_msg = validate_name(user_input)
        if is_valid:
            context.user_data["input_data"][current_field] = user_input
    elif current_field == "birthday":
        is_valid, error_msg = validate_date(user_input)
        if is_valid:
            context.user_data["input_data"][current_field] = user_input
    elif current_field == "birth_time":
        is_valid, error_msg = validate_time(user_input)
        if is_valid:
            context.user_data["input_data"][current_field] = user_input
    
    # 获取用户语言
    user = update.effective_user
    from bot.database.db import get_db_session
    from bot.models.user import User as DBUser
    user_lang = 'en'
    with get_db_session() as db:
        db_user = db.query(DBUser).filter(DBUser.telegram_id == user.id).first()
        if db_user:
            user_lang = get_user_language(db_user.language_code or user.language_code)
        else:
            user_lang = get_user_language(user.language_code)
    
    if not is_valid:
        error_text = translate("input.invalid_retry", user_lang, error=error_msg)
        await update.message.reply_text(error_text)
        return INPUTTING_DATA
    
    # 输入有效，继续下一个字段
    context.user_data["current_field_index"] += 1
    logger.info(f"[handle_input] Field '{current_field}' saved. Updated current_field_index to {context.user_data['current_field_index']}")
    
    # 移除键盘
    saved_text = translate("input.saved", user_lang)
    await update.message.reply_text(saved_text, reply_markup=None)
    
    logger.info(f"[handle_input] Calling prompt_next_input after saving field '{current_field}'")
    return await prompt_next_input(update, context)


async def handle_zodiac_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理星座选择回调"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"[handle_zodiac_callback] Received zodiac selection callback: data={query.data}")
    
    await _remove_instruction_message(context, context.bot)
    
    zodiac = query.data.split("_")[-1]
    context.user_data["input_data"]["zodiac"] = zodiac
    
    context.user_data["current_field_index"] += 1
    logger.info(f"[handle_zodiac_callback] Saved zodiac={zodiac}, current_field_index={context.user_data['current_field_index']}")
    
    # 获取用户语言
    user = query.from_user
    from bot.database.db import get_db_session
    from bot.models.user import User as DBUser
    user_lang = 'en'
    with get_db_session() as db:
        db_user = db.query(DBUser).filter(DBUser.telegram_id == user.id).first()
        if db_user:
            user_lang = get_user_language(db_user.language_code or user.language_code)
        else:
            user_lang = get_user_language(user.language_code)
    
    # 清除上一条星座选择消息的键盘，避免用户再次点击
    selected_text = translate("input.selected_zodiac", user_lang, name=zodiac)
    try:
        await query.edit_message_text(selected_text)
    except Exception as e:
        logger.warning(f"Failed to edit zodiac selection message: {e}")
        await query.message.reply_text(selected_text)
    
    return await prompt_next_input(update, context)


async def handle_chinese_zodiac_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理生肖选择回调"""
    query = update.callback_query
    await query.answer()
    
    await _remove_instruction_message(context, context.bot)
    
    parts = query.data.split("_")
    # 回调数据格式：input_chinese_zodiac_{field}_{zodiac}
    # field中本身包含下划线，例如 zodiac_a，需要重新组合
    field = "_".join(parts[3:-1])  # 恢复成 zodiac_a 或 zodiac_b
    zodiac = parts[-1]  # 生肖中文名（如"羊"、"猪"）
    
    # 保存生肖到用户输入数据
    context.user_data["input_data"][field] = zodiac
    
    # 获取用户语言
    user = query.from_user
    from bot.database.db import get_db_session
    from bot.models.user import User as DBUser
    user_lang = 'en'
    with get_db_session() as db:
        db_user = db.query(DBUser).filter(DBUser.telegram_id == user.id).first()
        if db_user:
            user_lang = get_user_language(db_user.language_code or user.language_code)
        else:
            user_lang = get_user_language(user.language_code)
    
    # 确定是第一个人还是第二个人
    selected_key = "input.selected_zodiac_a" if field.endswith("a") else "input.selected_zodiac_b"
    selected_text = translate(selected_key, user_lang, name=zodiac)
    
    context.user_data["current_field_index"] += 1
    
    # 清除上一条生肖选择消息的键盘，避免用户再次点击
    try:
        await query.edit_message_text(selected_text)
    except Exception as e:
        logger.warning(f"Failed to edit chinese zodiac selection message: {e}")
        await query.message.reply_text(selected_text)
    
    return await prompt_next_input(update, context)


async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    显示确认信息
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
        
    Returns:
        对话状态
    """
    product = context.user_data.get("product")
    input_data = context.user_data.get("input_data", {})
    
    # 确定 chat_id
    chat_id = None
    if update.message and update.message.chat:
        chat_id = update.message.chat.id
    elif update.effective_chat and update.effective_chat.id:
        chat_id = update.effective_chat.id
    elif update.callback_query and update.callback_query.message:
        chat_id = update.callback_query.message.chat.id
    elif update.effective_user:
        chat_id = update.effective_user.id
    
    if not chat_id:
        logger.error("[show_confirmation] Unable to determine chat_id; cannot send confirmation message")
        return INPUTTING_DATA
    
    logger.info(f"[show_confirmation] Preparing confirmation for chat {chat_id}, product={product.name_en}")
    
    # 构建确认信息
    confirmation_text = (
        f"📋 订单确认 / Order Confirmation\n\n"
        f"产品 / Product: {product.name_zh} / {product.name_en}\n"
    )
    # 免费产品不显示价格
    if product.price_usd > 0.00:
        confirmation_text += f"价格 / Price: ${product.price_usd}\n\n"
    else:
        confirmation_text += "\n"
    
    if input_data:
        confirmation_text += "输入信息 / Input Information:\n"
        for key, value in input_data.items():
            confirmation_text += f"• {key}: {value}\n"
    
    confirmation_text += "\n请确认订单 / Please confirm your order:"
    
    # 根据产品是否免费显示不同的按钮文本
    if product.price_usd == 0.00:
        keyboard = [
            [
                InlineKeyboardButton("✅ 确认生成 / Confirm & Generate", callback_data="confirm_order"),
                InlineKeyboardButton("❌ 取消 / Cancel", callback_data="cancel_order")
            ]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("✅ 确认并支付 / Confirm & Pay", callback_data="confirm_order"),
                InlineKeyboardButton("❌ 取消 / Cancel", callback_data="cancel_order")
            ]
        ]
    
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=confirmation_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info(f"[show_confirmation] Confirmation message sent to chat {chat_id}")
    except Exception as e:
        logger.error(f"[show_confirmation] Failed to send confirmation message: {e}", exc_info=True)
        return INPUTTING_DATA
    
    return CONFIRMING_ORDER


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    取消订单
    
    Args:
        update: Telegram更新对象
        context: 上下文对象
        
    Returns:
        对话结束
    """
    user = update.effective_user
    
    if update.callback_query:
        query = update.callback_query
        # 尝试回答回调查询（如果查询已过期，捕获异常）
        try:
            await query.answer()
        except Exception as e:
            # 查询可能已过期，但仍然继续处理用户的意图
            logger.warning(f"Callback query answer failed (may be expired) in cancel_order: {e}")
            # 发送新消息告知用户
            try:
                await query.message.reply_text("❌ 订单已取消 / Order cancelled")
            except:
                pass
            # 清除会话数据
            context.user_data.clear()
            from bot.utils.session_manager import clear_session
            clear_session(user.id)
            return ConversationHandler.END
        
        try:
            await query.edit_message_text("❌ 订单已取消 / Order cancelled")
        except Exception as e:
            logger.warning(f"Failed to edit message in cancel_order: {e}")
            # 如果编辑失败，尝试发送新消息
            try:
                await query.message.reply_text("❌ 订单已取消 / Order cancelled")
            except:
                pass
    else:
        await update.message.reply_text("❌ 订单已取消 / Order cancelled")
    
    # 清除用户数据
    context.user_data.clear()
    
    # 清除数据库会话
    from bot.utils.session_manager import clear_session
    clear_session(user.id)
    
    return ConversationHandler.END


# 创建产品对话处理器
def create_product_conversation_handler():
    """创建产品选择对话处理器"""
    from bot.handlers.payment import confirm_order_callback
    
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(product_callback, pattern=r"^product_\d+$")
        ],
        states={
            INPUTTING_DATA: [
                CallbackQueryHandler(handle_zodiac_callback, pattern=r"^input_zodiac_"),
                CallbackQueryHandler(handle_chinese_zodiac_callback, pattern=r"^input_chinese_zodiac_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input),
            ],
            CONFIRMING_ORDER: [
                CallbackQueryHandler(confirm_order_callback, pattern=r"^confirm_order$"),
                CallbackQueryHandler(cancel_order, pattern=r"^cancel_order$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_order, pattern=r"^cancel_order$"),
            MessageHandler(filters.COMMAND, cancel_order),
        ],
        name="product_conversation",
        per_message=False,  # 使用按聊天会话，避免新消息导致回调无法匹配
        # persistent=False,  # 我们使用数据库管理会话状态，不需要内置持久化
    )

