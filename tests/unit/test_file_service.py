#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FileService全面单元测试
测试文件服务的所有功能，包括文件处理、验证、清理等
"""

import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.config import ConfigManager
from src.services.file_service import FileService


class TestFileService:
    """FileService测试类"""

    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_config_manager = Mock(spec=ConfigManager)

        # 配置mock配置管理器
        self.test_config_manager.get.side_effect = lambda key, default=None: {
            "save_dir": "downloads",
            "files.allowed_extensions": [".pdf", ".txt", ".doc", ".docx"],
        }.get(key, default)

        self.test_config_manager.use_constants.return_value = r'[<>:"/\\|?*]'

        self.file_service = FileService(config_manager=self.test_config_manager)

    def teardown_method(self):
        """测试清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_init(self):
        """测试初始化"""
        # 测试默认初始化
        default_service = FileService()
        assert default_service.config_manager is not None
        assert default_service.logger is not None

        # 测试自定义配置管理器
        custom_service = FileService(config_manager=self.test_config_manager)
        assert custom_service.config_manager == self.test_config_manager

    def test_clean_filename(self):
        """测试文件名清理"""
        test_cases = [
            ("正常文件名.pdf", "正常文件名.pdf"),
            ("包含/斜杠.pdf", "包含_斜杠.pdf"),
            ("包含:冒号.pdf", "包含_冒号.pdf"),
            ("包含*星号.pdf", "包含_星号.pdf"),
            ("包含?问号.pdf", "包含_问号.pdf"),
            ('包含"引号.pdf', "包含_引号.pdf"),
            ("包含<小于号.pdf", "包含_小于号.pdf"),
            ("包含>大于号.pdf", "包含_大于号.pdf"),
            ("包含|竖线.pdf", "包含_竖线.pdf"),
        ]

        for input_name, expected in test_cases:
            result = self.file_service.clean_filename(input_name)
            assert result == expected

    def test_clean_filename_config_variants(self):
        """测试不同配置源下的 clean_filename"""
        # Case 1: ConfigManager with use_constants
        self.test_config_manager.use_constants.return_value = r'[x]'
        self.file_service.config_manager = self.test_config_manager
        assert self.file_service.clean_filename("axb") == "a_b"

        # Case 2: Dict config
        self.file_service.config_manager = {"INVALID_FILENAME_CHARS": r'[y]'}
        assert self.file_service.clean_filename("ayb") == "a_b"

        # Case 3: Exception/Fallback (mocking AttributeError on config_manager)
        mock_bad_config = Mock(spec=object)
        self.file_service.config_manager = mock_bad_config
        # Should fallback to default pattern (includes :)
        assert self.file_service.clean_filename("a:b") == "a_b"

    def test_get_stock_directory(self):
        """测试获取股票目录"""
        stock_code = "300470"
        stock_name = "中密控股"

        # 测试目录创建
        stock_dir = self.file_service.get_stock_directory(stock_code, stock_name)

        assert stock_dir.exists()
        assert stock_dir.name == "300470_中密控股"
        assert stock_dir.parent.name == "downloads"

        # 测试目录已存在的情况
        stock_dir2 = self.file_service.get_stock_directory(stock_code, stock_name)
        assert stock_dir2 == stock_dir

    def test_save_downloaded_file_success(self):
        """测试成功保存下载的文件"""
        # 创建源文件
        source_file = Path(self.temp_dir) / "source.pdf"
        source_file.write_text("测试文件内容")

        # 创建目标目录
        target_dir = Path(self.temp_dir) / "target"
        target_dir.mkdir()

        # 文档信息
        document_info = {
            "title": "投资者关系活动记录表",
            "date": "20240101",
            "file_type": "pdf",
        }

        # 保存文件
        result = self.file_service.save_downloaded_file(
            str(source_file), target_dir, "300470", document_info
        )

        assert result is not None
        assert Path(result).exists()
        assert Path(result).name == "300470_投资者关系活动记录表_20240101.pdf"

        # 验证源文件已被移动
        assert not source_file.exists()

    def test_save_downloaded_file_source_not_exists(self):
        """测试源文件不存在的情况"""
        target_dir = Path(self.temp_dir) / "target"
        target_dir.mkdir()

        document_info = {"title": "测试文档", "file_type": "pdf"}

        result = self.file_service.save_downloaded_file(
            "/nonexistent/file.pdf", target_dir, "300470", document_info
        )

        assert result is None

    def test_save_downloaded_file_exception(self):
        """测试保存文件时的异常处理"""
        # 创建源文件
        source_file = Path(self.temp_dir) / "source.pdf"
        source_file.write_text("测试内容")

        target_dir = Path(self.temp_dir) / "target"
        document_info = {"title": "测试", "file_type": "pdf"}

        # 模拟移动文件时出现异常
        with patch("shutil.move") as mock_move:
            mock_move.side_effect = Exception("移动文件失败")

            result = self.file_service.save_downloaded_file(
                str(source_file), target_dir, "300470", document_info
            )

            assert result is None

    def test_generate_filename(self):
        """测试文件名生成"""
        test_cases = [
            # 有日期的情况
            (
                {
                    "title": "投资者关系活动记录表",
                    "date": "20240115",
                    "file_type": "pdf",
                },
                "300470_投资者关系活动记录表_20240115.pdf",
            ),
            # 无日期的情况
            ({"title": "年度报告", "file_type": "pdf"}, "300470_年度报告.pdf"),
            # 包含特殊字符的标题
            (
                {"title": "测试/文档:名称", "date": "20240101", "file_type": "docx"},
                "300470_测试_文档_名称_20240101.docx",
            ),
        ]

        for document_info, expected in test_cases:
            result = self.file_service._generate_filename("300470", document_info)
            assert result == expected

    def test_validate_downloaded_file_success(self):
        """测试文件验证成功"""
        # 创建有效文件
        valid_file = Path(self.temp_dir) / "valid.pdf"
        valid_file.write_text("x" * 1024)  # 1KB文件

        result = self.file_service.validate_downloaded_file(str(valid_file))
        assert result is True

    def test_validate_downloaded_file_with_expected_size(self):
        """测试带预期大小的文件验证"""
        # 创建文件
        test_file = Path(self.temp_dir) / "test.pdf"
        content = "x" * 2048  # 2KB
        test_file.write_text(content)

        # 测试大小匹配
        result = self.file_service.validate_downloaded_file(
            str(test_file), expected_size=2048
        )
        assert result is True

        # 测试大小不匹配
        result = self.file_service.validate_downloaded_file(
            str(test_file), expected_size=1024
        )
        assert result is False

    def test_validate_downloaded_file_not_exists(self):
        """测试文件不存在的情况"""
        result = self.file_service.validate_downloaded_file("/nonexistent/file.pdf")
        assert result is False

    def test_validate_downloaded_file_empty(self):
        """测试空文件"""
        empty_file = Path(self.temp_dir) / "empty.pdf"
        empty_file.write_text("")  # 空文件

        result = self.file_service.validate_downloaded_file(str(empty_file))
        assert result is False

    def test_validate_downloaded_file_invalid_extension(self):
        """测试无效文件扩展名"""
        # 创建不支持的文件类型
        invalid_file = Path(self.temp_dir) / "test.exe"
        invalid_file.write_text("test")

        result = self.file_service.validate_downloaded_file(str(invalid_file))
        assert result is False

    def test_cleanup_temp_files(self):
        """测试临时文件清理"""
        # 创建测试目录
        test_dir = Path(self.temp_dir) / "downloads"
        test_dir.mkdir()

        # 创建不同年龄的文件
        current_time = datetime.now()

        # 新文件（1小时前）
        new_file = test_dir / "new.pdf"
        new_file.write_text("新文件")
        new_file_stat = new_file.stat()
        os.utime(
            new_file,
            (new_file_stat.st_atime, (current_time - timedelta(hours=1)).timestamp()),
        )

        # 旧文件（25小时前）
        old_file = test_dir / "old.pdf"
        old_file.write_text("旧文件")
        old_file_stat = old_file.stat()
        os.utime(
            old_file,
            (old_file_stat.st_atime, (current_time - timedelta(hours=25)).timestamp()),
        )

        # 执行清理（最大年龄24小时）
        cleaned_count = self.file_service.cleanup_temp_files(
            str(test_dir), max_age_hours=24
        )

        # 验证结果
        assert cleaned_count == 1
        assert not old_file.exists()  # 旧文件应被删除
        assert new_file.exists()  # 新文件应保留

    def test_cleanup_temp_files_nonexistent_dir(self):
        """测试清理不存在的目录"""
        cleaned_count = self.file_service.cleanup_temp_files("/nonexistent/directory")
        assert cleaned_count == 0

    def test_cleanup_temp_files_exception(self):
        """测试清理文件时的异常处理"""
        # 创建测试目录
        test_dir = Path(self.temp_dir) / "test"
        test_dir.mkdir()

        # 模拟删除文件时出现异常
        with patch("pathlib.Path.unlink") as mock_unlink:
            mock_unlink.side_effect = Exception("删除失败")

            cleaned_count = self.file_service.cleanup_temp_files(str(test_dir))
            assert cleaned_count == 0

    def test_get_file_info_success(self):
        """测试成功获取文件信息"""
        # 创建测试文件
        test_file = Path(self.temp_dir) / "test.pdf"
        test_file.write_text("测试内容")

        file_info = self.file_service.get_file_info(str(test_file))

        assert file_info["name"] == "test.pdf"
        assert file_info["size"] > 0
        assert file_info["extension"] == ".pdf"
        assert "created_time" in file_info
        assert "modified_time" in file_info
        assert "path" in file_info

    def test_get_file_info_not_exists(self):
        """测试获取不存在的文件信息"""
        file_info = self.file_service.get_file_info("/nonexistent/file.pdf")
        assert file_info == {}

    def test_get_file_info_exception(self):
        """测试获取文件信息时的异常处理"""
        # 创建测试文件
        test_file = Path(self.temp_dir) / "test.pdf"
        test_file.write_text("test")

        # 模拟获取文件信息时出现异常
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.side_effect = Exception("获取文件信息失败")

            file_info = self.file_service.get_file_info(str(test_file))
            assert file_info == {}

    def test_backup_file_success(self):
        """测试成功备份文件"""
        # 创建源文件
        source_file = Path(self.temp_dir) / "source.pdf"
        source_file.write_text("源文件内容")

        # 备份目录
        backup_dir = Path(self.temp_dir) / "backup"

        # 执行备份
        backup_path = self.file_service.backup_file(str(source_file), str(backup_dir))

        assert backup_path is not None
        assert Path(backup_path).exists()
        assert backup_dir.exists()

        # 验证备份文件内容
        backup_content = Path(backup_path).read_text()
        assert backup_content == "源文件内容"

    def test_backup_file_source_not_exists(self):
        """测试备份不存在的源文件"""
        backup_dir = Path(self.temp_dir) / "backup"

        result = self.file_service.backup_file(
            "/nonexistent/source.pdf", str(backup_dir)
        )
        assert result is None

    def test_backup_file_exception(self):
        """测试备份文件时的异常处理"""
        # 创建源文件
        source_file = Path(self.temp_dir) / "source.pdf"
        source_file.write_text("test")

        backup_dir = Path(self.temp_dir) / "backup"

        # 模拟复制文件时出现异常
        with patch("shutil.copy2") as mock_copy:
            mock_copy.side_effect = Exception("复制失败")

            result = self.file_service.backup_file(str(source_file), str(backup_dir))
            assert result is None

    def test_error_handling_consistency(self):
        """测试错误处理的一致性"""
        # 测试各种错误情况

        # 文件不存在的情况
        result = self.file_service.save_downloaded_file(
            "/nonexistent/file.pdf", Path("/tmp"), "300470", {}
        )
        assert result is None

        # 文件验证失败
        result = self.file_service.validate_downloaded_file("/nonexistent/file.pdf")
        assert result is False

        # 获取文件信息失败
        result = self.file_service.get_file_info("/nonexistent/file.pdf")
        assert result == {}

        # 备份文件失败
        result = self.file_service.backup_file("/nonexistent/file.pdf", "/tmp")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
