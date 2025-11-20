"""
基础功能测试（不依赖外部API）
"""
import pytest
from bot.config.settings import Settings
from bot.utils.logger import setup_logger


def test_settings_validation():
    """测试配置验证"""
    # 测试缺少必要配置
    original_token = Settings.TELEGRAM_BOT_TOKEN
    Settings.TELEGRAM_BOT_TOKEN = ""
    
    with pytest.raises(ValueError):
        Settings.validate()
    
    # 恢复
    Settings.TELEGRAM_BOT_TOKEN = original_token


def test_logger_setup():
    """测试日志设置"""
    logger = setup_logger("test")
    assert logger is not None
    assert logger.name == "test"


def test_environment_detection():
    """测试环境检测"""
    original_env = Settings.ENVIRONMENT
    
    Settings.ENVIRONMENT = "development"
    assert Settings.is_development() is True
    assert Settings.is_production() is False
    
    Settings.ENVIRONMENT = "production"
    assert Settings.is_development() is False
    assert Settings.is_production() is True
    
    # 恢复
    Settings.ENVIRONMENT = original_env

