"""
Exception Handling Best Practices Module
Provides unified exception handling patterns and tools.

Note: This module provides a SIMPLE error handling stack (ErrorHandler, with_error_handling)
suitable for general-purpose use. For StockInfoError-based handling with retry/recovery,
use src.core.exceptions instead.
"""

import sys
import traceback
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type

from .logger import get_logger


class ErrorHandler:
    """Error Handler"""

    def __init__(self, logger: Optional[Any] = None) -> None:
        """
        Initialize ErrorHandler

        Args:
            logger: Logger instance
        """
        self.logger = logger or get_logger(__name__)

    def handle_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        reraise: bool = True,
        default_return: Any = None,
    ) -> Any:
        """
        Unified exception handling

        Args:
            exception: Exception object
            context: Context information
            reraise: Whether to re-raise exception
            default_return: Default return value

        Returns:
            Any: Default value if not re-raising
        """
        # Build error info
        error_info = self._build_error_info(exception, context)

        # Log error
        self._log_error(error_info)

        # Return default value if not re-raising
        if not reraise:
            return default_return

        # Re-raise exception
        raise exception

    def _build_error_info(
        self, exception: Exception, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build error info dictionary

        Args:
            exception: Exception object
            context: Context information

        Returns:
            Dict[str, Any]: Error information
        """
        error_info = {
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "traceback": traceback.format_exc(),
            "context": context or {},
        }

        # Add system info
        error_info.update({"python_version": sys.version, "platform": sys.platform})

        return error_info

    def _log_error(self, error_info: Dict[str, Any]) -> None:
        """
        Log error information

        Args:
            error_info: Error information
        """
        error_msg = (
            f"Exception Type: {error_info['exception_type']}\n"
            f"Exception Message: {error_info['exception_message']}\n"
            f"Context: {error_info['context']}"
        )

        if error_info["exception_type"] in ["TimeoutError", "ConnectionError"]:
            self.logger.warning(error_msg)
        else:
            self.logger.error(error_msg + f"\nTraceback:\n{error_info['traceback']}")


def with_error_handling(
    error_types: Optional[Type] = None,
    context: Optional[Dict[str, Any]] = None,
    reraise: bool = True,
    default_return: Any = None,
    log_level: str = "error",
) -> Callable[[Callable], Callable]:
    """
    Error handling decorator

    Args:
        error_types: Exception types to catch
        context: Context information
        reraise: Whether to re-raise
        default_return: Default return value
        log_level: Log level

    Returns:
        Callable: Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            error_handler = ErrorHandler()
            error_context = context or {}
            error_context["function"] = func.__name__
            error_context["args"] = str(args)[:100]  # Limit arg length
            error_context["kwargs"] = str(kwargs)[:100]

            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Check if in specified exception types
                if error_types and not isinstance(e, error_types):
                    raise

                return error_handler.handle_exception(
                    exception=e,
                    context=error_context,
                    reraise=reraise,
                    default_return=default_return,
                )

        return wrapper

    return decorator


class RetryHandler:
    """Retry Handler"""

    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        exceptions: tuple[type[BaseException], ...] = (Exception,),
    ):
        """
        Initialize RetryHandler

        Args:
            max_attempts: Max attempts
            delay: Initial delay (s)
            backoff_factor: Backoff factor
            exceptions: Exception types to retry
        """
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.exceptions = exceptions
        self.logger = get_logger(__name__)

    def retry(self, func: Callable) -> Callable:
        """
        Retry decorator

        Args:
            func: Function to retry

        Returns:
            Callable: Decorator function
        """

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: BaseException | None = None

            for attempt in range(1, self.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except self.exceptions as e:
                    last_exception = e

                    if attempt == self.max_attempts:
                        self.logger.error(
                            f"Function {func.__name__} still failed after {self.max_attempts} attempts"
                        )
                        raise e

                    # Calculate delay
                    current_delay = self.delay * (self.backoff_factor ** (attempt - 1))
                    self.logger.warning(
                        f"Function {func.__name__} attempt {attempt} failed, "
                        f"retrying in {current_delay:.2f}s. Error: {e}"
                    )

                    import time

                    time.sleep(current_delay)

            # Raise last exception if all attempts fail
            if last_exception is None:
                raise RuntimeError(
                    "Unexpected state: retry loop completed without exception"
                )
            raise last_exception

        return wrapper


class ResourceGuard:
    """Resource Guard ensures resources are properly released"""

    def __init__(self) -> None:
        """Initialize ResourceGuard"""
        self.resources: list = []
        self.logger = get_logger(__name__)

    def add_resource(self, resource: Any, cleanup_func: Callable) -> None:
        """
        Add resource to be cleaned up

        Args:
            resource: Resource object
            cleanup_func: Cleanup function
        """
        self.resources.append((resource, cleanup_func))
        self.logger.debug(f"Added resource to guard: {type(resource).__name__}")

    def cleanup(self) -> None:
        """Cleanup all resources"""
        for resource, cleanup_func in reversed(self.resources):
            try:
                cleanup_func(resource)
                self.logger.debug(
                    f"Successfully cleaned up resource: {type(resource).__name__}"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to cleanup resource: {type(resource).__name__}, Error: {e}"
                )

        self.resources.clear()

    def __enter__(self) -> "ResourceGuard":
        """Context manager entry"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit"""
        self.cleanup()


def safe_execute(
    func: Callable, *args: Any, default_return: Any = None, **kwargs: Any
) -> Any:
    """
    Safely execute a function

    Args:
        func: Function to execute
        *args: Positional arguments
        default_return: Default return value
        **kwargs: Keyword arguments

    Returns:
        Any: Function result or default value
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger = get_logger(__name__)
        logger.warning(f"Safe execute function {func.__name__} failed: {e}")
        return default_return


def validate_params(**param_validators: Any) -> Callable[[Callable], Callable]:
    """
    Parameter validation decorator

    Args:
        **param_validators: Parameter validator dictionary

    Returns:
        Callable: Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get function parameters
            import inspect

            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Validate parameters
            for param_name, validator in param_validators.items():
                if param_name in bound_args.arguments:
                    param_value = bound_args.arguments[param_name]
                    if not validator(param_value):
                        raise ValueError(
                            f"Parameter {param_name} validation failed: {param_value}"
                        )

            return func(*args, **kwargs)

        return wrapper

    return decorator


# Common validator functions
def validate_non_empty(value: str) -> bool:
    """Validate non-empty string"""
    return isinstance(value, str) and value.strip() != ""


def validate_positive_number(value: float) -> bool:
    """Validate positive number"""
    return isinstance(value, (int, float)) and value > 0


def validate_file_exists(file_path: str) -> bool:
    """Validate file existence"""
    import os

    return os.path.exists(file_path)


def validate_url(url: str) -> bool:
    """Validate URL format"""
    import re

    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)",
        re.IGNORECASE,
    )
    return isinstance(url, str) and url_pattern.match(url) is not None
