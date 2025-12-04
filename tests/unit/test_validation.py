#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强数据验证模块的单元测试
"""

import pytest
from datetime import date, datetime
from src.utils.validation import DataValidator, ValidationError, validate_data, validate_batch_data


class TestDataValidator:
    """测试数据验证器"""
    
    def setup_method(self):
        """设置测试方法"""
        self.validator = DataValidator()
    
    def test_validate_stock_code_valid(self):
        """测试有效股票代码验证"""
        valid_codes = ["000001", "002415", "600000", "688036", "300750"]
        for code in valid_codes:
            is_valid, result = self.validator.validate(code, "stock_code")
            assert is_valid is True
            assert result == code
    
    def test_validate_stock_code_invalid(self):
        """测试无效股票代码验证"""
        invalid_codes = ["", "1234567", "abcdef", "0000010", "999999"]
        for code in invalid_codes:
            is_valid, result = self.validator.validate(code, "stock_code")
            assert is_valid is False
    
    def test_validate_stock_code_allow_empty(self):
        """测试允许空股票代码"""
        is_valid, result = self.validator.validate("", "stock_code", allow_empty=True)
        assert is_valid is True
        assert result == ""
    
    def test_validate_org_id_valid(self):
        """测试有效组织ID验证"""
        valid_org_ids = ["9900000001", "9912345678", "9999999999"]
        for org_id in valid_org_ids:
            is_valid, result = self.validator.validate(org_id, "org_id")
            assert is_valid is True
            assert result == org_id
    
    def test_validate_org_id_invalid(self):
        """测试无效组织ID验证"""
        invalid_org_ids = ["", "123", "990000000", "99000000000", "abcdefghij", "9800000000"]
        for org_id in invalid_org_ids:
            is_valid, result = self.validator.validate(org_id, "org_id")
            assert is_valid is False
    
    def test_validate_company_name_valid(self):
        """测试有效公司名称验证"""
        valid_names = ["平安银行", "海康威视", "Apple Inc.", "腾讯控股"]
        for name in valid_names:
            is_valid, result = self.validator.validate(name, "company_name")
            assert is_valid is True
    
    def test_validate_company_name_invalid(self):
        """测试无效公司名称验证"""
        invalid_names = ["", "A", "x" * 51, "公司<script>", "公司&名称"]
        for name in invalid_names:
            is_valid, result = self.validator.validate(name, "company_name")
            assert is_valid is False
    
    def test_validate_url_valid(self):
        """测试有效URL验证"""
        valid_urls = [
            "https://www.example.com",
            "http://test.com/path",
            "https://site.com/page?param=value"
        ]
        for url in valid_urls:
            is_valid, result = self.validator.validate(url, "url")
            assert is_valid is True
    
    def test_validate_url_invalid(self):
        """测试无效URL验证"""
        invalid_urls = [
            "",
            "not_a_url",
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>"
        ]
        for url in invalid_urls:
            is_valid, result = self.validator.validate(url, "url")
            assert is_valid is False
    
    def test_validate_url_require_https(self):
        """测试HTTPS要求验证"""
        is_valid, result = self.validator.validate("http://example.com", "url", require_https=True)
        assert is_valid is False
        
        is_valid, result = self.validator.validate("https://example.com", "url", require_https=True)
        assert is_valid is True
    
    def test_validate_date_string(self):
        """测试日期字符串验证"""
        valid_dates = ["2023-12-25"]
        for date_str in valid_dates:
            is_valid, result = self.validator.validate(date_str, "date")
            assert is_valid is True
            assert isinstance(result, date)
    
    def test_validate_date_object(self):
        """测试日期对象验证"""
        test_date = date(2023, 12, 25)
        is_valid, result = self.validator.validate(test_date, "date")
        assert is_valid is True
        assert result == test_date
    
    def test_validate_date_invalid(self):
        """测试无效日期验证"""
        invalid_dates = ["", "2023-13-01", "invalid_date", "2023-02-30"]
        for date_str in invalid_dates:
            is_valid, result = self.validator.validate(date_str, "date")
            assert is_valid is False
    
    def test_validate_date_future_not_allowed(self):
        """测试不允许未来日期"""
        future_date = (date.today()).replace(year=date.today().year + 1)
        is_valid, result = self.validator.validate(future_date, "date", allow_future=False)
        assert is_valid is False
    
    def test_validate_email_valid(self):
        """测试有效邮箱验证"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org"
        ]
        for email in valid_emails:
            is_valid, result = self.validator.validate(email, "email")
            assert is_valid is True
    
    def test_validate_email_invalid(self):
        """测试无效邮箱验证"""
        invalid_emails = [
            "",
            "invalid.email",
            "@example.com",
            "user@",
            "user@.com"
        ]
        for email in invalid_emails:
            is_valid, result = self.validator.validate(email, "email")
            assert is_valid is False
    
    def test_validate_phone_cn_valid(self):
        """测试有效中国手机号验证"""
        valid_phones = ["13812345678", "15987654321", "18612345678"]
        for phone in valid_phones:
            is_valid, result = self.validator.validate(phone, "phone")
            assert is_valid is True
    
    def test_validate_phone_invalid(self):
        """测试无效手机号验证"""
        invalid_phones = [
            "",
            "12345678901",
            "1381234567",
            "138123456789",
            "abcdefghijk"
        ]
        for phone in invalid_phones:
            is_valid, result = self.validator.validate(phone, "phone")
            assert is_valid is False
    
    def test_validate_numeric_range_valid(self):
        """测试有效数值范围验证"""
        # 测试整数
        is_valid, result = self.validator.validate(50, "numeric_range", min_val=0, max_val=100)
        assert is_valid is True
        assert result == 50.0
        
        # 测试浮点数
        is_valid, result = self.validator.validate(3.14, "numeric_range", min_val=0, max_val=10)
        assert is_valid is True
        assert result == 3.14
    
    def test_validate_numeric_range_invalid(self):
        """测试无效数值范围验证"""
        # 超出范围
        is_valid, result = self.validator.validate(150, "numeric_range", min_val=0, max_val=100)
        assert is_valid is False
        
        # 非数值
        is_valid, result = self.validator.validate("invalid", "numeric_range")
        assert is_valid is False
    
    def test_validate_string_length_valid(self):
        """测试有效字符串长度验证"""
        is_valid, result = self.validator.validate("hello", "string_length", min_length=3, max_length=10)
        assert is_valid is True
        assert result == "hello"
    
    def test_validate_string_length_invalid(self):
        """测试无效字符串长度验证"""
        # 太短
        is_valid, result = self.validator.validate("hi", "string_length", min_length=3)
        assert is_valid is False
        
        # 太长
        is_valid, result = self.validator.validate("this is too long", "string_length", max_length=10)
        assert is_valid is False
    
    def test_validate_enum_value_valid(self):
        """测试有效枚举值验证"""
        allowed_values = ["option1", "option2", "option3"]
        for value in allowed_values:
            is_valid, result = self.validator.validate(value, "enum_value", allowed_values=allowed_values)
            assert is_valid is True
    
    def test_validate_enum_value_case_insensitive(self):
        """测试不区分大小写的枚举值验证"""
        allowed_values = ["OPTION1", "OPTION2"]
        is_valid, result = self.validator.validate("option1", "enum_value", allowed_values=allowed_values, case_sensitive=False)
        assert is_valid is True
    
    def test_validate_enum_value_invalid(self):
        """测试无效枚举值验证"""
        allowed_values = ["option1", "option2"]
        is_valid, result = self.validator.validate("invalid", "enum_value", allowed_values=allowed_values)
        assert is_valid is False
    
    def test_validate_batch_success(self):
        """测试批量验证成功"""
        data = {
            "stock_code": "000001",
            "company_name": "测试公司",
            "email": "test@example.com"
        }
        
        rules = {
            "stock_code": {"type": "stock_code"},
            "company_name": {"type": "company_name"},
            "email": {"type": "email"}
        }
        
        results = self.validator.validate_batch(data, rules)
        
        for field_name, result in results.items():
            assert result["valid"] is True
            assert result["error"] is None
    
    def test_validate_batch_with_errors(self):
        """测试批量验证包含错误"""
        data = {
            "stock_code": "invalid",
            "company_name": "",
            "email": "invalid_email"
        }
        
        rules = {
            "stock_code": {"type": "stock_code"},
            "company_name": {"type": "company_name"},
            "email": {"type": "email"}
        }
        
        results = self.validator.validate_batch(data, rules)
        
        for field_name, result in results.items():
            assert result["valid"] is False
            assert result["error"] is not None
    
    def test_convenience_functions(self):
        """测试便捷函数"""
        # 测试单个数据验证
        is_valid, result = validate_data("000001", "stock_code")
        assert is_valid is True
        
        # 测试批量数据验证
        data = {"stock_code": "000001", "company_name": "测试公司"}
        rules = {
            "stock_code": {"type": "stock_code"},
            "company_name": {"type": "company_name"}
        }
        results = validate_batch_data(data, rules)
        
        for result in results.values():
            assert result["valid"] is True
    
    def test_unsupported_validation_type(self):
        """测试不支持的验证类型"""
        is_valid, result = self.validator.validate("test", "unsupported_type")
        assert is_valid is False
        assert isinstance(result, ValidationError)
        assert "Unsupported validation type" in str(result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])