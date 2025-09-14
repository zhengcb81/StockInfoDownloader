"""
结构化错误处理系统
提供全面的错误分类、上下文管理和恢复机制
"""

import os
import sys
import time
import traceback
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, asdict
from pathlib import Path

# 错误代码枚举
class ErrorCode(Enum):
    """错误代码枚举"""
    # 系统错误 (1000-1999)
    SYSTEM_ERROR = "SYS_1000"
    INITIALIZATION_ERROR = "SYS_1001"
    RESOURCE_ERROR = "SYS_1002"
    
    # WebDriver错误 (2000-2999)
    WEBDRIVER_INIT_ERROR = "WD_2000"
    WEBDRIVER_CONNECTION_ERROR = "WD_2001"
    WEBDRIVER_TIMEOUT_ERROR = "WD_2002"
    WEBDRIVER_ELEMENT_ERROR = "WD_2003"
    WEBDRIVER_NAVIGATION_ERROR = "WD_2004"
    WEBDRIVER_SESSION_ERROR = "WD_2005"
    WEBDRIVER_CRASH_ERROR = "WD_2006"
    WEBDRIVER_STRATEGY_ERROR = "WD_2007"
    
    # 配置错误 (3000-3999)
    CONFIG_FILE_ERROR = "CFG_3000"
    CONFIG_FILE_NOT_FOUND = "CFG_3001"
    CONFIG_FORMAT_ERROR = "CFG_3002"
    CONFIG_LOAD_ERROR = "CFG_3003"
    CONFIG_SAVE_ERROR = "CFG_3004"
    CONFIG_VALIDATION_ERROR = "CFG_3005"
    CONFIG_MISSING_ERROR = "CFG_3006"
    CONFIG_PATH_NOT_SET = "CFG_3007"
    
    # 下载错误 (4000-4999)
    DOWNLOAD_INIT_ERROR = "DL_4000"
    DOWNLOAD_NETWORK_ERROR = "DL_4001"
    DOWNLOAD_FILE_ERROR = "DL_4002"
    DOWNLOAD_TIMEOUT_ERROR = "DL_4003"
    DOWNLOAD_PERMISSION_ERROR = "DL_4004"
    DOWNLOAD_RATE_LIMIT_ERROR = "DL_4005"
    DOWNLOAD_VALIDATION_ERROR = "DL_4006"
    DOWNLOAD_TASK_ERROR = "DL_4007"
    DOWNLOAD_STOCK_INFO_ERROR = "DL_4008"
    DOWNLOAD_ORG_ID_ERROR = "DL_4009"
    
    # 数据处理错误 (5000-5999)
    DATA_PARSING_ERROR = "DATA_5000"
    DATA_VALIDATION_ERROR = "DATA_5001"
    DATA_MAPPING_ERROR = "DATA_5002"
    DATA_STORAGE_ERROR = "DATA_5003"
    
    # 组织ID错误 (6000-6999)
    ORGID_FETCH_ERROR = "ORG_6000"
    ORGID_VALIDATION_ERROR = "ORG_6001"
    ORGID_MAPPING_ERROR = "ORG_6002"
    
    # 网络错误 (7000-7999)
    NETWORK_CONNECTION_ERROR = "NET_7000"
    NETWORK_TIMEOUT_ERROR = "NET_7001"
    NETWORK_HTTP_ERROR = "NET_7002"
    NETWORK_DNS_ERROR = "NET_7003"
    
    # 文件系统错误 (8000-8999)
    FILE_NOT_FOUND_ERROR = "FILE_8000"
    FILE_PERMISSION_ERROR = "FILE_8001"
    FILE_DISK_SPACE_ERROR = "FILE_8002"
    FILE_FORMAT_ERROR = "FILE_8003"
    
    # 验证错误 (9000-9999)
    VALIDATION_INPUT_ERROR = "VAL_9000"
    VALIDATION_FORMAT_ERROR = "VAL_9001"
    VALIDATION_RANGE_ERROR = "VAL_9002"
    VALIDATION_REQUIRED_ERROR = "VAL_9003"
    VALIDATION_TYPE_NOT_SUPPORTED = "VAL_9004"
    VALIDATION_PROCESSING_ERROR = "VAL_9005"
    VALIDATION_STOCK_CODE_ERROR = "VAL_9006"
    VALIDATION_STOCK_CODE_EMPTY = "VAL_9007"
    VALIDATION_STOCK_CODE_FORMAT = "VAL_9008"
    VALIDATION_STOCK_CODE_RANGE = "VAL_9009"

# 错误严重级别枚举
class ErrorSeverity(Enum):
    """错误严重级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"

# 错误恢复策略枚举
class RecoveryStrategy(Enum):
    """错误恢复策略"""
    NONE = "NONE"  # 无恢复
    RETRY = "RETRY"  # 重试
    FALLBACK = "FALLBACK"  # 降级
    SKIP = "SKIP"  # 跳过
    TERMINATE = "TERMINATE"  # 终止
    MANUAL = "MANUAL"  # 手动处理

@dataclass
class ErrorContext:
    """错误上下文信息"""
    timestamp: datetime
    error_code: ErrorCode
    severity: ErrorSeverity
    message: str
    module: str
    function: str
    line_number: int
    file_path: str
    user_action: Optional[str] = None
    system_state: Optional[Dict[str, Any]] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['error_code'] = self.error_code.value
        data['severity'] = self.severity.value
        return data

class StockInfoError(Exception):
    """基础异常类"""
    
    def __init__(self, 
                 message: str,
                 error_code: ErrorCode = ErrorCode.SYSTEM_ERROR,
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 recovery_strategy: RecoveryStrategy = RecoveryStrategy.NONE,
                 context: Optional[Dict[str, Any]] = None,
                 original_exception: Optional[Exception] = None):
        """
        初始化异常
        
        Args:
            message: 错误消息
            error_code: 错误代码
            severity: 错误严重级别
            recovery_strategy: 恢复策略
            context: 错误上下文
            original_exception: 原始异常
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.recovery_strategy = recovery_strategy
        self.context = context or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now()
        
        # 获取调用栈信息
        self.stack_trace = traceback.format_exc()
        self.caller_info = self._get_caller_info()
        
        # 创建错误上下文
        self.error_context = ErrorContext(
            timestamp=self.timestamp,
            error_code=error_code,
            severity=severity,
            message=message,
            module=self.caller_info.get('module', 'unknown'),
            function=self.caller_info.get('function', 'unknown'),
            line_number=self.caller_info.get('line_number', 0),
            file_path=self.caller_info.get('file_path', 'unknown'),
            system_state=context,
            recovery_attempted=False,
            recovery_successful=False
        )
    
    def _get_caller_info(self) -> Dict[str, str]:
        """获取调用者信息"""
        try:
            # 跳过前几帧（异常构造和当前帧）
            frame = sys._getframe(2)
            while frame:
                filename = frame.f_code.co_filename
                if 'src' in filename:  # 只关心项目源码
                    return {
                        'module': frame.f_globals.get('__name__', 'unknown'),
                        'function': frame.f_code.co_name,
                        'line_number': frame.f_lineno,
                        'file_path': filename
                    }
                frame = frame.f_back
        except:
            pass
        return {
            'module': 'unknown',
            'function': 'unknown',
            'line_number': 0,
            'file_path': 'unknown'
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'error_code': self.error_code.value,
            'severity': self.severity.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'recovery_strategy': self.recovery_strategy.value,
            'context': self.context,
            'caller_info': self.caller_info,
            'stack_trace': self.stack_trace,
            'original_exception': str(self.original_exception) if self.original_exception else None
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"[{self.error_code.value}] {self.severity.value}: {self.message}"

# WebDriver相关异常
class WebDriverError(StockInfoError):
    """WebDriver相关异常"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get('error_code', ErrorCode.WEBDRIVER_CONNECTION_ERROR),
            severity=kwargs.get('severity', ErrorSeverity.ERROR),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.RETRY),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

class WebDriverInitError(WebDriverError):
    """WebDriver初始化错误"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.WEBDRIVER_INIT_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.CRITICAL),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.RETRY),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

class WebDriverTimeoutError(WebDriverError):
    """WebDriver超时错误"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.WEBDRIVER_TIMEOUT_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.WARNING),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.RETRY),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

class WebDriverCrashError(WebDriverError):
    """WebDriver崩溃错误"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.WEBDRIVER_CRASH_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.CRITICAL),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.TERMINATE),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

class BrowserStrategyError(WebDriverError):
    """浏览器策略错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.WEBDRIVER_STRATEGY_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.ERROR),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.RETRY),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# 配置相关异常
class ConfigError(StockInfoError):
    """配置相关异常"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get('error_code', ErrorCode.CONFIG_FILE_ERROR),
            severity=kwargs.get('severity', ErrorSeverity.ERROR),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.NONE),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

class ConfigValidationError(ConfigError):
    """配置验证错误"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIG_VALIDATION_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.WARNING),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.NONE),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# 下载相关异常
class DownloadError(StockInfoError):
    """下载相关异常"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get('error_code', ErrorCode.DOWNLOAD_NETWORK_ERROR),
            severity=kwargs.get('severity', ErrorSeverity.ERROR),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.RETRY),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

class DownloadTimeoutError(DownloadError):
    """下载超时错误"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.DOWNLOAD_TIMEOUT_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.WARNING),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.RETRY),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

class DownloadRateLimitError(DownloadError):
    """下载速率限制错误"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.DOWNLOAD_RATE_LIMIT_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.WARNING),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.RETRY),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# 组织ID相关异常
class OrgIdError(StockInfoError):
    """组织ID获取异常"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get('error_code', ErrorCode.ORGID_FETCH_ERROR),
            severity=kwargs.get('severity', ErrorSeverity.ERROR),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.FALLBACK),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

class OrgIdValidationError(OrgIdError):
    """组织ID验证错误"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.ORGID_VALIDATION_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.WARNING),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.NONE),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# 网络相关异常
class NetworkError(StockInfoError):
    """网络相关异常"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get('error_code', ErrorCode.NETWORK_CONNECTION_ERROR),
            severity=kwargs.get('severity', ErrorSeverity.ERROR),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.RETRY),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

class NetworkTimeoutError(NetworkError):
    """网络超时错误"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.NETWORK_TIMEOUT_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.WARNING),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.RETRY),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# 文件系统相关异常
class FileSystemError(StockInfoError):
    """文件系统相关异常"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get('error_code', ErrorCode.FILE_NOT_FOUND_ERROR),
            severity=kwargs.get('severity', ErrorSeverity.ERROR),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.FALLBACK),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

class FilePermissionError(FileSystemError):
    """文件权限错误"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.FILE_PERMISSION_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.ERROR),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.NONE),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# 数据处理相关异常
class DataError(StockInfoError):
    """数据处理相关异常"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get('error_code', ErrorCode.DATA_PARSING_ERROR),
            severity=kwargs.get('severity', ErrorSeverity.ERROR),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.SKIP),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

class DataValidationError(DataError):
    """数据验证错误"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATA_VALIDATION_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.WARNING),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.SKIP),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# 验证相关异常
class ValidationError(StockInfoError):
    """验证相关异常"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get('error_code', ErrorCode.VALIDATION_INPUT_ERROR),
            severity=kwargs.get('severity', ErrorSeverity.WARNING),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.NONE),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# 错误处理器类
class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self.error_history: List[ErrorContext] = []
        self.recovery_handlers: Dict[ErrorCode, Callable] = {}
        self.max_history_size = 1000
    
    def register_recovery_handler(self, error_code: ErrorCode, handler: Callable):
        """注册错误恢复处理器"""
        self.recovery_handlers[error_code] = handler
    
    def handle_error(self, error: StockInfoError) -> bool:
        """处理错误"""
        try:
            # 记录错误历史
            self._record_error(error)
            
            # 记录错误上下文
            error.error_context.recovery_attempted = True
            
            # 尝试恢复
            recovery_success = False
            if error.recovery_strategy != RecoveryStrategy.NONE:
                recovery_success = self._attempt_recovery(error)
            
            error.error_context.recovery_successful = recovery_success
            
            # 记录错误日志
            self._log_error(error)
            
            return recovery_success
            
        except Exception as e:
            # 错误处理器本身出错
            print(f"Error handler failed: {e}")
            return False
    
    def _record_error(self, error: StockInfoError):
        """记录错误历史"""
        self.error_history.append(error.error_context)
        
        # 限制历史记录大小
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
    
    def _attempt_recovery(self, error: StockInfoError) -> bool:
        """尝试错误恢复"""
        try:
            # 查找注册的恢复处理器
            handler = self.recovery_handlers.get(error.error_code)
            if handler:
                return handler(error)
            
            # 默认恢复策略
            return self._default_recovery(error)
            
        except Exception as e:
            print(f"Recovery attempt failed: {e}")
            return False
    
    def _default_recovery(self, error: StockInfoError) -> bool:
        """默认恢复策略"""
        strategy = error.recovery_strategy
        
        if strategy == RecoveryStrategy.RETRY:
            # 简单延迟后重试
            time.sleep(min(2 ** len(self.error_history), 30))  # 指数退避
            return True
        elif strategy == RecoveryStrategy.SKIP:
            # 跳过当前操作
            return True
        elif strategy == RecoveryStrategy.FALLBACK:
            # 使用备用方案
            return True
        elif strategy == RecoveryStrategy.TERMINATE:
            # 终止程序
            sys.exit(1)
        
        return False
    
    def _log_error(self, error: StockInfoError):
        """记录错误日志"""
        try:
            # 这里可以集成日志系统
            error_dict = error.to_dict()
            
            # 根据严重级别选择输出方式
            if error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
                print(f"CRITICAL ERROR: {error_dict}")
            elif error.severity == ErrorSeverity.ERROR:
                print(f"ERROR: {error_dict}")
            elif error.severity == ErrorSeverity.WARNING:
                print(f"WARNING: {error_dict}")
            else:
                print(f"INFO: {error_dict}")
                
        except Exception as e:
            print(f"Failed to log error: {e}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        if not self.error_history:
            return {"total_errors": 0}
        
        error_codes = {}
        severities = {}
        modules = {}
        
        for context in self.error_history:
            # 按错误代码统计
            code = context.error_code.value
            error_codes[code] = error_codes.get(code, 0) + 1
            
            # 按严重级别统计
            severity = context.severity.value
            severities[severity] = severities.get(severity, 0) + 1
            
            # 按模块统计
            module = context.module
            modules[module] = modules.get(module, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "error_codes": error_codes,
            "severities": severities,
            "modules": modules,
            "recovery_rate": sum(1 for ctx in self.error_history if ctx.recovery_successful) / len(self.error_history)
        }

# 全局错误处理器实例
error_handler = ErrorHandler()

# 便捷函数
def handle_error(error: StockInfoError) -> bool:
    """便捷的错误处理函数"""
    return error_handler.handle_error(error)

def register_recovery_handler(error_code: ErrorCode, handler: Callable):
    """便捷的恢复处理器注册函数"""
    error_handler.register_recovery_handler(error_code, handler)

def get_error_statistics() -> Dict[str, Any]:
    """便捷的错误统计函数"""
    return error_handler.get_error_statistics()

# 装饰器
def with_error_handling(error_code: ErrorCode = ErrorCode.SYSTEM_ERROR,
                       severity: ErrorSeverity = ErrorSeverity.ERROR,
                       recovery_strategy: RecoveryStrategy = RecoveryStrategy.NONE,
                       max_retries: int = 0):
    """错误处理装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except StockInfoError as e:
                    last_error = e
                    if attempt < max_retries:
                        time.sleep(min(2 ** attempt, 10))  # 指数退避
                        continue
                    else:
                        # 如果已经是配置相关的错误，直接抛出原异常
                        if e.error_code.value.startswith('CFG_'):
                            raise e
                        # 转换为指定类型的错误
                        raise StockInfoError(
                            message=f"{func.__name__} failed after {max_retries + 1} attempts: {e}",
                            error_code=error_code,
                            severity=severity,
                            recovery_strategy=recovery_strategy,
                            context={"function": func.__name__, "args": str(args), "kwargs": str(kwargs)},
                            original_exception=e
                        )
                except Exception as e:
                    # 将普通异常转换为StockInfoError
                    raise StockInfoError(
                        message=f"Unexpected error in {func.__name__}: {e}",
                        error_code=error_code,
                        severity=severity,
                        recovery_strategy=recovery_strategy,
                        context={"function": func.__name__, "args": str(args), "kwargs": str(kwargs)},
                        original_exception=e
                    )
            
            raise last_error
        return wrapper
    return decorator