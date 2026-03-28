#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
错误处理模块 (error_handling.py) 单元测试
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from src.core.error_handling import (
    ErrorHandler,
    ResourceGuard,
    RetryHandler,
    safe_execute,
    validate_non_empty,
    validate_params,
    validate_positive_number,
    validate_url,
    with_error_handling,
)


class TestErrorHandler:
    """测试 ErrorHandler 类"""

    def test_init_default_logger(self):
        """测试默认初始化"""
        handler = ErrorHandler()
        assert handler.logger is not None

    def test_init_custom_logger(self):
        """测试自定义 logger"""
        mock_logger = MagicMock()
        handler = ErrorHandler(mock_logger)
        assert handler.logger is mock_logger

    def test_handle_exception_reraise(self):
        """测试重新抛出异常"""
        handler = ErrorHandler()
        exception = ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            handler.handle_exception(exception, reraise=True)

    def test_handle_exception_no_reraise(self):
        """测试不重新抛出异常"""
        handler = ErrorHandler()
        exception = ValueError("Test error")

        result = handler.handle_exception(
            exception, reraise=False, default_return="default"
        )

        assert result == "default"

    def test_handle_exception_with_context(self):
        """测试带上下文的异常处理"""
        handler = ErrorHandler()
        context = {"key": "value"}

        with pytest.raises(ValueError):
            handler.handle_exception(
                ValueError("Test"), context=context, reraise=True
            )

    def test_build_error_info(self):
        """测试构建错误信息"""
        handler = ErrorHandler()
        exception = ValueError("Test error")
        context = {"operation": "test"}

        error_info = handler._build_error_info(exception, context)

        assert error_info["exception_type"] == "ValueError"
        assert error_info["exception_message"] == "Test error"
        assert error_info["context"] == context
        assert "traceback" in error_info
        assert "python_version" in error_info
        assert "platform" in error_info

    def test_log_error_timeout(self):
        """测试超时类型错误的日志"""
        mock_logger = MagicMock()
        handler = ErrorHandler(mock_logger)

        error_info = {
            "exception_type": "TimeoutError",
            "exception_message": "Timeout",
            "context": {},
            "traceback": "",
        }

        handler._log_error(error_info)

        mock_logger.warning.assert_called_once()

    def test_log_error_connection(self):
        """测试连接类型错误的日志"""
        mock_logger = MagicMock()
        handler = ErrorHandler(mock_logger)

        error_info = {
            "exception_type": "ConnectionError",
            "exception_message": "Connection failed",
            "context": {},
            "traceback": "",
        }

        handler._log_error(error_info)

        mock_logger.warning.assert_called_once()

    def test_log_error_other(self):
        """测试其他类型错误的日志"""
        mock_logger = MagicMock()
        handler = ErrorHandler(mock_logger)

        error_info = {
            "exception_type": "ValueError",
            "exception_message": "Invalid value",
            "context": {},
            "traceback": "traceback here",
        }

        handler._log_error(error_info)

        mock_logger.error.assert_called_once()


class TestWithErrorHandling:
    """测试 with_error_handling 装饰器"""

    def test_successful_function(self):
        """测试成功函数"""

        @with_error_handling()
        def success_func():
            return "success"

        result = success_func()
        assert result == "success"

    def test_failed_function_reraise(self):
        """测试失败函数重新抛出"""

        @with_error_handling(reraise=True)
        def fail_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            fail_func()

    def test_failed_function_no_reraise(self):
        """测试失败函数不重新抛出"""

        @with_error_handling(reraise=False, default_return="default")
        def fail_func():
            raise ValueError("Test error")

        result = fail_func()
        assert result == "default"

    def test_specific_error_types(self):
        """测试特定错误类型"""

        @with_error_handling(error_types=ValueError, reraise=False, default_return="caught")
        def fail_func():
            raise ValueError("Test error")

        result = fail_func()
        assert result == "caught"

    def test_unmatched_error_type(self):
        """测试不匹配的错误类型"""

        @with_error_handling(error_types=TypeError, reraise=False, default_return="caught")
        def fail_func():
            raise ValueError("Test error")

        # ValueError 不在指定的 error_types 中，应该重新抛出
        with pytest.raises(ValueError):
            fail_func()

    def test_with_context(self):
        """测试带上下文的装饰器"""

        @with_error_handling(context={"operation": "test"}, reraise=False, default_return="default")
        def fail_func():
            raise ValueError("Test error")

        result = fail_func()
        assert result == "default"


class TestRetryHandler:
    """测试 RetryHandler 类"""

    def test_init(self):
        """测试初始化"""
        handler = RetryHandler()
        assert handler.max_attempts == 3
        assert handler.delay == 1.0
        assert handler.backoff_factor == 2.0

    def test_init_custom(self):
        """测试自定义初始化"""
        handler = RetryHandler(max_attempts=5, delay=0.5, backoff_factor=1.5)
        assert handler.max_attempts == 5
        assert handler.delay == 0.5
        assert handler.backoff_factor == 1.5

    def test_retry_success_first_attempt(self):
        """测试第一次就成功"""
        handler = RetryHandler()

        @handler.retry
        def success_func():
            return "success"

        result = success_func()
        assert result == "success"

    def test_retry_success_second_attempt(self):
        """测试第二次成功"""
        handler = RetryHandler(delay=0.01)
        call_count = [0]

        @handler.retry
        def eventual_success():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("Not yet")
            return "success"

        result = eventual_success()
        assert result == "success"
        assert call_count[0] == 2

    def test_retry_all_attempts_fail(self):
        """测试所有尝试都失败"""
        handler = RetryHandler(max_attempts=2, delay=0.01)

        @handler.retry
        def always_fail():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_fail()

    def test_retry_specific_exception(self):
        """测试特定异常类型"""
        handler = RetryHandler(
            max_attempts=2, delay=0.01, exceptions=(ValueError,)
        )

        @handler.retry
        def fail_with_value_error():
            raise ValueError("Value error")

        with pytest.raises(ValueError):
            fail_with_value_error()

    def test_retry_unmatched_exception(self):
        """测试不匹配的异常类型立即抛出"""
        handler = RetryHandler(
            max_attempts=3, delay=0.01, exceptions=(ValueError,)
        )

        @handler.retry
        def fail_with_type_error():
            raise TypeError("Type error")

        # TypeError 不在 exceptions 中，应该立即抛出
        with pytest.raises(TypeError):
            fail_with_type_error()


class TestResourceGuard:
    """测试 ResourceGuard 类"""

    def test_init(self):
        """测试初始化"""
        guard = ResourceGuard()
        assert guard.resources == []

    def test_add_resource(self):
        """测试添加资源"""
        guard = ResourceGuard()
        resource = MagicMock()

        guard.add_resource(resource, lambda r: r.close())

        assert len(guard.resources) == 1

    def test_cleanup(self):
        """测试清理资源"""
        guard = ResourceGuard()
        resource1 = MagicMock()
        resource2 = MagicMock()

        guard.add_resource(resource1, lambda r: r.close())
        guard.add_resource(resource2, lambda r: r.close())

        guard.cleanup()

        resource1.close.assert_called_once()
        resource2.close.assert_called_once()
        assert guard.resources == []

    def test_cleanup_in_reverse_order(self):
        """测试按逆序清理资源"""
        guard = ResourceGuard()
        call_order = []

        def cleanup1(r):
            call_order.append(1)

        def cleanup2(r):
            call_order.append(2)

        guard.add_resource("r1", cleanup1)
        guard.add_resource("r2", cleanup2)

        guard.cleanup()

        assert call_order == [2, 1]

    def test_cleanup_with_error(self):
        """测试清理时发生错误"""
        guard = ResourceGuard()

        def failing_cleanup(r):
            raise Exception("Cleanup error")

        guard.add_resource("resource", failing_cleanup)

        # 不应该抛出异常
        guard.cleanup()

    def test_context_manager(self):
        """测试上下文管理器"""
        resource = MagicMock()

        with ResourceGuard() as guard:
            guard.add_resource(resource, lambda r: r.close())

        resource.close.assert_called_once()

    def test_context_manager_with_exception(self):
        """测试上下文管理器中的异常"""
        resource = MagicMock()

        with pytest.raises(ValueError):
            with ResourceGuard() as guard:
                guard.add_resource(resource, lambda r: r.close())
                raise ValueError("Test error")

        # 即使发生异常，资源也应该被清理
        resource.close.assert_called_once()


class TestSafeExecute:
    """测试 safe_execute 函数"""

    def test_successful_execution(self):
        """测试成功执行"""

        def add(a, b):
            return a + b

        result = safe_execute(add, 1, 2)
        assert result == 3

    def test_failed_execution(self):
        """测试失败执行"""

        def fail():
            raise ValueError("Test error")

        result = safe_execute(fail, default_return="default")
        assert result == "default"

    def test_with_kwargs(self):
        """测试带关键字参数"""

        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = safe_execute(greet, "World", greeting="Hi")
        assert result == "Hi, World!"


class TestValidateParams:
    """测试 validate_params 装饰器"""

    def test_valid_params(self):
        """测试有效参数"""

        @validate_params(name=lambda x: len(x) > 0)
        def greet(name):
            return f"Hello, {name}"

        result = greet("World")
        assert result == "Hello, World"

    def test_invalid_params(self):
        """测试无效参数"""

        @validate_params(name=lambda x: len(x) > 0)
        def greet(name):
            return f"Hello, {name}"

        with pytest.raises(ValueError, match="validation failed"):
            greet("")

    def test_multiple_params(self):
        """测试多个参数"""

        @validate_params(
            name=lambda x: len(x) > 0,
            age=lambda x: x > 0,
        )
        def describe(name, age):
            return f"{name} is {age} years old"

        result = describe("Alice", 30)
        assert result == "Alice is 30 years old"

    def test_with_default_params(self):
        """测试带默认值的参数"""

        @validate_params(value=lambda x: x > 0)
        def process(value=10):
            return value * 2

        result = process()
        assert result == 20


class TestValidatorFunctions:
    """测试验证器函数"""

    def test_validate_non_empty_valid(self):
        """测试有效非空字符串"""
        assert validate_non_empty("hello") is True

    def test_validate_non_empty_empty(self):
        """测试空字符串"""
        assert validate_non_empty("") is False

    def test_validate_non_empty_whitespace(self):
        """测试空白字符串"""
        assert validate_non_empty("   ") is False

    def test_validate_non_empty_not_string(self):
        """测试非字符串"""
        assert validate_non_empty(123) is False

    def test_validate_positive_number_valid(self):
        """测试有效正数"""
        assert validate_positive_number(5) is True
        assert validate_positive_number(3.14) is True

    def test_validate_positive_number_zero(self):
        """测试零"""
        assert validate_positive_number(0) is False

    def test_validate_positive_number_negative(self):
        """测试负数"""
        assert validate_positive_number(-5) is False

    def test_validate_positive_number_not_number(self):
        """测试非数字"""
        assert validate_positive_number("string") is False

    def test_validate_url_valid_http(self):
        """测试有效 HTTP URL"""
        assert validate_url("http://example.com") is True

    def test_validate_url_valid_https(self):
        """测试有效 HTTPS URL"""
        assert validate_url("https://example.com/path") is True

    def test_validate_url_valid_localhost(self):
        """测试有效 localhost URL"""
        assert validate_url("http://localhost:8080") is True

    def test_validate_url_valid_ip(self):
        """测试有效 IP URL"""
        assert validate_url("http://192.168.1.1") is True

    def test_validate_url_invalid_no_protocol(self):
        """测试无效 URL（无协议）"""
        assert validate_url("example.com") is False

    def test_validate_url_invalid_not_string(self):
        """测试无效 URL（非字符串）"""
        assert validate_url(123) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
