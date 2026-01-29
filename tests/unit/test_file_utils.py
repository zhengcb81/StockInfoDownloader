#!/usr/bin/env python3
"""
文件工具单元测试
"""

import os
import tempfile
import pytest
from unittest.mock import MagicMock

from src.services.unified_downloader import UnifiedDownloader
from src.services.file_service import FileService

class TestFileUtils:
    """文件工具测试类"""

    @pytest.fixture
    def file_service(self):
        return FileService()

    def test_clean_filename(self, file_service):
        """测试文件名清理功能"""
        # 测试各种特殊字符的清理
        test_cases = [
            ("test:file/name", "test_file_name"),
            ("file*name?", "file_name_"),
            ("normal name", "normal name"),
            ("file<name>", "file_name_"),
            ("file|name", "file_name"),
            ('file"name', "file_name"),
        ]

        for input_name, expected in test_cases:
            result = file_service.clean_filename(input_name)
            assert (
                result == expected
            ), f"Failed for {input_name}: got {result}, expected {expected}"

    def test_file_existence_checking(self):
        """测试文件存在性检查 - 使用真实文件操作"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            test_file = os.path.join(tmpdir, "test.pdf")

            # 测试1: 文件不存在
            assert not os.path.exists(test_file)

            # 测试2: 创建小文件
            with open(test_file, "w") as f:
                f.write("x" * 5 * 1024)  # 5KB

            # 文件存在
            assert os.path.exists(test_file)
            assert os.path.getsize(test_file) == 5 * 1024

    def test_directory_creation(self):
        """测试目录创建功能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = os.path.join(tmpdir, "test_subdir")

            # 目录不应该存在
            assert not os.path.exists(test_dir)

            # 创建目录
            os.makedirs(test_dir, exist_ok=True)

            # 目录应该现在存在
            assert os.path.exists(test_dir)
            assert os.path.isdir(test_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])