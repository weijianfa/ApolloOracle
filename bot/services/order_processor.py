"""
订单处理服务（协调支付、八字API、AI生成等流程）

根据修正后的系统架构图和PRD文档要求：
- [步骤1] 支付成功验证 (PingPong Webhook)
- [步骤2] 首先调用八字接口 (缘分居API) - 获取结构化数据
- [步骤3] AI生成报告 (DeepSeek API) - 使用八字数据作为核心依据
- [步骤4] 发送报告给用户 (Telegram Bot API)
"""
from typing import Optional
import asyncio
from bot.database.db import get_db_session
from bot.models.order import Order
from bot.models.user import User
from bot.services.bazi_service import bazi_service
from bot.services.ai_service import ai_service
from bot.utils.logger import logger
from bot.utils.operation_logger import log_operation
from bot.config.settings import settings
from bot.config.products import get_product
import json
from datetime import datetime


class OrderProcessor:
    """订单处理服务类"""
    
    async def process_paid_order(self, order_id: str) -> bool:
        """
        处理已支付的订单
        
        根据PRD文档"2.调用时机与流程"的要求，流程如下：
        1. [步骤1] 检查订单状态（支付成功验证）
        2. [步骤2] 首先调用八字接口（缘分居API）- 如果产品需要八字数据
           - 调用时机：支付成功后首先调用
           - 返回：结构化八字数据
        3. [步骤3] AI生成报告（DeepSeek API）
           - 输入：用户输入 + 八字结构化数据（核心依据）
           - 输出：AI生成的个性化报告
        4. [步骤4] 发送报告给用户（Telegram Bot API）
        5. 更新订单状态为completed
        
        Args:
            order_id: 订单ID
            
        Returns:
            处理是否成功
        """
        try:
            # 使用独立的数据库会话，避免长时间操作导致会话超时
            # AI生成可能需要较长时间，所以先获取必要信息，然后在操作完成后更新
            with get_db_session() as db:
                order = db.query(Order).filter(Order.order_id == order_id).first()
                if not order:
                    logger.error(f"Order not found: {order_id}")
                    return False
                
                # 检查订单状态
                if order.status != "paid":
                    logger.warning(f"Order {order_id} is not in paid status, current status: {order.status}")
                    return False
                
                # 保存必要信息（避免后续访问脱离会话的对象）
                user_id = order.user_id
                product_id = order.product_id
                product_name = order.product_name
                amount_usd = order.amount_usd
                user_input_str = order.user_input
                
                # 获取用户信息
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    logger.error(f"User not found for order {order_id}")
                    order.status = "failed"
                    order.error_message = "User not found"
                    db.commit()
                    return False
                
                telegram_id = user.telegram_id
                # 使用i18n系统获取用户语言
                from bot.utils.i18n import get_user_language
                language = get_user_language(user.language_code)
                
                # 更新状态为生成中
                order.status = "generating"
                db.commit()
                logger.info(f"Order {order_id} status updated to 'generating'")
            
            # 在会话外进行长时间操作（AI生成）
            # 这样可以避免数据库会话超时
            
            # 解析用户输入（使用之前保存的字符串）
            try:
                if user_input_str:
                    user_input = json.loads(user_input_str)
                    logger.info(f"Parsed user_input for order {order_id}: {json.dumps(user_input, ensure_ascii=False)}")
                else:
                    user_input = {}
                    logger.info(f"user_input_str is empty for order {order_id}")
            except Exception as e:
                logger.error(f"Error parsing user_input for order {order_id}: {e}, user_input_str: {user_input_str}")
                user_input = {}
            
            # 对于不需要输入的产品（如每日塔罗），确保user_input为空字典
            # 如果用户没有提供任何输入，使用默认值
            if not user_input:
                user_input = {}
                # 对于每日塔罗等免费产品，即使没有用户输入也能正常处理
                logger.info(f"User input is empty for order {order_id}, proceeding with default processing")
            
            # [步骤2] 首先调用八字接口（如果产品需要）
            # 根据PRD文档：支付成功后首先调用八字接口，将返回的结构化数据作为AI生成的核心依据
            bazi_data = None
            product = get_product(product_id)
            if product and product.requires_bazi:
                logger.info(f"[步骤2] 首先调用八字接口 - Fetching Bazi data for order {order_id} (product: {product.name_zh})")
                
                # 从用户输入中提取信息
                name = user_input.get("name", "用户")
                birthday = user_input.get("birthday")
                birth_time = user_input.get("birth_time", "12:00")  # 默认中午12点
                gender = user_input.get("gender", 1)
                
                if not birthday:
                    logger.error(f"Missing birthday for order {order_id}")
                    with get_db_session() as db:
                        order = db.query(Order).filter(Order.order_id == order_id).first()
                        if order:
                            order.status = "failed"
                            order.error_message = "Missing required information: birthday"
                            db.commit()
                    return False
                
                # 调用八字API
                bazi_result = await bazi_service.get_bazi_data(
                    name=name,
                    birthday=birthday,
                    birth_time=birth_time,
                    gender=gender
                )
                
                if not bazi_result:
                    # 八字API调用失败，停止流程并退款
                    logger.error(
                        f"Failed to get Bazi data for order {order_id}, initiating refund. "
                        f"User input: name={name}, birthday={birthday}, time={birth_time}, gender={gender}. "
                        f"Possible reasons: "
                        f"1. YUANFENJU_API_KEY not configured in .env file, "
                        f"2. API URL incorrect or unreachable, "
                        f"3. API request format incorrect, "
                        f"4. Network connection issue. "
                        f"Check logs above for detailed error messages."
                    )
                    with get_db_session() as db:
                        order = db.query(Order).filter(Order.order_id == order_id).first()
                        if order:
                            order.status = "failed"
                            order.error_message = "Failed to fetch Bazi data from API - check YUANFENJU_API_KEY configuration"
                            db.commit()
                            
                            # 触发退款
                            from bot.services.payment_service import payment_service
                            refund_success = payment_service.refund_order(
                                order=order,
                                reason="Bazi API call failed"
                            )
                            
                            # 记录操作日志
                            log_operation(
                                operation_type="refund",
                                status="success" if refund_success else "failed",
                                user_id=user_id,
                                order_id=order_id,
                                operation_detail={
                                    "reason": "Bazi API call failed",
                                    "refund_success": refund_success,
                                    "user_input": {"name": name, "birthday": birthday, "time": birth_time, "gender": gender}
                                },
                                error_message=None if refund_success else "Refund API call failed"
                            )
                            
                            if refund_success:
                                logger.info(f"Order {order_id} refunded successfully due to Bazi API failure")
                                # 通知用户退款成功
                                try:
                                    await self._notify_user_generation_failed(
                                        telegram_id=telegram_id,
                                        order_id=order_id,
                                        product_name=product_name,
                                        is_free_product=False
                                    )
                                except Exception as notify_error:
                                    logger.error(f"Failed to notify user about refund: {notify_error}")
                            else:
                                logger.error(f"Failed to refund order {order_id}")
                                
                                # 通知管理员
                                await self._notify_admin(
                                    f"⚠️ 订单 {order_id} 八字API调用失败，退款也失败\n"
                                    f"用户: {telegram_id}\n"
                                    f"产品: {product_name}\n"
                                    f"请手动处理退款"
                                )
                    
                    return False
                
                # 保存八字数据（结构化数据，将作为AI生成的核心依据）
                bazi_data = bazi_service.parse_bazi_response(bazi_result)
                with get_db_session() as db:
                    order = db.query(Order).filter(Order.order_id == order_id).first()
                    if order:
                        order.bazi_data = json.dumps(bazi_data, ensure_ascii=False)
                        db.commit()
                        logger.info(f"[步骤2完成] 八字结构化数据已获取并保存 for order {order_id}")
            else:
                # 产品不需要八字数据
                logger.info(f"[步骤2] 产品 {product.name_zh if product else product_id} 不需要八字数据，跳过八字接口调用")
            
            # [步骤3] AI生成报告（所有产品都需要）
            # 根据PRD文档：将八字结构化数据作为核心依据传递给AI生成层（如果产品需要八字数据）
            logger.info(f"[步骤3] 开始AI生成报告 - Generating AI report for order {order_id}")
            
            if not product:
                product = get_product(product_id)
            if not product:
                logger.error(f"Product not found: {product_id}")
                with get_db_session() as db:
                    order = db.query(Order).filter(Order.order_id == order_id).first()
                    if order:
                        order.status = "failed"
                        order.error_message = "Product not found"
                        db.commit()
                return False
            
            # 加载提示词模板
            template = ai_service.load_prompt_template(product_id, language)
            
            # 构建提示词
            # 注意：bazi_data作为核心依据传递给AI生成层（根据PRD文档要求，如果产品需要八字数据）
            prompt = ai_service.build_prompt(
                template=template,
                user_input=user_input,
                bazi_data=bazi_data,  # 八字结构化数据作为核心依据（如果产品需要）
                product_id=product_id
            )
            
            # 记录提示词构建信息（包含用户输入的关键信息，但不泄露敏感数据）
            user_input_summary = {}
            if user_input:
                for key in user_input.keys():
                    if key in ["name", "zodiac", "zodiac_a", "zodiac_b"]:
                        user_input_summary[key] = user_input[key]
                    elif key in ["gender", "gender_a", "gender_b"]:
                        user_input_summary[key] = "已提供"
                    elif key in ["birthday", "birth_time"]:
                        user_input_summary[key] = "已提供"
            
            logger.info(
                f"[步骤3] 提示词已构建 for order {order_id}, "
                f"用户输入摘要: {json.dumps(user_input_summary, ensure_ascii=False)}, "
                f"{'包含八字数据（核心依据）' if bazi_data else '无八字数据'}"
            )
            
            # 生成报告（带超时处理）
            # 注意：generate_report 内部已经有重试机制
            # 单次请求超时可配置（默认60秒），最多3次尝试（1次初始+2次重试），加上重试间隔
            # 总体超时从配置读取（默认240秒/4分钟），确保有足够时间完成AI生成
            # AI生成时间与内容大小相关，特别是启用深度思考时可能需要更长时间
            from bot.config.settings import settings
            configured_total_timeout = settings.DEEPSEEK_API_TOTAL_TIMEOUT
            dynamic_timeout_budget = sum(
                ai_service.timeout * (2 ** i) for i in range(ai_service.max_retries + 1)
            )
            # 额外缓冲30秒，覆盖网络波动和响应解析
            recommended_total_timeout = dynamic_timeout_budget + 30
            total_timeout = max(configured_total_timeout, recommended_total_timeout)
            logger.info(
                f"[步骤3] 开始调用AI生成报告，总体超时设置为 {total_timeout} 秒 "
                f"(配置值: {configured_total_timeout}s, 推荐值: {recommended_total_timeout}s) for order {order_id}"
            )
            
            try:
                # 使用 asyncio.wait_for 包装，确保总体超时
                report = await asyncio.wait_for(
                    ai_service.generate_report(prompt, language),
                    timeout=float(total_timeout)  # 从配置读取总体超时时间
                )
                logger.info(f"[步骤3] AI报告生成成功 for order {order_id}")
                error_message = None
            except asyncio.TimeoutError:
                # 总体超时
                logger.error(f"[步骤3] AI报告生成超时 for order {order_id} (超过 {total_timeout} 秒)")
                report = None
                error_message = f"AI report generation timeout (exceeded {total_timeout // 60} minutes after all retries)"
            except Exception as e:
                # 其他异常
                logger.error(f"[步骤3] AI报告生成过程中发生错误 for order {order_id}: {e}", exc_info=True)
                report = None
                error_message = f"AI report generation error: {str(e)}"
            
            if not report:
                # AI生成失败或超时，通知用户并处理退款（如果是付费产品）
                logger.error(f"Failed to generate AI report for order {order_id}")
                
                # 先通知用户
                await self._notify_user_generation_failed(
                    telegram_id=telegram_id,
                    order_id=order_id,
                    product_name=product_name,
                    is_free_product=(amount_usd == 0.0)
                )
                
                # 重新打开会话更新订单状态
                with get_db_session() as db:
                    order = db.query(Order).filter(Order.order_id == order_id).first()
                    if order:
                        order.status = "failed"
                        order.error_message = error_message or "Failed to generate AI report"
                        db.commit()
                
                # 如果是付费产品，触发退款
                if amount_usd > 0.0:
                    with get_db_session() as db:
                        order = db.query(Order).filter(Order.order_id == order_id).first()
                        if order:
                            from bot.services.payment_service import payment_service
                            refund_success = payment_service.refund_order(
                                order=order,
                                reason="AI report generation failed"
                            )
                            
                            # 记录操作日志
                            log_operation(
                                operation_type="refund",
                                status="success" if refund_success else "failed",
                                user_id=user_id,
                                order_id=order_id,
                                operation_detail={
                                    "reason": "AI report generation failed",
                                    "refund_success": refund_success
                                },
                                error_message=None if refund_success else "Refund API call failed"
                            )
                            
                            if refund_success:
                                logger.info(f"Order {order_id} refunded due to AI generation failure")
                            else:
                                logger.error(f"Failed to refund order {order_id}")
                
                # 通知管理员
                await self._notify_admin(
                    f"⚠️ 订单 {order_id} AI报告生成失败\n"
                    f"用户: {telegram_id}\n"
                    f"产品: {product_name}\n"
                    f"错误: {error_message or 'Failed to generate AI report'}\n"
                    f"{'已自动退款' if amount_usd > 0.0 else '免费产品，无需退款'}"
                )
                
                return False
            
            # 保存报告（重新打开会话）
            with get_db_session() as db:
                order = db.query(Order).filter(Order.order_id == order_id).first()
                if order:
                    order.ai_report = report
                    order.status = "completed"
                    order.completed_at = datetime.now()
                    
                    # 更新推广员统计（如果订单有关联的推广员）
                    if order.affiliate_code and order.commission_amount and order.amount_usd:
                        from bot.services.affiliate_service import affiliate_service
                        from decimal import Decimal
                        success = affiliate_service.update_affiliate_sales(
                            affiliate_code=order.affiliate_code,
                            order_amount=Decimal(str(order.amount_usd)),
                            commission_amount=Decimal(str(order.commission_amount))
                        )
                        if success:
                            logger.info(f"Affiliate sales updated for order {order_id}, affiliate_code={order.affiliate_code}")
                        else:
                            logger.warning(f"Failed to update affiliate sales for order {order_id}")
                    
                    db.commit()
                    logger.info(f"[步骤3完成] AI报告已生成并保存 for order {order_id}")
                else:
                    logger.error(f"Order {order_id} not found when saving report")
                    return False
            
            # [步骤4] 发送报告给用户
            logger.info(f"[步骤4] 开始发送报告给用户 - Sending report to user {telegram_id} for order {order_id}")
            # 重新查询订单对象用于发送报告
            # 在会话内提取需要的属性值，避免在会话外访问对象属性
            product_name = None
            with get_db_session() as db:
                order = db.query(Order).filter(Order.order_id == order_id).first()
                if order:
                    product_name = order.product_name
                    product_id = order.product_id
                else:
                    logger.error(f"Order {order_id} not found when sending report")
                    return False
            
            # 在会话外调用发送方法，使用提取的值
            if product_name:
                try:
                    await self._send_report_to_user(telegram_id, order_id, product_name, product_id, report, user_language=language)
                    logger.info(f"[步骤4完成] 报告已发送给用户 for order {order_id}")
                except Exception as send_error:
                    logger.error(f"[步骤4] 发送报告时发生错误 for order {order_id}: {send_error}", exc_info=True)
                    # 即使发送失败，订单状态已经是completed，报告已保存
                    # 不返回False，因为报告已成功生成
            else:
                logger.error(f"Product name not found for order {order_id}")
                return False
            
            return True
                
        except Exception as e:
            logger.error(f"Error processing order {order_id}: {e}", exc_info=True)
            
            # 更新订单状态为失败
            try:
                with get_db_session() as db:
                    order = db.query(Order).filter(Order.order_id == order_id).first()
                    if order:
                        order.status = "failed"
                        order.error_message = f"Processing error: {str(e)}"
                        db.commit()
                        
                        # 尝试通知用户（如果可能）
                        try:
                            user = db.query(User).filter(User.id == order.user_id).first()
                            if user:
                                await self._notify_user_generation_failed(
                                    telegram_id=user.telegram_id,
                                    order_id=order_id,
                                    product_name=order.product_name,
                                    is_free_product=(order.amount_usd == 0.0)
                                )
                        except Exception as notify_error:
                            logger.error(f"Failed to notify user after processing error: {notify_error}")
            except Exception as db_error:
                logger.error(f"Failed to update order status after processing error: {db_error}", exc_info=True)
            
            # 重新抛出异常，让调用者知道发生了错误
            raise
    
    async def _notify_admin(self, message: str):
        """
        通知管理员
        
        Args:
            message: 通知消息
        """
        try:
            if settings.ADMIN_TELEGRAM_ID:
                # 这里将在后续实现Telegram消息发送
                # 暂时只记录日志
                logger.info(f"Admin notification: {message}")
        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")
    
    async def _notify_user_generation_failed(
        self,
        telegram_id: int,
        order_id: str,
        product_name: str,
        is_free_product: bool = False
    ):
        """
        通知用户报告生成失败
        
        Args:
            telegram_id: Telegram用户ID
            order_id: 订单ID
            product_name: 产品名称
            is_free_product: 是否为免费产品
        """
        try:
            from telegram import Bot
            
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            
            if is_free_product:
                # 免费产品失败消息
                error_message = (
                    f"❌ 报告生成失败 / Report Generation Failed\n\n"
                    f"很抱歉，{product_name}报告生成时遇到了问题。\n"
                    f"Sorry, we encountered an issue while generating your {product_name} report.\n\n"
                    f"订单号 / Order ID: `{order_id}`\n\n"
                    f"💡 建议：\n"
                    f"• 请稍后重试\n"
                    f"• 如果问题持续，请联系客服\n\n"
                    f"💡 Suggestions:\n"
                    f"• Please try again later\n"
                    f"• If the problem persists, please contact support"
                )
            else:
                # 付费产品失败消息（会退款）
                error_message = (
                    f"❌ 报告生成失败，已自动退款 / Report Generation Failed, Refunded\n\n"
                    f"很抱歉，{product_name}报告生成时遇到了问题。\n"
                    f"Sorry, we encountered an issue while generating your {product_name} report.\n\n"
                    f"订单号 / Order ID: `{order_id}`\n\n"
                    f"💰 退款信息 / Refund Information:\n"
                    f"• 订单金额已自动退回您的账户\n"
                    f"• 退款将在1-3个工作日内到账\n\n"
                    f"💰 Refund Info:\n"
                    f"• Order amount has been automatically refunded\n"
                    f"• Refund will arrive within 1-3 business days\n\n"
                    f"💡 建议：\n"
                    f"• 请稍后重试\n"
                    f"• 如果问题持续，请联系客服\n\n"
                    f"💡 Suggestions:\n"
                    f"• Please try again later\n"
                    f"• If the problem persists, please contact support"
                )
            
            await bot.send_message(
                chat_id=telegram_id,
                text=error_message,
                parse_mode="Markdown"
            )
            
            logger.info(f"Failure notification sent to user {telegram_id} for order {order_id}")
            
        except Exception as e:
            logger.error(f"Error sending failure notification to user {telegram_id}: {e}")
    
    async def _send_report_to_user(
        self, 
        telegram_id: int, 
        order_id: str, 
        product_name: str, 
        product_id: int, 
        report: str,
        user_language: str = "en"
    ):
        """
        发送报告给用户
        
        Args:
            telegram_id: Telegram用户ID
            order_id: 订单ID
            product_name: 产品名称
            product_id: 产品ID
            report: 报告内容
        """
        try:
            from telegram import Bot
            from bot.utils.message_splitter import split_message, format_markdown
            
            logger.info(f"[_send_report_to_user] Starting to send report to user {telegram_id} for order {order_id}")
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            
            # 格式化报告
            logger.debug(f"[_send_report_to_user] Formatting report (length: {len(report)} chars)")
            formatted_report = format_markdown(report)
            logger.debug(f"[_send_report_to_user] Report formatted (length: {len(formatted_report)} chars)")
            
            # 分段发送
            segments = split_message(formatted_report)
            logger.info(f"[_send_report_to_user] Report split into {len(segments)} segment(s)")
            
            # 获取用户语言（如果未提供）
            if not user_language:
                from bot.database.db import get_db_session
                from bot.models.user import User
                from bot.utils.i18n import get_user_language
                with get_db_session() as db:
                    user = db.query(User).filter(User.telegram_id == telegram_id).first()
                    if user:
                        user_language = get_user_language(user.language_code)
                    else:
                        user_language = "en"
            
            # 发送报告标题（使用i18n）
            from bot.utils.i18n import translate
            report_ready = translate("report.ready", user_language, product=product_name)
            order_id_label = translate("report.order_id", user_language, order_id=order_id)
            report_header = (
                f"✨ *{report_ready}*\n\n"
                f"{order_id_label}\n\n"
            )
            
            logger.info(f"[_send_report_to_user] Sending report header to user {telegram_id}")
            try:
                await bot.send_message(
                    chat_id=telegram_id,
                    text=report_header,
                    parse_mode="Markdown"
                )
                logger.info(f"[_send_report_to_user] Report header sent successfully")
            except Exception as header_error:
                logger.error(f"[_send_report_to_user] Failed to send report header: {header_error}", exc_info=True)
                # 如果Markdown格式错误，尝试不使用parse_mode发送
                try:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=report_header.replace("*", "").replace("`", ""),
                        parse_mode=None
                    )
                    logger.info(f"[_send_report_to_user] Report header sent as plain text")
                except Exception as header_plain_error:
                    logger.error(f"[_send_report_to_user] Failed to send report header even as plain text: {header_plain_error}", exc_info=True)
                    raise
            
            # 发送报告内容（分段），AI内容已转换为纯文本格式
            logger.info(f"[_send_report_to_user] Sending {len(segments)} report segment(s)")
            for i, segment in enumerate(segments, 1):
                if len(segments) > 1:
                    segment = f"📄 第 {i}/{len(segments)} 部分\n\n{segment}"
                
                try:
                    logger.debug(f"[_send_report_to_user] Sending segment {i}/{len(segments)} (length: {len(segment)} chars)")
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=segment,
                        parse_mode=None
                    )
                    logger.info(f"[_send_report_to_user] Segment {i}/{len(segments)} sent successfully")
                except Exception as e:
                    logger.error(f"[_send_report_to_user] Failed to send segment {i}/{len(segments)}: {e}", exc_info=True)
                    # 继续发送其他段，不中断
                
                # 避免发送过快（Telegram速率限制）
                if i < len(segments):
                    await asyncio.sleep(0.5)
            
            # 发送完成提示（根据产品类型生成不同的结束语，使用i18n）
            from bot.config.products import get_product
            product = get_product(product_id)
            
            # 根据产品ID和用户语言生成完成消息
            completion_key_map = {
                1: "report.completion.tarot",
                2: "report.completion.horoscope",
                3: "report.completion.name",
                4: "report.completion.compatibility",
                5: "report.completion.bazi",
                6: "report.completion.annual",
            }
            
            completion_key = completion_key_map.get(product_id if product else 0, "report.completion.default")
            try:
                completion_message = translate(completion_key, user_language)
            except:
                # 如果翻译键不存在，使用默认消息
                if user_language == "zh":
                    completion_message = "\n✨ 感谢您使用我们的服务\n\n💫 祝您一切顺利"
                else:
                    completion_message = "\n✨ Thank you for using our service\n\n💫 Wishing you all the best"
            
            logger.info(f"[_send_report_to_user] Sending completion message")
            try:
                await bot.send_message(
                    chat_id=telegram_id,
                    text=completion_message
                )
                logger.info(f"[_send_report_to_user] Completion message sent successfully")
            except Exception as completion_error:
                logger.error(f"[_send_report_to_user] Failed to send completion message: {completion_error}", exc_info=True)
                # 完成消息发送失败不影响整体流程
            
            logger.info(f"[_send_report_to_user] Report sent to user {telegram_id} for order {order_id} successfully")
            
        except Exception as e:
            logger.error(f"[_send_report_to_user] Error sending report to user {telegram_id} for order {order_id}: {e}", exc_info=True)
            # 即使发送失败，订单状态已经是completed，报告已保存
            raise  # 重新抛出异常，让调用者知道发送失败


# 创建全局订单处理器实例
order_processor = OrderProcessor()

