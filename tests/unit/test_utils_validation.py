#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validation 模块测试
"""

import pytest
from datetime import date, datetime
from pathlib import Path
import tempfile
import json
from src.utils.validation import DataValidator, data_validator, validate_data, validate_batch_data
from src.core.exceptions import ValidationError


class TestDataValidator:
    """测试 DataValidator 类"""

    def setup_method(self):
        self.validator = DataValidator()

    def test_validate_stock_code_enhanced_valid(self):
        """测试有效的股票代码验证"""
        is_valid, result = self.validator.validate("000001", "stock_code")
        assert is_valid is True
        assert result == "000001"

    def test_validate_stock_code_enhanced_invalid(self):
        """测试无效的股票代码验证"""
        is_valid, result = self.validator.validate("invalid", "stock_code")
        assert is_valid is False
        assert isinstance(result, ValidationError)

    def test_validate_stock_code_enhanced_empty_allowed(self):
        """测试允许空的股票代码"""
        is_valid, result = self.validator.validate("", "stock_code", allow_empty=True)
        assert is_valid is True
        assert result == ""

    def test_validate_stock_code_enhanced_range_check(self):
        """测试股票代码范围验证"""
        is_valid, result = self.validator.validate("999999", "stock_code")
        assert is_valid is False

    def test_validate_org_id_enhanced_valid(self):
        """测试有效的组织机构ID验证"""
        is_valid, result = self.validator.validate("9900056250", "org_id")
        assert is_valid is True
        assert result == "9900056250"

    def test_validate_org_id_enhanced_invalid(self):
        """测试无效的组织机构ID验证"""
        is_valid, result = self.validator.validate("1234567890", "org_id")
        assert is_valid is False

    def test_validate_company_name_valid(self):
        """测试有效的公司名称验证"""
        is_valid, result = self.validator.validate("测试公司", "company_name")
        assert is_valid is True
        assert result == "测试公司"

    def test_validate_company_name_invalid_length(self):
        """测试公司名称长度验证"""
        is_valid, result = self.validator.validate("a", "company_name", min_length=2)
        assert is_valid is False

    def test_validate_company_name_forbidden_chars(self):
        """测试公司名称包含禁止字符"""
        is_valid, result = self.validator.validate("公司<script>", "company_name")
        assert is_valid is False

    def test_validate_url_valid(self):
        """测试有效的URL验证"""
        is_valid, result = self.validator.validate("https://example.com", "url")
        assert is_valid is True
        assert result == "https://example.com"

    def test_validate_url_invalid_scheme(self):
        """测试无效的URL协议"""
        is_valid, result = self.validator.validate("javascript:alert(1)", "url")
        assert is_valid is False

    def test_validate_url_https_required(self):
        """测试要求HTTPS的URL验证"""
        is_valid, result = self.validator.validate("http://example.com", "url", require_https=True)
        assert is_valid is False

    def test_validate_date_valid_string(self):
        """测试有效的日期字符串验证"""
        is_valid, result = self.validator.validate("2025-01-01", "date")
        assert is_valid is True
        assert isinstance(result, date)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 1

    def test_validate_date_invalid_format(self):
        """测试无效的日期格式"""
        is_valid, result = self.validator.validate("invalid-date", "date")
        assert is_valid is False

    def test_validate_date_future_not_allowed(self):
        """测试不允许未来日期"""
        future_date = date.today().replace(year=date.today().year + 1)
        is_valid, result = self.validator.validate(future_date.isoformat(), "date", allow_future=False)
        assert is_valid is False

    def test_validate_email_valid(self):
        """测试有效的邮箱验证"""
        is_valid, result = self.validator.validate("test@example.com", "email")
        assert is_valid is True
        assert result == "test@example.com"

    def test_validate_email_invalid(self):
        """测试无效的邮箱验证"""
        is_valid, result = self.validator.validate("invalid-email", "email")
        assert is_valid is False

    def test_validate_phone_chinese_valid(self):
        """测试有效的中国手机号验证"""
        is_valid, result = self.validator.validate("13800138000", "phone", country_code="CN")
        assert is_valid is True
        assert result == "13800138000"

    def test_validate_phone_invalid(self):
        """测试无效的手机号验证"""
        is_valid, result = self.validator.validate("123456", "phone")
        assert is_valid is False

    def test_validate_file_path_exists(self):
        """测试文件路径存在验证"""
        with tempfile.NamedTemporaryFile(suffix=".txt") as tmp_file:
            is_valid, result = self.validator.validate(tmp_file.name, "file_path", must_exist=True)
            assert is_valid is True
            assert result == tmp_file.name

    def test_validate_file_path_not_exists(self):
        """测试文件路径不存在验证"""
        is_valid, result = self.validator.validate("/nonexistent/file.txt", "file_path", must_exist=True)
        assert is_valid is False

    def test_validate_file_path_extension_check(self):
        """测试文件扩展名验证"""
        with tempfile.NamedTemporaryFile(suffix=".txt") as tmp_file:
            is_valid, result = self.validator.validate(
                tmp_file.name, "file_path",
                allowed_extensions=[".txt", ".pdf"]
            )
            assert is_valid is True

    def test_validate_directory_path_exists(self):
        """测试目录路径存在验证"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            is_valid, result = self.validator.validate(tmp_dir, "directory_path", must_exist=True)
            assert is_valid is True

    def test_validate_directory_path_create_if_not_exist(self):
        """测试目录路径不存在时创建"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            new_dir = Path(tmp_dir) / "new_subdir"
            is_valid, result = self.validator.validate(
                str(new_dir), "directory_path",
                create_if_not_exist=True
            )
            assert is_valid is True
            assert new_dir.exists()

    def test_validate_json_data_valid(self):
        """测试有效的JSON数据验证"""
        json_str = '{"key": "value"}'
        is_valid, result = self.validator.validate(json_str, "json_data")
        assert is_valid is True
        assert isinstance(result, dict)
        assert result["key"] == "value"

    def test_validate_json_data_invalid(self):
        """测试无效的JSON数据验证"""
        is_valid, result = self.validator.validate("{invalid}", "json_data")
        assert is_valid is False

    def test_validate_json_data_required_fields(self):
        """测试JSON数据必需字段验证"""
        json_data = {"key": "value"}
        is_valid, result = self.validator.validate(
            json_data, "json_data",
            required_fields=["key", "missing"]
        )
        assert is_valid is False

    def test_validate_numeric_range_valid(self):
        """测试有效的数值范围验证"""
        is_valid, result = self.validator.validate(5, "numeric_range", min_val=0, max_val=10)
        assert is_valid is True
        assert result == 5.0

    def test_validate_numeric_range_out_of_range(self):
        """测试数值超出范围验证"""
        is_valid, result = self.validator.validate(15, "numeric_range", min_val=0, max_val=10)
        assert is_valid is False

    def test_validate_string_length_valid(self):
        """测试有效的字符串长度验证"""
        is_valid, result = self.validator.validate("test", "string_length", min_length=2, max_length=10)
        assert is_valid is True
        assert result == "test"

    def test_validate_string_length_too_short(self):
        """测试字符串过短验证"""
        is_valid, result = self.validator.validate("a", "string_length", min_length=2)
        assert is_valid is False

    def test_validate_string_length_too_long(self):
        """测试字符串过长验证"""
        is_valid, result = self.validator.validate("very long string", "string_length", max_length=5)
        assert is_valid is False

    def test_validate_enum_value_valid(self):
        """测试有效的枚举值验证"""
        is_valid, result = self.validator.validate(
            "option1", "enum_value",
            allowed_values=["option1", "option2", "option3"]
        )
        assert is_valid is True
        assert result == "option1"

    def test_validate_enum_value_case_insensitive(self):
        """测试枚举值不区分大小写验证"""
        is_valid, result = self.validator.validate(
            "OPTION1", "enum_value",
            allowed_values=["option1", "option2"],
            case_sensitive=False
        )
        assert is_valid is True

    def test_validate_enum_value_invalid(self):
        """测试无效的枚举值验证"""
        is_valid, result = self.validator.validate(
            "invalid", "enum_value",
            allowed_values=["option1", "option2"]
        )
        assert is_valid is False

    def test_validate_batch(self):
        """测试批量验证"""
        data_dict = {
            "stock_code": "000001",
            "org_id": "9900056250",
            "company_name": "测试公司"
        }
        validation_rules = {
            "stock_code": {"type": "stock_code"},
            "org_id": {"type": "org_id"},
            "company_name": {"type": "company_name"}
        }
        results = self.validator.validate_batch(data_dict, validation_rules)
        assert "stock_code" in results
        assert "org_id" in results
        assert "company_name" in results
        assert results["stock_code"]["valid"] is True
        assert results["org_id"]["valid"] is True
        assert results["company_name"]["valid"] is True


class TestGlobalValidatorFunctions:
    """测试全局验证函数"""

    def test_validate_data_function(self):
        """测试 validate_data 辅助函数"""
        is_valid, result = validate_data("000001", "stock_code")
        assert is_valid is True
        assert result == "000001"

    def test_validate_batch_data_function(self):
        """测试 validate_batch_data 辅助函数"""
        data_dict = {"stock_code": "000001"}
        validation_rules = {"stock_code": {"type": "stock_code"}}
        results = validate_batch_data(data_dict, validation_rules)
        assert "stock_code" in results
        assert results["stock_code"]["valid"] is True

    def test_data_validator_instance(self):
        """测试全局 data_validator 实例"""
        assert data_validator is not None
        assert isinstance(data_validator, DataValidator)


class TestEdgeCases:
    """测试边界情况"""

    def setup_method(self):
        self.validator = DataValidator()

    def test_validate_unknown_type(self):
        """测试未知的验证类型"""
        is_valid, result = self.validator.validate("data", "unknown_type")
        assert is_valid is False
        assert isinstance(result, ValidationError)

    def test_validate_empty_data_without_allow_empty(self):
        """测试不允许空数据的验证"""
        is_valid, result = self.validator.validate("", "stock_code", allow_empty=False)
        assert is_valid is False

    def test_validate_none_data(self):
        """测试None数据的验证"""
        is_valid, result = self.validator.validate(None, "stock_code")
        assert is_valid is False