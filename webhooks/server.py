"""
Webhook服务器（用于生产环境）
"""
import sys
import os

# 添加项目根目录到Python路径（支持从任何目录运行）
# 获取当前文件的目录，然后获取项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from bot.config.settings import settings
from bot.utils.logger import logger
from webhooks.pingpong import router as pingpong_router

app = FastAPI(title="Telegram Bot Webhook Server")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(pingpong_router)


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "service": "telegram-bot-webhook"}


def run_webhook_server():
    """运行Webhook服务器（用于接收PingPong支付回调）"""
    # 开发环境可以不使用SSL（配合ngrok等工具）
    # 生产环境必须使用SSL
    
    # 检查SSL证书文件是否存在
    cert_exists = settings.SSL_CERT_PATH and os.path.exists(settings.SSL_CERT_PATH)
    key_exists = settings.SSL_KEY_PATH and os.path.exists(settings.SSL_KEY_PATH)
    use_ssl = cert_exists and key_exists
    
    if settings.is_production() and not use_ssl:
        if settings.SSL_CERT_PATH or settings.SSL_KEY_PATH:
            logger.error(
                f"SSL certificate or key file not found!\n"
                f"Certificate path: {settings.SSL_CERT_PATH}\n"
                f"Key path: {settings.SSL_KEY_PATH}\n"
                f"SSL certificate and key files are required for production webhook server"
            )
        else:
            logger.error("SSL certificate and key paths are not configured. Required for production webhook server")
        return
    
    # 如果配置了SSL路径但文件不存在（开发环境），给出警告并回退到非SSL模式
    if (settings.SSL_CERT_PATH or settings.SSL_KEY_PATH) and not use_ssl:
        logger.warning(
            f"SSL certificate or key file not found, running without SSL (development mode)\n"
            f"Certificate path: {settings.SSL_CERT_PATH or 'Not configured'}\n"
            f"Key path: {settings.SSL_KEY_PATH or 'Not configured'}"
        )
    
    # 使用独立的PingPong Webhook端口配置
    listen_host = settings.PINGPONG_WEBHOOK_LISTEN
    listen_port = settings.PINGPONG_WEBHOOK_PORT
    
    if use_ssl:
        logger.info(f"Starting PingPong webhook server with SSL on {listen_host}:{listen_port}")
        logger.info(f"Webhook URL: https://yourdomain.com/webhook/pingpong")
        uvicorn.run(
            app,
            host=listen_host,
            port=listen_port,
            ssl_keyfile=settings.SSL_KEY_PATH,
            ssl_certfile=settings.SSL_CERT_PATH,
            log_level=settings.LOG_LEVEL.lower()
        )
    else:
        # 开发环境：不使用SSL（配合ngrok等隧道工具）
        logger.warning("Running webhook server without SSL (development mode)")
        logger.info(f"Starting PingPong webhook server on {listen_host}:{listen_port}")
        logger.info("⚠️  For production, use HTTPS with SSL certificates")
        logger.info("💡 For development, use ngrok or similar tunnel tool")
        logger.info(f"💡 Example ngrok command: ngrok http {listen_port}")
        logger.info(f"💡 Then configure PingPong webhook URL: https://xxxx.ngrok-free.app/webhook/pingpong")
        
        uvicorn.run(
            app,
            host=listen_host,
            port=listen_port,
            log_level=settings.LOG_LEVEL.lower()
        )


if __name__ == "__main__":
    run_webhook_server()

