"""
增强错误处理和重试机制模块
提供智能重试、错误分类、熔断器等功能
"""

import asyncio
import functools
import random
import threading
import time
import traceback
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, cast

from src.core.logger import get_logger


class ErrorSeverity(Enum):
    """错误严重程度"""

    LOW = "low"  # 低严重度，可以忽略
    MEDIUM = "medium"  # 中等严重度，需要记录
    HIGH = "high"  # 高严重度，需要立即处理
    CRITICAL = "critical"  # 严重错误，需要中断操作


class ErrorCategory(Enum):
    """错误类别"""

    NETWORK = "network"  # 网络相关错误
    TIMEOUT = "timeout"  # 超时错误
    AUTHENTICATION = "auth"  # 认证错误
    PERMISSION = "permission"  # 权限错误
    VALIDATION = "validation"  # 验证错误
    BUSINESS = "business"  # 业务逻辑错误
    SYSTEM = "system"  # 系统错误
    EXTERNAL = "external"  # 外部服务错误
    CRITICAL = "critical"  # 严重错误
    UNKNOWN = "unknown"  # 未知错误


class RetryStrategy(Enum):
    """重试策略"""

    FIXED = "fixed"  # 固定间隔
    EXPONENTIAL = "exponential"  # 指数退避
    LINEAR = "linear"  # 线性增加
    RANDOM = "random"  # 随机间隔
    ADAPTIVE = "adaptive"  # 自适应间隔


@dataclass
class ErrorInfo:
    """错误信息"""

    exception: Exception
    error_type: str
    error_category: ErrorCategory
    severity: ErrorSeverity
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    traceback: str = ""
    retry_count: int = 0
    should_retry: bool = True


@dataclass
class RetryConfig:
    """重试配置"""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    jitter_range: Tuple[float, float] = (0.8, 1.2)
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    non_retryable_exceptions: Tuple[Type[Exception], ...] = ()


class CircuitBreakerState(Enum):
    """熔断器状态"""

    CLOSED = "closed"  # 关闭状态，正常工作
    OPEN = "open"  # 开启状态，快速失败
    HALF_OPEN = "half_open"  # 半开状态，尝试恢复


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""

    failure_threshold: int = 5  # 失败阈值
    recovery_timeout: float = 60.0  # 恢复超时时间
    expected_exception: Tuple[Type[Exception], ...] = (Exception,)
    half_open_max_calls: int = 3  # 半开状态最大调用次数


class ErrorClassifier:
    """错误分类器"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.error_patterns = {
            ErrorCategory.NETWORK: [
                "ConnectionError",
                "TimeoutError",
                "NetworkError",
                "requests.exceptions.ConnectionError",
                "requests.exceptions.Timeout",
                "selenium.common.exceptions.WebDriverException",
            ],
            ErrorCategory.TIMEOUT: [
                "TimeoutError",
                "Timeout",
                "time out",
                "requests.exceptions.Timeout",
            ],
            ErrorCategory.AUTHENTICATION: [
                "AuthenticationError",
                "Unauthorized",
                "401",
                "403",
                "LoginError",
                "AuthError",
            ],
            ErrorCategory.PERMISSION: [
                "PermissionError",
                "AccessDenied",
                "Forbidden",
                "403",
            ],
            ErrorCategory.VALIDATION: [
                "ValidationError",
                "ValueError",
                "TypeError",
                "InvalidInput",
                "FormatError",
            ],
            ErrorCategory.SYSTEM: ["MemoryError", "OSError", "IOError", "SystemError"],
        }

    def classify_error(
        self, exception: Exception, context: Optional[Dict[str, Any]] = None
    ) -> ErrorInfo:
        """
        分类错误

        Args:
            exception: 异常对象
            context: 上下文信息

        Returns:
            ErrorInfo: 错误信息
        """
        error_type = type(exception).__name__
        error_message = str(exception).lower()

        # 确定错误类别
        category = ErrorCategory.UNKNOWN
        for error_category, patterns in self.error_patterns.items():
            if any(
                pattern.lower() in error_type.lower()
                or pattern.lower() in error_message
                for pattern in patterns
            ):
                category = error_category
                break

        # 确定严重程度
        severity = self._determine_severity(category, exception, context)

        # 获取堆栈跟踪
        traceback_str = "".join(
            traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
        )

        # 判断是否应该重试
        should_retry = self._should_retry_error(category, severity, exception)

        return ErrorInfo(
            exception=exception,
            error_type=error_type,
            error_category=category,
            severity=severity,
            context=context or {},
            traceback=traceback_str,
            should_retry=should_retry,
        )

    def _determine_severity(
        self,
        category: ErrorCategory,
        exception: Exception,
        context: Optional[Dict[str, Any]],
    ) -> ErrorSeverity:
        """确定错误严重程度"""
        if category in [ErrorCategory.SYSTEM, ErrorCategory.CRITICAL]:
            return ErrorSeverity.CRITICAL
        elif category in [ErrorCategory.AUTHENTICATION, ErrorCategory.PERMISSION]:
            return ErrorSeverity.HIGH
        elif category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT]:
            return ErrorSeverity.MEDIUM
        elif category == ErrorCategory.BUSINESS:
            return ErrorSeverity.LOW
        else:
            return ErrorSeverity.MEDIUM

    def _should_retry_error(
        self, category: ErrorCategory, severity: ErrorSeverity, exception: Exception
    ) -> bool:
        """判断错误是否应该重试"""
        # 高严重度和严重错误通常不应该重试
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            return False

        # 某些类别的错误适合重试
        if category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT]:
            return True

        # 系统错误通常不适合重试
        if category == ErrorCategory.SYSTEM:
            return False

        # 认证和权限错误不适合重试
        if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.PERMISSION]:
            return False

        # 其他情况默认可以重试
        return True


class RetryManager:
    """重试管理器"""

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        初始化重试管理器

        Args:
            config: 重试配置
        """
        self.config = config or RetryConfig()
        self.logger = get_logger(__name__)
        self.error_classifier = ErrorClassifier()
        self.retry_stats: Dict[str, int] = defaultdict(int)

    def calculate_delay(self, attempt: int, error_info: ErrorInfo) -> float:
        """
        计算重试延迟

        Args:
            attempt: 重试次数
            error_info: 错误信息

        Returns:
            float: 延迟时间（秒）
        """
        if attempt == 0:
            return 0.0

        base_delay = self.config.base_delay

        if self.config.strategy == RetryStrategy.FIXED:
            delay = base_delay
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = base_delay * (self.config.backoff_factor ** (attempt - 1))
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = base_delay * attempt
        elif self.config.strategy == RetryStrategy.RANDOM:
            delay = random.uniform(base_delay, self.config.max_delay)
        elif self.config.strategy == RetryStrategy.ADAPTIVE:
            # 基于错误类型自适应调整
            if error_info.error_category == ErrorCategory.NETWORK:
                delay = base_delay * (self.config.backoff_factor ** (attempt - 1))
            else:
                delay = base_delay * attempt
        else:
            delay = base_delay

        # 应用最大延迟限制
        delay = min(delay, self.config.max_delay)

        # 添加抖动
        if self.config.jitter:
            jitter_min, jitter_max = self.config.jitter_range
            delay = delay * random.uniform(jitter_min, jitter_max)

        return delay

    def should_retry(self, error_info: ErrorInfo, attempt: int) -> bool:
        """
        判断是否应该重试

        Args:
            error_info: 错误信息
            attempt: 当前重试次数

        Returns:
            bool: 是否应该重试
        """
        # 检查重试次数限制
        if attempt >= self.config.max_retries:
            return False

        # 检查错误类型是否允许重试
        if not error_info.should_retry:
            return False

        # 检查异常类型
        if isinstance(error_info.exception, self.config.non_retryable_exceptions):
            return False

        if not isinstance(error_info.exception, self.config.retryable_exceptions):
            return False

        return True

    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行带重试的函数

        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            Any: 函数执行结果

        Raises:
            Exception: 最后一次失败时的异常
        """
        last_error = None

        for attempt in range(self.config.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                # 成功，更新统计
                self.retry_stats["success"] += 1
                return result

            except Exception as e:
                # 分类错误
                error_info = self.error_classifier.classify_error(
                    e,
                    {
                        "function": func.__name__,
                        "attempt": attempt,
                        "args": str(args)[:100],
                        "kwargs": str(kwargs)[:100],
                    },
                )
                error_info.retry_count = attempt

                # 记录错误
                self._log_error(error_info)

                # 检查是否应该重试
                if not self.should_retry(error_info, attempt):
                    self.retry_stats["final_failure"] += 1
                    raise e

                last_error = e

                # 计算延迟并等待
                delay = self.calculate_delay(attempt + 1, error_info)
                if delay > 0:
                    self.logger.info(
                        f"等待 {delay:.2f}s 后重试 (尝试 {attempt + 1}/{self.config.max_retries})"
                    )
                    time.sleep(delay)

        # 重试次数用完，抛出最后一个错误
        self.retry_stats["max_retries_exceeded"] += 1
        if last_error is not None:
            raise last_error
        raise RuntimeError("All retry attempts failed but no exception was captured")

    async def execute_with_retry_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        异步执行带重试的函数

        Args:
            func: 要执行的异步函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            Any: 函数执行结果

        Raises:
            Exception: 最后一次失败时的异常
        """
        last_error = None

        for attempt in range(self.config.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                self.retry_stats["success"] += 1
                return result

            except Exception as e:
                error_info = self.error_classifier.classify_error(
                    e,
                    {
                        "function": func.__name__,
                        "attempt": attempt,
                        "args": str(args)[:100],
                        "kwargs": str(kwargs)[:100],
                    },
                )
                error_info.retry_count = attempt

                self._log_error(error_info)

                if not self.should_retry(error_info, attempt):
                    self.retry_stats["final_failure"] += 1
                    raise e

                last_error = e

                delay = self.calculate_delay(attempt + 1, error_info)
                if delay > 0:
                    self.logger.info(
                        f"异步等待 {delay:.2f}s 后重试 (尝试 {attempt + 1}/{self.config.max_retries})"
                    )
                    await asyncio.sleep(delay)

        self.retry_stats["max_retries_exceeded"] += 1
        if last_error is not None:
            raise last_error
        raise RuntimeError("All retry attempts failed but no exception was captured")

    def _log_error(self, error_info: ErrorInfo):
        """记录错误日志"""
        log_method = {
            ErrorSeverity.LOW: self.logger.debug,
            ErrorSeverity.MEDIUM: self.logger.warning,
            ErrorSeverity.HIGH: self.logger.error,
            ErrorSeverity.CRITICAL: self.logger.critical,
        }.get(error_info.severity, self.logger.error)

        log_method(
            f"错误: {error_info.error_type} ({error_info.error_category.value}) - "
            f"重试次数: {error_info.retry_count} - "
            f"消息: {str(error_info.exception)[:200]}"
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取重试统计信息"""
        total_attempts = sum(self.retry_stats.values())
        success_rate = (self.retry_stats["success"] / max(total_attempts, 1)) * 100

        return {
            "retry_stats": dict(self.retry_stats),
            "total_attempts": total_attempts,
            "success_rate": success_rate,
            "config": {
                "max_retries": self.config.max_retries,
                "strategy": self.config.strategy.value,
                "base_delay": self.config.base_delay,
            },
        }


class CircuitBreaker:
    """熔断器"""

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        """
        初始化熔断器

        Args:
            config: 熔断器配置
        """
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.half_open_calls = 0
        self.lock = threading.Lock()
        self.logger = get_logger(__name__)

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        调用函数（带熔断保护）

        Args:
            func: 要调用的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            Any: 函数执行结果

        Raises:
            Exception: 熔断器开启时的异常或函数执行异常
        """
        with self.lock:
            current_state = self.state

            if current_state == CircuitBreakerState.OPEN:
                # 检查是否可以尝试恢复
                if time.time() - self.last_failure_time > self.config.recovery_timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.half_open_calls = 0
                    self.logger.info("熔断器状态从 OPEN 转为 HALF_OPEN")
                else:
                    raise Exception("熔断器开启，服务暂时不可用")

            elif current_state == CircuitBreakerState.HALF_OPEN:
                self.half_open_calls += 1
                if self.half_open_calls > self.config.half_open_max_calls:
                    self.state = CircuitBreakerState.OPEN
                    self.logger.info("熔断器状态从 HALF_OPEN 转为 OPEN")
                    raise Exception("熔断器开启，服务暂时不可用")

        try:
            result = func(*args, **kwargs)

            # 成功调用，重置状态
            with self.lock:
                if self.state != CircuitBreakerState.CLOSED:
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    self.logger.info("熔断器状态重置为 CLOSED")

            return result

        except Exception as e:
            # 检查是否是预期的异常
            if isinstance(e, self.config.expected_exception):
                with self.lock:
                    self.failure_count += 1
                    self.last_failure_time = time.time()

                    if (
                        self.failure_count >= self.config.failure_threshold
                        and self.state == CircuitBreakerState.CLOSED
                    ):
                        self.state = CircuitBreakerState.OPEN
                        self.logger.warning(
                            f"熔断器开启 (失败次数: {self.failure_count})"
                        )

            raise e

    def get_state(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        with self.lock:
            return {
                "state": self.state.value,
                "failure_count": self.failure_count,
                "last_failure_time": self.last_failure_time,
                "half_open_calls": self.half_open_calls,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "half_open_max_calls": self.config.half_open_max_calls,
                },
            }


class EnhancedErrorHandler:
    """增强错误处理器"""

    def __init__(self):
        """
        初始化增强错误处理器
        """
        self.logger = get_logger(__name__)
        self.error_classifier = ErrorClassifier()
        self.retry_manager = RetryManager()
        self.circuit_breakers = {}
        self.error_history: deque[ErrorInfo] = deque(maxlen=1000)  # 保留最近1000个错误
        self.error_stats = defaultdict(int)
        self.lock = threading.Lock()

    def handle_error(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        circuit_breaker_key: Optional[str] = None,
    ) -> ErrorInfo:
        """
        处理错误

        Args:
            exception: 异常对象
            context: 上下文信息
            circuit_breaker_key: 熔断器键

        Returns:
            ErrorInfo: 错误信息
        """
        # 分类错误
        error_info = self.error_classifier.classify_error(exception, context)

        # 记录错误历史
        with self.lock:
            self.error_history.append(error_info)
            self.error_stats[error_info.error_category] += 1

        # 记录错误日志
        self._log_error(error_info)

        # 触发错误处理策略
        self._trigger_error_handlers(error_info)

        return cast(ErrorInfo, error_info)

    def execute_with_protection(
        self,
        func: Callable,
        *args,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_key: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        带保护的函数执行

        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            retry_config: 重试配置
            circuit_breaker_key: 熔断器键

        Returns:
            Any: 函数执行结果
        """
        # 获取或创建熔断器
        circuit_breaker = None
        if circuit_breaker_key:
            if circuit_breaker_key not in self.circuit_breakers:
                self.circuit_breakers[circuit_breaker_key] = CircuitBreaker()
            circuit_breaker = self.circuit_breakers[circuit_breaker_key]

        # 创建重试管理器
        retry_manager = (
            RetryManager(retry_config) if retry_config else self.retry_manager
        )

        def protected_func():
            if circuit_breaker:
                return circuit_breaker.call(func, *args, **kwargs)
            else:
                return func(*args, **kwargs)

        try:
            return retry_manager.execute_with_retry(protected_func)
        except Exception as e:
            error_info = self.handle_error(
                e,
                {
                    "function": func.__name__,
                    "circuit_breaker_key": circuit_breaker_key,
                    "args": str(args)[:100],
                    "kwargs": str(kwargs)[:100],
                },
            )
            raise e

    async def execute_with_protection_async(
        self,
        func: Callable,
        *args,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_key: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        异步带保护的函数执行

        Args:
            func: 要执行的异步函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            retry_config: 重试配置
            circuit_breaker_key: 熔断器键

        Returns:
            Any: 函数执行结果
        """
        circuit_breaker = None
        if circuit_breaker_key:
            if circuit_breaker_key not in self.circuit_breakers:
                self.circuit_breakers[circuit_breaker_key] = CircuitBreaker()
            circuit_breaker = self.circuit_breakers[circuit_breaker_key]

        retry_manager = (
            RetryManager(retry_config) if retry_config else self.retry_manager
        )

        async def protected_func():
            if circuit_breaker:
                return await asyncio.get_event_loop().run_in_executor(
                    None, circuit_breaker.call, func, *args, **kwargs
                )
            else:
                return await func(*args, **kwargs)

        try:
            return await retry_manager.execute_with_retry_async(protected_func)
        except Exception as e:
            error_info = self.handle_error(
                e,
                {
                    "function": func.__name__,
                    "circuit_breaker_key": circuit_breaker_key,
                    "args": str(args)[:100],
                    "kwargs": str(kwargs)[:100],
                },
            )
            raise e

    def _log_error(self, error_info: ErrorInfo):
        """记录错误日志"""
        log_method = {
            ErrorSeverity.LOW: self.logger.debug,
            ErrorSeverity.MEDIUM: self.logger.warning,
            ErrorSeverity.HIGH: self.logger.error,
            ErrorSeverity.CRITICAL: self.logger.critical,
        }.get(error_info.severity, self.logger.error)

        log_method(
            f"错误处理: {error_info.error_type} ({error_info.error_category.value}) - "
            f"严重程度: {error_info.severity.value} - "
            f"消息: {str(error_info.exception)[:200]}"
        )

    def _trigger_error_handlers(self, error_info: ErrorInfo):
        """触发错误处理策略"""
        # 这里可以添加自定义的错误处理逻辑
        # 例如：发送告警、记录到外部系统等

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        with self.lock:
            return {
                "error_categories": {
                    category.value: count
                    for category, count in self.error_stats.items()
                },
                "total_errors": sum(self.error_stats.values()),
                "recent_errors": len(self.error_history),
                "circuit_breakers": {
                    key: breaker.get_state()
                    for key, breaker in self.circuit_breakers.items()
                },
                "retry_stats": self.retry_manager.get_stats(),
            }

    def get_error_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取错误历史"""
        with self.lock:
            recent_errors = list(self.error_history)[-limit:]
            return [
                {
                    "timestamp": error.timestamp,
                    "error_type": error.error_type,
                    "category": error.error_category.value,
                    "severity": error.severity.value,
                    "message": str(error.exception)[:200],
                    "retry_count": error.retry_count,
                    "context": error.context,
                }
                for error in recent_errors
            ]


# 装饰器模式
def error_protected(
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_key: Optional[str] = None,
):
    """
    错误保护装饰器

    Args:
        retry_config: 重试配置
        circuit_breaker_key: 熔断器键
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = get_global_error_handler()
            return handler.execute_with_protection(
                func,
                *args,
                **kwargs,
                retry_config=retry_config,
                circuit_breaker_key=circuit_breaker_key,
            )

        return wrapper

    return decorator


def error_protected_async(
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_key: Optional[str] = None,
):
    """
    异步错误保护装饰器

    Args:
        retry_config: 重试配置
        circuit_breaker_key: 熔断器键
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            handler = get_global_error_handler()
            return await handler.execute_with_protection_async(
                func,
                *args,
                **kwargs,
                retry_config=retry_config,
                circuit_breaker_key=circuit_breaker_key,
            )

        return wrapper

    return decorator


# 全局错误处理器实例
_global_error_handler: Optional[EnhancedErrorHandler] = None
_error_handler_lock = threading.Lock()


def get_global_error_handler() -> EnhancedErrorHandler:
    """获取全局错误处理器实例"""
    global _global_error_handler
    if _global_error_handler is None:
        with _error_handler_lock:
            if _global_error_handler is None:
                _global_error_handler = EnhancedErrorHandler()
    return _global_error_handler


# 便捷函数
def handle_error(
    exception: Exception, context: Optional[Dict[str, Any]] = None
) -> ErrorInfo:
    """便捷函数：处理错误"""
    return get_global_error_handler().handle_error(exception, context)


def execute_with_protection(
    func: Callable,
    *args,
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_key: Optional[str] = None,
    **kwargs,
) -> Any:
    """便捷函数：带保护的函数执行"""
    return get_global_error_handler().execute_with_protection(
        func,
        *args,
        **kwargs,
        retry_config=retry_config,
        circuit_breaker_key=circuit_breaker_key,
    )
