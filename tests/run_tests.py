"""
运行测试脚本
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

if __name__ == "__main__":
    # 运行所有测试
    pytest.main([
        __file__.replace("run_tests.py", ""),
        "-v",  # 详细输出
        "--tb=short",  # 简短的错误追踪
        "-x",  # 遇到第一个失败就停止
    ])

