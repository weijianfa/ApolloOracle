"""
环境检查脚本
检查开发环境是否配置正确
"""
import sys
import os
import io

# 设置UTF-8编码（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

def check_python_version():
    """检查Python版本"""
    print("检查Python版本...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python版本过低: {version.major}.{version.minor}.{version.micro} (需要3.9+)")
        return False


def check_dependencies():
    """检查依赖包"""
    print("\n检查依赖包...")
    required_packages = [
        "telegram",
        "dotenv",
        "sqlalchemy",
        "aiohttp",
        "jinja2",
    ]
    
    missing = []
    for package in required_packages:
        try:
            if package == "telegram":
                __import__("telegram")
            elif package == "dotenv":
                __import__("dotenv")
            elif package == "sqlalchemy":
                __import__("sqlalchemy")
            elif package == "aiohttp":
                __import__("aiohttp")
            elif package == "jinja2":
                __import__("jinja2")
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (未安装)")
            missing.append(package)
    
    if missing:
        print(f"\n缺少以下依赖包: {', '.join(missing)}")
        print("请运行: pip install -r requirements.txt")
        return False
    return True


def check_env_file():
    """检查.env文件"""
    print("\n检查环境变量文件...")
    env_file = os.path.join(project_root, ".env")
    env_example = os.path.join(project_root, ".env.example")
    
    if os.path.exists(env_file):
        print("  ✅ .env 文件存在")
        return True
    else:
        print("  ⚠️ .env 文件不存在")
        if os.path.exists(env_example):
            print(f"  💡 请复制 .env.example 为 .env 并配置")
            print(f"     命令: copy .env.example .env")
        return False


def check_project_structure():
    """检查项目结构"""
    print("\n检查项目结构...")
    required_dirs = [
        "bot",
        "bot/handlers",
        "bot/services",
        "bot/models",
        "bot/database",
        "bot/utils",
        "bot/config",
        "prompts",
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        full_path = os.path.join(project_root, dir_path)
        if os.path.exists(full_path):
            print(f"  ✅ {dir_path}/")
        else:
            print(f"  ❌ {dir_path}/ (缺失)")
            all_exist = False
    
    return all_exist


def main():
    """主函数"""
    print("="*60)
    print("阿波罗神谕 Bot - 环境检查")
    print("="*60)
    
    results = []
    results.append(("Python版本", check_python_version()))
    results.append(("依赖包", check_dependencies()))
    results.append(("环境变量文件", check_env_file()))
    results.append(("项目结构", check_project_structure()))
    
    print("\n" + "="*60)
    print("检查结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{check_name}: {status}")
    
    print(f"\n总计: {passed}/{total} 检查通过")
    
    if passed == total:
        print("\n🎉 环境检查通过！可以开始测试。")
        return 0
    else:
        print(f"\n⚠️ 有 {total - passed} 项检查未通过，请先解决这些问题。")
        return 1


if __name__ == "__main__":
    exit(main())

