#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ValidationService 模块测试
提升 src/services/validation_service.py 模块的测试覆盖率
"""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.services.validation_service import ValidationService


class TestValidationService:
    """测试 ValidationService 类"""

    def test_init_default(self):
        """测试默认初始化"""
        service = ValidationService()
        assert service.config == {}
        assert service.logger is not None

    def test_init_with_config(self):
        """测试带配置初始化"""
        config = {"key": "value", "max_size": 1000}
        service = ValidationService(config)
        assert service.config == config
        assert service.logger is not None

    def test_init_with_none_config(self):
        """测试传入 None 配置"""
        service = ValidationService(None)
        assert service.config == {}


class TestValidatePdf:
    """测试 validate_pdf 方法"""

    def test_validate_pdf_nonexistent_file(self):
        """测试验证不存在的 PDF 文件"""
        service = ValidationService()
        result = service.validate_pdf("/nonexistent/file.pdf")
        assert result is False

    def test_validate_pdf_valid_file(self):
        """测试验证有效的 PDF 文件"""
        service = ValidationService()
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".pdf") as f:
            # 写入有效的 PDF 头部
            f.write(b"%PDF-1.4\n")
            f.write(b"x" * 200)  # 足够的内容
            temp_path = f.name

        try:
            result = service.validate_pdf(temp_path)
            assert result is True
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_validate_pdf_invalid_header(self):
        """测试验证无效头部的 PDF 文件"""
        service = ValidationService()
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".pdf") as f:
            # 写入无效的头部
            f.write(b"INVALID")
            f.write(b"x" * 200)
            temp_path = f.name

        try:
            result = service.validate_pdf(temp_path)
            assert result is False
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_validate_pdf_too_small(self):
        """测试验证太小的 PDF 文件"""
        service = ValidationService()
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".pdf") as f:
            # 写入有效的头部但文件太小
            f.write(b"%PDF")
            temp_path = f.name

        try:
            result = service.validate_pdf(temp_path)
            assert result is False
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_validate_pdf_empty_file(self):
        """测试验证空文件"""
        service = ValidationService()
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".pdf") as f:
            # 不写入任何内容
            temp_path = f.name

        try:
            result = service.validate_pdf(temp_path)
            assert result is False
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_validate_pdf_read_error(self):
        """测试 PDF 读取错误"""
        service = ValidationService()
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".pdf") as f:
            f.write(b"%PDF-1.4\n")
            f.write(b"x" * 200)
            temp_path = f.name

        try:
            # 模拟读取错误
            with patch("builtins.open", side_effect=IOError("Read error")):
                result = service.validate_pdf(temp_path)
                assert result is False
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_validate_pdf_os_error(self):
        """测试 PDF 文件系统错误"""
        service = ValidationService()
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".pdf") as f:
            f.write(b"%PDF-1.4\n")
            f.write(b"x" * 200)
            temp_path = f.name

        try:
            # 模拟文件存在但读取时 stat() 方法返回错误
            # 通过 patch exists() 返回 True，然后 stat() 抛出错误
            original_exists = Path.exists

            def mock_exists(self):
                return True  # 文件存在

            with patch.object(Path, "exists", mock_exists):
                with patch.object(Path, "stat", side_effect=OSError("Permission denied")):
                    result = service.validate_pdf(temp_path)
                    assert result is False
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestValidateDownloadResult:
    """测试 validate_download_result 方法"""

    def test_validate_download_result_exact_match(self):
        """测试验证下载结果 - 精确匹配"""
        service = ValidationService()
        files = ["/path/file1.pdf", "/path/file2.pdf", "/path/file3.pdf"]
        result = service.validate_download_result(files, 3)
        assert result is True

    def test_validate_download_result_more_than_expected(self):
        """测试验证下载结果 - 多于预期"""
        service = ValidationService()
        files = ["/path/file1.pdf", "/path/file2.pdf", "/path/file3.pdf", "/path/file4.pdf"]
        result = service.validate_download_result(files, 3)
        assert result is True

    def test_validate_download_result_less_than_expected(self):
        """测试验证下载结果 - 少于预期"""
        service = ValidationService()
        files = ["/path/file1.pdf", "/path/file2.pdf"]
        result = service.validate_download_result(files, 3)
        assert result is False

    def test_validate_download_result_empty_list(self):
        """测试验证下载结果 - 空列表"""
        service = ValidationService()
        files = []
        result = service.validate_download_result(files, 0)
        assert result is True

    def test_validate_download_result_empty_with_expected(self):
        """测试验证下载结果 - 空列表但有预期"""
        service = ValidationService()
        files = []
        result = service.validate_download_result(files, 1)
        assert result is False

    def test_validate_download_result_single_file(self):
        """测试验证下载结果 - 单个文件"""
        service = ValidationService()
        files = ["/path/file1.pdf"]
        result = service.validate_download_result(files, 1)
        assert result is True

    def test_validate_download_result_zero_expected(self):
        """测试验证下载结果 - 预期0个文件"""
        service = ValidationService()
        files = ["/path/file1.pdf", "/path/file2.pdf"]
        result = service.validate_download_result(files, 0)
        assert result is True

    def test_validate_download_result_large_numbers(self):
        """测试验证下载结果 - 大数字"""
        service = ValidationService()
        files = [f"/path/file{i}.pdf" for i in range(1000)]
        result = service.validate_download_result(files, 1000)
        assert result is True


class TestValidationServiceIntegration:
    """集成测试"""

    def test_complete_validation_workflow(self):
        """测试完整的验证工作流"""
        service = ValidationService({"strict_mode": True})

        # 创建一个有效的 PDF 文件
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".pdf") as f:
            f.write(b"%PDF-1.4\n")
            f.write(b"x" * 500)
            temp_path = f.name

        try:
            # 验证 PDF
            pdf_valid = service.validate_pdf(temp_path)
            assert pdf_valid is True

            # 验证下载结果
            files = [temp_path]
            download_valid = service.validate_download_result(files, 1)
            assert download_valid is True

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_multiple_pdf_validation(self):
        """测试多个 PDF 文件验证"""
        service = ValidationService()

        # 创建多个 PDF 文件
        temp_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".pdf") as f:
                f.write(b"%PDF-1.4\n")
                f.write(b"x" * 500)
                temp_files.append(f.name)

        try:
            # 验证所有文件
            for file_path in temp_files:
                assert service.validate_pdf(file_path) is True

            # 验证下载结果
            assert service.validate_download_result(temp_files, 3) is True

        finally:
            for file_path in temp_files:
                Path(file_path).unlink(missing_ok=True)
