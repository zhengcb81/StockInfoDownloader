"""
统一日志管理模块
提供结构化的日志配置和管理功能，支持中文编码和JSON上下文
"""

import os
import logging
import logging.handlers
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class SafeStreamHandler(logging.StreamHandler):
    """Safe stream handler that handles encoding issues robustly"""
    
    def emit(self, record):
        try:
            msg = self.format(record)
            # Standardize on UTF-8 for internal consistency, but adapt to stream if needed
            stream = self.stream
            if hasattr(stream, 'encoding') and stream.encoding:
                try:
                    # Attempt to encode/decode to ensure compatibility with the current terminal
                    msg.encode(stream.encoding, errors='replace').decode(stream.encoding)
                except Exception:
                    # Fallback to UTF-8 if current encoding is broken
                    pass
            
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


class StructuredLogger:
    """结构化日志记录器，支持中文编码和JSON上下文"""
    
    def __init__(self, name: str, log_file: Optional[str] = None, level: int = logging.INFO):
        """
        初始化结构化日志记录器
        
        Args:
            name: 日志记录器名称
            log_file: 日志文件路径
            level: 日志级别
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.name = name
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers(log_file)
    
    def _setup_handlers(self, log_file: Optional[str]):
        """设置日志处理器"""
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台处理器 - 处理中文编码问题
        console_handler = SafeStreamHandler()
        console_handler.setLevel(self.logger.level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        if log_file:
            log_path = Path(log_file)
            # 确保日志目录存在
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(self.logger.level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
            # 强制创建文件并写入一条测试日志来确保文件存在
            original_level = self.logger.level
            self.logger.setLevel(logging.INFO)
            self.info("Logger initialized")
            self.logger.handlers[-1].flush()  # 强制刷新
            self.logger.setLevel(original_level)
    
    def _format_message(self, message: str, **kwargs) -> str:
        """格式化消息，包含上下文信息"""
        if kwargs:
            context = json.dumps(kwargs, ensure_ascii=False)
            return f"{message} | Context: {context}"
        return message
    
    def debug(self, message: str, **kwargs):
        """记录调试日志"""
        formatted_message = self._format_message(message, **kwargs)
        self.logger.debug(formatted_message)
        self._flush_handlers()
    
    def info(self, message: str, **kwargs):
        """记录信息日志"""
        formatted_message = self._format_message(message, **kwargs)
        self.logger.info(formatted_message)
        self._flush_handlers()
    
    def warning(self, message: str, **kwargs):
        """记录警告日志"""
        formatted_message = self._format_message(message, **kwargs)
        self.logger.warning(formatted_message)
        self._flush_handlers()
    
    def error(self, message: str, **kwargs):
        """记录错误日志"""
        formatted_message = self._format_message(message, **kwargs)
        self.logger.error(formatted_message)
        self._flush_handlers()
    
    def critical(self, message: str, **kwargs):
        """记录严重错误日志"""
        formatted_message = self._format_message(message, **kwargs)
        self.logger.critical(formatted_message)
        self._flush_handlers()
    
    def _flush_handlers(self):
        """强制刷新所有处理器"""
        for handler in self.logger.handlers:
            handler.flush()


class LoggerManager:
    """统一的日志管理器，单例模式"""
    
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
        structured: bool = True
    ) -> StructuredLogger:
        """
        获取结构化日志器
        
        Args:
            name: 日志器名称
            log_file: 日志文件路径，如果为None则使用name.log
            level: 日志级别
            structured: 是否使用结构化日志器
            
        Returns:
            StructuredLogger: 结构化日志器实例
        """
        if name in self._loggers:
            return self._loggers[name]
        
        # 设置日志文件路径
        if log_file is None:
            log_file = str(self._log_dir / f"{name}.log")
        
        # 创建结构化日志器
        logger = StructuredLogger(name, log_file, level)
        
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


# 为向后兼容性提供 Logger 别名
Logger = StructuredLogger


# 全局日志管理器实例
logger_manager = LoggerManager()


def get_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO
) -> StructuredLogger:
    """
    便捷获取结构化日志器的函数

    Args:
        name: 日志器名称
        log_file: 日志文件路径
        level: 日志级别

    Returns:
        StructuredLogger: 结构化日志器实例
    """
    return logger_manager.get_logger(name, log_file, level)


def setup_global_logging(log_dir: str, level: int = logging.INFO) -> None:
    """
    设置全局日志配置

    Args:
        log_dir: 日志目录路径
        level: 日志级别
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 控制台处理器
    console_handler = SafeStreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器
    app_log_file = log_path / 'application.log'
    file_handler = logging.handlers.RotatingFileHandler(
        app_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)