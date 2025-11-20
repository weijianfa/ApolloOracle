"""
DeepSeek API服务模块（AI报告生成）
"""
import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from bot.config.settings import settings
from bot.utils.logger import logger
from bot.utils.operation_logger import log_operation
from jinja2 import Template
import json


class AIService:
    """AI服务类"""
    
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.api_url = settings.DEEPSEEK_API_URL
        # AI生成时间与内容大小相关，特别是启用深度思考时可能需要更长时间
        # 单次请求超时：从配置读取，默认60秒（1分钟）
        self.timeout = settings.DEEPSEEK_API_TIMEOUT
        self.max_retries = 2  # 最多重试2次（总共3次尝试）
        # 总体超时时间：从配置读取，默认240秒（4分钟）
        # 总体超时时间计算：
        # - 单次请求：60秒（可配置）
        # - 最多3次尝试：60秒 * 3 = 180秒
        # - 重试间隔：1秒 + 2秒 = 3秒
        # - 总计：约183秒，设置为4分钟（240秒）以确保安全
        self.total_timeout = settings.DEEPSEEK_API_TOTAL_TIMEOUT
    
    def load_prompt_template(self, product_id: int, language: str = "zh") -> Optional[str]:
        """
        加载提示词模板
        
        Args:
            product_id: 产品ID
            language: 语言（zh/en）
            
        Returns:
            提示词模板字符串
        """
        try:
            # 从文件加载模板（后续可以从数据库加载）
            template_path = f"prompts/{self._get_template_filename(product_id, language)}"
            
            try:
                with open(template_path, "r", encoding="utf-8") as f:
                    return f.read()
            except FileNotFoundError:
                # 如果文件不存在，使用默认模板
                logger.warning(f"Template file not found: {template_path}, using default template")
                return self._get_default_template(product_id, language)
                
        except Exception as e:
            logger.error(f"Error loading prompt template: {e}")
            return self._get_default_template(product_id, language)
    
    def _get_template_filename(self, product_id: int, language: str) -> str:
        """获取模板文件名"""
        template_names = {
            1: "daily_tarot",
            2: "weekly_horoscope",
            3: "name_analysis",
            4: "compatibility",
            5: "bazi_report",
            6: "annual_forecast",
        }
        base_name = template_names.get(product_id, "default")
        return f"{base_name}_{language}.txt"
    
    def _get_default_template(self, product_id: int, language: str) -> str:
        """获取默认模板"""
        if language == "zh":
            return f"你是一位专业的占卜师。请根据用户提供的信息，生成一份详细的占卜报告。产品ID：{product_id}"
        else:
            return f"You are a professional fortune teller. Please generate a detailed fortune report based on the user's information. Product ID: {product_id}"
    
    def build_prompt(
        self,
        template: str,
        user_input: Dict[str, Any],
        bazi_data: Optional[Dict[str, Any]] = None,
        product_id: int = 1
    ) -> str:
        """
        构建完整的提示词
        
        根据PRD文档要求：将八字接口返回的结构化数据作为后续生成AI报告的核心依据。
        
        Args:
            template: 模板字符串
            user_input: 用户输入数据
            bazi_data: 八字结构化数据（核心依据，如果产品需要）
            product_id: 产品ID
            
        Returns:
            完整的提示词
        """
        try:
            # 使用Jinja2模板引擎
            jinja_template = Template(template)
            
            # 准备模板变量
            # 注意：bazi_data是核心依据，如果存在，应该在模板中重点使用
            # 对于不需要输入的产品（如每日塔罗），user_input可能为空字典
            # 将bazi_data转换为字符串格式（如果是字典）
            bazi_data_str = None
            if bazi_data:
                if isinstance(bazi_data, dict):
                    bazi_data_str = json.dumps(bazi_data, ensure_ascii=False, indent=2)
                else:
                    bazi_data_str = str(bazi_data)
            
            template_vars = {
                "user_input": user_input if user_input else {},  # 确保不为None
                "bazi_data": bazi_data_str,  # 八字结构化数据（核心依据），转换为字符串格式
                "product_id": product_id,
                "current_date": datetime.now().strftime("%Y-%m-%d"),
            }
            
            # 记录用户输入信息（用于调试）
            if user_input:
                logger.info(f"Building prompt with user_input for product {product_id}: {json.dumps(user_input, ensure_ascii=False)}")
            else:
                logger.info(f"Building prompt without user_input for product {product_id}")
            
            # 如果存在八字数据，记录日志
            if bazi_data:
                logger.info(f"Building prompt with Bazi data as core basis for product {product_id}")
            
            # 对于每日塔罗等不需要输入的产品，记录日志
            if product_id == 1 and not user_input:
                logger.info(f"Building prompt for Daily Tarot (product {product_id}) without user input - using default processing")
            
            # 渲染模板
            try:
                prompt = jinja_template.render(**template_vars)
            except Exception as render_error:
                logger.error(f"Error rendering template for product {product_id}: {render_error}")
                # 如果模板渲染失败，尝试使用简化的提示词
                if user_input:
                    prompt = f"请根据以下用户信息生成报告：{json.dumps(user_input, ensure_ascii=False)}"
                    if bazi_data:
                        prompt += f"\n\n八字数据：{json.dumps(bazi_data, ensure_ascii=False)}"
                else:
                    prompt = f"请根据当前日期 {datetime.now().strftime('%Y-%m-%d')} 生成报告。"
                logger.warning(f"Using fallback prompt for product {product_id}")
            
            # 记录渲染后的提示词（用于调试，只记录前500字符）
            logger.debug(f"Rendered prompt (first 500 chars) for product {product_id}: {prompt[:500]}")
            
            return prompt
            
        except Exception as e:
            logger.error(f"Error building prompt: {e}")
            # 如果模板渲染失败，返回简单提示词
            # 对于空输入，提供默认提示
            if not user_input:
                return f"请根据当前日期 {datetime.now().strftime('%Y-%m-%d')} 生成占卜报告。"
            return f"请根据以下信息生成占卜报告：{json.dumps(user_input, ensure_ascii=False)}"
    
    async def generate_report(
        self,
        prompt: str,
        language: str = "zh"
    ) -> Optional[str]:
        """
        生成AI报告
        
        Args:
            prompt: 提示词
            language: 语言（zh/en）
            
        Returns:
            生成的报告文本，失败返回None
        """
        logger.debug(f"Starting AI report generation, timeout: {self.timeout}s, max retries: {self.max_retries}")
        
        if not self.api_key:
            logger.error("DeepSeek API key not configured")
            return None
        
        # 构建请求数据
        # 根据产品类型和用户语言设置不同的system message
        # 注意：system message应该与产品类型匹配，避免混用
        
        # 根据语言和prompt内容判断产品类型，设置更合适的system message
        if language == "zh":
            system_message = "你是一位专业的占卜师，擅长用专业、神秘、富有洞察力的语言为用户解读命运。"
            if "姓名" in prompt or "name" in prompt.lower():
                system_message = "你是一位专业的姓名学大师，擅长用专业而富有洞察力的语言分析姓名。"
            elif "塔罗" in prompt or "tarot" in prompt.lower():
                system_message = "你是一位专业的塔罗牌占卜师，擅长用专业、神秘、富有洞察力的语言为用户解读塔罗牌。"
            elif "星座" in prompt or "horoscope" in prompt.lower() or "zodiac" in prompt.lower():
                system_message = "你是一位专业的占星师，擅长用专业、富有洞察力的语言为用户解读星座运势。"
            elif "生肖" in prompt or "compatibility" in prompt.lower():
                system_message = "你是一位专业的生肖配对分析师，擅长用专业、富有洞察力的语言分析两人关系。"
            elif "八字" in prompt or "bazi" in prompt.lower():
                system_message = "你是一位专业的八字命理师，擅长用专业、深入的语言为用户解读八字命盘。"
            elif "流年" in prompt or "annual" in prompt.lower():
                system_message = "你是一位专业的命理师，擅长用专业、富有洞察力的语言为用户解读年度运势。"
        else:
            # 英文system message
            system_message = "You are a professional fortune teller, skilled in interpreting destiny with professional, mysterious, and insightful language."
            if "name" in prompt.lower():
                system_message = "You are a professional name interpretation master, skilled in interpreting names with professional and insightful language."
            elif "tarot" in prompt.lower():
                system_message = "You are a professional tarot reader, skilled in interpreting tarot cards with professional, mysterious, and insightful language."
            elif "horoscope" in prompt.lower() or "zodiac" in prompt.lower():
                system_message = "You are a professional astrologer, skilled in interpreting zodiac fortunes with professional and insightful language."
            elif "compatibility" in prompt.lower():
                system_message = "You are a professional relationship compatibility analyst, skilled in analyzing relationships with professional and insightful language."
            elif "bazi" in prompt.lower():
                system_message = "You are a professional Bazi (Four Pillars of Destiny) master, skilled in analyzing Bazi charts with professional and in-depth language."
            elif "annual" in prompt.lower():
                system_message = "You are a professional fortune teller, skilled in interpreting annual fortunes with professional and insightful language."
        
        request_data = {
            "model": "deepseek-chat",  # 根据实际模型名称调整
            "messages": [
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000,  # 根据需求调整
        }
        
        # 重试机制
        last_error = None
        base_timeout = self.timeout
        logger.info(f"Starting DeepSeek API call with base timeout {base_timeout}s, max {self.max_retries + 1} attempts (per-attempt timeout doubles)")
        
        for attempt in range(self.max_retries + 1):
            logger.debug(f"DeepSeek API attempt {attempt + 1}/{self.max_retries + 1}")
            try:
                if attempt > 0:
                    # 指数退避
                    wait_time = 2 ** (attempt - 1)
                    logger.info(f"Retrying DeepSeek API call (attempt {attempt + 1}/{self.max_retries + 1}), waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                
                attempt_timeout = base_timeout * (2 ** attempt)
                logger.info(
                    f"Making DeepSeek API request (attempt {attempt + 1}/{self.max_retries + 1}), "
                    f"timeout: {attempt_timeout}s"
                )
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.api_url,
                        json=request_data,
                        timeout=aiohttp.ClientTimeout(total=attempt_timeout),
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        }
                    ) as response:
                        # 记录响应状态，帮助调试
                        logger.info(f"DeepSeek API response received: status {response.status} (attempt {attempt + 1})")
                        
                        if response.status == 200:
                            try:
                                logger.info(f"Parsing DeepSeek API response JSON (attempt {attempt + 1})")
                                result = await response.json()
                                logger.info(f"DeepSeek API response parsed successfully (attempt {attempt + 1})")
                                
                                # 提取生成的文本
                                if "choices" in result and len(result["choices"]) > 0:
                                    content = result["choices"][0].get("message", {}).get("content", "")
                                    if content:
                                        logger.info(f"AI report generated successfully (attempt {attempt + 1}, length: {len(content)} chars)")
                                        
                                        # 记录操作日志
                                        log_operation(
                                            operation_type="ai_report_generated",
                                            status="success",
                                            operation_detail={
                                                "model": request_data.get("model"),
                                                "content_length": len(content),
                                                "attempt": attempt + 1
                                            }
                                        )
                                        
                                        return content
                                    else:
                                        logger.error(f"No content in AI response (attempt {attempt + 1}): {result}")
                                        last_error = "Empty response"
                                else:
                                    logger.error(f"Unexpected response format (attempt {attempt + 1}): {result}")
                                    last_error = "Invalid response format"
                            except Exception as e:
                                logger.error(f"Error parsing DeepSeek API response (attempt {attempt + 1}): {e}", exc_info=True)
                                last_error = f"Response parsing error: {str(e)}"
                                # 如果是最后一次尝试，不再重试
                                if attempt >= self.max_retries:
                                    break
                                continue
                                
                        elif response.status >= 500:
                            # 5XX错误，可以重试
                            error_text = await response.text()
                            logger.warning(
                                f"DeepSeek API server error (attempt {attempt + 1}/{self.max_retries + 1}): "
                                f"{response.status} - {error_text[:200]}"
                            )
                            last_error = f"Server error {response.status}"
                        else:
                            # 4XX错误，不重试
                            error_text = await response.text()
                            logger.error(f"DeepSeek API client error: {response.status} - {error_text[:200]}")
                            last_error = f"Client error {response.status}"
                            break
                            
            except asyncio.TimeoutError:
                logger.warning(
                    f"DeepSeek API timeout (attempt {attempt + 1}/{self.max_retries + 1}), "
                    f"timeout threshold was {attempt_timeout}s"
                )
                last_error = "Request timeout"
                # 如果是最后一次尝试，不再重试
                if attempt >= self.max_retries:
                    break
                # 继续重试
                continue
                    
            except aiohttp.ClientError as e:
                logger.warning(
                    f"DeepSeek API connection error (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                )
                last_error = f"Connection error: {str(e)}"
                # 如果是最后一次尝试，不再重试
                if attempt >= self.max_retries:
                    break
                # 继续重试
                continue
                    
            except Exception as e:
                logger.error(f"Unexpected error calling DeepSeek API: {e}")
                last_error = f"Unexpected error: {str(e)}"
                break
        
        # 所有重试都失败
        logger.error(f"Failed to generate AI report after {self.max_retries + 1} attempts. Last error: {last_error}")
        return None


# 创建全局AI服务实例
ai_service = AIService()

