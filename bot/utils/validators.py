"""
输入验证工具
"""
import re
from datetime import datetime
from typing import Optional, Tuple


def validate_date(date_str: str) -> Tuple[bool, Optional[str]]:
    """
    验证日期格式 (YYYY-MM-DD)
    
    Args:
        date_str: 日期字符串
        
    Returns:
        (是否有效, 错误信息)
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        # 检查日期是否合理（不能是未来日期，不能太早）
        if date_obj > datetime.now():
            return False, "日期不能是未来日期"
        if date_obj.year < 1900:
            return False, "日期不能早于1900年"
        return True, None
    except ValueError:
        return False, "日期格式错误，请使用 YYYY-MM-DD 格式（例如：1990-01-01）"


def validate_time(time_str: str) -> Tuple[bool, Optional[str]]:
    """
    验证时间格式 (HH:MM)
    
    Args:
        time_str: 时间字符串
        
    Returns:
        (是否有效, 错误信息)
    """
    try:
        datetime.strptime(time_str, "%H:%M")
        return True, None
    except ValueError:
        return False, "时间格式错误，请使用 HH:MM 格式（例如：14:30）"


def validate_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    验证姓名
    
    Args:
        name: 姓名字符串
        
    Returns:
        (是否有效, 错误信息)
    """
    if not name or not name.strip():
        return False, "姓名不能为空"
    
    name = name.strip()
    
    # 长度检查（2-50个字符）
    if len(name) < 2:
        return False, "姓名至少需要2个字符"
    if len(name) > 50:
        return False, "姓名不能超过50个字符"
    
    # 检查是否包含特殊字符（允许中英文、数字、空格、连字符）
    if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9\s\-]+$', name):
        return False, "姓名只能包含中英文、数字、空格和连字符"
    
    return True, None


def validate_zodiac(zodiac: str) -> Tuple[bool, Optional[str]]:
    """
    验证星座
    
    Args:
        zodiac: 星座字符串
        
    Returns:
        (是否有效, 错误信息)
    """
    from bot.config.products import ZODIAC_SIGNS
    
    zodiac_lower = zodiac.lower()
    valid_zodiacs = [z[0].lower() for z in ZODIAC_SIGNS] + [z[1] for z in ZODIAC_SIGNS]
    
    if zodiac_lower not in [z.lower() for z in valid_zodiacs]:
        return False, f"无效的星座，请从以下选择：{', '.join([z[0] for z in ZODIAC_SIGNS])}"
    
    return True, None


def validate_chinese_zodiac(zodiac: str) -> Tuple[bool, Optional[str]]:
    """
    验证生肖
    
    Args:
        zodiac: 生肖字符串
        
    Returns:
        (是否有效, 错误信息)
    """
    from bot.config.products import CHINESE_ZODIAC
    
    zodiac_lower = zodiac.lower()
    valid_zodiacs = [z[0].lower() for z in CHINESE_ZODIAC] + [z[1] for z in CHINESE_ZODIAC]
    
    if zodiac_lower not in [z.lower() for z in valid_zodiacs]:
        return False, f"无效的生肖，请从以下选择：{', '.join([z[1] for z in CHINESE_ZODIAC])}"
    
    return True, None


def validate_gender(gender: str) -> Tuple[bool, Optional[str]]:
    """
    验证性别
    
    Args:
        gender: 性别字符串（可能是按钮文本，如 "👨 男 / Male" 或 "👩 女 / Female"）
    
    Returns:
        (是否有效, 错误信息)
    """
    gender_lower = gender.lower().strip()
    
    # 处理按钮文本格式（包含 emoji 和斜杠）
    # 例如："👨 男 / Male" -> 提取 "男" 或 "male"
    if "男" in gender or "male" in gender_lower or "👨" in gender:
        return True, None
    elif "女" in gender or "female" in gender_lower or "👩" in gender:
        return True, None
    
    # 处理简单格式
    valid_genders = ["male", "female", "男", "女", "m", "f", "1", "2"]
    
    if gender_lower in valid_genders:
        return True, None
    
    return False, "无效的性别，请输入：男/女 或 male/female"


def normalize_gender(gender: str) -> int:
    """
    标准化性别为数字（1=男, 2=女）
    
    Args:
        gender: 性别字符串（可能是按钮文本，如 "👨 男 / Male" 或 "👩 女 / Female"）
    
    Returns:
        性别数字（1或2）
    """
    gender_lower = gender.lower().strip()
    
    # 处理按钮文本格式（包含 emoji 和斜杠）
    # 例如："👨 男 / Male" -> 提取 "男" 或 "male"
    if "男" in gender or ("male" in gender_lower and "female" not in gender_lower) or "👨" in gender:
        return 1
    elif "女" in gender or "female" in gender_lower or "👩" in gender:
        return 2
    
    # 处理简单格式
    if gender_lower in ["male", "m", "男", "1"]:
        return 1
    else:
        return 2

