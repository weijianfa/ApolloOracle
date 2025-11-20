"""数据模型模块"""
from bot.models.user import User
from bot.models.order import Order
from bot.models.user_session import UserSession
from bot.models.affiliate import Affiliate
from bot.models.operation_log import OperationLog
from bot.models.system_config import SystemConfig
from bot.models.prompt import Prompt
from bot.models.exchange_rate import ExchangeRate

__all__ = [
    'User',
    'Order',
    'UserSession',
    'Affiliate',
    'OperationLog',
    'SystemConfig',
    'Prompt',
    'ExchangeRate',
]

