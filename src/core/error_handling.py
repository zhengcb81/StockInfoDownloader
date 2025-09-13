"""
异常处理最佳实践模块
提供统一的异常处理模式和工具
"""

import sys
import traceback
from typing import Dict, Any, Optional, Callable, Type
from functools import wraps
from .logger import get_logger
from .exceptions import StockDownloaderError


class ErrorHandler:
    """错误处理器"""

    def __init__(self, logger=None):
        """
        初始化错误处理器

        Args:
            logger: 日志记录器
        """
        self.logger = logger or get_logger(__name__)

    def handle_exception(self,
                        exception: Exception,
                        context: Optional[Dict[str, Any]] = None,
                        reraise: bool = True,
                        default_return: Any = None) -> Any:
        """
        统一异常处理

        Args:
            exception: 异常对象
            context: 上下文信息
            reraise: 是否重新抛出异常
            default_return: 默认返回值

        Returns:
            Any: 如果不重新抛出异常，返回默认值
        """
        # 构建错误信息
        error_info = self._build_error_info(exception, context)

        # 记录错误日志
        self._log_error(error_info)

        # 如果不重新抛出异常，返回默认值
        if not reraise:
            return default_return

        # 重新抛出异常
        raise exception

    def _build_error_info(self,
                          exception: Exception,
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        构建错误信息

        Args:
            exception: 异常对象
            context: 上下文信息

        Returns:
            Dict[str, Any]: 错误信息
        """
        error_info = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc(),
            'context': context or {}
        }

        # 添加系统信息
        error_info.update({
            'python_version': sys.version,
            'platform': sys.platform
        })

        return error_info

    def _log_error(self, error_info: Dict[str, Any]) -> None:
        """
        记录错误日志

        Args:
            error_info: 错误信息
        """
        error_msg = (
            f"异常类型: {error_info['exception_type']}\n"
            f"异常消息: {error_info['exception_message']}\n"
            f"上下文: {error_info['context']}"
        )

        if error_info['exception_type'] in ['TimeoutError', 'ConnectionError']:
            self.logger.warning(error_msg)
        else:
            self.logger.error(error_msg + f"\n堆栈跟踪:\n{error_info['traceback']}")


def with_error_handling(error_types: Optional[Type] = None,
                       context: Optional[Dict[str, Any]] = None,
                       reraise: bool = True,
                       default_return: Any = None,
                       log_level: str = 'error'):
    """
    错误处理装饰器

    Args:
        error_types: 要捕获的异常类型
        context: 上下文信息
        reraise: 是否重新抛出异常
        default_return: 默认返回值
        log_level: 日志级别

    Returns:
        Callable: 装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            error_context = context or {}
            error_context['function'] = func.__name__
            error_context['args'] = str(args)[:100]  # 限制参数长度
            error_context['kwargs'] = str(kwargs)[:100]

            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 检查是否在指定的异常类型中
                if error_types and not isinstance(e, error_types):
                    raise

                return error_handler.handle_exception(
                    exception=e,
                    context=error_context,
                    reraise=reraise,
                    default_return=default_return
                )

        return wrapper
    return decorator


class RetryHandler:
    """重试处理器"""

    def __init__(self,
                 max_attempts: int = 3,
                 delay: float = 1.0,
                 backoff_factor: float = 2.0,
                 exceptions: tuple = (Exception,)):
        """
        初始化重试处理器

        Args:
            max_attempts: 最大尝试次数
            delay: 初始延迟时间（秒）
            backoff_factor: 退避因子
            exceptions: 要重试的异常类型
        """
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.exceptions = exceptions
        self.logger = get_logger(__name__)

    def retry(self, func: Callable) -> Callable:
        """
        重试装饰器

        Args:
            func: 要重试的函数

        Returns:
            Callable: 装饰器函数
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, self.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except self.exceptions as e:
                    last_exception = e

                    if attempt == self.max_attempts:
                        self.logger.error(
                            f"函数 {func.__name__} 在 {self.max_attempts} 次尝试后仍然失败"
                        )
                        raise

                    # 计算延迟时间
                    current_delay = self.delay * (self.backoff_factor ** (attempt - 1))
                    self.logger.warning(
                        f"函数 {func.__name__} 第 {attempt} 次尝试失败，"
                        f"{current_delay:.2f} 秒后重试。错误: {e}"
                    )

                    import time
                    time.sleep(current_delay)

            # 如果所有尝试都失败，抛出最后一个异常
            raise last_exception

        return wrapper


class ResourceGuard:
    """资源守卫，确保资源正确释放"""

    def __init__(self):
        """初始化资源守卫"""
        self.resources = []
        self.logger = get_logger(__name__)

    def add_resource(self, resource: Any, cleanup_func: Callable) -> None:
        """
        添加需要清理的资源

        Args:
            resource: 资源对象
            cleanup_func: 清理函数
        """
        self.resources.append((resource, cleanup_func))
        self.logger.debug(f"添加资源到守卫: {type(resource).__name__}")

    def cleanup(self) -> None:
        """清理所有资源"""
        for resource, cleanup_func in reversed(self.resources):
            try:
                cleanup_func(resource)
                self.logger.debug(f"成功清理资源: {type(resource).__name__}")
            except Exception as e:
                self.logger.error(f"清理资源失败: {type(resource).__name__}, 错误: {e}")

        self.resources.clear()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup()


def safe_execute(func: Callable,
                 *args,
                 default_return: Any = None,
                 **kwargs) -> Any:
    """
    安全执行函数

    Args:
        func: 要执行的函数
        *args: 函数参数
        default_return: 默认返回值
        **kwargs: 函数关键字参数

    Returns:
        Any: 函数执行结果或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger = get_logger(__name__)
        logger.warning(f"安全执行函数 {func.__name__} 失败: {e}")
        return default_return


def validate_params(**param_validators):
    """
    参数验证装饰器

    Args:
        **param_validators: 参数验证器字典

    Returns:
        Callable: 装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取函数参数
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # 验证参数
            for param_name, validator in param_validators.items():
                if param_name in bound_args.arguments:
                    param_value = bound_args.arguments[param_name]
                    if not validator(param_value):
                        raise ValueError(f"参数 {param_name} 验证失败: {param_value}")

            return func(*args, **kwargs)

        return wrapper
    return decorator


# 常用的验证器函数
def validate_non_empty(value: str) -> bool:
    """验证非空字符串"""
    return isinstance(value, str) and value.strip() != ""


def validate_positive_number(value: (int, float)) -> bool:
    """验证正数"""
    return isinstance(value, (int, float)) and value > 0


def validate_file_exists(file_path: str) -> bool:
    """验证文件存在"""
    import os
    return os.path.exists(file_path)


def validate_url(url: str) -> bool:
    """验证URL格式"""
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return isinstance(url, str) and url_pattern.match(url) is not None