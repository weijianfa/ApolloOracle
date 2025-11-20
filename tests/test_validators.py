"""
输入验证测试
"""
import pytest
from bot.utils.validators import (
    validate_date, validate_time, validate_name,
    validate_zodiac, validate_chinese_zodiac, validate_gender, normalize_gender
)


def test_validate_date():
    """测试日期验证"""
    # 有效日期
    is_valid, error = validate_date("1990-01-01")
    assert is_valid is True
    assert error is None
    
    # 无效格式
    is_valid, error = validate_date("1990/01/01")
    assert is_valid is False
    assert error is not None
    
    # 未来日期
    is_valid, error = validate_date("2099-01-01")
    assert is_valid is False
    assert "未来" in error or "future" in error.lower()


def test_validate_time():
    """测试时间验证"""
    # 有效时间
    is_valid, error = validate_time("14:30")
    assert is_valid is True
    assert error is None
    
    # 无效格式
    is_valid, error = validate_time("14.30")
    assert is_valid is False
    assert error is not None


def test_validate_name():
    """测试姓名验证"""
    # 有效姓名
    is_valid, error = validate_name("张三")
    assert is_valid is True
    assert error is None
    
    is_valid, error = validate_name("John Smith")
    assert is_valid is True
    assert error is None
    
    # 太短
    is_valid, error = validate_name("A")
    assert is_valid is False
    
    # 太长
    is_valid, error = validate_name("A" * 100)
    assert is_valid is False


def test_validate_gender():
    """测试性别验证"""
    # 有效性别
    for gender in ["male", "female", "男", "女", "m", "f", "1", "2"]:
        is_valid, error = validate_gender(gender)
        assert is_valid is True, f"Gender {gender} should be valid"
    
    # 无效性别
    is_valid, error = validate_gender("unknown")
    assert is_valid is False


def test_normalize_gender():
    """测试性别标准化"""
    assert normalize_gender("male") == 1
    assert normalize_gender("m") == 1
    assert normalize_gender("男") == 1
    assert normalize_gender("1") == 1
    
    assert normalize_gender("female") == 2
    assert normalize_gender("f") == 2
    assert normalize_gender("女") == 2
    assert normalize_gender("2") == 2

