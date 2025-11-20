"""
产品配置测试
"""
import pytest
from bot.config.products import get_product, get_all_products, PRODUCTS


def test_get_all_products():
    """测试获取所有产品"""
    products = get_all_products()
    assert len(products) == 6
    assert all(p.id in PRODUCTS for p in products)


def test_get_product():
    """测试获取单个产品"""
    # 有效产品ID
    product = get_product(1)
    assert product is not None
    assert product.id == 1
    assert product.name_zh == "每日塔罗"
    assert product.price_usd == 1.00
    
    # 无效产品ID
    product = get_product(999)
    assert product is None


def test_product_fields():
    """测试产品字段"""
    product = get_product(1)
    assert hasattr(product, 'id')
    assert hasattr(product, 'name_zh')
    assert hasattr(product, 'name_en')
    assert hasattr(product, 'price_usd')
    assert hasattr(product, 'input_fields')
    assert hasattr(product, 'requires_bazi')


def test_product_input_fields():
    """测试产品输入字段"""
    # 产品1（每日塔罗）不需要输入
    product = get_product(1)
    assert len(product.input_fields) == 0
    
    # 产品2（每周星座）需要星座
    product = get_product(2)
    assert "zodiac" in product.input_fields
    
    # 产品5（生辰八字）需要八字数据
    product = get_product(5)
    assert product.requires_bazi is True
    assert "birthday" in product.input_fields
    assert "birth_time" in product.input_fields

