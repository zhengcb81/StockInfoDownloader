"""
FileService 测试模块
覆盖文件服务的各种功能
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.config import ConfigManager
from src.services.file_service import FileService


class TestFileService:
    """FileService 测试类"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def config_manager(self, temp_dir):
        """创建配置管理器"""
        config = ConfigManager()
        config.set("save_dir", temp_dir)
        return config

    @pytest.fixture
    def file_service(self, config_manager):
        """创建文件服务实例"""
        return FileService(config_manager)

    def test_init_with_config_manager(self, config_manager):
        """测试使用配置管理器初始化"""
        service = FileService(config_manager)
        assert service.config_manager == config_manager
        assert service.logger is not None

    def test_init_without_config_manager(self):
        """测试不使用配置管理器初始化"""
        service = FileService()
        assert service.config_manager is not None
        assert isinstance(service.config_manager, ConfigManager)

    def test_clean_filename_basic(self, file_service):
        """测试基本文件名清理"""
        # 测试非法字符替换
        assert file_service.clean_filename("test/file:name") == "test_file_name"
        assert file_service.clean_filename("test\\file:name") == "test_file_name"
        assert file_service.clean_filename('test"file:name') == "test_file_name"
        assert file_service.clean_filename("test*file?:name") == "test_file__name"
        assert file_service.clean_filename("test<file>name|") == "test_file_name_"

    def test_clean_filename_empty(self, file_service):
        """测试空文件名"""
        assert file_service.clean_filename("") == ""
        assert file_service.clean_filename("   ") == "   "

    def test_clean_filename_special_chars(self, file_service):
        """测试特殊字符处理"""
        assert file_service.clean_filename("正常文件名") == "正常文件名"
        assert file_service.clean_filename("file with spaces") == "file with spaces"
        assert file_service.clean_filename("file.with.dots") == "file.with.dots"

    def test_get_stock_directory(self, file_service, temp_dir):
        """测试获取股票目录"""
        stock_dir = file_service.get_stock_directory("000001", "测试股票")
        expected_dir = Path(temp_dir) / "000001_测试股票"
        assert stock_dir == expected_dir
        assert stock_dir.exists()
        assert stock_dir.is_dir()

    def test_get_stock_directory_with_special_chars(self, file_service, temp_dir):
        """测试包含特殊字符的股票名称"""
        stock_dir = file_service.get_stock_directory("000002", "测试*股票/名称")
        expected_dir = Path(temp_dir) / "000002_测试_股票_名称"
        assert stock_dir == expected_dir
        assert stock_dir.exists()

    def test_save_downloaded_file_success(self, file_service, temp_dir):
        """测试成功保存文件"""
        # 创建源文件
        source_dir = Path(temp_dir) / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_file = source_dir / "test.pdf"
        source_file.write_text("test content")

        # 创建目标目录
        target_dir = Path(temp_dir) / "target"
        target_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件
        document_info = {
            "title": "测试文档",
            "date": "2023-01-01",
            "file_type": "pdf"
        }
        result = file_service.save_downloaded_file(
            str(source_file),
            target_dir,
            "000001",
            document_info
        )

        assert result is not None
        assert Path(result).exists()
        assert not source_file.exists()  # 源文件应该被移动

    def test_save_downloaded_file_source_not_exist(self, file_service, temp_dir):
        """测试源文件不存在"""
        target_dir = Path(temp_dir) / "target"
        target_dir.mkdir(parents=True, exist_ok=True)

        result = file_service.save_downloaded_file(
            "non_existent.pdf",
            target_dir,
            "000001",
            {"title": "测试"}
        )

        assert result is None

    def test_generate_filename_with_date(self, file_service):
        """测试生成带日期的文件名"""
        document_info = {
            "title": "测试报告",
            "date": "2023-01-01",
            "file_type": "pdf"
        }
        filename = file_service._generate_filename("000001", document_info)
        assert filename == "000001_测试报告_2023-01-01.pdf"

    def test_generate_filename_without_date(self, file_service):
        """测试生成不带日期的文件名"""
        document_info = {
            "title": "测试报告",
            "file_type": "pdf"
        }
        filename = file_service._generate_filename("000001", document_info)
        assert filename == "000001_测试报告.pdf"

    def test_generate_filename_with_special_chars(self, file_service):
        """测试生成带特殊字符的文件名"""
        document_info = {
            "title": "测试/报告*名称",
            "date": "2023-01-01",
            "file_type": "pdf"
        }
        filename = file_service._generate_filename("000001", document_info)
        assert "000001" in filename
        assert "_2023-01-01.pdf" in filename
        assert "/" not in filename
        assert "*" not in filename

    def test_validate_downloaded_file_success(self, file_service, temp_dir):
        """测试验证文件成功"""
        # 创建测试文件
        test_file = Path(temp_dir) / "test.pdf"
        test_file.write_text("test content")

        result = file_service.validate_downloaded_file(str(test_file))
        assert result is True

    def test_validate_downloaded_file_not_exist(self, file_service):
        """测试验证不存在的文件"""
        result = file_service.validate_downloaded_file("non_existent.pdf")
        assert result is False

    def test_validate_downloaded_file_empty(self, file_service, temp_dir):
        """测试验证空文件"""
        test_file = Path(temp_dir) / "empty.pdf"
        test_file.write_text("")

        result = file_service.validate_downloaded_file(str(test_file))
        assert result is False

    def test_validate_downloaded_file_size_mismatch(self, file_service, temp_dir):
        """测试文件大小不匹配"""
        test_file = Path(temp_dir) / "test.pdf"
        test_file.write_text("test content")

        result = file_service.validate_downloaded_file(str(test_file), expected_size=9999)
        assert result is False

    def test_validate_downloaded_file_invalid_extension(self, file_service, temp_dir):
        """测试无效的文件扩展名"""
        test_file = Path(temp_dir) / "test.xyz"
        test_file.write_text("test content")

        result = file_service.validate_downloaded_file(str(test_file))
        assert result is False

    def test_cleanup_temp_files(self, file_service, temp_dir):
        """测试清理临时文件"""
        # 创建一些测试文件
        (Path(temp_dir) / "old_file.txt").write_text("old")

        # 创建一个新文件
        new_file = Path(temp_dir) / "new_file.txt"
        new_file.write_text("new")
        # 设置文件的修改时间为当前
        new_file.touch()

        # 清理超过1小时的文件
        import time
        old_time = time.time() - 7200  # 2小时前
        os.utime(Path(temp_dir) / "old_file.txt", (old_time, old_time))

        cleaned_count = file_service.cleanup_temp_files(temp_dir, max_age_hours=1)

        # 应该清理了旧文件，保留了新文件
        assert cleaned_count == 1
        assert not (Path(temp_dir) / "old_file.txt").exists()
        assert new_file.exists()

    def test_cleanup_temp_files_directory_not_exist(self, file_service):
        """测试清理不存在的目录"""
        cleaned_count = file_service.cleanup_temp_files("non_existent_dir")
        assert cleaned_count == 0

    def test_get_file_info_success(self, file_service, temp_dir):
        """测试获取文件信息"""
        test_file = Path(temp_dir) / "test.pdf"
        test_file.write_text("test content")

        info = file_service.get_file_info(str(test_file))

        assert info["name"] == "test.pdf"
        assert info["size"] > 0
        assert info["extension"] == ".pdf"
        assert "created_time" in info
        assert "modified_time" in info
        assert "path" in info

    def test_get_file_info_not_exist(self, file_service):
        """测试获取不存在文件的信息"""
        info = file_service.get_file_info("non_existent.pdf")
        assert info == {}

    def test_backup_file_success(self, file_service, temp_dir):
        """测试备份文件成功"""
        # 创建源文件
        source_file = Path(temp_dir) / "source.pdf"
        source_file.write_text("test content")

        # 创建备份目录
        backup_dir = Path(temp_dir) / "backup"

        # 备份文件
        result = file_service.backup_file(str(source_file), str(backup_dir))

        assert result is not None
        assert Path(result).exists()
        assert source_file.exists()  # 源文件应该保留

    def test_backup_file_source_not_exist(self, file_service, temp_dir):
        """测试备份不存在的文件"""
        backup_dir = Path(temp_dir) / "backup"
        result = file_service.backup_file("non_existent.pdf", str(backup_dir))
        assert result is None

    def test_backup_file_creates_backup_dir(self, file_service, temp_dir):
        """测试备份时自动创建备份目录"""
        source_file = Path(temp_dir) / "source.pdf"
        source_file.write_text("test content")

        backup_dir = Path(temp_dir) / "new_backup" / "nested"
        result = file_service.backup_file(str(source_file), str(backup_dir))

        assert result is not None
        assert backup_dir.exists()
        assert Path(result).exists()

    def test_config_manager_with_dict(self, temp_dir):
        """测试使用字典作为配置管理器"""
        config = {"save_dir": temp_dir}
        service = FileService(config)  # type: ignore

        stock_dir = service.get_stock_directory("000001", "测试")
        assert stock_dir.exists()

    def test_config_manager_fallback(self, temp_dir):
        """测试配置管理器回退行为"""
        # 测试使用非标准配置管理器时的回退行为
        # 使用一个简单的字典作为配置管理器（不是 ConfigManager 实例）
        config = {"save_dir": temp_dir}
        service = FileService(config)  # type: ignore

        # 应该使用默认值处理文件名清理
        filename = service.clean_filename("test/file:name")
        assert filename == "test_file_name"
