"""
应用配置管理模块
"""
import os
from dotenv import load_dotenv
from typing import Optional

# 加载环境变量
load_dotenv()


class Settings:
    """应用配置类"""
    
    # Telegram Bot配置
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # PingPong Payment配置
    PINGPONG_API_KEY: str = os.getenv("PINGPONG_API_KEY", "")
    PINGPONG_WEBHOOK_SECRET: str = os.getenv("PINGPONG_WEBHOOK_SECRET", "")
    PINGPONG_MERCHANT_ID: str = os.getenv("PINGPONG_MERCHANT_ID", "")
    PINGPONG_API_BASE_URL: str = os.getenv("PINGPONG_API_BASE_URL", "https://api.pingpongx.com")
    PINGPONG_MOCK_PAYMENT_URL: str = os.getenv(
        "PINGPONG_MOCK_PAYMENT_URL",
        "https://example.com/mock-pingpong-payment"
    )
    
    # DeepSeek API配置
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_URL: str = os.getenv(
        "DEEPSEEK_API_URL", 
        "https://api.deepseek.com/v1/chat/completions"
    )
    
    # 缘分居API配置
    YUANFENJU_API_KEY: str = os.getenv("YUANFENJU_API_KEY", "")
    YUANFENJU_API_URL: str = os.getenv(
        "YUANFENJU_API_URL",
        "https://api.yuanfenju.com/index.php/v1/Bazi/jingsuan"
    )
    
    # 汇率API配置
    EXCHANGE_RATE_API_KEY: str = os.getenv("EXCHANGE_RATE_API_KEY", "")
    EXCHANGE_RATE_API_URL: str = os.getenv(
        "EXCHANGE_RATE_API_URL",
        "https://api.exchangerate-api.com/v4/latest/USD"
    )
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///bot.db")
    
    # Redis配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # 管理员配置
    @staticmethod
    def _safe_int_env(key: str, default: int = 0) -> int:
        """安全地获取整数环境变量"""
        try:
            value = os.getenv(key, str(default))
            if not value or value.strip() == "":
                return default
            return int(value)
        except (ValueError, TypeError):
            return default
    
    ADMIN_TELEGRAM_ID: int = _safe_int_env("ADMIN_TELEGRAM_ID", 0)

    @staticmethod
    def _safe_bool_env(key: str, default: bool = False) -> bool:
        """安全地获取布尔环境变量"""
        value = os.getenv(key)
        if value is None:
            return default
        return value.strip().lower() in ("1", "true", "yes", "on")
    
    # DeepSeek API超时配置（需要在_safe_int_env定义后使用）
    # AI生成时间与内容大小相关，特别是启用深度思考时可能需要更长时间
    # 单次请求超时：默认60秒（1分钟），可通过环境变量覆盖
    DEEPSEEK_API_TIMEOUT: int = _safe_int_env("DEEPSEEK_API_TIMEOUT", 60)
    # 总体超时（包括重试）：默认240秒（4分钟），可通过环境变量覆盖
    DEEPSEEK_API_TOTAL_TIMEOUT: int = _safe_int_env("DEEPSEEK_API_TOTAL_TIMEOUT", 240)
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "")
    
    # 环境配置
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    PINGPONG_USE_MOCK: bool = _safe_bool_env("PINGPONG_USE_MOCK", True)
    
    # MaxMind GeoIP配置
    MAXMIND_LICENSE_KEY: str = os.getenv("MAXMIND_LICENSE_KEY", "")
    
    # Webhook配置（生产环境）
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    WEBHOOK_PORT: int = _safe_int_env("WEBHOOK_PORT", 8443)
    WEBHOOK_LISTEN: str = os.getenv("WEBHOOK_LISTEN", "0.0.0.0")
    
    # PingPong Webhook服务器配置（独立运行，用于接收支付回调）
    PINGPONG_WEBHOOK_PORT: int = _safe_int_env("PINGPONG_WEBHOOK_PORT", 8000)
    PINGPONG_WEBHOOK_LISTEN: str = os.getenv("PINGPONG_WEBHOOK_LISTEN", "0.0.0.0")
    
    # SSL证书路径（生产环境）
    SSL_CERT_PATH: str = os.getenv("SSL_CERT_PATH", "")
    SSL_KEY_PATH: str = os.getenv("SSL_KEY_PATH", "")
    
    @classmethod
    def validate(cls) -> None:
        """
        验证必要的配置项
        
        Raises:
            ValueError: 如果缺少必要的配置项
        """
        required_configs = {
            "TELEGRAM_BOT_TOKEN": cls.TELEGRAM_BOT_TOKEN,
        }
        
        missing = [key for key, value in required_configs.items() if not value]
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please check your .env file or set these environment variables."
            )
    
    @classmethod
    def is_production(cls) -> bool:
        """判断是否为生产环境"""
        return cls.ENVIRONMENT.lower() == "production"
    
    @classmethod
    def is_development(cls) -> bool:
        """判断是否为开发环境"""
        return cls.ENVIRONMENT.lower() == "development"


# 创建全局配置实例
settings = Settings()

