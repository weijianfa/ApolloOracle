"""
缘分居API服务模块（八字接口）
"""
import aiohttp
import asyncio
import json
from typing import Optional, Dict, Any
from datetime import datetime
from bot.config.settings import settings
from bot.utils.logger import logger
from bot.utils.operation_logger import log_operation


class BaziService:
    """缘分居API服务类"""
    
    def __init__(self):
        self.api_key = settings.YUANFENJU_API_KEY
        self.api_url = settings.YUANFENJU_API_URL
        self.timeout = 15  # 15秒超时
        self.max_retries = 2  # 最多重试2次
        self.mock_mode = settings.PINGPONG_USE_MOCK
        self.default_calendar_type = 1  # 1=公历
        self.default_sect = 2  # 晚子时算当天
        self.default_zhen = 2  # 不考虑真太阳时
        self.default_lang = "zh-cn"
        self.default_factor = 0
    
    async def get_bazi_data(
        self,
        name: str,
        birthday: str,
        birth_time: str,
        gender: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取八字数据
        
        Args:
            name: 姓名
            birthday: 出生日期 (YYYY-MM-DD)
            birth_time: 出生时间 (HH:MM)
            gender: 性别 (1=男, 2=女)
            
        Returns:
            八字数据字典，失败返回None
        """
        if not self.api_key:
            if self.mock_mode:
                logger.warning(
                    f"Yuanfenju API key missing, using mock Bazi data (mock mode enabled). "
                    f"API URL: {self.api_url}"
                )
                return self._generate_mock_bazi_data(name, birthday, birth_time, gender)
            logger.error(
                f"Yuanfenju API key not configured. "
                f"Please set YUANFENJU_API_KEY in .env file. "
                f"API URL: {self.api_url}"
            )
            return None
        
        payload = self._build_request_payload(name, birthday, birth_time, gender)
        if not payload:
            return None
        
        # 为日志构造安全版本（隐藏api_key）
        safe_payload = payload.copy()
        if "api_key" in safe_payload:
            safe_payload["api_key"] = "***"
        
        # 重试机制
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    # 指数退避：第1次重试等待1秒，第2次等待2秒
                    wait_time = 2 ** (attempt - 1)
                    logger.info(f"Retrying Bazi API call (attempt {attempt + 1}/{self.max_retries + 1}), waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                
                logger.info(
                    f"Calling Yuanfenju Bazi API (attempt {attempt + 1}/{self.max_retries + 1}). "
                    f"URL: {self.api_url}. Payload: {json.dumps(safe_payload, ensure_ascii=False)}"
                )
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.api_url,
                        data=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded",
                            "User-Agent": "Telegram-Bot/1.0"
                        }
                    ) as response:
                        response_text = await response.text()
                        logger.info(
                            f"Yuanfenju API responded with status {response.status} "
                            f"(attempt {attempt + 1}). Raw response (first 500 chars): {response_text[:500]}"
                        )
                        
                        if response.status == 200:
                            try:
                                result = json.loads(response_text)
                            except Exception:
                                logger.error(f"Failed to parse Bazi API response as JSON: {response_text[:200]}")
                                last_error = "Invalid JSON response"
                                break
                            
                            # 检查API返回的状态
                            errcode = result.get("errcode")
                            code = result.get("code")
                            status = result.get("status")
                            success = (
                                (errcode is not None and str(errcode) == "0")
                                or (code is not None and str(code) == "200")
                                or (status == "success")
                            )
                            
                            if success:
                                logger.info(f"Bazi data retrieved successfully for {name}")
                                
                                # 记录操作日志
                                log_operation(
                                    operation_type="bazi_api_call",
                                    status="success",
                                    operation_detail={
                                        "name": name,
                                        "birthday": birthday,
                                        "attempt": attempt + 1
                                    }
                                )
                                data = result.get("data") or result
                                return data
                            else:
                                error_msg = (
                                    result.get("errmsg")
                                    or result.get("message")
                                    or result.get("error")
                                    or "Unknown error"
                                )
                                logger.error(f"Bazi API returned error: {error_msg}")
                                last_error = error_msg
                                
                                # 如果是业务错误（非5XX），不重试
                                if response.status < 500:
                                    break
                        elif response.status >= 500:
                            # 5XX错误，可以重试
                            logger.warning(
                                f"Bazi API server error (attempt {attempt + 1}/{self.max_retries + 1}): "
                                f"{response.status} - {response_text[:200]}"
                            )
                            last_error = f"Server error {response.status}"
                        else:
                            # 4XX错误，不重试
                            logger.error(f"Bazi API client error: {response.status} - {response_text[:200]}")
                            last_error = f"Client error {response.status}"
                            break
                            
            except asyncio.TimeoutError:
                logger.warning(
                    f"Bazi API timeout (attempt {attempt + 1}/{self.max_retries + 1})"
                )
                last_error = "Request timeout"
                if attempt == self.max_retries:
                    break
                    
            except aiohttp.ClientError as e:
                logger.warning(
                    f"Bazi API connection error (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                )
                last_error = f"Connection error: {str(e)}"
                if attempt == self.max_retries:
                    break
                    
            except Exception as e:
                logger.error(f"Unexpected error calling Bazi API: {e}")
                last_error = f"Unexpected error: {str(e)}"
                break
        
        # 所有重试都失败
        logger.error(
            f"Failed to get Bazi data after {self.max_retries + 1} attempts. "
            f"Last error: {last_error}. "
            f"API URL: {self.api_url}, "
            f"Request data: name={name}, birthday={birthday}, time={birth_time}, gender={gender}"
        )
        if self.mock_mode:
            logger.warning(
                f"Using mock Bazi data due to API failure (mock mode enabled). "
                f"Original error: {last_error}"
            )
            return self._generate_mock_bazi_data(name, birthday, birth_time, gender)
        logger.error(
            f"Bazi API call failed and mock mode is disabled. "
            f"To use mock data in development, set PINGPONG_USE_MOCK=true in .env file."
        )
        return None
    
    def parse_bazi_response(self, bazi_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析八字API返回的数据
        
        Args:
            bazi_data: API返回的原始数据
            
        Returns:
            解析后的结构化数据
        """
        try:
            # 根据实际API返回格式解析
            # 这里是一个示例结构，需要根据实际API文档调整
            parsed = {
                "birthday": bazi_data.get("birthday"),
                "birth_time": bazi_data.get("time"),
                "gender": bazi_data.get("gender"),
                "bazi": bazi_data.get("bazi", {}),  # 八字信息
                "wuxing": bazi_data.get("wuxing", {}),  # 五行信息
                "analysis": bazi_data.get("analysis", {}),  # 分析结果
                "raw_data": bazi_data  # 保留原始数据
            }
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing Bazi response: {e}")
            return {"raw_data": bazi_data}

    def _generate_mock_bazi_data(self, name: str, birthday: str, birth_time: str, gender: int) -> Dict[str, Any]:
        """
        生成Mock模式下的八字数据，便于本地开发调试
        """
        logger.info(f"[MOCK] Generating mock Bazi data for {name} ({birthday} {birth_time})")
        return {
            "name": name,
            "birthday": birthday,
            "time": birth_time,
            "gender": gender,
            "bazi": {
                "heavenly_stems": ["庚", "戊", "乙", "辛"],
                "earthly_branches": ["子", "辰", "巳", "酉"],
                "day_master": "乙木",
                "structure": "偏印格"
            },
            "wuxing": {
                "metal": 2,
                "wood": 3,
                "water": 2,
                "fire": 1,
                "earth": 2,
                "favorable": ["水", "木"]
            },
            "analysis": {
                "career": "具备创新思维，适合文化创意、教育或咨询类行业。2025年偏财透出，适合尝试副业合作。",
                "wealth": "财星稳定但不宜冒进，重视长期积累和稳健投资。",
                "relationship": "感情以温柔沟通为主，2025下半年有利于确立长期关系。",
                "health": "注意肝胆与睡眠，保持规律作息，适合多亲近自然。",
                "advice": "善用乙木包容力，保持学习和输出，能在变化中掌握主动权。"
            }
        }

    def _build_request_payload(
        self,
        name: str,
        birthday: str,
        birth_time: str,
        gender: int
    ) -> Optional[Dict[str, Any]]:
        """
        根据缘分居文档构建 form-data 参数
        """
        try:
            date_obj = datetime.strptime(birthday, "%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid birthday format for Bazi API: {birthday}")
            return None
        
        time_str = birth_time or "12:00"
        try:
            time_obj = datetime.strptime(time_str, "%H:%M")
        except ValueError:
            logger.warning(f"Invalid birth_time '{birth_time}', fallback to 12:00")
            time_obj = datetime.strptime("12:00", "%H:%M")
        
        sex_value = 0 if gender == 1 else 1  # 文档：0=男,1=女
        
        payload = {
            "api_key": self.api_key,
            "name": name or "用户",
            "sex": sex_value,
            "type": self.default_calendar_type,
            "year": date_obj.year,
            "month": date_obj.month,
            "day": date_obj.day,
            "hours": time_obj.hour,
            "minute": time_obj.minute,
            "sect": self.default_sect,
            "zhen": self.default_zhen,
            "lang": self.default_lang,
            "factor": self.default_factor,
        }
        
        return payload


# 创建全局服务实例
bazi_service = BaziService()

