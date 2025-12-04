#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
错误处理系统测试
测试ErrorHandler、装饰器、重试机制等核心错误处理功能
"""

import pytest
import time
import sys
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.error_handling import (
    ErrorHandler,
    with_error_handling,
    RetryHandler,
    ResourceGuard,
    safe_execute,
    validate_params,
    validate_non_empty,
    validate_positive_number,
    validate_file_exists,
    validate_url
)
from pathlib import Path


class TestErrorHandler:
    """测试ErrorHandler类"""

    def test_initialization(self):
        """测试初始化"""
        handler = ErrorHandler()
        assert handler.logger is not None

        mock_logger = Mock()
        handler = ErrorHandler(logger=mock_logger)
        assert handler.logger == mock_logger

    def test_handle_exception_reraises(self):
        """测试处理异常并重新抛出"""
        handler = ErrorHandler()

        with pytest.raises(ValueError, match="test error"):
            handler.handle_exception(ValueError("test error"))

    def test_handle_exception_with_context(self):
        """测试带上下文的异常处理"""
        handler = ErrorHandler()
        mock_logger = Mock()
        handler.logger = mock_logger

        context = {"operation": "test", "data": "sample"}

        # 不重新抛出异常，返回默认值
        result = handler.handle_exception(
            ValueError("test error"),
            context=context,
            reraise=False,
            default_return="default"
        )

        assert result == "default"
        # 验证日志被调用
        assert mock_logger.error.called

    def test_build_error_info(self):
        """测试构建错误信息"""
        handler = ErrorHandler()

        error_info = handler._build_error_info(ValueError("test"), {"ctx": "value"})

        assert error_info["exception_type"] == "ValueError"
        assert error_info["exception_message"] == "test"
        assert error_info["context"] == {"ctx": "value"}
        assert "python_version" in error_info
        assert "platform" in error_info

    def test_log_error_warning_level(self):
        """测试日志记录警告级别"""
        handler = ErrorHandler()
        mock_logger = Mock()
        handler.logger = mock_logger

        error_info = {
            'exception_type': 'TimeoutError',
            'exception_message': 'timeout',
            'traceback': 'trace',
            'context': {}
        }

        handler._log_error(error_info)
        mock_logger.warning.assert_called_once()

    def test_log_error_error_level(self):
        """测试日志记录错误级别"""
        handler = ErrorHandler()
        mock_logger = Mock()
        handler.logger = mock_logger

        error_info = {
            'exception_type': 'ValueError',
            'exception_message': 'error',
            'traceback': 'trace',
            'context': {}
        }

        handler._log_error(error_info)
        mock_logger.error.assert_called_once()


class TestErrorHandlingDecorator:
    """测试错误处理装饰器"""

    def test_with_error_handling_success(self):
        """测试装饰器成功执行"""
        @with_error_handling()
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_with_error_handling_catches_exception(self):
        """测试装饰器捕获异常"""
        @with_error_handling(reraise=False, default_return="default")
        def test_func():
            raise ValueError("error")

        result = test_func()
        assert result == "default"

    def test_with_error_handling_specific_error_types(self):
        """测试装饰器捕获特定异常类型"""
        @with_error_handling(error_types=ValueError, reraise=False, default_return="default")
        def test_func():
            raise ValueError("error")

        result = test_func()
        assert result == "default"

    def test_with_error_handling_other_exception_reraises(self):
        """测试装饰器不捕获其他异常"""
        @with_error_handling(error_types=ValueError, reraise=True)
        def test_func():
            raise TypeError("type error")

        with pytest.raises(TypeError):
            test_func()

    def test_with_error_handling_context(self):
        """测试装饰器上下文"""
        mock_handler = Mock()
        mock_handler.handle_exception = Mock(return_value="default")

        with patch('src.core.error_handling.ErrorHandler', return_value=mock_handler):
            @with_error_handling(context={"test": "context"}, reraise=False)
            def test_func():
                raise ValueError("error")

            test_func()

            # 验证handle_exception被调用
            mock_handler.handle_exception.assert_called_once()
            call_context = mock_handler.handle_exception.call_args[1]["context"]
            assert call_context["test"] == "context"
            assert "function" in call_context


class TestRetryHandler:
    """测试重试处理器"""

    def test_initialization(self):
        """测试初始化"""
        handler = RetryHandler(max_attempts=5, delay=2.0, backoff_factor=3.0)

        assert handler.max_attempts == 5
        assert handler.delay == 2.0
        assert handler.backoff_factor == 3.0
        assert handler.exceptions == (Exception,)

    def test_retry_success_on_first_attempt(self):
        """测试第一次尝试成功"""
        handler = RetryHandler(max_attempts=3)
        mock_func = Mock(return_value="success")

        decorated = handler.retry(mock_func)
        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_success_on_second_attempt(self):
        """测试第二次尝试成功"""
        handler = RetryHandler(max_attempts=3)
        mock_func = Mock(side_effect=[ValueError("error"), "success"])
        mock_func.__name__ = "test_func"

        decorated = handler.retry(mock_func)
        result = decorated()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_fails_all_attempts(self):
        """测试所有尝试都失败"""
        handler = RetryHandler(max_attempts=2)
        mock_func = Mock(side_effect=ValueError("error"))
        mock_func.__name__ = "test_func"

        decorated = handler.retry(mock_func)

        with pytest.raises(ValueError):
            decorated()

        assert mock_func.call_count == 2

    def test_retry_with_specific_exceptions(self):
        """测试特定异常重试"""
        handler = RetryHandler(exceptions=(ValueError,))
        mock_func = Mock(side_effect=[ValueError("error"), "success"])
        mock_func.__name__ = "test_func"

        decorated = handler.retry(mock_func)
        result = decorated()

        assert result == "success"

    def test_retry_other_exception_not_retried(self):
        """测试其他异常不重试"""
        handler = RetryHandler(exceptions=(ValueError,))
        mock_func = Mock(side_effect=TypeError("type error"))
        mock_func.__name__ = "test_func"

        decorated = handler.retry(mock_func)

        with pytest.raises(TypeError):
            decorated()

        assert mock_func.call_count == 1


class TestResourceGuard:
    """测试资源守卫"""

    def test_initialization(self):
        """测试初始化"""
        guard = ResourceGuard()
        assert guard.resources == []
        assert guard.logger is not None

    def test_add_resource(self):
        """测试添加资源"""
        guard = ResourceGuard()
        mock_resource = Mock()
        mock_cleanup = Mock()

        guard.add_resource(mock_resource, mock_cleanup)

        assert len(guard.resources) == 1
        assert guard.resources[0] == (mock_resource, mock_cleanup)

    def test_cleanup(self):
        """测试清理资源"""
        guard = ResourceGuard()
        mock_resource1 = Mock()
        mock_cleanup1 = Mock()
        mock_resource2 = Mock()
        mock_cleanup2 = Mock()

        guard.add_resource(mock_resource1, mock_cleanup1)
        guard.add_resource(mock_resource2, mock_cleanup2)

        guard.cleanup()

        mock_cleanup1.assert_called_once_with(mock_resource1)
        mock_cleanup2.assert_called_once_with(mock_resource2)
        assert guard.resources == []

    def test_cleanup_reverse_order(self):
        """测试反向顺序清理"""
        guard = ResourceGuard()
        call_order = []

        def cleanup1(resource):
            call_order.append(1)

        def cleanup2(resource):
            call_order.append(2)

        guard.add_resource("res1", cleanup1)
        guard.add_resource("res2", cleanup2)

        guard.cleanup()

        assert call_order == [2, 1]  # 反向顺序

    def test_cleanup_with_exception(self):
        """测试清理时发生异常"""
        guard = ResourceGuard()
        mock_logger = Mock()
        guard.logger = mock_logger

        def failing_cleanup(resource):
            raise ValueError("cleanup failed")

        guard.add_resource("resource", failing_cleanup)

        # 不应该抛出异常
        guard.cleanup()

        mock_logger.error.assert_called_once()

    def test_context_manager(self):
        """测试上下文管理器"""
        guard = ResourceGuard()
        mock_cleanup = Mock()

        with guard as g:
            g.add_resource("resource", mock_cleanup)

        # 退出上下文时自动清理
        mock_cleanup.assert_called_once_with("resource")


class TestSafeExecute:
    """测试safe_execute函数"""

    def test_safe_execute_success(self):
        """测试安全执行成功"""
        mock_func = Mock(return_value="success")

        result = safe_execute(mock_func, "arg1", key="value")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", key="value")

    def test_safe_execute_failure(self):
        """测试安全执行失败"""
        mock_func = Mock(side_effect=ValueError("error"))
        mock_func.__name__ = "test_func"

        result = safe_execute(mock_func, default_return="default")

        assert result == "default"

    def test_safe_execute_custom_default(self):
        """测试自定义默认返回值"""
        mock_func = Mock(side_effect=ValueError("error"))
        mock_func.__name__ = "test_func"

        result = safe_execute(mock_func, default_return={"key": "value"})

        assert result == {"key": "value"}


class TestValidateParams:
    """测试参数验证装饰器"""

    def test_validate_params_success(self):
        """测试参数验证成功"""
        @validate_params(name=validate_non_empty, age=validate_positive_number)
        def test_func(name, age):
            return f"{name}:{age}"

        result = test_func("John", 30)
        assert result == "John:30"

    def test_validate_params_failure(self):
        """测试参数验证失败"""
        @validate_params(name=validate_non_empty)
        def test_func(name):
            return name

        with pytest.raises(ValueError, match="参数 name 验证失败"):
            test_func("")  # 空字符串

    def test_validate_params_with_defaults(self):
        """测试带默认值的参数验证"""
        @validate_params(threshold=validate_positive_number)
        def test_func(value, threshold=1.0):
            return value > threshold

        result = test_func(2.0)
        assert result is True

        # 验证默认值
        result = test_func(0.5)
        assert result is False


class TestValidatorFunctions:
    """测试验证器函数"""

    def test_validate_non_empty(self):
        """测试非空验证"""
        assert validate_non_empty("text") is True
        assert validate_non_empty("") is False
        assert validate_non_empty("   ") is False
        assert validate_non_empty(123) is False

    def test_validate_positive_number(self):
        """测试正数验证"""
        assert validate_positive_number(5) is True
        assert validate_positive_number(0) is False
        assert validate_positive_number(-1) is False
        assert validate_positive_number(3.14) is True
        assert validate_positive_number("5") is False

    def test_validate_file_exists(self):
        """测试文件存在验证"""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            assert validate_file_exists("/path/to/file") is True

            mock_exists.return_value = False
            assert validate_file_exists("/nonexistent") is False

    def test_validate_url(self):
        """测试URL验证"""
        assert validate_url("https://example.com") is True
        assert validate_url("http://example.com/path") is True
        assert validate_url("ftp://example.com") is False
        assert validate_url("not a url") is False
        assert validate_url("") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])