"""
Enhanced Validation Module Tests
覆盖数据验证模块的各种功能
"""

import pytest
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

from src.core.exceptions import ErrorCode, ValidationError
from src.utils.validation import DataValidator


class TestDataValidator:
    """DataValidator 测试类"""

    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        return DataValidator()

    # ==================== Generic Validation ====================

    def test_validate_unsupported_type(self, validator):
        """测试不支持的验证类型"""
        is_valid, result = validator.validate("test", "unsupported_type")
        assert is_valid is False
        assert isinstance(result, ValidationError)

    def test_validate_returns_available_types(self, validator):
        """测试返回可用的验证类型"""
        is_valid, result = validator.validate("test", "unsupported_type")
        assert "available_types" in result.context
        expected_types = [
            "stock_code", "org_id", "company_name", "url", "date",
            "email", "phone", "file_path", "directory_path",
            "json_data", "numeric_range", "string_length", "enum_value"
        ]
        for expected in expected_types:
            assert expected in result.context["available_types"]

    # ==================== Stock Code Validation ====================

    def test_validate_stock_code_valid_shanghai(self, validator):
        """测试有效的上海主板股票代码"""
        is_valid, result = validator.validate("600000", "stock_code")
        assert is_valid is True
        assert result == "600000"

    def test_validate_stock_code_valid_star_market(self, validator):
        """测试有效的科创板股票代码"""
        is_valid, result = validator.validate("688001", "stock_code")
        assert is_valid is True
        assert result == "688001"

    def test_validate_stock_code_valid_shenzhen_main(self, validator):
        """测试有效的深圳主板股票代码"""
        is_valid, result = validator.validate("000001", "stock_code")
        assert is_valid is True
        assert result == "000001"

    def test_validate_stock_code_valid_chinext(self, validator):
        """测试有效的创业板股票代码"""
        is_valid, result = validator.validate("300001", "stock_code")
        assert is_valid is True
        assert result == "300001"

    def test_validate_stock_code_empty(self, validator):
        """测试空股票代码"""
        is_valid, result = validator.validate("", "stock_code")
        assert is_valid is False
        assert isinstance(result, ValidationError)
        assert result.error_code == ErrorCode.VALIDATION_STOCK_CODE_EMPTY

    def test_validate_stock_code_empty_allowed(self, validator):
        """测试允许空股票代码"""
        is_valid, result = validator.validate("", "stock_code", allow_empty=True)
        assert is_valid is True
        assert result == ""

    def test_validate_stock_code_invalid_format(self, validator):
        """测试无效格式的股票代码"""
        is_valid, result = validator.validate("12345", "stock_code")
        assert is_valid is False
        assert isinstance(result, ValidationError)

    def test_validate_stock_code_non_numeric(self, validator):
        """测试非数字股票代码"""
        is_valid, result = validator.validate("abcdef", "stock_code")
        assert is_valid is False
        assert isinstance(result, ValidationError)

    def test_validate_stock_code_out_of_range(self, validator):
        """测试超出范围的股票代码"""
        is_valid, result = validator.validate("999999", "stock_code")
        assert is_valid is False
        assert isinstance(result, ValidationError)
        assert result.error_code == ErrorCode.VALIDATION_STOCK_CODE_RANGE

    # ==================== URL Validation ====================

    def test_validate_url_valid_http(self, validator):
        """测试有效的 HTTP URL"""
        is_valid, result = validator.validate("http://example.com", "url")
        assert is_valid is True
        assert result == "http://example.com"

    def test_validate_url_valid_https(self, validator):
        """测试有效的 HTTPS URL"""
        is_valid, result = validator.validate("https://example.com/path", "url")
        assert is_valid is True
        assert result == "https://example.com/path"

    def test_validate_url_invalid_no_scheme(self, validator):
        """测试没有协议的 URL"""
        is_valid, result = validator.validate("example.com", "url")
        assert is_valid is False

    def test_validate_url_invalid_format(self, validator):
        """测试无效格式的 URL"""
        is_valid, result = validator.validate("not a url", "url")
        assert is_valid is False

    def test_validate_url_empty(self, validator):
        """测试空 URL"""
        is_valid, result = validator.validate("", "url")
        assert is_valid is False

    # ==================== Date Validation ====================

    def test_validate_date_valid_string(self, validator):
        """测试有效的日期字符串"""
        is_valid, result = validator.validate("2023-01-01", "date")
        assert is_valid is True

    def test_validate_date_valid_date_object(self, validator):
        """测试有效的日期对象"""
        test_date = date(2023, 1, 1)
        is_valid, result = validator.validate(test_date, "date")
        assert is_valid is True

    def test_validate_date_valid_datetime_object(self, validator):
        """测试有效的日期时间对象"""
        test_datetime = datetime(2023, 1, 1, 12, 0)
        is_valid, result = validator.validate(test_datetime, "date")
        assert is_valid is True

    def test_validate_date_invalid_string(self, validator):
        """测试无效的日期字符串"""
        is_valid, result = validator.validate("not-a-date", "date")
        assert is_valid is False

    def test_validate_date_empty(self, validator):
        """测试空日期"""
        is_valid, result = validator.validate("", "date")
        assert is_valid is False

    # ==================== Email Validation ====================

    def test_validate_email_valid(self, validator):
        """测试有效的电子邮件地址"""
        is_valid, result = validator.validate("test@example.com", "email")
        assert is_valid is True

    def test_validate_email_valid_with_dots(self, validator):
        """测试带点的有效电子邮件地址"""
        is_valid, result = validator.validate("test.name@example.com", "email")
        assert is_valid is True

    def test_validate_email_valid_with_plus(self, validator):
        """测试带加号的有效电子邮件地址"""
        is_valid, result = validator.validate("test+tag@example.com", "email")
        assert is_valid is True

    def test_validate_email_invalid_no_at(self, validator):
        """测试没有 @ 符号的电子邮件"""
        is_valid, result = validator.validate("testexample.com", "email")
        assert is_valid is False

    def test_validate_email_invalid_no_domain(self, validator):
        """测试没有域名的电子邮件"""
        is_valid, result = validator.validate("test@", "email")
        assert is_valid is False

    def test_validate_email_invalid_no_local(self, validator):
        """测试没有本地部分的电子邮件"""
        is_valid, result = validator.validate("@example.com", "email")
        assert is_valid is False

    def test_validate_email_empty(self, validator):
        """测试空电子邮件"""
        is_valid, result = validator.validate("", "email")
        assert is_valid is False

    # ==================== Phone Validation ====================

    def test_validate_phone_valid_mobile(self, validator):
        """测试有效的手机号码（中国格式）"""
        is_valid, result = validator.validate("13812345678", "phone")
        assert is_valid is True

    def test_validate_phone_valid_with_country_code(self, validator):
        """测试带国家代码的电话号码（非中国格式）"""
        # 使用带横线的格式
        is_valid, result = validator.validate("123-4567-8901", "phone", country_code="US")
        assert is_valid is True

    def test_validate_phone_valid_landline(self, validator):
        """测试有效的固定电话（非中国格式）"""
        is_valid, result = validator.validate("010-1234-5678", "phone", country_code="US")
        assert is_valid is True

    def test_validate_phone_invalid_short(self, validator):
        """测试过短的电话号码"""
        is_valid, result = validator.validate("12345", "phone")
        assert is_valid is False

    def test_validate_phone_invalid_chars(self, validator):
        """测试包含非法字符的电话号码"""
        is_valid, result = validator.validate("abcdefghijk", "phone")
        assert is_valid is False

    def test_validate_phone_empty(self, validator):
        """测试空电话号码"""
        is_valid, result = validator.validate("", "phone")
        assert is_valid is False

    # ==================== File Path Validation ====================

    def test_validate_file_path_valid_absolute(self, validator):
        """测试有效的绝对文件路径"""
        is_valid, result = validator.validate("/path/to/file.txt", "file_path")
        assert is_valid is True

    def test_validate_file_path_valid_relative(self, validator):
        """测试有效的相对文件路径"""
        is_valid, result = validator.validate("relative/path/file.txt", "file_path")
        assert is_valid is True

    def test_validate_file_path_valid_windows(self, validator):
        """测试有效的 Windows 文件路径"""
        is_valid, result = validator.validate("C:\\path\\to\\file.txt", "file_path")
        assert is_valid is True

    def test_validate_file_path_empty(self, validator):
        """测试空文件路径"""
        is_valid, result = validator.validate("", "file_path")
        assert is_valid is False

    # ==================== Directory Path Validation ====================

    def test_validate_directory_path_valid_absolute(self, validator):
        """测试有效的绝对目录路径"""
        is_valid, result = validator.validate("/path/to/directory", "directory_path")
        assert is_valid is True

    def test_validate_directory_path_valid_relative(self, validator):
        """测试有效的相对目录路径"""
        is_valid, result = validator.validate("relative/path", "directory_path")
        assert is_valid is True

    def test_validate_directory_path_empty(self, validator):
        """测试空目录路径"""
        is_valid, result = validator.validate("", "directory_path")
        assert is_valid is False

    # ==================== JSON Data Validation ====================

    def test_validate_json_data_valid_object(self, validator):
        """测试有效的 JSON 对象"""
        is_valid, result = validator.validate('{"key": "value"}', "json_data")
        assert is_valid is True
        assert result == {"key": "value"}

    def test_validate_json_data_invalid(self, validator):
        """测试无效的 JSON 数据"""
        is_valid, result = validator.validate('{not json}', "json_data")
        assert is_valid is False

    def test_validate_json_data_empty_string(self, validator):
        """测试空字符串 JSON"""
        is_valid, result = validator.validate("", "json_data")
        assert is_valid is False

    def test_validate_json_data_python_dict(self, validator):
        """测试 Python 字典作为 JSON"""
        is_valid, result = validator.validate({"key": "value"}, "json_data")
        assert is_valid is True
        assert result == {"key": "value"}

    def test_validate_json_data_empty_allowed(self, validator):
        """测试允许空 JSON"""
        is_valid, result = validator.validate("", "json_data", allow_empty=True)
        assert is_valid is True
        assert result == {}

    # ==================== Numeric Range Validation ====================

    def test_validate_numeric_range_in_range(self, validator):
        """测试在范围内的数值"""
        is_valid, result = validator.validate(50, "numeric_range", min_val=0, max_val=100)
        assert is_valid is True

    def test_validate_numeric_range_below_min(self, validator):
        """测试低于最小值的数值"""
        is_valid, result = validator.validate(-1, "numeric_range", min_val=0, max_val=100)
        assert is_valid is False

    def test_validate_numeric_range_above_max(self, validator):
        """测试高于最大值的数值"""
        is_valid, result = validator.validate(101, "numeric_range", min_val=0, max_val=100)
        assert is_valid is False

    def test_validate_numeric_range_at_boundaries(self, validator):
        """测试边界值"""
        is_valid1, result1 = validator.validate(0, "numeric_range", min_val=0, max_val=100)
        is_valid2, result2 = validator.validate(100, "numeric_range", min_val=0, max_val=100)
        assert is_valid1 is True
        assert is_valid2 is True

    def test_validate_numeric_range_float(self, validator):
        """测试浮点数范围"""
        is_valid, result = validator.validate(0.5, "numeric_range", min_val=0, max_val=1)
        assert is_valid is True

    # ==================== String Length Validation ====================

    def test_validate_string_length_valid(self, validator):
        """测试有效的字符串长度"""
        is_valid, result = validator.validate("test", "string_length", min_length=2, max_length=10)
        assert is_valid is True

    def test_validate_string_length_too_short(self, validator):
        """测试过短的字符串"""
        is_valid, result = validator.validate("t", "string_length", min_length=2, max_length=10)
        assert is_valid is False

    def test_validate_string_length_too_long(self, validator):
        """测试过长的字符串"""
        is_valid, result = validator.validate("this is too long", "string_length", min_length=2, max_length=10)
        assert is_valid is False

    def test_validate_string_length_at_boundaries(self, validator):
        """测试边界长度"""
        is_valid1, result1 = validator.validate("ab", "string_length", min_length=2, max_length=10)
        is_valid2, result2 = validator.validate("1234567890", "string_length", min_length=2, max_length=10)
        assert is_valid1 is True
        assert is_valid2 is True

    def test_validate_string_length_empty_allowed(self, validator):
        """测试允许空字符串"""
        is_valid, result = validator.validate("", "string_length", min_length=0, max_length=10, allow_empty=True)
        assert is_valid is True

    # ==================== Enum Value Validation ====================

    def test_validate_enum_value_valid(self, validator):
        """测试有效的枚举值"""
        is_valid, result = validator.validate("option1", "enum_value", allowed_values=["option1", "option2", "option3"])
        assert is_valid is True

    def test_validate_enum_value_invalid(self, validator):
        """测试无效的枚举值"""
        is_valid, result = validator.validate("invalid", "enum_value", allowed_values=["option1", "option2"])
        assert is_valid is False

    def test_validate_enum_value_numeric(self, validator):
        """测试数字枚举值"""
        is_valid, result = validator.validate(1, "enum_value", allowed_values=[1, 2, 3])
        assert is_valid is True

    def test_validate_enum_value_empty_allowed_list(self, validator):
        """测试空允许值列表"""
        is_valid, result = validator.validate("test", "enum_value", allowed_values=[])
        assert is_valid is False

    # ==================== Company Name Validation ====================

    def test_validate_company_name_valid(self, validator):
        """测试有效的公司名称"""
        is_valid, result = validator.validate("测试科技有限公司", "company_name")
        assert is_valid is True

    def test_validate_company_name_empty(self, validator):
        """测试空公司名称"""
        is_valid, result = validator.validate("", "company_name")
        assert is_valid is False

    def test_validate_company_name_too_short(self, validator):
        """测试过短的公司名称"""
        is_valid, result = validator.validate("A", "company_name")
        assert is_valid is False

    # ==================== Org ID Validation ====================

    def test_validate_org_id_valid(self, validator):
        """测试有效的组织机构 ID"""
        is_valid, result = validator.validate("9900056250", "org_id")
        assert is_valid is True

    def test_validate_org_id_invalid_format(self, validator):
        """测试无效格式的组织机构 ID"""
        is_valid, result = validator.validate("12345", "org_id")
        assert is_valid is False

    def test_validate_org_id_empty(self, validator):
        """测试空组织机构 ID"""
        is_valid, result = validator.validate("", "org_id")
        assert is_valid is False
