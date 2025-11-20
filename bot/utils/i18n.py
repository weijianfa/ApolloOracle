"""
国际化工具模块
Internationalization (i18n) utility module
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional
from bot.utils.logger import logger

# 支持的语言列表
SUPPORTED_LANGUAGES = ['en', 'zh']
DEFAULT_LANGUAGE = 'en'

# 语言文件路径
LOCALES_DIR = Path(__file__).parent.parent.parent / 'locales'


class I18n:
    """国际化类"""
    
    def __init__(self):
        self._translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()
    
    def _load_translations(self):
        """加载所有语言文件"""
        for lang in SUPPORTED_LANGUAGES:
            lang_file = LOCALES_DIR / f"{lang}.json"
            if lang_file.exists():
                try:
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        self._translations[lang] = json.load(f)
                    logger.info(f"Loaded translations for language: {lang}")
                except Exception as e:
                    logger.error(f"Failed to load translations for {lang}: {e}")
                    self._translations[lang] = {}
            else:
                logger.warning(f"Translation file not found: {lang_file}")
                self._translations[lang] = {}
    
    def get_language(self, language_code: Optional[str] = None) -> str:
        """
        获取用户语言代码
        
        Args:
            language_code: Telegram用户语言代码（如 'en', 'zh-CN', 'en-US'）
        
        Returns:
            支持的语言代码（'en' 或 'zh'）
        """
        if not language_code:
            return DEFAULT_LANGUAGE
        
        # 标准化语言代码（'zh-CN' -> 'zh', 'en-US' -> 'en'）
        lang = language_code.lower().split('-')[0]
        
        if lang in SUPPORTED_LANGUAGES:
            return lang
        
        # 默认返回英语
        return DEFAULT_LANGUAGE
    
    def t(self, key: str, language: Optional[str] = None, **kwargs) -> str:
        """
        翻译文本
        
        Args:
            key: 翻译键（支持点号分隔的嵌套键，如 'welcome.title'）
            language: 目标语言（'en' 或 'zh'），如果为None则使用默认语言
            **kwargs: 格式化参数
        
        Returns:
            翻译后的文本，如果找不到则返回键本身
        """
        if language is None:
            language = DEFAULT_LANGUAGE
        
        if language not in self._translations:
            language = DEFAULT_LANGUAGE
        
        # 获取翻译文本
        translation = self._get_nested_value(self._translations.get(language, {}), key)
        
        if translation is None:
            # 如果找不到，尝试从默认语言获取
            if language != DEFAULT_LANGUAGE:
                translation = self._get_nested_value(self._translations.get(DEFAULT_LANGUAGE, {}), key)
            
            # 如果还是找不到，返回键本身
            if translation is None:
                logger.warning(f"Translation key not found: {key} (language: {language})")
                return key
        
        # 格式化文本（如果有参数）
        if kwargs:
            try:
                return translation.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing format parameter {e} for key: {key}")
                return translation
        
        return translation
    
    def _get_nested_value(self, data: Dict, key: str) -> Optional[str]:
        """
        获取嵌套字典的值（支持点号分隔的键）
        
        Args:
            data: 字典数据
            key: 键（支持 'key.subkey.subsubkey' 格式）
        
        Returns:
            值或None
        """
        keys = key.split('.')
        value = data
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return None
            else:
                return None
        
        return value if isinstance(value, str) else None
    
    def reload(self):
        """重新加载翻译文件"""
        self._translations.clear()
        self._load_translations()
        logger.info("Translations reloaded")


# 创建全局i18n实例
i18n = I18n()


def get_user_language(user_language_code: Optional[str] = None) -> str:
    """
    获取用户语言（便捷函数）
    
    Args:
        user_language_code: Telegram用户语言代码
    
    Returns:
        支持的语言代码
    """
    return i18n.get_language(user_language_code)


def translate(key: str, language: Optional[str] = None, **kwargs) -> str:
    """
    翻译文本（便捷函数）
    
    Args:
        key: 翻译键
        language: 目标语言
        **kwargs: 格式化参数
    
    Returns:
        翻译后的文本
    """
    return i18n.t(key, language, **kwargs)

