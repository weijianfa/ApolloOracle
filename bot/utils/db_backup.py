"""
数据库备份工具
"""
import os
import shutil
from typing import Optional
from datetime import datetime
from pathlib import Path
from bot.config.settings import settings
from bot.utils.logger import logger


def backup_database(backup_dir: str = "backups") -> Optional[str]:
    """
    备份数据库（SQLite）
    
    Args:
        backup_dir: 备份目录
        
    Returns:
        备份文件路径，失败返回None
    """
    try:
        # 创建备份目录
        backup_path = Path(backup_dir)
        backup_path.mkdir(exist_ok=True)
        
        # 获取数据库文件路径
        if "sqlite" in settings.DATABASE_URL:
            # 从DATABASE_URL提取文件路径
            db_path = settings.DATABASE_URL.replace("sqlite:///", "")
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.getcwd(), db_path)
        else:
            logger.warning("Database backup currently only supports SQLite")
            return None
        
        if not os.path.exists(db_path):
            logger.error(f"Database file not found: {db_path}")
            return None
        
        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"bot_backup_{timestamp}.db"
        backup_filepath = backup_path / backup_filename
        
        # 复制数据库文件
        shutil.copy2(db_path, backup_filepath)
        
        logger.info(f"Database backed up to: {backup_filepath}")
        
        # 清理旧备份（保留最近7天）
        cleanup_old_backups(backup_path, days=7)
        
        return str(backup_filepath)
        
    except Exception as e:
        logger.error(f"Error backing up database: {e}")
        return None


def cleanup_old_backups(backup_dir: Path, days: int = 7):
    """
    清理旧的备份文件
    
    Args:
        backup_dir: 备份目录
        days: 保留天数
    """
    try:
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
        
        for backup_file in backup_dir.glob("bot_backup_*.db"):
            if backup_file.stat().st_mtime < cutoff_time:
                backup_file.unlink()
                logger.info(f"Deleted old backup: {backup_file}")
                
    except Exception as e:
        logger.error(f"Error cleaning up old backups: {e}")


def restore_database(backup_filepath: str) -> bool:
    """
    恢复数据库（SQLite）
    
    Args:
        backup_filepath: 备份文件路径
        
    Returns:
        恢复是否成功
    """
    try:
        if not os.path.exists(backup_filepath):
            logger.error(f"Backup file not found: {backup_filepath}")
            return False
        
        # 获取数据库文件路径
        if "sqlite" in settings.DATABASE_URL:
            db_path = settings.DATABASE_URL.replace("sqlite:///", "")
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.getcwd(), db_path)
        else:
            logger.warning("Database restore currently only supports SQLite")
            return False
        
        # 备份当前数据库（如果存在）
        if os.path.exists(db_path):
            current_backup = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(db_path, current_backup)
            logger.info(f"Current database backed up to: {current_backup}")
        
        # 恢复数据库
        shutil.copy2(backup_filepath, db_path)
        
        logger.info(f"Database restored from: {backup_filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Error restoring database: {e}")
        return False

