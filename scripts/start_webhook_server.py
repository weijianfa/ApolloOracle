#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动PingPong Webhook服务器脚本
用于独立运行Webhook服务器，接收PingPong支付回调
"""
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from webhooks.server import run_webhook_server
from bot.utils.logger import logger

if __name__ == "__main__":
    try:
        logger.info("=" * 60)
        logger.info("Starting PingPong Webhook Server")
        logger.info("=" * 60)
        run_webhook_server()
    except KeyboardInterrupt:
        logger.info("\n🛑 Webhook server stopped by user (Ctrl+C)")
        print("\n✅ Webhook server stopped gracefully. Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise

