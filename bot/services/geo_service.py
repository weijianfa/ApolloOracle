"""
地理限制服务模块
Geographic Restriction Service Module
"""
from typing import Optional, Tuple
from bot.config.settings import settings
from bot.utils.logger import logger

# 中国大陆的国家代码（ISO 3166-1 alpha-2）
BLOCKED_COUNTRIES = ["CN"]  # 中国大陆

# 允许访问的国家/地区代码（可选，如果为空则允许所有非阻止国家）
ALLOWED_COUNTRIES = [
    # 欧美
    "US", "CA", "GB", "IE", "FR", "DE", "IT", "ES", "NL", "BE", "CH", "AT", "SE", "NO", "DK", "FI", "PL", "PT", "GR",
    # 东南亚
    "SG", "MY", "TH", "PH", "ID", "VN", "KH", "LA", "MM", "BN",
    # 港澳台
    "HK", "MO", "TW",
    # 其他
    "AU", "NZ", "JP", "KR", "IN", "BR", "MX", "AR", "CL", "ZA"
]


class GeoService:
    """地理限制服务类"""
    
    def __init__(self):
        self.maxmind_license_key = settings.MAXMIND_LICENSE_KEY
        self.maxmind_enabled = bool(self.maxmind_license_key)
        
        if not self.maxmind_enabled:
            logger.warning(
                "MaxMind GeoIP not configured. Geographic restriction will be disabled. "
                "Set MAXMIND_LICENSE_KEY in .env to enable."
            )
    
    def get_country_from_ip(self, ip_address: str) -> Optional[str]:
        """
        根据IP地址获取国家代码
        
        Args:
            ip_address: IP地址
        
        Returns:
            国家代码（ISO 3166-1 alpha-2），失败返回None
        """
        if not self.maxmind_enabled:
            # 如果没有配置MaxMind，返回None（不进行限制）
            logger.debug(f"MaxMind not enabled, skipping IP check for {ip_address}")
            return None
        
        try:
            # 使用MaxMind GeoIP2数据库查询
            import maxminddb
            
            # 注意：需要下载MaxMind GeoLite2数据库文件
            # 可以从 https://dev.maxmind.com/geoip/geoip2/geolite2/ 下载
            # 或者使用MaxMind GeoIP2 API
            # 这里提供一个基础框架，实际使用时需要配置数据库文件路径
            
            # 方法1：使用本地数据库文件（需要下载GeoLite2-Country.mmdb）
            # db_path = "data/GeoLite2-Country.mmdb"
            # with maxminddb.open_database(db_path) as reader:
            #     response = reader.get(ip_address)
            #     if response:
            #         return response.get("country", {}).get("iso_code")
            
            # 方法2：使用MaxMind GeoIP2 Web Service API
            # 需要安装 geoip2 库
            # import geoip2.webservice
            # client = geoip2.webservice.Client(account_id, self.maxmind_license_key)
            # response = client.country(ip_address)
            # return response.country.iso_code
            
            # 当前实现：返回None（表示未检测，不进行限制）
            logger.debug(f"IP geolocation not fully implemented for {ip_address}")
            return None
            
        except ImportError:
            logger.warning("maxminddb or geoip2 not installed. Install with: pip install maxminddb geoip2")
            return None
        except Exception as e:
            logger.error(f"Error getting country from IP {ip_address}: {e}", exc_info=True)
            return None
    
    def is_ip_allowed(self, ip_address: str) -> Tuple[bool, Optional[str]]:
        """
        检查IP地址是否允许访问
        
        Args:
            ip_address: IP地址
        
        Returns:
            (是否允许, 原因说明)
        """
        # 如果没有启用MaxMind，默认允许访问（开发环境）
        if not self.maxmind_enabled:
            if settings.is_development():
                logger.debug(f"Development mode: allowing IP {ip_address} without geo check")
                return True, None
            else:
                # 生产环境但没有配置GeoIP，记录警告但允许访问
                logger.warning(
                    f"Production mode but MaxMind not configured. "
                    f"Allowing IP {ip_address} (geographic restriction disabled)."
                )
                return True, None
        
        # 获取国家代码
        country_code = self.get_country_from_ip(ip_address)
        
        if country_code is None:
            # 无法确定国家，默认允许（避免误拦截）
            logger.warning(f"Could not determine country for IP {ip_address}, allowing access")
            return True, None
        
        # 检查是否在阻止列表中
        if country_code in BLOCKED_COUNTRIES:
            logger.info(f"IP {ip_address} from blocked country {country_code}, denying access")
            return False, f"Service is not available in {country_code}. This service is only available for overseas users."
        
        # 如果设置了允许列表，检查是否在允许列表中
        if ALLOWED_COUNTRIES:
            if country_code not in ALLOWED_COUNTRIES:
                logger.info(f"IP {ip_address} from country {country_code} not in allowed list, denying access")
                return False, f"Service is not available in {country_code}. This service is only available for specific regions."
        
        # 允许访问
        logger.debug(f"IP {ip_address} from country {country_code}, allowing access")
        return True, None
    
    def get_user_ip_from_telegram(self, update) -> Optional[str]:
        """
        从Telegram更新对象中获取用户IP地址
        
        注意：Telegram Bot API不直接提供用户IP地址
        这个方法返回None，实际IP检测需要在Webhook层面进行
        
        Args:
            update: Telegram更新对象
        
        Returns:
            IP地址（通常为None，因为Bot API不提供）
        """
        # Telegram Bot API不提供用户IP地址
        # 如果需要IP检测，需要在Webhook服务器层面获取请求IP
        # 或者在用户访问Web界面时检测
        return None


# 创建全局地理服务实例
geo_service = GeoService()

