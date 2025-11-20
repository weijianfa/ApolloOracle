"""
Bot功能测试脚本（不依赖实际Telegram连接）
"""
import sys
import os
import io
import asyncio
from pathlib import Path

# 设置UTF-8编码（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

# 检查依赖
try:
    from bot.config.settings import settings
    from bot.utils.logger import setup_logger
    from bot.database.db import init_db, get_db_session
    from bot.models import User, Order
    from bot.config.products import get_all_products, get_product
    from bot.utils.validators import validate_date, validate_time, validate_name
    from bot.utils.message_splitter import split_message
except ImportError as e:
    print(f"\n❌ 导入错误: {e}")
    print("\n请先安装依赖:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

logger = setup_logger("test")


def test_database_initialization():
    """测试数据库初始化"""
    print("\n" + "="*50)
    print("测试1: 数据库初始化")
    print("="*50)
    
    try:
        init_db()
        print("✅ 数据库初始化成功")
        return True
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False


def test_product_configuration():
    """测试产品配置"""
    print("\n" + "="*50)
    print("测试2: 产品配置")
    print("="*50)
    
    try:
        products = get_all_products()
        print(f"✅ 成功加载 {len(products)} 个产品")
        
        for product in products:
            print(f"  - {product.name_zh} ({product.name_en}): ${product.price_usd}")
        
        # 测试获取单个产品
        product = get_product(1)
        assert product is not None, "产品1应该存在"
        print(f"✅ 成功获取产品: {product.name_zh}")
        
        return True
    except Exception as e:
        print(f"❌ 产品配置测试失败: {e}")
        return False


def test_input_validation():
    """测试输入验证"""
    print("\n" + "="*50)
    print("测试3: 输入验证")
    print("="*50)
    
    try:
        # 测试日期验证
        is_valid, error = validate_date("1990-01-01")
        assert is_valid, f"有效日期验证失败: {error}"
        print("✅ 日期验证通过")
        
        # 测试时间验证
        is_valid, error = validate_time("14:30")
        assert is_valid, f"有效时间验证失败: {error}"
        print("✅ 时间验证通过")
        
        # 测试姓名验证
        is_valid, error = validate_name("张三")
        assert is_valid, f"有效姓名验证失败: {error}"
        print("✅ 姓名验证通过")
        
        return True
    except Exception as e:
        print(f"❌ 输入验证测试失败: {e}")
        return False


def test_message_splitting():
    """测试消息分段"""
    print("\n" + "="*50)
    print("测试4: 消息分段")
    print("="*50)
    
    try:
        # 短消息
        short_text = "这是一条短消息"
        segments = split_message(short_text)
        assert len(segments) == 1, "短消息不应该分段"
        print("✅ 短消息处理正确")
        
        # 长消息（创建超过4000字符的文本）
        long_text = "这是一个很长的段落内容。\n\n" * 300  # 创建超过4000字符的长文本
        assert len(long_text) > 4000, "测试文本应该超过4000字符"
        segments = split_message(long_text)
        assert len(segments) > 1, f"长消息应该分段，当前分为 {len(segments)} 段"
        print(f"✅ 长消息分段成功，分为 {len(segments)} 段")
        
        # 检查每段长度
        for i, segment in enumerate(segments, 1):
            assert len(segment) <= 4000, f"第{i}段超过4000字符"
        print("✅ 所有分段长度符合要求")
        
        return True
    except Exception as e:
        print(f"❌ 消息分段测试失败: {e}")
        return False


def test_database_operations():
    """测试数据库操作"""
    print("\n" + "="*50)
    print("测试5: 数据库操作")
    print("="*50)
    
    try:
        with get_db_session() as db:
            # 测试创建用户
            test_user = User(
                telegram_id=999999999,
                username="test_user",
                first_name="Test",
                language_code="zh"
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            
            assert test_user.id is not None, "用户ID应该被分配"
            print(f"✅ 成功创建测试用户 (ID: {test_user.id})")
            
            # 测试创建订单
            test_order = Order(
                order_id="TEST_ORDER_001",
                user_id=test_user.id,
                product_id=1,
                product_name="测试产品",
                status="pending_payment",
                amount_usd=1.00
            )
            db.add(test_order)
            db.commit()
            db.refresh(test_order)
            
            assert test_order.id is not None, "订单ID应该被分配"
            print(f"✅ 成功创建测试订单 (ID: {test_order.order_id})")
            
            # 清理测试数据
            db.delete(test_order)
            db.delete(test_user)
            db.commit()
            print("✅ 测试数据清理完成")
        
        return True
    except Exception as e:
        print(f"❌ 数据库操作测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_configuration():
    """测试配置"""
    print("\n" + "="*50)
    print("测试6: 配置验证")
    print("="*50)
    
    try:
        # 测试环境检测
        is_dev = settings.is_development()
        is_prod = settings.is_production()
        print(f"✅ 环境检测: development={is_dev}, production={is_prod}")
        
        # 测试配置验证（如果缺少必要配置会抛出异常）
        try:
            settings.validate()
            print("✅ 配置验证通过")
        except ValueError as e:
            print(f"⚠️ 配置验证警告: {e}")
            print("   这是正常的，如果.env文件未配置")
        
        return True
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("阿波罗神谕 Bot - 第一阶段功能测试")
    print("="*60)
    
    results = []
    
    # 运行测试
    results.append(("数据库初始化", test_database_initialization()))
    results.append(("产品配置", test_product_configuration()))
    results.append(("输入验证", test_input_validation()))
    results.append(("消息分段", test_message_splitting()))
    results.append(("数据库操作", test_database_operations()))
    results.append(("配置验证", test_configuration()))
    
    # 输出测试结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！第一阶段开发完成。")
        return 0
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    exit(main())

