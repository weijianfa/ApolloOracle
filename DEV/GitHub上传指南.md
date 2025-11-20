# GitHub上传指南

**目标仓库**: https://github.com/weijianfa/ApolloOracle

本文档说明如何将"阿波罗神谕"Telegram Bot项目代码上传到GitHub仓库。

---

## 一、准备工作

### 1.1 检查Git是否已安装

```bash
git --version
```

如果未安装，请先安装Git：
- Windows: 下载 https://git-scm.com/download/win
- macOS: `brew install git`
- Linux: `sudo apt-get install git` 或 `sudo yum install git`

### 1.2 配置Git用户信息（如果未配置）

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

---

## 二、初始化Git仓库（如果尚未初始化）

### 2.1 检查是否已有Git仓库

```bash
# 在项目根目录执行
git status
```

如果显示 "not a git repository"，需要初始化：

### 2.2 初始化Git仓库

```bash
# 在项目根目录执行
git init
```

---

## 三、配置远程仓库

### 3.1 添加远程仓库

```bash
git remote add origin https://github.com/weijianfa/ApolloOracle.git
```

### 3.2 验证远程仓库配置

```bash
git remote -v
```

应该显示：
```
origin  https://github.com/weijianfa/ApolloOracle.git (fetch)
origin  https://github.com/weijianfa/ApolloOracle.git (push)
```

---

## 四、添加文件到Git

### 4.1 查看当前状态

```bash
git status
```

### 4.2 添加所有文件（.gitignore中排除的文件不会被添加）

```bash
git add .
```

### 4.3 查看将要提交的文件

```bash
git status
```

**注意**: 确保以下文件**不会**被提交：
- `.env` - 环境变量文件（包含敏感信息）
- `*.db` - 数据库文件
- `__pycache__/` - Python缓存文件
- `DEV/` - 开发文档（已在.gitignore中排除）
- `PRD/` - 产品需求文档（已在.gitignore中排除）

---

## 五、提交代码

### 5.1 创建首次提交

```bash
git commit -m "Initial commit: Apollo Oracle Telegram Bot

- Complete Telegram bot with 6 divination products
- PingPong payment integration
- AI report generation with DeepSeek API
- Bazi data integration with Yuanfenju API
- Multi-language support (Chinese/English)
- Affiliate system
- Webhook server for payment callbacks"
```

### 5.2 查看提交历史

```bash
git log --oneline
```

---

## 六、推送到GitHub

### 6.1 拉取远程仓库内容（如果远程有LICENSE文件）

```bash
git pull origin main --allow-unrelated-histories
```

如果出现冲突，需要解决冲突后再继续。

### 6.2 推送到远程仓库

```bash
# 首次推送，设置上游分支
git push -u origin main
```

**注意**: 如果远程仓库默认分支是 `master` 而不是 `main`，使用：
```bash
git push -u origin main:master
```

或者先重命名本地分支：
```bash
git branch -M master
git push -u origin master
```

### 6.3 如果推送失败（需要认证）

如果提示需要认证，可以使用以下方式：

**方式1：使用Personal Access Token（推荐）**

1. 在GitHub上生成Personal Access Token：
   - 访问：https://github.com/settings/tokens
   - 点击 "Generate new token (classic)"
   - 选择权限：至少需要 `repo` 权限
   - 复制生成的token

2. 推送时使用token作为密码：
   ```bash
   # 用户名：你的GitHub用户名
   # 密码：使用Personal Access Token（不是GitHub密码）
   git push -u origin main
   ```

**方式2：使用SSH密钥**

1. 生成SSH密钥（如果还没有）：
   ```bash
   ssh-keygen -t ed25519 -C "your.email@example.com"
   ```

2. 将公钥添加到GitHub：
   - 复制 `~/.ssh/id_ed25519.pub` 的内容
   - 访问：https://github.com/settings/keys
   - 点击 "New SSH key"，粘贴公钥

3. 修改远程仓库URL为SSH：
   ```bash
   git remote set-url origin git@github.com:weijianfa/ApolloOracle.git
   ```

4. 推送：
   ```bash
   git push -u origin main
   ```

---

## 七、验证上传结果

### 7.1 在浏览器中访问

访问 https://github.com/weijianfa/ApolloOracle

应该能看到所有项目文件。

### 7.2 检查文件列表

确保以下重要文件已上传：
- ✅ `README.md`
- ✅ `main.py`
- ✅ `requirements.txt`
- ✅ `bot/` 目录
- ✅ `webhooks/` 目录
- ✅ `prompts/` 目录
- ✅ `locales/` 目录
- ✅ `.gitignore`

确保以下文件**未**上传：
- ❌ `.env`
- ❌ `*.db`
- ❌ `__pycache__/`
- ❌ `DEV/`
- ❌ `PRD/`

---

## 八、后续更新代码

### 8.1 日常更新流程

```bash
# 1. 查看更改
git status

# 2. 添加更改的文件
git add .

# 3. 提交更改
git commit -m "描述你的更改"

# 4. 推送到GitHub
git push
```

### 8.2 查看提交历史

```bash
git log --oneline --graph
```

---

## 九、常见问题

### 9.1 推送被拒绝（Push rejected）

**原因**: 远程仓库有本地没有的提交（如LICENSE文件）

**解决方案**:
```bash
# 拉取远程更改并合并
git pull origin main --allow-unrelated-histories

# 解决可能的冲突后，再次推送
git push -u origin main
```

### 9.2 认证失败

**原因**: GitHub不再支持密码认证

**解决方案**: 使用Personal Access Token或SSH密钥（见第六节）

### 9.3 分支名称不匹配

**原因**: 本地分支是 `main`，远程默认分支是 `master`（或反之）

**解决方案**:
```bash
# 重命名本地分支
git branch -M master

# 或推送到指定分支
git push -u origin main:master
```

### 9.4 忘记添加.gitignore

**解决方案**:
```bash
# 如果已经提交了不应该提交的文件，需要从Git历史中移除
git rm --cached .env
git rm --cached *.db
git commit -m "Remove sensitive files from Git"
git push
```

---

## 十、完整命令序列（快速参考）

```bash
# 1. 初始化Git仓库（如果尚未初始化）
git init

# 2. 添加远程仓库
git remote add origin https://github.com/weijianfa/ApolloOracle.git

# 3. 添加所有文件
git add .

# 4. 提交
git commit -m "Initial commit: Apollo Oracle Telegram Bot"

# 5. 拉取远程内容（如果有）
git pull origin main --allow-unrelated-histories

# 6. 推送到GitHub
git push -u origin main
```

---

## 十一、安全注意事项

### 11.1 确保不提交敏感信息

在推送前，检查以下文件是否在.gitignore中：
- ✅ `.env` - 环境变量（包含API密钥）
- ✅ `*.db` - 数据库文件（可能包含用户数据）
- ✅ `*.pem`, `*.key`, `*.crt` - SSL证书

### 11.2 如果已经提交了敏感信息

**立即处理**:
1. 从Git历史中移除敏感文件
2. 更改所有已泄露的密钥和密码
3. 使用 `git filter-branch` 或 `git filter-repo` 清理历史

---

## 十二、项目结构说明

上传到GitHub的项目应包含：

```
ApolloOracle/
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
├── scripts/               # 工具脚本
├── .gitignore             # Git忽略文件
├── .env.example           # 环境变量示例
├── requirements.txt       # Python依赖
├── README.md              # 项目说明
└── main.py                # 入口文件
```

---

**提示**: 如果遇到问题，可以查看GitHub的官方文档：https://docs.github.com/en/get-started/getting-started-with-git

