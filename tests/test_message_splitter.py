"""
长消息分段测试
"""
import pytest
from bot.utils.message_splitter import split_message, format_markdown


def test_split_short_message():
    """测试短消息（不需要分段）"""
    text = "这是一条短消息"
    segments = split_message(text)
    assert len(segments) == 1
    assert segments[0] == text


def test_split_long_message():
    """测试长消息（需要分段）"""
    # 创建一条超过4000字符的消息
    long_text = "段落1\n\n" * 500  # 大约5000字符
    segments = split_message(long_text)
    
    assert len(segments) > 1
    # 检查每段长度
    for segment in segments:
        assert len(segment) <= 4000


def test_split_preserves_formatting():
    """测试分段保持格式"""
    text = "标题\n\n段落1\n\n段落2\n\n段落3"
    segments = split_message(text, max_length=20)
    
    # 应该按段落分割
    assert len(segments) > 1


def test_format_markdown():
    """测试Markdown格式化"""
    text = "# 标题\n\n这是**粗体**文本"
    formatted = format_markdown(text)
    assert "粗体" in formatted
    assert "*" not in formatted

