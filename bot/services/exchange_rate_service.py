"""
实时汇率服务模块
"""
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from bot.config.settings import settings
from bot.utils.logger import logger
from bot.database.db import get_db_session
from bot.models.exchange_rate import ExchangeRate
import json


class ExchangeRateService:
    """汇率服务类"""
    
    # 支持的货币列表
    SUPPORTED_CURRENCIES = {
        'USD': {'symbol': '$', 'decimals': 2, 'rounding': 'normal'},
        'EUR': {'symbol': '€', 'decimals': 2, 'rounding': 'normal'},
        'GBP': {'symbol': '£', 'decimals': 2, 'rounding': 'normal'},
        'JPY': {'symbol': '¥', 'decimals': 0, 'rounding': 'round'},  # 日元取整
        'HKD': {'symbol': 'HK$', 'decimals': 2, 'rounding': 'normal'},
        'CAD': {'symbol': 'C$', 'decimals': 2, 'rounding': 'normal'},
        'AUD': {'symbol': 'A$', 'decimals': 2, 'rounding': 'normal'},
    }
    
    # 缓存有效期（6小时）
    CACHE_DURATION = timedelta(hours=6)
    
    def __init__(self):
        self.api_key = settings.EXCHANGE_RATE_API_KEY
        self.api_url = settings.EXCHANGE_RATE_API_URL
        self.base_currency = 'USD'
        self.redis_client = None  # Redis客户端（可选）
        
        # 尝试初始化Redis（如果可用）
        try:
            if settings.REDIS_URL and 'redis' in settings.REDIS_URL:
                import redis
                self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis not available, using database cache only: {e}")
    
    async def get_exchange_rate(
        self,
        target_currency: str,
        base_currency: str = 'USD'
    ) -> Optional[Decimal]:
        """
        获取汇率
        
        Args:
            target_currency: 目标货币代码
            base_currency: 基础货币代码（默认USD）
            
        Returns:
            汇率值，失败返回None
        """
        if target_currency == base_currency:
            return Decimal('1.0')
        
        # 检查Redis缓存
        if self.redis_client:
            cache_key = f"exchange_rate:{base_currency}:{target_currency}"
            cached_rate = self.redis_client.get(cache_key)
            if cached_rate:
                try:
                    rate = Decimal(cached_rate)
                    logger.debug(f"Rate from Redis cache: {base_currency}->{target_currency}={rate}")
                    return rate
                except:
                    pass
        
        # 检查数据库缓存
        with get_db_session() as db:
            rate_record = db.query(ExchangeRate).filter(
                ExchangeRate.base_currency == base_currency,
                ExchangeRate.target_currency == target_currency
            ).first()
            
            if rate_record:
                # 检查是否过期
                age = datetime.now() - rate_record.updated_at
                if age < self.CACHE_DURATION:
                    rate = Decimal(str(rate_record.rate))
                    logger.debug(f"Rate from database cache: {base_currency}->{target_currency}={rate}")
                    
                    # 更新Redis缓存
                    if self.redis_client:
                        self.redis_client.setex(
                            f"exchange_rate:{base_currency}:{target_currency}",
                            int(self.CACHE_DURATION.total_seconds()),
                            str(rate)
                        )
                    
                    return rate
        
        # 缓存过期或不存在，从API获取
        logger.info(f"Fetching exchange rate from API: {base_currency}->{target_currency}")
        rates = await self._fetch_rates_from_api(base_currency)
        
        if rates and target_currency in rates:
            rate = Decimal(str(rates[target_currency]))
            
            # 保存到数据库
            with get_db_session() as db:
                existing = db.query(ExchangeRate).filter(
                    ExchangeRate.base_currency == base_currency,
                    ExchangeRate.target_currency == target_currency
                ).first()
                
                if existing:
                    existing.rate = rate
                    existing.updated_at = datetime.now()
                else:
                    new_rate = ExchangeRate(
                        base_currency=base_currency,
                        target_currency=target_currency,
                        rate=rate
                    )
                    db.add(new_rate)
                db.commit()
            
            # 保存到Redis
            if self.redis_client:
                self.redis_client.setex(
                    f"exchange_rate:{base_currency}:{target_currency}",
                    int(self.CACHE_DURATION.total_seconds()),
                    str(rate)
                )
            
            return rate
        
        return None
    
    async def _fetch_rates_from_api(self, base_currency: str = 'USD') -> Optional[Dict[str, float]]:
        """
        从API获取汇率
        
        Args:
            base_currency: 基础货币
            
        Returns:
            汇率字典，失败返回None
        """
        try:
            # 构建API URL
            if 'exchangerate-api.com' in self.api_url:
                # Exchangerate-API免费版不需要API密钥，直接访问即可
                # 格式：https://api.exchangerate-api.com/v4/latest/{base_currency}
                url = f"{self.api_url.replace('/latest/USD', '')}/latest/{base_currency}"
                # 如果有API密钥（付费版），可以添加到URL
                if self.api_key and self.api_key.strip() and self.api_key != 'your_exchange_rate_key':
                    url += f"?apikey={self.api_key}"
            else:
                url = self.api_url
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # 解析不同API格式
                        if 'rates' in data:
                            return data['rates']
                        elif 'conversion_rates' in data:
                            return data['conversion_rates']
                        else:
                            # 尝试直接使用返回数据
                            return data
                    else:
                        logger.error(f"Exchange rate API error: {response.status}")
                        return self._get_fallback_rates()
                        
        except asyncio.TimeoutError:
            logger.warning("Exchange rate API timeout, using cached or fallback rates")
            return self._get_fallback_rates()
        except Exception as e:
            logger.error(f"Error fetching exchange rates: {e}")
            # API失败时尝试使用备用汇率
            return self._get_fallback_rates()
    
    def _get_fallback_rates(self) -> Dict[str, float]:
        """
        获取备用汇率（用于开发测试）
        
        Returns:
            备用汇率字典
        """
        return {
            'USD': 1.0,
            'EUR': 0.92,
            'GBP': 0.79,
            'JPY': 149.5,
            'HKD': 7.82,
            'CAD': 1.35,
            'AUD': 1.52,
        }
    
    def convert_price(
        self,
        amount_usd: Decimal,
        target_currency: str
    ) -> Optional[Decimal]:
        """
        转换价格
        
        Args:
            amount_usd: USD金额
            target_currency: 目标货币
            
        Returns:
            转换后的金额，失败返回None
        """
        if target_currency == 'USD':
            return amount_usd
        
        # 获取汇率（同步调用，需要在实际使用时改为异步）
        # 这里先返回None，实际使用时需要通过异步方法获取
        return None
    
    async def convert_price_async(
        self,
        amount_usd: Decimal,
        target_currency: str
    ) -> Optional[Decimal]:
        """
        异步转换价格
        
        Args:
            amount_usd: USD金额
            target_currency: 目标货币
            
        Returns:
            转换后的金额，失败返回None
        """
        if target_currency == 'USD':
            return amount_usd
        
        rate = await self.get_exchange_rate(target_currency, 'USD')
        if not rate:
            return None
        
        converted = amount_usd * rate
        return converted
    
    def format_price(
        self,
        amount: Decimal,
        currency: str
    ) -> str:
        """
        格式化价格显示
        
        Args:
            amount: 金额
            currency: 货币代码
            
        Returns:
            格式化后的价格字符串
        """
        if currency not in self.SUPPORTED_CURRENCIES:
            # 不支持的货币，使用默认格式
            return f"{amount:.2f} {currency}"
        
        currency_info = self.SUPPORTED_CURRENCIES[currency]
        symbol = currency_info['symbol']
        decimals = currency_info['decimals']
        rounding = currency_info['rounding']
        
        # 根据货币规则取整
        if rounding == 'round' and decimals == 0:
            # 日元：取整到整数
            rounded_amount = amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        else:
            # 其他货币：保留指定小数位
            decimal_places = Decimal('0.1') ** decimals
            rounded_amount = amount.quantize(decimal_places, rounding=ROUND_HALF_UP)
        
        # 格式化显示
        if decimals == 0:
            return f"{symbol}{rounded_amount:,.0f}"
        else:
            return f"{symbol}{rounded_amount:,.2f}"
    
    def detect_user_currency(self, user_language_code: Optional[str] = None) -> str:
        """
        检测用户货币（基于语言代码）
        
        Args:
            user_language_code: 用户语言代码（如 'en-US', 'zh-CN'）
            
        Returns:
            货币代码
        """
        # 默认货币映射
        currency_map = {
            'en-US': 'USD',
            'en-GB': 'GBP',
            'en-AU': 'AUD',
            'en-CA': 'CAD',
            'zh-CN': 'CNY',  # 人民币（如果支持）
            'zh-HK': 'HKD',
            'zh-TW': 'TWD',  # 台币（如果支持）
            'ja': 'JPY',
        }
        
        if user_language_code:
            # 尝试精确匹配
            if user_language_code in currency_map:
                return currency_map[user_language_code]
            
            # 尝试语言代码匹配
            lang = user_language_code.split('-')[0]
            if lang == 'en':
                return 'USD'  # 默认英语用户使用USD
            elif lang == 'zh':
                return 'HKD'  # 默认中文用户使用HKD
            elif lang == 'ja':
                return 'JPY'
        
        # 默认返回USD
        return 'USD'
    
    async def refresh_all_rates(self) -> bool:
        """
        刷新所有支持的货币汇率
        
        Returns:
            是否成功
        """
        try:
            rates = await self._fetch_rates_from_api(self.base_currency)
            if not rates:
                return False
            
            with get_db_session() as db:
                for currency in self.SUPPORTED_CURRENCIES.keys():
                    if currency == self.base_currency:
                        continue
                    
                    if currency in rates:
                        rate = Decimal(str(rates[currency]))
                        
                        existing = db.query(ExchangeRate).filter(
                            ExchangeRate.base_currency == self.base_currency,
                            ExchangeRate.target_currency == currency
                        ).first()
                        
                        if existing:
                            existing.rate = rate
                            existing.updated_at = datetime.now()
                        else:
                            new_rate = ExchangeRate(
                                base_currency=self.base_currency,
                                target_currency=currency,
                                rate=rate
                            )
                            db.add(new_rate)
                
                db.commit()
            
            logger.info("All exchange rates refreshed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing exchange rates: {e}")
            return False


# 创建全局汇率服务实例
exchange_rate_service = ExchangeRateService()

