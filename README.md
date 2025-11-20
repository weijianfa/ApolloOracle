# 阿波罗神谕 Telegram Bot
# Apollo Oracle Telegram Bot

一个全自动化的Telegram占卜机器人，用户可选择不同占卜产品并完成支付，系统自动调用AI生成个性化报告并发送给用户。

## 目标市场

- **主要用户**：占卜爱好者、对神秘学感兴趣的用户
- **地理范围**：海外用户（非中国大陆），包括：
  - 欧美地区英语用户
  - 东南亚地区用户
  - 海外华人（港澳台、海外华人社区等）
- **市场定位**：面向海外市场的占卜服务，提供中英文双语支持

## 功能特性

- 🔮 6种占卜产品（塔罗、星座、姓名解析、生肖配对、生辰八字、年度预测）
- 💳 集成PingPong支付网关，支持多币种支付
- 🤖 AI自动生成个性化报告（DeepSeek API）
- 🌍 多语言支持（中英文）
- 📊 推广员系统，支持佣金计算
- 🔒 完善的异常处理和监控机制

## 技术栈

- **后端框架**: Python 3.9+, python-telegram-bot v20.7+
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **缓存**: Redis
- **支付**: PingPong Payment Gateway
- **AI服务**: DeepSeek API
- **占卜数据**: 缘分居API

## 快速开始

### 1. 环境要求

- Python 3.9 或更高版本
- Redis (可选，开发环境可不用)

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入必要的配置
# 至少需要配置 TELEGRAM_BOT_TOKEN
```

### 4. 运行Bot

```bash
python main.py
```

## 项目结构

```
telegram-bot/
├── bot/                    # Bot核心代码
│   ├── handlers/          # 消息处理器
│   ├── services/          # 业务服务层
│   ├── models/            # 数据模型
│   ├── database/          # 数据库操作
│   ├── utils/             # 工具函数
│   └── config/            # 配置管理
├── webhooks/              # Webhook处理
├── prompts/               # AI提示词模板
├── locales/               # 多语言文件
├── tests/                 # 测试文件
├── .env.example           # 环境变量示例
├── requirements.txt       # Python依赖
├── README.md
└── main.py                # 入口文件
```

## 开发文档

详细的开发文档请参考：
- [开发计划文档](DEV/开发计划文档.md)
- [本地开发环境搭建文档](DEV/本地开发环境搭建文档.md)

## 许可证

本项目为私有项目，未经授权不得使用。

## 联系方式

如有问题，请联系开发团队。

