"""
推广员服务模块
Affiliate Service Module
"""
import random
import string
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from bot.database.db import get_db_session
from bot.models.user import User
from bot.models.affiliate import Affiliate
from bot.models.order import Order
from bot.utils.logger import logger
from bot.utils.operation_logger import log_operation


class AffiliateService:
    """推广员服务类"""
    
    # 佣金阶梯配置
    COMMISSION_TIERS = [
        {"min_sales": 0, "max_sales": 1000, "rate": 0.20},      # 20%
        {"min_sales": 1001, "max_sales": 3000, "rate": 0.25},   # 25%
        {"min_sales": 3001, "max_sales": 5000, "rate": 0.30},   # 30%
        {"min_sales": 5001, "max_sales": float('inf'), "rate": 0.35},  # 35%
    ]
    
    # 额外奖励阈值
    BONUS_THRESHOLD = 8000
    BONUS_AMOUNT = 500
    
    def generate_affiliate_code(self) -> str:
        """
        生成唯一推广码（格式：AFF_08XJ23）
        
        Returns:
            推广码字符串
        """
        while True:
            # 生成8位随机字符（数字+大写字母）
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            code = f"AFF_{random_part}"
            
            # 检查是否已存在
            with get_db_session() as db:
                existing = db.query(Affiliate).filter(Affiliate.affiliate_code == code).first()
                if not existing:
                    return code
    
    def register_affiliate(
        self,
        user_id: int,
        real_name: str,
        contact_info: str,
        payout_account: str
    ) -> Optional[str]:
        """
        注册推广员
        
        Args:
            user_id: 用户ID
            real_name: 真实姓名
            contact_info: 联系方式
            payout_account: 收款账户
        
        Returns:
            推广码，失败返回None
        """
        try:
            with get_db_session() as db:
                # 检查用户是否存在
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    logger.error(f"User not found for affiliate registration: {user_id}")
                    return None
                
                # 检查是否已经是推广员
                if user.is_affiliate:
                    logger.warning(f"User {user_id} is already an affiliate")
                    return user.affiliate_code
                
                # 检查是否已有推广员记录
                existing_affiliate = db.query(Affiliate).filter(Affiliate.user_id == user_id).first()
                if existing_affiliate:
                    logger.warning(f"Affiliate record already exists for user {user_id}")
                    # 更新用户信息
                    user.is_affiliate = True
                    user.affiliate_code = existing_affiliate.affiliate_code
                    user.real_name = real_name
                    user.contact_info = contact_info
                    user.payout_account = payout_account
                    user.agreement_date = datetime.now()
                    db.commit()
                    return existing_affiliate.affiliate_code
                
                # 生成推广码
                affiliate_code = self.generate_affiliate_code()
                
                # 创建推广员记录
                affiliate = Affiliate(
                    affiliate_code=affiliate_code,
                    user_id=user_id,
                    total_sales=Decimal('0.00'),
                    total_commission=Decimal('0.00'),
                    current_tier=1
                )
                db.add(affiliate)
                
                # 更新用户信息
                user.is_affiliate = True
                user.affiliate_code = affiliate_code
                user.real_name = real_name
                user.contact_info = contact_info
                user.payout_account = payout_account
                user.agreement_date = datetime.now()
                
                db.commit()
                
                logger.info(f"Affiliate registered: user_id={user_id}, code={affiliate_code}")
                
                # 记录操作日志
                log_operation(
                    operation_type="affiliate_registration",
                    status="success",
                    user_id=user_id,
                    operation_detail={
                        "affiliate_code": affiliate_code,
                        "real_name": real_name
                    }
                )
                
                return affiliate_code
                
        except Exception as e:
            logger.error(f"Error registering affiliate for user {user_id}: {e}", exc_info=True)
            return None
    
    def get_affiliate_by_code(self, affiliate_code: str) -> Optional[Affiliate]:
        """
        根据推广码获取推广员信息
        
        Args:
            affiliate_code: 推广码
        
        Returns:
            推广员对象，不存在返回None
        """
        try:
            with get_db_session() as db:
                return db.query(Affiliate).filter(Affiliate.affiliate_code == affiliate_code).first()
        except Exception as e:
            logger.error(f"Error getting affiliate by code {affiliate_code}: {e}", exc_info=True)
            return None
    
    def get_affiliate_by_user_id(self, user_id: int) -> Optional[Affiliate]:
        """
        根据用户ID获取推广员信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            推广员对象，不存在返回None
        """
        try:
            with get_db_session() as db:
                return db.query(Affiliate).filter(Affiliate.user_id == user_id).first()
        except Exception as e:
            logger.error(f"Error getting affiliate by user_id {user_id}: {e}", exc_info=True)
            return None
    
    def calculate_commission(self, total_sales: Decimal, order_amount: Decimal) -> Dict[str, Any]:
        """
        计算佣金
        
        Args:
            total_sales: 累计销售额（计算佣金前）
            order_amount: 当前订单金额
        
        Returns:
            包含佣金率、佣金金额、新累计销售额、新佣金等级、额外奖励的字典
        """
        # 计算新的累计销售额
        new_total_sales = total_sales + order_amount
        
        # 确定佣金率（基于当前累计销售额，不包括当前订单）
        commission_rate = 0.20  # 默认20%
        new_tier = 1
        
        for tier in self.COMMISSION_TIERS:
            if tier["min_sales"] <= float(total_sales) < tier["max_sales"]:
                commission_rate = tier["rate"]
                new_tier = self.COMMISSION_TIERS.index(tier) + 1
                break
        
        # 计算佣金
        commission_amount = order_amount * Decimal(str(commission_rate))
        
        # 计算额外奖励（如果达到阈值）
        bonus = Decimal('0.00')
        if float(new_total_sales) >= self.BONUS_THRESHOLD and float(total_sales) < self.BONUS_THRESHOLD:
            # 首次达到阈值，给予奖励
            bonus = Decimal(str(self.BONUS_AMOUNT))
            logger.info(f"Affiliate reached bonus threshold: total_sales={new_total_sales}, bonus={bonus}")
        
        total_commission = commission_amount + bonus
        
        return {
            "commission_rate": commission_rate,
            "commission_amount": commission_amount,
            "bonus": bonus,
            "total_commission": total_commission,
            "new_total_sales": new_total_sales,
            "new_tier": new_tier,
            "old_tier": new_tier - 1 if commission_rate > 0.20 else 1
        }
    
    def update_affiliate_sales(
        self,
        affiliate_code: str,
        order_amount: Decimal,
        commission_amount: Decimal
    ) -> bool:
        """
        更新推广员销售和佣金统计
        
        Args:
            affiliate_code: 推广码
            order_amount: 订单金额
            commission_amount: 佣金金额
        
        Returns:
            成功返回True，失败返回False
        """
        try:
            with get_db_session() as db:
                affiliate = db.query(Affiliate).filter(Affiliate.affiliate_code == affiliate_code).first()
                if not affiliate:
                    logger.error(f"Affiliate not found: {affiliate_code}")
                    return False
                
                # 计算新的累计销售额和佣金
                old_total_sales = affiliate.total_sales
                new_total_sales = old_total_sales + order_amount
                new_total_commission = affiliate.total_commission + commission_amount
                
                # 确定新的佣金等级
                new_tier = 1
                for tier in self.COMMISSION_TIERS:
                    if tier["min_sales"] <= float(new_total_sales) < tier["max_sales"]:
                        new_tier = self.COMMISSION_TIERS.index(tier) + 1
                        break
                
                # 更新推广员统计
                affiliate.total_sales = new_total_sales
                affiliate.total_commission = new_total_commission
                affiliate.current_tier = new_tier
                
                db.commit()
                
                logger.info(
                    f"Affiliate sales updated: code={affiliate_code}, "
                    f"sales: {old_total_sales} -> {new_total_sales}, "
                    f"commission: {affiliate.total_commission} -> {new_total_commission}, "
                    f"tier: {affiliate.current_tier} -> {new_tier}"
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Error updating affiliate sales for {affiliate_code}: {e}", exc_info=True)
            return False
    
    def get_affiliate_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取推广员统计信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            统计信息字典，失败返回None
        """
        try:
            with get_db_session() as db:
                affiliate = db.query(Affiliate).filter(Affiliate.user_id == user_id).first()
                if not affiliate:
                    return None
                
                # 计算当前佣金率
                current_rate = 0.20
                for tier in self.COMMISSION_TIERS:
                    if tier["min_sales"] <= float(affiliate.total_sales) < tier["max_sales"]:
                        current_rate = tier["rate"]
                        break
                
                # 计算距离下一级的销售额
                next_tier_sales = None
                if affiliate.current_tier < len(self.COMMISSION_TIERS):
                    next_tier = self.COMMISSION_TIERS[affiliate.current_tier]
                    next_tier_sales = next_tier["min_sales"] - float(affiliate.total_sales)
                
                return {
                    "affiliate_code": affiliate.affiliate_code,
                    "total_sales": float(affiliate.total_sales),
                    "total_commission": float(affiliate.total_commission),
                    "current_tier": affiliate.current_tier,
                    "current_rate": current_rate,
                    "next_tier_sales": next_tier_sales,
                    "bonus_eligible": float(affiliate.total_sales) >= self.BONUS_THRESHOLD
                }
                
        except Exception as e:
            logger.error(f"Error getting affiliate stats for user {user_id}: {e}", exc_info=True)
            return None
    
    def generate_referral_link(self, affiliate_code: str, bot_username: str) -> str:
        """
        生成推广链接
        
        Args:
            affiliate_code: 推广码
            bot_username: Bot用户名（不含@）
        
        Returns:
            推广链接
        """
        return f"https://t.me/{bot_username}?start=ref_{affiliate_code}"


# 创建全局推广员服务实例
affiliate_service = AffiliateService()

