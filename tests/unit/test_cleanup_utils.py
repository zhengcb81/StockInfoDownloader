#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CleanupUtils 模块测试
提升 src/utils/cleanup_utils.py 模块的测试覆盖率
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.cleanup_utils import (
    safe_cleanup,
    cleanup_directory,
    cleanup_file,
    cleanup_path,
    cleanup_multiple_paths,
    cleanup_temp_files,
    cleanup_empty_directories,
    get_directory_size,
    cleanup_large_files,
    safe_remove_tree,
    safe_move_file,
    safe_copy_file,
)


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
        with open(test_file, "w") as f:
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
        with open(test_file, "w") as f:
            f.write("test")

        assert os.path.exists(test_file)

        result = cleanup_directory(os.path.join(self.temp_dir, "level1"))
        assert result is True
        assert not os.path.exists(os.path.join(self.temp_dir, "level1"))

    def test_cleanup_file_success(self):
        """测试文件清理成功"""
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, "w") as f:
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
        with open(test_file, "w") as f:
            f.write("test")

        # 模拟权限错误
        def failing_cleanup():
            raise PermissionError("Permission denied")

        # 使用mock来测试异常处理
        from unittest.mock import patch

        with patch("os.remove", side_effect=failing_cleanup):
            result = cleanup_file(test_file)
            assert result is False

    def test_safe_cleanup_preserves_exception_details(self):
        """测试安全清理保留异常信息"""
        from unittest.mock import patch

        def cleanup_func():
            raise RuntimeError("测试异常")

        # 捕获日志输出
        with patch("src.utils.cleanup_utils.logger") as mock_logger:
            result = safe_cleanup(cleanup_func, "清理失败")

            # 验证返回False
            assert result is False

            # 验证logger.warning被调用，包含错误信息
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "清理失败" in call_args
            assert "测试异常" in call_args


class TestSafeCleanupTypeErrors:
    """测试 safe_cleanup 类型错误"""

    def test_safe_cleanup_non_callable(self):
        """测试传入非可调用对象"""
        with pytest.raises(TypeError, match="cleanup_func必须是可调用对象"):
            safe_cleanup("not_a_function")


class TestCleanupPath:
    """测试 cleanup_path 函数"""

    def test_cleanup_path_none(self):
        """测试清理 None 路径"""
        result = cleanup_path(None)
        assert result is True

    def test_cleanup_path_file(self):
        """测试清理文件路径"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            result = cleanup_path(temp_path)
            assert result is True
            assert not temp_path.exists()
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_cleanup_path_directory(self):
        """测试清理目录路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)
            result = cleanup_path(temp_path)
            assert result is True

    def test_cleanup_path_nonexistent(self):
        """测试清理不存在的路径"""
        temp_path = Path("/nonexistent/path")
        result = cleanup_path(temp_path)
        assert result is True


class TestCleanupMultiplePaths:
    """测试 cleanup_multiple_paths 函数"""

    def test_cleanup_multiple_paths_empty(self):
        """测试清理空路径列表"""
        result = cleanup_multiple_paths([])
        assert result is True

    def test_cleanup_multiple_paths_strings(self):
        """测试清理字符串路径列表"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件和目录
            test_file = os.path.join(tmpdir, "test.txt")
            test_dir = os.path.join(tmpdir, "test_dir")
            os.makedirs(test_dir)

            with open(test_file, "w") as f:
                f.write("test")

            result = cleanup_multiple_paths([test_file, test_dir])
            assert result is True
            assert not os.path.exists(test_file)
            assert not os.path.exists(test_dir)

    def test_cleanup_multiple_paths_path_objects(self):
        """测试清理 Path 对象列表"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")

            result = cleanup_multiple_paths([test_file])
            assert result is True
            assert not test_file.exists()

    def test_cleanup_multiple_paths_nonexistent(self):
        """测试清理不存在的路径列表"""
        result = cleanup_multiple_paths(["/nonexistent1", "/nonexistent2"])
        assert result is True


class TestCleanupTempFiles:
    """测试 cleanup_temp_files 函数"""

    def test_cleanup_temp_files_none_directory(self):
        """测试清理 None 目录的临时文件"""
        result = cleanup_temp_files(None)
        assert result is True

    def test_cleanup_temp_files_nonexistent_directory(self):
        """测试清理不存在的目录"""
        result = cleanup_temp_files("/nonexistent/directory")
        assert result is True

    def test_cleanup_temp_files_default_extensions(self):
        """测试使用默认扩展名清理临时文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建临时文件
            temp_file = os.path.join(tmpdir, "test.tmp")
            with open(temp_file, "w") as f:
                f.write("temp content")

            # 创建一个正常文件
            normal_file = os.path.join(tmpdir, "normal.txt")
            with open(normal_file, "w") as f:
                f.write("normal content")

            result = cleanup_temp_files(tmpdir)
            assert result is True

            # 验证临时文件被清理
            assert not os.path.exists(temp_file)
            # 验证正常文件保留
            assert os.path.exists(normal_file)

    def test_cleanup_temp_files_custom_extensions(self):
        """测试使用自定义扩展名清理临时文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            temp_file = os.path.join(tmpdir, "test.bak")
            normal_file = os.path.join(tmpdir, "test.txt")

            with open(temp_file, "w") as f:
                f.write("temp")
            with open(normal_file, "w") as f:
                f.write("normal")

            result = cleanup_temp_files(tmpdir, extensions=[".bak"])
            assert result is True

            assert not os.path.exists(temp_file)
            assert os.path.exists(normal_file)


class TestCleanupEmptyDirectories:
    """测试 cleanup_empty_directories 函数"""

    def test_cleanup_empty_directories_none(self):
        """测试清理 None 目录的空目录"""
        result = cleanup_empty_directories(None)
        assert result is True

    def test_cleanup_empty_directories_nonexistent(self):
        """测试清理不存在的目录"""
        result = cleanup_empty_directories("/nonexistent/directory")
        assert result is True

    def test_cleanup_empty_directories_with_empty_dirs(self):
        """测试清理空目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建空子目录
            empty_dir = os.path.join(tmpdir, "empty")
            os.makedirs(empty_dir)

            # 创建非空目录
            nonempty_dir = os.path.join(tmpdir, "nonempty")
            os.makedirs(nonempty_dir)
            with open(os.path.join(nonempty_dir, "file.txt"), "w") as f:
                f.write("content")

            result = cleanup_empty_directories(tmpdir)
            assert result is True

            assert not os.path.exists(empty_dir)
            assert os.path.exists(nonempty_dir)


class TestGetDirectorySize:
    """测试 get_directory_size 函数"""

    def test_get_directory_size_none(self):
        """测试获取 None 目录的大小"""
        result = get_directory_size(None)
        assert result == 0

    def test_get_directory_size_nonexistent(self):
        """测试获取不存在目录的大小"""
        result = get_directory_size("/nonexistent/directory")
        assert result == 0

    def test_get_directory_size_empty(self):
        """测试获取空目录的大小"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_directory_size(tmpdir)
            assert result == 0

    def test_get_directory_size_with_files(self):
        """测试获取包含文件的目录大小"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            file1 = os.path.join(tmpdir, "file1.txt")
            file2 = os.path.join(tmpdir, "file2.txt")

            with open(file1, "w") as f:
                f.write("x" * 100)
            with open(file2, "w") as f:
                f.write("x" * 200)

            result = get_directory_size(tmpdir)
            assert result == 300


class TestCleanupLargeFiles:
    """测试 cleanup_large_files 函数"""

    def test_cleanup_large_files_none(self):
        """测试清理 None 目录的大文件"""
        result = cleanup_large_files(None)
        assert result is True

    def test_cleanup_large_files_nonexistent(self):
        """测试清理不存在目录的大文件"""
        result = cleanup_large_files("/nonexistent/directory")
        assert result is True

    def test_cleanup_large_files_default_threshold(self):
        """测试使用默认阈值清理大文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建小文件（不会被清理）
            small_file = os.path.join(tmpdir, "small.txt")
            with open(small_file, "w") as f:
                f.write("x" * 1000)

            result = cleanup_large_files(tmpdir, max_size_mb=1)
            assert result is True
            assert os.path.exists(small_file)


class TestSafeRemoveTree:
    """测试 safe_remove_tree 函数"""

    def test_safe_remove_tree_none(self):
        """测试删除 None 目录树"""
        result = safe_remove_tree(None)
        assert result is True

    def test_safe_remove_tree_nonexistent(self):
        """测试删除不存在的目录树"""
        result = safe_remove_tree("/nonexistent/directory")
        assert result is True

    def test_safe_remove_tree_existing(self):
        """测试删除现有目录树"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建嵌套结构
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)
            test_file = os.path.join(subdir, "test.txt")
            with open(test_file, "w") as f:
                f.write("content")

            result = safe_remove_tree(tmpdir)
            assert result is True
            assert not os.path.exists(tmpdir)


class TestSafeMoveFile:
    """测试 safe_move_file 函数"""

    def test_safe_move_file_nonexistent_source(self):
        """测试移动不存在的源文件"""
        result = safe_move_file("/nonexistent/source.txt", "/tmp/dest.txt")
        assert result is False

    def test_safe_move_file_success(self):
        """测试成功移动文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "source.txt")
            dest = os.path.join(tmpdir, "subdir", "dest.txt")

            with open(source, "w") as f:
                f.write("test content")

            result = safe_move_file(source, dest)
            assert result is True
            assert not os.path.exists(source)
            assert os.path.exists(dest)


class TestSafeCopyFile:
    """测试 safe_copy_file 函数"""

    def test_safe_copy_file_nonexistent_source(self):
        """测试复制不存在的源文件"""
        result = safe_copy_file("/nonexistent/source.txt", "/tmp/dest.txt")
        assert result is False

    def test_safe_copy_file_success(self):
        """测试成功复制文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "source.txt")
            dest = os.path.join(tmpdir, "subdir", "dest.txt")

            with open(source, "w") as f:
                f.write("test content")

            result = safe_copy_file(source, dest)
            assert result is True
            assert os.path.exists(source)  # 源文件应该保留
            assert os.path.exists(dest)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
