# 支付流程与Webhook机制详解

**文档版本**: v1.0  
**最后更新**: 2025-11-18

---

## 一、概述

本文档详细说明用户支付后的完整流程，包括PingPong如何通知Bot，以及整个交易流程的各个环节。

### 1.1 核心流程

支付成功后的业务逻辑执行顺序：
1. ✅ **支付成功验证**（PingPong Webhook）
2. ✅ **调用缘分居API**（获取八字数据，如果需要）
3. ✅ **调用DeepSeek API**（生成AI报告）
4. ✅ **发送报告给用户**（Telegram Bot API）

---

## 二、完整支付流程

### 2.1 用户下单阶段

```
用户 → Bot → 创建订单 → 生成支付链接 → 用户跳转支付
```

**详细步骤**：

1. **用户选择产品**
   - 用户在Bot中选择产品（如"生辰八字"）
   - 输入必要信息（如出生日期、时间等）
   - 点击"确认订单"

2. **Bot创建订单**
   - `bot/handlers/payment.py` → `confirm_order_callback()`
   - 调用 `payment_service.create_order()`
   - 订单状态：`pending_payment`
   - 订单ID格式：`ORD_{timestamp}_{uuid}`

3. **生成支付链接**
   - 调用 `payment_service.create_payment_link()`
   - 如果是Mock模式：返回模拟支付链接
   - 如果是真实模式：调用PingPong API创建支付
   - 支付链接包含：
     - `order_id`: 订单ID
     - `amount`: 金额
     - `notify_url`: Webhook回调地址（`https://yourdomain.com/webhook/pingpong`）

4. **用户跳转支付**
   - Bot发送支付链接给用户
   - 用户点击链接，跳转到PingPong支付页面

---

### 2.2 用户支付阶段

```
用户 → PingPong支付页面 → 完成支付 → PingPong处理
```

**详细步骤**：

1. **用户在PingPong页面支付**
   - 选择支付方式
   - 输入支付信息
   - 确认支付

2. **PingPong处理支付**
   - 验证支付信息
   - 处理支付请求
   - 更新支付状态

---

### 2.3 PingPong Webhook通知阶段

```
PingPong → Webhook服务器（独立进程） → 验证签名 → 更新订单状态 → 触发业务逻辑
```

**重要说明**: 
- Webhook服务器（`webhooks/server.py`）是一个**独立的FastAPI进程**
- 与main.py（Telegram Bot主进程）是**不同的进程**
- 两个进程通过**共享数据库**和**共享业务逻辑代码**协作

**详细步骤**：

1. **PingPong发送Webhook通知**
   - PingPong在支付状态变更时，向配置的Webhook URL发送POST请求
   - Webhook URL：`https://yourdomain.com/webhook/pingpong`
   - **注意**: 这个URL指向**Webhook服务器进程**，不是main.py进程
   - 请求头包含：
     - `X-Signature`: HMAC签名（用于验证请求真实性）
   - 请求体包含：
     ```json
     {
       "order_id": "ORD_1234567890_ABCD1234",
       "status": "paid",
       "payment_id": "PP_xxxxx",
       "amount": 29.99,
       "currency": "USD",
       "payment_method": "credit_card",
       "timestamp": 1234567890
     }
     ```

2. **Webhook服务器接收请求（独立进程）**
   - **进程**: `webhooks/server.py`（FastAPI服务器，独立进程）
   - **路由**: `webhooks/pingpong.py` → `pingpong_webhook()`
   - FastAPI路由：`POST /webhook/pingpong`
   - 提取请求体和签名

3. **验证签名**
   - 调用 `payment_service.process_payment_webhook()`
   - 使用 `PINGPONG_WEBHOOK_SECRET` 验证HMAC签名
   - 确保请求来自PingPong，防止伪造

4. **更新订单状态（共享数据库）**
   - 查询订单：`Order.order_id == payload.order_id`
   - **注意**: 通过共享数据库访问订单数据
   - 更新订单状态：
     - 如果 `status == "paid"`：订单状态 → `paid`
     - 如果 `status == "failed"`：订单状态 → `failed`
   - 保存支付信息：`payment_id`, `payment_method`

5. **通知用户支付成功（直接调用Telegram Bot API）**
   - 如果支付成功（`status == "paid"`）
   - 调用 `notify_user_payment_success(order_id)`
   - **重要**: Webhook服务器**直接调用Telegram Bot API**发送消息
   - **不需要通过main.py进程**
   - 立即发送消息给用户：
     - ✅ 支付成功确认
     - 📋 订单信息（订单号、产品、金额）
     - 🔄 正在生成报告，请稍候...

6. **触发订单处理流程（Webhook服务器进程内）**
   - 调用 `trigger_order_processing(order_id)`
   - **注意**: 所有后续处理都在Webhook服务器进程内执行
   - 异步执行后续业务逻辑

---

### 2.4 订单处理阶段（业务逻辑）

```
订单处理 → 调用缘分居API → 调用DeepSeek API → 发送报告 → 完成
```

**详细步骤**：

#### [步骤1] 支付成功验证 ✅

- 位置：`webhooks/pingpong.py` → `trigger_order_processing()`
- 状态：已完成（Webhook已验证并更新订单状态）

#### [步骤2] 调用缘分居API（如果需要）🔮

- 位置：`bot/services/order_processor.py` → `process_paid_order()`
- 条件：产品需要八字数据（`product.requires_bazi == True`）
- 调用：`bazi_service.get_bazi_data()`
- 输入：
  - 用户输入的出生信息（年、月、日、时、性别）
- 输出：
  - 结构化八字数据（JSON格式）
  - 包含：四柱信息、五行、性格、运势等
- 保存：将八字数据保存到 `Order.bazi_data` 字段

**适用产品**：
- ✅ 生辰八字（Birth Bazi Chart）
- ✅ 流年运势（Annual Forecast）

**不适用产品**：
- ❌ 每日塔罗（Daily Tarot）
- ❌ 星座周运（Weekly Horoscope）
- ❌ 姓名解析（Name Interpretation）
- ❌ 生肖配对（Compatibility Test）

#### [步骤3] AI生成报告 🤖

- 位置：`bot/services/order_processor.py` → `process_paid_order()`
- 调用：`ai_service.generate_report()`
- 输入：
  - 用户输入（`user_input`）
  - 八字数据（`bazi_data`，如果产品需要）
  - 产品类型（`product_id`）
  - 用户语言（`language`）
- 流程：
  1. 加载提示词模板（`prompts/{product}_{lang}.txt`）
  2. 构建完整提示词（使用Jinja2模板引擎）
  3. 调用DeepSeek API（带重试和超时机制）
  4. 解析AI响应
  5. 格式化报告（Markdown → 纯文本）
- 输出：
  - AI生成的个性化报告（纯文本格式）
- 保存：将报告保存到 `Order.ai_report` 字段

#### [步骤4] 发送报告给用户 📨

- 位置：`bot/services/order_processor.py` → `_send_report_to_user()`
- 调用：`context.bot.send_message()`
- 内容：
  1. 报告标题（包含订单ID）
  2. 报告内容（分段发送，每段≤4096字符）
  3. 完成提示（根据产品类型）
- 更新订单状态：`generating` → `completed`

#### [步骤5] 更新推广员统计（如果有关联）📊

- 位置：`bot/services/order_processor.py` → `process_paid_order()`
- 条件：订单有关联的推广员代码（`affiliate_code`）
- 调用：`affiliate_service.update_affiliate_sales()`
- 更新：
  - 推广员总销售额
  - 推广员总佣金
  - 推广员等级（根据销售额）

---

## 三、时序图

### 3.1 完整支付流程时序图

```
┌──────┐         ┌──────┐         ┌─────────┐         ┌──────────┐         ┌──────────┐
│ 用户 │         │ Bot  │         │PingPong │         │Webhook服务器│         │业务逻辑层│
└──┬───┘         └──┬───┘         └────┬────┘         └─────┬────┘         └────┬─────┘
   │                 │                  │                     │                    │
   │ 1.选择产品      │                  │                     │                    │
   │────────────────>│                  │                     │                    │
   │                 │                  │                     │                    │
   │ 2.输入信息      │                  │                     │                    │
   │────────────────>│                  │                     │                    │
   │                 │                  │                     │                    │
   │ 3.确认订单      │                  │                     │                    │
   │────────────────>│                  │                     │                    │
   │                 │                  │                     │                    │
   │                 │ 4.创建订单       │                     │                    │
   │                 │─────────────────>│                     │                    │
   │                 │                  │                     │                    │
   │                 │ 5.生成支付链接   │                     │                    │
   │                 │─────────────────>│                     │                    │
   │                 │                  │                     │                    │
   │                 │ 6.返回支付链接   │                     │                    │
   │                 │<─────────────────│                     │                    │
   │                 │                  │                     │                    │
   │ 7.发送支付链接  │                  │                     │                    │
   │<────────────────│                  │                     │                    │
   │                 │                  │                     │                    │
   │ 8.跳转支付页面  │                  │                     │                    │
   │────────────────────────────────────>│                     │                    │
   │                 │                  │                     │                    │
   │ 9.完成支付      │                  │                     │                    │
   │────────────────────────────────────>│                     │                    │
   │                 │                  │                     │                    │
   │                 │                  │ 10.发送Webhook通知  │                    │
   │                 │                  │─────────────────────>│                    │
   │                 │                  │                     │                    │
   │                 │                  │                     │ 11.验证签名        │
   │                 │                  │                     │───────────────────>│
   │                 │                  │                     │                    │
   │                 │                  │                     │ 12.更新订单状态    │
   │                 │                  │                     │───────────────────>│
   │                 │                  │                     │                    │
   │                 │                  │                     │ 13.触发订单处理    │
   │                 │                  │                     │───────────────────>│
   │                 │                  │                     │                    │
   │                 │                  │                     │ 14.调用缘分居API    │
   │                 │                  │                     │───────────────────>│
   │                 │                  │                     │                    │
   │                 │                  │                     │ 15.返回八字数据    │
   │                 │                  │                     │<───────────────────│
   │                 │                  │                     │                    │
   │                 │                  │                     │ 16.调用DeepSeek API│
   │                 │                  │                     │───────────────────>│
   │                 │                  │                     │                    │
   │                 │                  │                     │ 17.返回AI报告      │
   │                 │                  │                     │<───────────────────│
   │                 │                  │                     │                    │
   │                 │                  │                     │ 18.发送报告给用户  │
   │                 │                  │                     │───────────────────>│
   │                 │                  │                     │                    │
   │ 19.收到报告     │                  │                     │                    │
   │<───────────────────────────────────────────────────────────────────────────────│
   │                 │                  │                     │                    │
   │                 │                  │                     │ 20.更新订单完成    │
   │                 │                  │                     │───────────────────>│
   │                 │                  │                     │                    │
```

### 3.2 Webhook通知详细流程

```
┌─────────┐         ┌──────────┐         ┌──────────┐         ┌──────────┐
│PingPong │         │Webhook服务器│         │支付服务│         │订单处理│
└────┬────┘         └─────┬────┘         └────┬─────┘         └────┬─────┘
     │                     │                     │                    │
     │ POST /webhook/pingpong                   │                    │
     │ Headers: X-Signature                     │                    │
     │ Body: {order_id, status, ...}            │                    │
     │─────────────────────────────────────────>│                    │
     │                     │                     │                    │
     │                     │ 提取payload和签名   │                    │
     │                     │────────────────────>│                    │
     │                     │                     │                    │
     │                     │                     │ 验证HMAC签名        │
     │                     │                     │───────────────────>│
     │                     │                     │                    │
     │                     │                     │ 返回验证结果        │
     │                     │                     │<───────────────────│
     │                     │                     │                    │
     │                     │ 如果验证成功        │                    │
     │                     │─────────────────────┼───────────────────>│
     │                     │                     │                    │
     │                     │                     │                    │ 查询订单
     │                     │                     │                    │ 更新状态为paid
     │                     │                     │                    │ 保存支付信息
     │                     │                     │                    │
     │                     │                     │                    │ 调用process_paid_order
     │                     │                     │                    │─────────────────┐
     │                     │                     │                    │                 │
     │                     │                     │                    │                 │ [步骤2] 调用缘分居API
     │                     │                     │                    │                 │─────────────────┐
     │                     │                     │                    │                 │                 │
     │                     │                     │                    │                 │ [步骤3] 调用DeepSeek API
     │                     │                     │                    │                 │─────────────────┐
     │                     │                     │                    │                 │                 │
     │                     │                     │                    │                 │ [步骤4] 发送报告
     │                     │                     │                    │                 │─────────────────┐
     │                     │                     │                    │                 │                 │
     │                     │                     │                    │                 │ [步骤5] 更新状态为completed
     │                     │                     │                    │                 │<─────────────────┘
     │                     │                     │                    │                 │<─────────────────┘
     │                     │                     │                    │                 │<─────────────────┘
     │                     │                     │                    │                 │<─────────────────┘
     │                     │                     │                    │<─────────────────┘
     │                     │                     │                    │
     │ 返回200 OK         │                     │                    │
     │<─────────────────────────────────────────│                    │
     │                     │                     │                    │
```

---

## 五、关键代码位置

### 4.1 用户下单

- **文件**: `bot/handlers/payment.py`
- **函数**: `confirm_order_callback()`
- **功能**: 处理用户确认订单，创建订单，生成支付链接

### 4.2 订单创建

- **文件**: `bot/services/payment_service.py`
- **函数**: `create_order()`
- **功能**: 创建订单记录，状态为 `pending_payment`

### 4.3 支付链接生成

- **文件**: `bot/services/payment_service.py`
- **函数**: `create_payment_link()`
- **功能**: 调用PingPong API或生成Mock支付链接
- **关键参数**: `notify_url` = `https://yourdomain.com/webhook/pingpong`

### 4.4 Webhook接收

- **文件**: `webhooks/pingpong.py`
- **函数**: `pingpong_webhook()`
- **路由**: `POST /webhook/pingpong`
- **功能**: 接收PingPong的Webhook通知
- **进程**: **独立的Webhook服务器进程**（`webhooks/server.py`），不是main.py的一部分

### 4.5 签名验证和订单更新

- **文件**: `bot/services/payment_service.py`
- **函数**: `process_payment_webhook()`
- **功能**: 验证HMAC签名，更新订单状态

### 4.6 订单处理触发

- **文件**: `webhooks/pingpong.py`
- **函数**: `trigger_order_processing()`
- **功能**: 触发订单后续处理流程

### 4.7 订单处理（业务逻辑）

- **文件**: `bot/services/order_processor.py`
- **函数**: `process_paid_order()`
- **功能**: 协调整个订单处理流程
  - [步骤2] 调用缘分居API
  - [步骤3] 调用DeepSeek API
  - [步骤4] 发送报告给用户
- **进程**: **Webhook服务器进程**（`webhooks/server.py`）
- **注意**: 订单处理在Webhook服务器进程内执行，通过Telegram Bot API直接发送消息给用户

### 4.8 八字API调用

- **文件**: `bot/services/bazi_service.py`
- **函数**: `get_bazi_data()`
- **功能**: 调用缘分居API获取八字数据

### 4.9 AI报告生成

- **文件**: `bot/services/ai_service.py`
- **函数**: `generate_report()`
- **功能**: 调用DeepSeek API生成AI报告

### 4.10 报告发送

- **文件**: `bot/services/order_processor.py`
- **函数**: `_send_report_to_user()`
- **功能**: 将报告分段发送给用户
- **进程**: **Webhook服务器进程**（`webhooks/server.py`）
- **方式**: 直接调用Telegram Bot API，不通过main.py进程

---

## 六、订单状态流转

```
pending_payment  →  paid  →  generating  →  completed
     ↓                ↓          ↓            ↓
   创建订单        支付成功    生成中        已完成
   
   如果失败：
   pending_payment  →  failed
   paid  →  failed (退款)
   generating  →  failed (退款)
```

---

## 七、Webhook配置要求

### 6.1 PingPong后台配置

- **Webhook URL**: `https://yourdomain.com/webhook/pingpong`
- **Webhook Secret**: 与 `.env` 中的 `PINGPONG_WEBHOOK_SECRET` 一致
- **通知事件**: 
  - ✅ 支付成功 (`paid`)
  - ✅ 支付失败 (`failed`)
  - ✅ 支付取消 (`cancelled`)

### 6.2 服务器要求

- **HTTPS**: 必须使用HTTPS（PingPong要求）
- **SSL证书**: 有效的SSL证书
- **可访问性**: 服务器必须能从公网访问
- **端口**: 建议443或8443

### 6.3 开发环境

- 使用ngrok等隧道工具提供HTTPS
- 配置ngrok URL到PingPong后台
- 注意：ngrok免费版URL会变化，需要重新配置

---

## 八、错误处理

### 7.1 Webhook验证失败

- **原因**: 签名不匹配
- **处理**: 返回401错误，不处理订单
- **日志**: 记录警告日志

### 7.2 订单不存在

- **原因**: Webhook中的order_id在数据库中不存在
- **处理**: 返回400错误
- **日志**: 记录错误日志

### 7.3 业务逻辑失败

- **原因**: API调用失败、超时等
- **处理**: 
  - 更新订单状态为 `failed`
  - 如果是付费产品，自动退款
  - 通知用户失败原因
- **日志**: 记录详细错误日志

---

## 九、安全机制

### 8.1 HMAC签名验证

- **目的**: 确保Webhook请求来自PingPong
- **实现**: 使用 `PINGPONG_WEBHOOK_SECRET` 验证签名
- **位置**: `payment_service.process_payment_webhook()`

### 8.2 幂等性处理

- **目的**: 防止重复处理相同的Webhook
- **实现**: 检查订单状态，已处理的不再处理
- **位置**: `payment_service.process_payment_webhook()`

### 8.3 订单状态检查

- **目的**: 确保订单状态正确流转
- **实现**: 在处理前检查订单状态
- **位置**: `order_processor.process_paid_order()`

---

## 十、总结

### 9.1 关键点

1. **支付成功后才执行业务逻辑** ✅
   - 只有收到PingPong的 `paid` 状态Webhook后，才触发订单处理

2. **Webhook是唯一触发源** ✅
   - 所有业务逻辑都从Webhook开始
   - 不依赖用户返回Bot

3. **异步处理** ✅
   - 订单处理是异步的，不阻塞Webhook响应
   - 用户可以立即收到Webhook确认

4. **错误恢复** ✅
   - 如果业务逻辑失败，自动退款
   - 用户会收到失败通知

### 9.2 流程优势

- ✅ **可靠性**: Webhook机制确保支付状态准确
- ✅ **安全性**: HMAC签名验证防止伪造
- ✅ **用户体验**: 支付后自动处理，无需用户操作
- ✅ **可追溯**: 完整的日志记录

---

**需要帮助？** 查看代码注释或联系技术支持。

