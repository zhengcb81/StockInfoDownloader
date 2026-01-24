"""
Structured Error Handling System
Provides comprehensive error classification, context management, and recovery mechanisms
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

# Import logger
try:
    from .logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Error Code Enum
class ErrorCode(Enum):
    """Error Code Enum"""
    # System Errors (1000-1999)
    SYSTEM_ERROR = "SYS_1000"
    INITIALIZATION_ERROR = "SYS_1001"
    RESOURCE_ERROR = "SYS_1002"
    
    # WebDriver Errors (2000-2999)
    WEBDRIVER_INIT_ERROR = "WD_2000"
    WEBDRIVER_CONNECTION_ERROR = "WD_2001"
    WEBDRIVER_TIMEOUT_ERROR = "WD_2002"
    WEBDRIVER_ELEMENT_ERROR = "WD_2003"
    WEBDRIVER_NAVIGATION_ERROR = "WD_2004"
    WEBDRIVER_SESSION_ERROR = "WD_2005"
    WEBDRIVER_CRASH_ERROR = "WD_2006"
    WEBDRIVER_STRATEGY_ERROR = "WD_2007"
    
    # Configuration Errors (3000-3999)
    CONFIG_FILE_ERROR = "CFG_3000"
    CONFIG_FILE_NOT_FOUND = "CFG_3001"
    CONFIG_FORMAT_ERROR = "CFG_3002"
    CONFIG_LOAD_ERROR = "CFG_3003"
    CONFIG_SAVE_ERROR = "CFG_3004"
    CONFIG_VALIDATION_ERROR = "CFG_3005"
    CONFIG_MISSING_ERROR = "CFG_3006"
    CONFIG_PATH_NOT_SET = "CFG_3007"
    
    # Download Errors (4000-4999)
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
    
    # Data Processing Errors (5000-5999)
    DATA_PARSING_ERROR = "DATA_5000"
    DATA_VALIDATION_ERROR = "DATA_5001"
    DATA_MAPPING_ERROR = "DATA_5002"
    DATA_STORAGE_ERROR = "DATA_5003"
    
    # Org ID Errors (6000-6999)
    ORGID_FETCH_ERROR = "ORG_6000"
    ORGID_VALIDATION_ERROR = "ORG_6001"
    ORGID_MAPPING_ERROR = "ORG_6002"
    
    # Network Errors (7000-7999)
    NETWORK_CONNECTION_ERROR = "NET_7000"
    NETWORK_TIMEOUT_ERROR = "NET_7001"
    NETWORK_HTTP_ERROR = "NET_7002"
    NETWORK_DNS_ERROR = "NET_7003"
    
    # File System Errors (8000-8999)
    FILE_NOT_FOUND_ERROR = "FILE_8000"
    FILE_PERMISSION_ERROR = "FILE_8001"
    FILE_DISK_SPACE_ERROR = "FILE_8002"
    FILE_FORMAT_ERROR = "FILE_8003"
    
    # Validation Errors (9000-9999)
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

# Error Severity Enum
class ErrorSeverity(Enum):
    """Error Severity"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"

# Error Recovery Strategy Enum
class RecoveryStrategy(Enum):
    """Error Recovery Strategy"""
    NONE = "NONE"  # No recovery
    RETRY = "RETRY"  # Retry
    FALLBACK = "FALLBACK"  # Fallback
    SKIP = "SKIP"  # Skip
    TERMINATE = "TERMINATE"  # Terminate
    MANUAL = "MANUAL"  # Manual handling

@dataclass
class ErrorContext:
    """Error Context Information"""
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
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['error_code'] = self.error_code.value
        data['severity'] = self.severity.value
        return data

class StockInfoError(Exception):
    """Base Exception Class"""
    
    def __init__(self, 
                 message: str,
                 error_code: ErrorCode = ErrorCode.SYSTEM_ERROR,
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 recovery_strategy: RecoveryStrategy = RecoveryStrategy.NONE,
                 context: Optional[Dict[str, Any]] = None,
                 original_exception: Optional[Exception] = None):
        """
        Initialize exception
        
        Args:
            message: Error message
            error_code: Error code
            severity: Error severity
            recovery_strategy: Recovery strategy
            context: Error context
            original_exception: Original exception
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.recovery_strategy = recovery_strategy
        self.context = context or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now()
        
        # Get stack trace info
        self.stack_trace = traceback.format_exc()
        self.caller_info = self._get_caller_info()
        
        # Create error context
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
        """Get caller info"""
        try:
            # Skip first few frames (exception construction and current frame)
            frame = sys._getframe(2)
            while frame:
                filename = frame.f_code.co_filename
                if 'src' in filename:  # Only care about project source
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
        """Convert to dictionary"""
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
        """String representation"""
        return f"[{self.error_code.value}] {self.severity.value}: {self.message}"

# WebDriver Related Exceptions
class WebDriverError(StockInfoError):
    """WebDriver related exceptions"""
    
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
    """WebDriver initialization error"""
    
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
    """WebDriver timeout error"""
    
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
    """WebDriver crash error"""
    
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
    """Browser strategy error"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.WEBDRIVER_STRATEGY_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.ERROR),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.RETRY),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# Configuration Related Exceptions
class ConfigError(StockInfoError):
    """Configuration related exceptions"""
    
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
    """Configuration validation error"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIG_VALIDATION_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.WARNING),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.NONE),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# Download Related Exceptions
class DownloadError(StockInfoError):
    """Download related exceptions"""
    
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
    """Download timeout error"""
    
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
    """Download rate limit error"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.DOWNLOAD_RATE_LIMIT_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.WARNING),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.RETRY),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# Org ID Related Exceptions
class OrgIdError(StockInfoError):
    """Org ID related exceptions"""
    
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
    """Org ID validation error"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.ORGID_VALIDATION_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.WARNING),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.NONE),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# Network Related Exceptions
class NetworkError(StockInfoError):
    """Network related exceptions"""
    
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
    """Network timeout error"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.NETWORK_TIMEOUT_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.WARNING),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.RETRY),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# File System Related Exceptions
class FileSystemError(StockInfoError):
    """File system related exceptions"""
    
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
    """File permission error"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.FILE_PERMISSION_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.ERROR),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.NONE),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# Data Processing Related Exceptions
class DataError(StockInfoError):
    """Data processing related exceptions"""
    
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
    """Data validation error"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATA_VALIDATION_ERROR,
            severity=kwargs.get('severity', ErrorSeverity.WARNING),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.SKIP),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# Validation Related Exceptions
class ValidationError(StockInfoError):
    """Validation related exceptions"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=kwargs.get('error_code', ErrorCode.VALIDATION_INPUT_ERROR),
            severity=kwargs.get('severity', ErrorSeverity.WARNING),
            recovery_strategy=kwargs.get('recovery_strategy', RecoveryStrategy.NONE),
            context=kwargs.get('context', {}),
            original_exception=kwargs.get('original_exception')
        )

# Error Handler Class
class ErrorHandler:
    """Error Handler"""
    
    def __init__(self):
        self.error_history: List[ErrorContext] = []
        self.recovery_handlers: Dict[ErrorCode, Callable] = {}
        self.max_history_size = 1000
    
    def register_recovery_handler(self, error_code: ErrorCode, handler: Callable):
        """Register error recovery handler"""
        self.recovery_handlers[error_code] = handler
    
    def handle_error(self, error: StockInfoError) -> bool:
        """Handle error"""
        try:
            # Record error history
            self._record_error(error)
            
            # Record error context
            error.error_context.recovery_attempted = True
            
            # Attempt recovery
            recovery_success = False
            if error.recovery_strategy != RecoveryStrategy.NONE:
                recovery_success = self._attempt_recovery(error)
            
            error.error_context.recovery_successful = recovery_success
            
            # Log error
            self._log_error(error)
            
            return recovery_success
            
        except Exception as e:
            # Error handler itself failed
            print(f"Error handler failed: {e}")
            return False
    
    def _record_error(self, error: StockInfoError):
        """Record error history"""
        self.error_history.append(error.error_context)
        
        # Limit history size
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
    
    def _attempt_recovery(self, error: StockInfoError) -> bool:
        """Attempt error recovery"""
        try:
            # Find registered recovery handler
            handler = self.recovery_handlers.get(error.error_code)
            if handler:
                return handler(error)
            
            # Default recovery strategy
            return self._default_recovery(error)
            
        except Exception as e:
            print(f"Recovery attempt failed: {e}")
            return False
    
    def _default_recovery(self, error: StockInfoError) -> bool:
        """Default recovery strategy"""
        strategy = error.recovery_strategy
        
        if strategy == RecoveryStrategy.RETRY:
            # Simple retry with backoff
            time.sleep(min(2 ** len(self.error_history), 30))  # Exponential backoff
            return True
        elif strategy == RecoveryStrategy.SKIP:
            # Skip current operation
            return True
        elif strategy == RecoveryStrategy.FALLBACK:
            # Use fallback
            return True
        elif strategy == RecoveryStrategy.TERMINATE:
            # Terminate program
            sys.exit(1)
        
        return False
    
    def _log_error(self, error: StockInfoError):
        """Log error"""
        try:
            # Here can integrate with logging system
            error_dict = error.to_dict()
            
            # Choose output method based on severity
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
        """Get error statistics"""
        if not self.error_history:
            return {"total_errors": 0}
        
        error_codes = {}
        severities = {}
        modules = {}
        
        for context in self.error_history:
            # Count by error code
            code = context.error_code.value
            error_codes[code] = error_codes.get(code, 0) + 1
            
            # Count by severity
            severity = context.severity.value
            severities[severity] = severities.get(severity, 0) + 1
            
            # Count by module
            module = context.module
            modules[module] = modules.get(module, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "error_codes": error_codes,
            "severities": severities,
            "modules": modules,
            "recovery_rate": sum(1 for ctx in self.error_history if ctx.recovery_successful) / len(self.error_history)
        }

# Global error handler instance
error_handler = ErrorHandler()

# Helper functions
def handle_error(error: StockInfoError) -> bool:
    """Helper error handling function"""
    return error_handler.handle_error(error)

def register_recovery_handler(error_code: ErrorCode, handler: Callable):
    """Helper recovery handler registration function"""
    error_handler.register_recovery_handler(error_code, handler)

def get_error_statistics() -> Dict[str, Any]:
    """Helper error statistics function"""
    return error_handler.get_error_statistics()

# Decorator
def with_error_handling(error_code: ErrorCode = ErrorCode.SYSTEM_ERROR,
                       severity: ErrorSeverity = ErrorSeverity.ERROR,
                       recovery_strategy: RecoveryStrategy = RecoveryStrategy.NONE,
                       max_retries: int = 0):
    """
    Enhanced error handling decorator

    Provides:
    1. Automatic retry mechanism (exponential backoff)
    2. Detailed error context logging
    3. Intelligent error type conversion
    4. Retry status tracking
    5. Performance monitoring

    Args:
        error_code: Error code
        severity: Error severity
        recovery_strategy: Recovery strategy
        max_retries: Maximum retries

    Returns:
        Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            start_time = time.time()
            attempt_details = []

            for attempt in range(max_retries + 1):
                attempt_start = time.time()
                try:
                    result = func(*args, **kwargs)

                    # If success after retry, log success info
                    if attempt > 0:
                        logger.info(
                            f"Function {func.__name__} executed successfully after {attempt + 1} attempts"
                        )

                    return result

                except StockInfoError as e:
                    last_error = e
                    attempt_time = time.time() - attempt_start

                    attempt_details.append({
                        'attempt': attempt + 1,
                        'error_code': e.error_code.value,
                        'error_type': type(e).__name__,
                        'message': str(e),
                        'duration': attempt_time
                    })

                    # Log detailed error info
                    logger.warning(
                        f"Function {func.__name__} attempt {attempt + 1}/{max_retries + 1} failed: "
                        f"[{e.error_code.value}] {e.message} (Duration: {attempt_time:.2f}s)"
                    )

                    # Determine if retry is needed
                    if attempt < max_retries:
                        # Exponential backoff delay, max 10 seconds
                        delay = min(2 ** attempt, 10)
                        logger.info(f"Retrying in {delay} seconds...")

                        # Skip delay in test environment
                        try:
                            from src.utils.browser_utils import is_test_environment
                            if not is_test_environment():
                                time.sleep(delay)
                        except ImportError:
                            # Conservative handling: skip delay if import fails
                            pass

                        continue
                    else:
                        # All retries failed
                        total_time = time.time() - start_time

                        # If config related error, raise original exception
                        if e.error_code.value.startswith('CFG_'):
                            logger.error(
                                f"Function {func.__name__} execution failed, config error unrecoverable: {e}"
                            )
                            raise e

                        # If subclass of StockInfoError (and not base class), raise original exception (preserve type and code)
                        if isinstance(e, StockInfoError) and type(e) != StockInfoError:
                            logger.error(
                                f"Function {func.__name__} failed after {max_retries + 1} attempts: {e}"
                            )
                            raise e

                        # Otherwise convert to specified error type, including retry history
                        raise StockInfoError(
                            message=f"{func.__name__} failed after {max_retries + 1} attempts: {e.message}",
                            error_code=error_code,
                            severity=severity,
                            recovery_strategy=recovery_strategy,
                            context={
                                "function": func.__name__,
                                "args": str(args)[:200],  # Limit length
                                "kwargs": str(kwargs)[:200],
                                "total_attempts": max_retries + 1,
                                "attempt_details": attempt_details,
                                "total_duration": total_time,
                                "final_error": str(e)
                            },
                            original_exception=e
                        )

                except Exception as e:
                    # Convert normal exception to StockInfoError
                    attempt_time = time.time() - attempt_start
                    total_time = time.time() - start_time

                    logger.error(
                        f"Function {func.__name__} unexpected error: {type(e).__name__}: {e}"
                    )

                    raise StockInfoError(
                        message=f"Function {func.__name__} execution unexpected error: {type(e).__name__}: {e}",
                        error_code=error_code,
                        severity=severity,
                        recovery_strategy=recovery_strategy,
                        context={
                            "function": func.__name__,
                            "args": str(args)[:200],
                            "kwargs": str(kwargs)[:200],
                            "total_duration": total_time,
                            "exception_type": type(e).__name__
                        },
                        original_exception=e
                    )

            # Should theoretically not reach here, but kept for completeness
            if last_error:
                raise last_error

            # If max_retries is 0 and no exception, return normally
            return None

        return wrapper
    return decorator