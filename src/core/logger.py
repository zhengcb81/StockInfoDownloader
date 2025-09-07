"""
日志管理模块
提供统一的日志配置和管理功能
"""

import os
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class SafeStreamHandler(logging.StreamHandler):
    """安全的流处理器，处理中文编码问题"""
    
    def emit(self, record):
        try:
            msg = self.format(record)
            # 处理中文编码问题
            if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding:
                try:
                    msg = msg.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)
                except (UnicodeEncodeError, UnicodeDecodeError):
                    # 如果编码失败，使用UTF-8
                    msg = msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            self.stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


class LoggerManager:
    """日志管理器"""
    
    _instance = None
    _loggers = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._log_dir = Path("logs")
            self._log_dir.mkdir(exist_ok=True)
    
    def get_logger(
        self, 
        name: str, 
        log_file: Optional[str] = None,
        level: int = logging.INFO,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ) -> logging.Logger:
        """
        获取日志器
        
        Args:
            name: 日志器名称
            log_file: 日志文件路径，如果为None则使用name.log
            level: 日志级别
            max_bytes: 单个日志文件最大大小
            backup_count: 备份文件数量
            
        Returns:
            logging.Logger: 日志器实例
        """
        if name in self._loggers:
            return self._loggers[name]
        
        # 创建日志器
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # 避免重复添加处理器
        if logger.handlers:
            return logger
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台处理器 - 处理中文编码问题
        console_handler = SafeStreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # 文件处理器
        if log_file is None:
            log_file = f"{name}.log"
        
        log_path = self._log_dir / log_file
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        self._loggers[name] = logger
        return logger
    
    def configure_logging(self, config: Dict[str, Any]) -> None:
        """
        根据配置配置日志系统
        
        Args:
            config: 日志配置字典
        """
        log_level = config.get('level', 'INFO')
        log_format = config.get('format', 
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s')
        log_dir = Path(config.get('log_dir', 'logs'))
        log_dir.mkdir(exist_ok=True)
        
        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 控制台处理器 - 处理中文编码问题
        console_handler = SafeStreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_formatter = logging.Formatter(log_format)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # 文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'app.log',
            maxBytes=config.get('max_bytes', 10 * 1024 * 1024),
            backupCount=config.get('backup_count', 5),
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    def set_log_level(self, name: str, level: int) -> None:
        """
        设置日志器级别
        
        Args:
            name: 日志器名称
            level: 日志级别
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)
    
    def get_log_files(self) -> Dict[str, str]:
        """获取所有日志文件路径"""
        log_files = {}
        for log_file in self._log_dir.glob('*.log*'):
            log_files[log_file.stem] = str(log_file)
        return log_files
    
    def cleanup_logs(self, days: int = 30) -> int:
        """
        清理旧日志文件
        
        Args:
            days: 保留天数
            
        Returns:
            int: 清理的文件数量
        """
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        for log_file in self._log_dir.glob('*.log*'):
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                try:
                    log_file.unlink()
                    cleaned_count += 1
                except Exception:
                    pass
        
        return cleaned_count


# 全局日志管理器实例
logger_manager = LoggerManager()


def get_logger(
    name: str, 
    log_file: Optional[str] = None,
    level: int = logging.INFO
) -> logging.Logger:
    """
    便捷获取日志器的函数
    
    Args:
        name: 日志器名称
        log_file: 日志文件路径
        level: 日志级别
        
    Returns:
        logging.Logger: 日志器实例
    """
    return logger_manager.get_logger(name, log_file, level)