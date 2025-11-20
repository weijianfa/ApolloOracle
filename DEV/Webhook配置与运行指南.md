# Webhook配置与运行指南

**文档版本**: v1.0  
**最后更新**: 2025-11-18

> 📖 **相关文档**: 
> - [支付流程与Webhook机制详解](./支付流程与Webhook机制详解.md) - 详细的支付流程和时序图
> - [本地开发环境搭建文档](./本地开发环境搭建文档.md) - 环境配置指南

---

## 一、概述

本指南说明如何配置和运行Webhook服务器，以接收PingPong支付系统的回调通知。

### 1.1 Webhook架构

项目中有两种Webhook：

1. **Telegram Bot Webhook** - 用于接收Telegram消息（生产环境）
2. **PingPong Payment Webhook** - 用于接收支付回调通知（开发和生产环境都需要）

### 1.2 Webhook端点

- **PingPong Webhook路径**: `/webhook/pingpong`
- **健康检查路径**: `/health`

---

## 二、开发环境配置

### 2.1 使用本地隧道工具（推荐）

由于PingPong需要HTTPS回调URL，而本地开发环境通常没有SSL证书，可以使用以下工具：

#### 选项1：使用 ngrok（推荐）

1. **安装ngrok**
   ```bash
   # Windows: 下载 https://ngrok.com/download
   # macOS: brew install ngrok
   # Linux: 下载并解压
   ```

2. **启动ngrok隧道**
   ```bash
   # 假设webhook服务器运行在8000端口
   ngrok http 8000
   ```

3. **获取HTTPS URL**
   ```
   Forwarding: https://xxxx-xx-xx-xx-xx.ngrok-free.app -> http://localhost:8000
   ```

4. **配置PingPong Webhook URL**
   ```
   https://xxxx-xx-xx-xx-xx.ngrok-free.app/webhook/pingpong
   ```

#### 选项2：使用 Cloudflare Tunnel

1. **安装cloudflared**
   ```bash
   # 下载: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
   ```

2. **启动隧道**
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

3. **使用生成的HTTPS URL配置PingPong**

#### 选项3：使用 localtunnel

```bash
npm install -g localtunnel
lt --port 8000
```

---

### 2.2 运行Webhook服务器

#### 方法1：独立运行（推荐用于开发测试）

**推荐方式**：使用启动脚本（已处理路径问题）

```bash
python scripts/start_webhook_server.py
```

**或者**：直接运行（已修复路径问题，现在可以从任何目录运行）

```bash
python webhooks/server.py
```

**或者**：使用uvicorn直接运行（需要从项目根目录运行）

```bash
# 从项目根目录运行
uvicorn webhooks.server:app --host 0.0.0.0 --port 8000
```

#### 方法2：与Bot同时运行（需要修改代码）

修改`main.py`，在开发环境同时启动webhook服务器。

---

## 三、生产环境配置

### 3.1 服务器要求

- **HTTPS**: 必须使用HTTPS（PingPong要求）
- **SSL证书**: 有效的SSL证书（Let's Encrypt免费证书可用）
- **域名**: 固定的域名（不能使用IP地址）
- **端口**: 建议使用443（HTTPS默认端口）或8443

### 3.2 环境变量配置

在`.env`文件中配置：

```bash
# Webhook服务器配置
WEBHOOK_LISTEN=0.0.0.0
WEBHOOK_PORT=8443

# SSL证书路径（生产环境必须）
SSL_CERT_PATH=/path/to/ssl/cert.pem
SSL_KEY_PATH=/path/to/ssl/key.pem

# PingPong Webhook配置
PINGPONG_WEBHOOK_SECRET=your_webhook_secret_from_pingpong
```

### 3.3 获取SSL证书

#### 使用Let's Encrypt（免费）

```bash
# 安装certbot
sudo apt-get install certbot

# 获取证书
sudo certbot certonly --standalone -d yourdomain.com

# 证书位置
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

### 3.4 运行Webhook服务器

```bash
# 使用systemd服务（推荐）
sudo systemctl start telegram-bot-webhook

# 或直接运行
python webhooks/server.py
```

---

## 四、PingPong Webhook配置

### 4.1 登录PingPong商户后台

1. 访问 [PingPong商户后台](https://merchant.pingpongx.com)
2. 登录您的账户

### 4.2 配置Webhook URL

1. **进入设置页面**
   - 导航到 "设置" -> "Webhook设置" 或 "API设置"

2. **填写Webhook URL**
   ```
   开发环境（使用ngrok）:
   https://xxxx-xx-xx-xx-xx.ngrok-free.app/webhook/pingpong
   
   生产环境:
   https://yourdomain.com/webhook/pingpong
   ```

3. **配置Webhook Secret**
   - 在PingPong后台生成Webhook Secret
   - 复制Secret到`.env`文件：
     ```bash
     PINGPONG_WEBHOOK_SECRET=your_webhook_secret_here
     ```

4. **选择通知事件**
   - ✅ 支付成功 (paid)
   - ✅ 支付失败 (failed)
   - ✅ 退款成功 (refunded)

5. **保存配置**

---

## 五、验证Webhook配置

### 5.1 测试健康检查端点

```bash
curl https://yourdomain.com/health
```

应该返回：
```json
{
  "status": "ok",
  "service": "telegram-bot-webhook"
}
```

### 5.2 测试PingPong Webhook

1. **在PingPong后台发送测试通知**
   - 进入Webhook设置页面
   - 点击"发送测试通知"

2. **检查日志**
   ```bash
   # 查看webhook服务器日志
   tail -f logs/webhook.log
   ```

3. **验证订单状态**
   - 检查数据库中订单状态是否更新
   - 检查用户是否收到通知

---

## 六、常见问题

### 6.1 Webhook未收到通知

**可能原因**：
- URL配置错误
- 服务器未运行
- 防火墙阻止
- SSL证书问题

**解决方法**：
1. 检查URL是否正确（包含`/webhook/pingpong`路径）
2. 确认服务器正在运行
3. 检查防火墙规则
4. 验证SSL证书有效性

### 6.2 签名验证失败

**可能原因**：
- `PINGPONG_WEBHOOK_SECRET`配置错误
- 请求被中间件修改

**解决方法**：
1. 确认`.env`中的`PINGPONG_WEBHOOK_SECRET`与PingPong后台一致
2. 检查是否有反向代理修改了请求头

### 6.3 开发环境无法接收Webhook

**解决方法**：
- 使用ngrok等隧道工具
- 确保隧道URL配置到PingPong后台
- 注意ngrok免费版URL会变化，需要重新配置

---

## 七、安全建议

### 7.1 IP白名单（可选）

如果PingPong支持IP白名单，建议配置：
- 获取PingPong的Webhook服务器IP列表
- 在服务器防火墙中只允许这些IP访问

### 7.2 签名验证

✅ **已实现**：代码中已包含签名验证逻辑

### 7.3 HTTPS强制

✅ **已实现**：生产环境必须使用HTTPS

---

## 八、监控和日志

### 8.1 日志位置

- Webhook服务器日志：`logs/webhook.log`
- 应用日志：`logs/bot.log`

### 8.2 监控指标

- Webhook接收次数
- 签名验证失败次数
- 订单处理成功率
- API响应时间

---

## 九、快速开始

### 开发环境

1. **启动ngrok**
   ```bash
   ngrok http 8000
   ```

2. **配置环境变量**
   ```bash
   PINGPONG_WEBHOOK_SECRET=your_secret
   ```

3. **运行Webhook服务器**
   ```bash
   python webhooks/server.py
   ```

4. **配置PingPong**
   - URL: `https://xxxx.ngrok-free.app/webhook/pingpong`
   - Secret: 与`.env`中一致

### 生产环境

1. **配置SSL证书**
2. **设置环境变量**
3. **运行Webhook服务器**
4. **配置PingPong Webhook URL**

---

**需要帮助？** 查看日志文件或联系技术支持。

