"""
支付服务模块
"""
import uuid
import hashlib
import hmac
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import requests
from bot.config.settings import settings
from bot.utils.logger import logger
from bot.database.db import get_db_session
from bot.models.order import Order
from bot.models.user import User


class PaymentService:
    """支付服务类"""
    
    def __init__(self):
        self.api_key = settings.PINGPONG_API_KEY
        self.merchant_id = settings.PINGPONG_MERCHANT_ID
        self.webhook_secret = settings.PINGPONG_WEBHOOK_SECRET
        self.base_url = settings.PINGPONG_API_BASE_URL or "https://api.pingpongx.com"
        self.mock_mode = settings.PINGPONG_USE_MOCK
        self.mock_payment_url = settings.PINGPONG_MOCK_PAYMENT_URL or "https://example.com/mock-pingpong-payment"
    
    def create_order(
        self,
        user_id: int,
        product_id: int,
        product_name: str,
        amount_usd: float,
        user_input: Dict[str, Any],
        affiliate_code: Optional[str] = None
    ) -> Optional[str]:
        """
        创建订单
        
        Args:
            user_id: 用户ID
            product_id: 产品ID
            product_name: 产品名称
            amount_usd: 金额（美元）
            user_input: 用户输入数据
            affiliate_code: 推广员代码
            
        Returns:
            创建的订单ID（字符串），失败返回None
        """
        try:
            # 生成订单ID
            order_id = f"ORD_{int(time.time())}_{uuid.uuid4().hex[:8].upper()}"
            
            # 创建订单记录
            with get_db_session() as db:
                db_user = db.query(User).filter(User.id == user_id).first()
                if not db_user:
                    logger.error(f"User not found: {user_id}")
                    return None
                
                # 将user_input转换为JSON字符串（使用json.dumps而不是str）
                import json
                user_input_json = json.dumps(user_input, ensure_ascii=False) if user_input else "{}"
                
                # 计算佣金（如果有关联的推广员）
                commission_rate = None
                commission_amount = None
                if affiliate_code:
                    from bot.services.affiliate_service import affiliate_service
                    affiliate = affiliate_service.get_affiliate_by_code(affiliate_code)
                    if affiliate:
                        # 计算佣金（基于当前累计销售额）
                        commission_info = affiliate_service.calculate_commission(
                            total_sales=affiliate.total_sales,
                            order_amount=Decimal(str(amount_usd))
                        )
                        commission_rate = Decimal(str(commission_info["commission_rate"]))
                        commission_amount = commission_info["total_commission"]  # 包含额外奖励
                        logger.info(
                            f"Commission calculated for order {order_id}: "
                            f"rate={commission_rate}, amount={commission_amount}, "
                            f"affiliate_code={affiliate_code}"
                        )
                
                order = Order(
                    order_id=order_id,
                    user_id=user_id,
                    product_id=product_id,
                    product_name=product_name,
                    status="pending_payment",
                    amount_usd=amount_usd,
                    user_input=user_input_json,  # JSON字符串格式
                    affiliate_code=affiliate_code,
                    commission_rate=float(commission_rate) if commission_rate else None,
                    commission_amount=float(commission_amount) if commission_amount else None
                )
                
                db.add(order)
                db.commit()
                # 返回 order_id 字符串，避免会话问题
                
                logger.info(f"Order created: {order_id} for user {user_id}")
                return order_id
                
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            return None
    
    def create_payment_link(
        self,
        order: Order,
        return_url: str,
        cancel_url: str
    ) -> Optional[str]:
        """
        创建支付链接
        
        Args:
            order: 订单对象
            return_url: 支付成功返回URL
            cancel_url: 支付取消返回URL
            
        Returns:
            支付链接URL，失败返回None
        """
        try:
            if self.mock_mode:
                return self._create_mock_payment_link(order)
            
            # 构建支付请求数据
            # 注意：这里需要根据PingPong实际API文档调整
            payment_data = {
                "merchant_id": self.merchant_id,
                "order_id": order.order_id,
                "amount": float(order.amount_usd),
                "currency": "USD",
                "description": f"{order.product_name} - Order {order.order_id}",
                "return_url": return_url,
                "cancel_url": cancel_url,
                "notify_url": f"{settings.WEBHOOK_URL}/webhook/pingpong",  # Webhook回调地址
                "timestamp": int(time.time()),
            }
            
            # 生成签名（根据PingPong文档要求）
            signature = self._generate_signature(payment_data)
            payment_data["signature"] = signature
            
            # 调用PingPong API创建支付
            response = requests.post(
                f"{self.base_url}/v1/payments/create",
                json=payment_data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                payment_url = result.get("payment_url")
                
                if payment_url:
                    logger.info(f"Payment link created for order {order.order_id}")
                    return payment_url
                else:
                    logger.error(f"No payment_url in response: {result}")
                    return None
            else:
                logger.error(f"Failed to create payment link: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating payment link: {e}")
            return None
    
    def _create_mock_payment_link(self, order: Order) -> str:
        """
        创建模拟支付链接（开发/测试环境使用）
        """
        mock_link = f"{self.mock_payment_url}?order_id={order.order_id}"
        logger.info(f"[MOCK] Payment link generated for order {order.order_id}: {mock_link}")
        return mock_link
    
    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """
        生成签名（根据PingPong文档要求）
        
        Args:
            data: 支付数据
            
        Returns:
            签名字符串
        """
        # 根据PingPong文档实现签名算法
        # 这里是一个示例，需要根据实际文档调整
        sorted_items = sorted(data.items())
        sign_string = "&".join([f"{k}={v}" for k, v in sorted_items if k != "signature"])
        sign_string += f"&key={self.webhook_secret}"
        
        signature = hashlib.md5(sign_string.encode()).hexdigest().upper()
        return signature
    
    def is_mock_mode(self) -> bool:
        """返回是否启用Mock模式"""
        return self.mock_mode

    async def simulate_mock_payment(
        self,
        order_id: str,
        status: str = "paid",
        error_message: Optional[str] = None,
        payment_method: str = "mock_pingpong"
    ) -> bool:
        """
        在Mock模式下模拟支付结果（用于开发测试）
        """
        if not self.mock_mode:
            logger.warning("simulate_mock_payment called when mock mode is disabled")
            return False
        
        try:
            # 在会话内获取所有需要的值
            amount = 0.0
            existing_payment_id = None
            with get_db_session() as db:
                order = db.query(Order).filter(Order.order_id == order_id).first()
                if not order:
                    logger.error(f"[MOCK] Order not found for simulation: {order_id}")
                    return False
                # 在会话内提取所有需要的值
                amount = float(order.amount_usd or 0.0)
                existing_payment_id = order.payment_id  # 在会话内访问
        
            # 构建payload（使用已提取的值）
            payload = {
                "order_id": order_id,
                "status": status,
                "payment_id": existing_payment_id or f"MOCKPAY-{uuid.uuid4().hex[:8].upper()}",
                "payment_method": payment_method,
                "amount": amount,
                "currency": "USD",
                "timestamp": int(time.time()),
            }
            
            if error_message:
                payload["error_message"] = error_message
            
            signature = self._generate_signature(payload)
            processed = self.process_payment_webhook(payload, signature)
            
            if processed and status == "paid":
                try:
                    from bot.services.order_processor import order_processor
                    logger.info(f"[MOCK] Triggering order processor for {order_id}")
                    success = await order_processor.process_paid_order(order_id)
                    if not success:
                        logger.error(f"[MOCK] Order processor returned False for {order_id}")
                    return success
                except Exception as e:
                    logger.error(f"[MOCK] Failed to trigger order processor: {e}", exc_info=True)
                    return False
            return processed
        except Exception as e:
            logger.error(f"[MOCK] Error simulating payment: {e}", exc_info=True)
            return False
    
    def verify_webhook_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        验证Webhook签名
        
        Args:
            payload: Webhook数据
            signature: 签名
            
        Returns:
            验证是否通过
        """
        try:
            # 根据PingPong文档实现签名验证
            expected_signature = self._generate_signature(payload)
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def process_payment_webhook(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        处理支付Webhook
        
        Args:
            payload: Webhook数据
            signature: 签名
            
        Returns:
            处理是否成功
        """
        try:
            # 验证签名
            if not self.verify_webhook_signature(payload, signature):
                logger.warning(f"Invalid webhook signature: {signature}")
                return False
            
            order_id = payload.get("order_id")
            payment_status = payload.get("status")  # paid, failed, cancelled
            payment_id = payload.get("payment_id")
            
            if not order_id:
                logger.error("No order_id in webhook payload")
                return False
            
            # 更新订单状态
            with get_db_session() as db:
                order = db.query(Order).filter(Order.order_id == order_id).first()
                if not order:
                    logger.error(f"Order not found: {order_id}")
                    return False
                
                if payment_status == "paid":
                    order.status = "paid"
                    order.payment_id = payment_id
                    order.payment_method = payload.get("payment_method", "unknown")
                    order.updated_at = datetime.now()
                    db.commit()
                    
                    logger.info(f"Order {order_id} payment confirmed")
                    return True
                elif payment_status == "failed":
                    order.status = "failed"
                    order.error_message = payload.get("error_message", "Payment failed")
                    order.updated_at = datetime.now()
                    db.commit()
                    
                    logger.warning(f"Order {order_id} payment failed")
                    return True
                elif payment_status == "cancelled":
                    order.status = "failed"
                    order.error_message = "Payment cancelled by user"
                    order.updated_at = datetime.now()
                    db.commit()
                    
                    logger.info(f"Order {order_id} payment cancelled")
                    return True
                else:
                    logger.warning(f"Unknown payment status: {payment_status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error processing payment webhook: {e}")
            return False
    
    def refund_order(self, order: Order, reason: str = "Service failed") -> bool:
        """
        退款订单
        
        Args:
            order: 订单对象
            reason: 退款原因
            
        Returns:
            退款是否成功
        """
        try:
            # Mock模式下直接模拟退款成功，避免真实API调用失败
            if self.mock_mode:
                logger.info(f"[MOCK] Simulating refund for order {order.order_id}, reason: {reason}")
                try:
                    with get_db_session() as db:
                        db_order = db.query(Order).filter(Order.order_id == order.order_id).first()
                        if db_order:
                            db_order.status = "refunded"
                            db_order.error_message = f"Refunded (mock): {reason}"
                            db_order.updated_at = datetime.now()
                            db.commit()
                    return True
                except Exception as mock_db_error:
                    logger.error(f"[MOCK] Failed to update order status after refund: {mock_db_error}")
                    return False
            
            if not order.payment_id:
                logger.error(f"No payment_id for order {order.order_id}")
                return False
            
            # 构建退款请求
            refund_data = {
                "merchant_id": self.merchant_id,
                "payment_id": order.payment_id,
                "amount": float(order.amount_usd),
                "reason": reason,
                "timestamp": int(time.time()),
            }
            
            signature = self._generate_signature(refund_data)
            refund_data["signature"] = signature
            
            # 调用PingPong API退款
            response = requests.post(
                f"{self.base_url}/v1/payments/refund",
                json=refund_data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    # 更新订单状态
                    with get_db_session() as db:
                        order = db.query(Order).filter(Order.id == order.id).first()
                        if order:
                            order.status = "refunded"
                            order.updated_at = datetime.now()
                            db.commit()
                    
                    logger.info(f"Order {order.order_id} refunded successfully")
                    return True
                else:
                    logger.error(f"Refund failed: {result}")
                    return False
            else:
                logger.error(f"Failed to refund: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error refunding order: {e}")
            return False
    
    def check_payment_timeout(self) -> int:
        """
        检查并处理支付超时的订单
        
        Returns:
            处理的订单数量
        """
        count = 0
        timeout_minutes = 30
        
        try:
            with get_db_session() as db:
                # 查找超过30分钟未支付的订单
                timeout_threshold = datetime.now() - timedelta(minutes=timeout_minutes)
                timeout_orders = db.query(Order).filter(
                    Order.status == "pending_payment",
                    Order.created_at < timeout_threshold
                ).all()
                
                for order in timeout_orders:
                    order.status = "failed"
                    order.error_message = "Payment timeout"
                    order.updated_at = datetime.now()
                    count += 1
                    logger.info(f"Order {order.order_id} timed out")
                
                db.commit()
                
        except Exception as e:
            logger.error(f"Error checking payment timeout: {e}")
        
        return count


# 创建全局支付服务实例
payment_service = PaymentService()

