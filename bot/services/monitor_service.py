"""
监控告警服务模块
Monitoring and Alerting Service Module
"""
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from decimal import Decimal
from bot.database.db import get_db_session
from bot.models.order import Order
from bot.models.operation_log import OperationLog
from bot.config.settings import settings
from bot.utils.logger import logger
from telegram import Bot


class MonitorService:
    """监控服务类"""
    
    # 告警阈值配置
    FAILURE_RATE_THRESHOLD = 0.05  # 5% 失败率
    ALERT_WINDOW_MINUTES = 10  # 10分钟窗口
    MIN_SAMPLES_FOR_ALERT = 10  # 至少10个样本才触发告警
    
    def __init__(self):
        self.bot: Optional[Bot] = None
        self.admin_telegram_id = settings.ADMIN_TELEGRAM_ID
        self._alert_cooldown = {}  # 告警冷却时间（避免重复告警）
        self._cooldown_minutes = 30  # 30分钟内不重复发送相同类型的告警
    
    def set_bot(self, bot: Bot):
        """设置Bot实例（用于发送告警消息）"""
        self.bot = bot
    
    async def get_payment_success_rate(self, minutes: int = 10) -> Tuple[float, int, int]:
        """
        获取支付成功率
        
        Args:
            minutes: 时间窗口（分钟）
        
        Returns:
            (成功率, 成功数, 总数)
        """
        try:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            
            with get_db_session() as db:
                # 查询指定时间窗口内的订单
                orders = db.query(Order).filter(
                    Order.created_at >= cutoff_time
                ).all()
                
                total = len(orders)
                if total == 0:
                    return 1.0, 0, 0
                
                # 统计成功订单（completed状态）
                successful = sum(1 for order in orders if order.status == "completed")
                
                success_rate = successful / total if total > 0 else 0.0
                
                return success_rate, successful, total
                
        except Exception as e:
            logger.error(f"Error calculating payment success rate: {e}", exc_info=True)
            return 0.0, 0, 0
    
    async def get_ai_call_success_rate(self, minutes: int = 10) -> Tuple[float, int, int]:
        """
        获取AI调用成功率
        
        Args:
            minutes: 时间窗口（分钟）
        
        Returns:
            (成功率, 成功数, 总数)
        """
        try:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            
            with get_db_session() as db:
                # 查询AI相关的操作日志
                logs = db.query(OperationLog).filter(
                    OperationLog.operation_type == "ai_generation",
                    OperationLog.created_at >= cutoff_time
                ).all()
                
                total = len(logs)
                if total == 0:
                    return 1.0, 0, 0
                
                # 统计成功的操作
                successful = sum(1 for log in logs if log.status == "success")
                
                success_rate = successful / total if total > 0 else 0.0
                
                return success_rate, successful, total
                
        except Exception as e:
            logger.error(f"Error calculating AI call success rate: {e}", exc_info=True)
            return 0.0, 0, 0
    
    async def get_api_response_times(self, minutes: int = 10) -> Dict[str, float]:
        """
        获取API平均响应时间
        
        Args:
            minutes: 时间窗口（分钟）
        
        Returns:
            字典：{api_name: 平均响应时间（秒）}
        """
        try:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            
            with get_db_session() as db:
                # 查询API调用日志
                logs = db.query(OperationLog).filter(
                    OperationLog.operation_type.in_(["bazi_api_call", "ai_generation"]),
                    OperationLog.created_at >= cutoff_time
                ).all()
                
                api_times = defaultdict(list)
                
                for log in logs:
                    # 从operation_detail中提取响应时间（如果有）
                    if log.operation_detail:
                        import json
                        try:
                            detail = json.loads(log.operation_detail) if isinstance(log.operation_detail, str) else log.operation_detail
                            if "response_time" in detail:
                                api_name = "bazi" if log.operation_type == "bazi_api_call" else "deepseek"
                                api_times[api_name].append(float(detail["response_time"]))
                        except:
                            pass
                
                # 计算平均值
                result = {}
                for api_name, times in api_times.items():
                    if times:
                        result[api_name] = sum(times) / len(times)
                
                return result
                
        except Exception as e:
            logger.error(f"Error calculating API response times: {e}", exc_info=True)
            return {}
    
    async def get_failure_rate(self, minutes: int = 10) -> Tuple[float, int, int]:
        """
        获取总体失败率
        
        Args:
            minutes: 时间窗口（分钟）
        
        Returns:
            (失败率, 失败数, 总数)
        """
        try:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            
            with get_db_session() as db:
                # 查询所有操作日志
                logs = db.query(OperationLog).filter(
                    OperationLog.created_at >= cutoff_time
                ).all()
                
                total = len(logs)
                if total == 0:
                    return 0.0, 0, 0
                
                # 统计失败的操作
                failed = sum(1 for log in logs if log.status == "failed")
                
                failure_rate = failed / total if total > 0 else 0.0
                
                return failure_rate, failed, total
                
        except Exception as e:
            logger.error(f"Error calculating failure rate: {e}", exc_info=True)
            return 0.0, 0, 0
    
    async def check_and_alert(self) -> bool:
        """
        检查指标并发送告警（如果需要）
        
        Returns:
            是否发送了告警
        """
        if not self.bot or not self.admin_telegram_id:
            logger.debug("Monitor service not configured (no bot or admin ID)")
            return False
        
        try:
            # 获取失败率
            failure_rate, failed_count, total_count = await self.get_failure_rate(
                minutes=self.ALERT_WINDOW_MINUTES
            )
            
            # 检查是否需要告警
            if total_count < self.MIN_SAMPLES_FOR_ALERT:
                logger.debug(f"Not enough samples for alert: {total_count} < {self.MIN_SAMPLES_FOR_ALERT}")
                return False
            
            if failure_rate > self.FAILURE_RATE_THRESHOLD:
                # 检查冷却时间
                alert_key = "failure_rate"
                now = datetime.now()
                
                if alert_key in self._alert_cooldown:
                    last_alert_time = self._alert_cooldown[alert_key]
                    if (now - last_alert_time).total_seconds() < self._cooldown_minutes * 60:
                        logger.debug(f"Alert cooldown active for {alert_key}")
                        return False
                
                # 发送告警
                await self._send_alert(
                    alert_type="failure_rate",
                    message=(
                        f"⚠️ 系统异常率告警\n\n"
                        f"过去 {self.ALERT_WINDOW_MINUTES} 分钟内：\n"
                        f"• 总操作数: {total_count}\n"
                        f"• 失败数: {failed_count}\n"
                        f"• 失败率: {failure_rate * 100:.2f}%\n"
                        f"• 阈值: {self.FAILURE_RATE_THRESHOLD * 100:.0f}%\n\n"
                        f"请检查系统状态！"
                    )
                )
                
                # 更新冷却时间
                self._alert_cooldown[alert_key] = now
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in check_and_alert: {e}", exc_info=True)
            return False
    
    async def get_system_health(self) -> Dict[str, any]:
        """
        获取系统健康状态
        
        Returns:
            系统健康指标字典
        """
        try:
            payment_rate, payment_success, payment_total = await self.get_payment_success_rate()
            ai_rate, ai_success, ai_total = await self.get_ai_call_success_rate()
            failure_rate, failed_count, total_count = await self.get_failure_rate()
            api_times = await self.get_api_response_times()
            
            return {
                "payment_success_rate": payment_rate,
                "payment_stats": {"success": payment_success, "total": payment_total},
                "ai_success_rate": ai_rate,
                "ai_stats": {"success": ai_success, "total": ai_total},
                "overall_failure_rate": failure_rate,
                "failure_stats": {"failed": failed_count, "total": total_count},
                "api_response_times": api_times,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}", exc_info=True)
            return {}
    
    async def _send_alert(self, alert_type: str, message: str) -> bool:
        """
        发送告警消息给管理员
        
        Args:
            alert_type: 告警类型
            message: 告警消息
        
        Returns:
            是否发送成功
        """
        if not self.bot or not self.admin_telegram_id:
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.admin_telegram_id,
                text=message
            )
            logger.info(f"Alert sent to admin: {alert_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send alert to admin: {e}", exc_info=True)
            return False
    
    async def send_health_report(self) -> bool:
        """
        发送系统健康报告给管理员
        
        Returns:
            是否发送成功
        """
        if not self.bot or not self.admin_telegram_id:
            return False
        
        try:
            health = await self.get_system_health()
            
            if not health:
                return False
            
            # 构建报告消息
            report = (
                f"📊 系统健康报告\n\n"
                f"⏰ 时间: {health.get('timestamp', 'N/A')}\n\n"
                f"💳 支付成功率: {health.get('payment_success_rate', 0) * 100:.2f}%\n"
                f"   成功: {health.get('payment_stats', {}).get('success', 0)}\n"
                f"   总数: {health.get('payment_stats', {}).get('total', 0)}\n\n"
                f"🤖 AI调用成功率: {health.get('ai_success_rate', 0) * 100:.2f}%\n"
                f"   成功: {health.get('ai_stats', {}).get('success', 0)}\n"
                f"   总数: {health.get('ai_stats', {}).get('total', 0)}\n\n"
                f"❌ 总体失败率: {health.get('overall_failure_rate', 0) * 100:.2f}%\n"
                f"   失败: {health.get('failure_stats', {}).get('failed', 0)}\n"
                f"   总数: {health.get('failure_stats', {}).get('total', 0)}\n"
            )
            
            # 添加API响应时间
            api_times = health.get('api_response_times', {})
            if api_times:
                report += "\n⏱️ API响应时间:\n"
                for api_name, avg_time in api_times.items():
                    report += f"   {api_name}: {avg_time:.2f}秒\n"
            
            await self.bot.send_message(
                chat_id=self.admin_telegram_id,
                text=report
            )
            
            logger.info("Health report sent to admin")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send health report: {e}", exc_info=True)
            return False


# 创建全局监控服务实例
monitor_service = MonitorService()

