"""
监控后台任务
Monitoring Background Task
"""
import asyncio
from bot.services.monitor_service import monitor_service
from bot.utils.logger import logger


async def start_monitoring_task(application):
    """
    启动监控后台任务
    
    Args:
        application: Telegram Application实例
    """
    # 设置Bot实例
    monitor_service.set_bot(application.bot)
    
    # 启动监控循环
    logger.info("Monitoring task started")
    
    while True:
        try:
            # 检查并发送告警（如果需要）
            await monitor_service.check_and_alert()
            
            # 等待5分钟后再检查
            await asyncio.sleep(300)  # 5分钟
            
        except asyncio.CancelledError:
            logger.info("Monitoring task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in monitoring task: {e}", exc_info=True)
            # 出错后等待1分钟再重试
            await asyncio.sleep(60)


async def send_daily_health_report(application):
    """
    发送每日健康报告（每天一次）
    
    Args:
        application: Telegram Application实例
    """
    monitor_service.set_bot(application.bot)
    
    logger.info("Daily health report task started")
    
    while True:
        try:
            # 等待到下一个整点（例如：每天00:00）
            # 简化实现：每24小时发送一次
            await asyncio.sleep(86400)  # 24小时
            
            # 发送健康报告
            await monitor_service.send_health_report()
            
        except asyncio.CancelledError:
            logger.info("Daily health report task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in daily health report task: {e}", exc_info=True)
            # 出错后等待1小时再重试
            await asyncio.sleep(3600)

