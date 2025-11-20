# Python版本兼容性说明

## 问题描述

在使用 Python 3.14 运行项目时，可能会遇到 SQLAlchemy 兼容性问题：

```
AssertionError: Class <class 'sqlalchemy.sql.elements.SQLCoreOperations'> directly inherits TypingOnly but has additional attributes
```

## 原因分析

SQLAlchemy 2.0.23 版本与 Python 3.14（非常新的版本）存在兼容性问题。Python 3.14 对类型系统的实现有所改变，导致旧版本的 SQLAlchemy 无法正常工作。

## 解决方案

### 方案1：更新 SQLAlchemy（推荐）

更新 `requirements.txt` 中的 SQLAlchemy 版本：

```txt
sqlalchemy>=2.0.25
```

然后重新安装：

```bash
pip install --upgrade sqlalchemy
```

### 方案2：使用 Python 3.11 或 3.12（更稳定）

Python 3.11 和 3.12 是更成熟稳定的版本，与所有依赖包兼容性更好。

**推荐使用 Python 3.11 或 3.12**，因为：
- 所有依赖包都经过充分测试
- 性能优化更好
- 兼容性更稳定

### 方案3：使用虚拟环境

如果必须使用 Python 3.14，建议：

1. 创建新的虚拟环境：
   ```bash
   python -m venv venv
   ```

2. 激活虚拟环境：
   ```bash
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

## 当前项目推荐的 Python 版本

- **推荐**: Python 3.11 或 3.12
- **最低要求**: Python 3.9
- **不推荐**: Python 3.14（太新，可能存在兼容性问题）

## 检查 Python 版本

```bash
python --version
```

## 如果遇到其他兼容性问题

1. 检查所有依赖包的最新版本
2. 查看依赖包的官方文档
3. 考虑使用 Python 3.11 或 3.12

---

**文档版本**: v1.0  
**创建日期**: 2024-11-15

