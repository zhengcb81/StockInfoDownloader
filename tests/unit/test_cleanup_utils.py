#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""清理工具测试"""

import pytest
import tempfile
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.cleanup_utils import safe_cleanup, cleanup_directory, cleanup_file


class TestCleanupUtils:
    """清理工具测试"""

    def setup_method(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """清理临时目录"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_safe_cleanup_success(self):
        """测试安全清理成功"""
        executed = []

        def cleanup_func():
            executed.append(True)

        result = safe_cleanup(cleanup_func)
        assert result is True
        assert len(executed) == 1

    def test_safe_cleanup_with_message(self):
        """测试带错误信息的安全清理"""
        executed = []

        def cleanup_func():
            executed.append(True)

        result = safe_cleanup(cleanup_func, "自定义错误信息")
        assert result is True
        assert len(executed) == 1

    def test_safe_cleanup_failure(self):
        """测试安全清理失败"""
        def cleanup_func():
            raise ValueError("清理失败")

        result = safe_cleanup(cleanup_func, "自定义错误信息")
        assert result is False

    def test_safe_cleanup_none_func(self):
        """测试None函数"""
        with pytest.raises(TypeError):
            safe_cleanup(None)

    def test_cleanup_directory_success(self):
        """测试目录清理成功"""
        # 创建测试目录和文件
        test_dir = os.path.join(self.temp_dir, "test_subdir")
        os.makedirs(test_dir)
        test_file = os.path.join(test_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test")

        assert os.path.exists(test_dir)
        assert os.path.exists(test_file)

        # 清理
        result = cleanup_directory(test_dir)
        assert result is True
        assert not os.path.exists(test_dir)

    def test_cleanup_directory_none(self):
        """测试清理None目录"""
        result = cleanup_directory(None)
        assert result is True

    def test_cleanup_directory_nonexistent(self):
        """测试清理不存在的目录"""
        nonexistent_dir = os.path.join(self.temp_dir, "nonexistent")
        result = cleanup_directory(nonexistent_dir)
        assert result is True

    def test_cleanup_directory_nested(self):
        """测试清理嵌套目录"""
        nested_dir = os.path.join(self.temp_dir, "level1", "level2", "level3")
        os.makedirs(nested_dir)
        test_file = os.path.join(nested_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test")

        assert os.path.exists(test_file)

        result = cleanup_directory(os.path.join(self.temp_dir, "level1"))
        assert result is True
        assert not os.path.exists(os.path.join(self.temp_dir, "level1"))

    def test_cleanup_file_success(self):
        """测试文件清理成功"""
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test")

        assert os.path.exists(test_file)

        result = cleanup_file(test_file)
        assert result is True
        assert not os.path.exists(test_file)

    def test_cleanup_file_none(self):
        """测试清理None文件"""
        result = cleanup_file(None)
        assert result is True

    def test_cleanup_file_nonexistent(self):
        """测试清理不存在的文件"""
        nonexistent_file = os.path.join(self.temp_dir, "nonexistent.txt")
        result = cleanup_file(nonexistent_file)
        assert result is True

    def test_cleanup_file_permission_error(self):
        """测试文件清理权限错误（模拟）"""
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test")

        # 模拟权限错误
        def failing_cleanup():
            raise PermissionError("Permission denied")

        # 使用mock来测试异常处理
        from unittest.mock import patch
        with patch('os.remove', side_effect=failing_cleanup):
            result = cleanup_file(test_file)
            assert result is False

    def test_safe_cleanup_preserves_exception_details(self):
        """测试安全清理保留异常信息"""
        import logging
        from unittest.mock import patch

        def cleanup_func():
            raise RuntimeError("测试异常")

        # 捕获日志输出
        with patch('src.utils.cleanup_utils.logger') as mock_logger:
            result = safe_cleanup(cleanup_func, "清理失败")

            # 验证返回False
            assert result is False

            # 验证logger.warning被调用，包含错误信息
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "清理失败" in call_args
            assert "测试异常" in call_args


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
