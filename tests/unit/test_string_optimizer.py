"""Tests for src.utils.string_optimizer.StringOptimizer"""

import pytest

from src.utils.string_optimizer import StringOptimizer


@pytest.fixture
def optimizer():
    return StringOptimizer()


class TestSanitizeFilename:
    def test_empty_filename(self, optimizer):
        assert optimizer.sanitize_filename("") == "unnamed"

    def test_none_filename(self, optimizer):
        assert optimizer.sanitize_filename(None) == "unnamed"

    def test_normal_filename(self, optimizer):
        assert optimizer.sanitize_filename("report.pdf") == "report.pdf"

    def test_special_chars_replaced(self, optimizer):
        result = optimizer.sanitize_filename("file:name*with?chars")
        assert ":" not in result
        assert "*" not in result
        assert "?" not in result

    def test_long_filename_truncated(self, optimizer):
        long_name = "a" * 250
        result = optimizer.sanitize_filename(long_name)
        assert len(result) <= 200

    def test_leading_trailing_stripped(self, optimizer):
        result = optimizer.sanitize_filename("._-file-_.")
        assert not result.startswith(("_", "-", "."))

    def test_custom_replacement(self, optimizer):
        result = optimizer.sanitize_filename("a/b\\c", replacement="-")
        assert "/" not in result


class TestStandardizeStockCode:
    def test_valid_6digit(self, optimizer):
        assert optimizer.standardize_stock_code("300470") == "300470"

    def test_padded_to_6(self, optimizer):
        assert optimizer.standardize_stock_code("470") == "000470"

    def test_invalid_too_long(self, optimizer):
        assert optimizer.standardize_stock_code("1234567") is None

    def test_empty_string(self, optimizer):
        assert optimizer.standardize_stock_code("") is None

    def test_none(self, optimizer):
        assert optimizer.standardize_stock_code(None) is None

    def test_with_spaces(self, optimizer):
        assert optimizer.standardize_stock_code("  300470  ") == "300470"

    def test_with_letters(self, optimizer):
        assert optimizer.standardize_stock_code("SZ300470") == "300470"


class TestNormalizeWhitespace:
    def test_empty(self, optimizer):
        assert optimizer.normalize_whitespace("") == ""

    def test_multiple_spaces(self, optimizer):
        assert optimizer.normalize_whitespace("a  b   c") == "a b c"

    def test_tabs_newlines(self, optimizer):
        assert optimizer.normalize_whitespace("a\t\nb") == "a b"

    def test_leading_trailing(self, optimizer):
        assert optimizer.normalize_whitespace("  hello  ") == "hello"


class TestCleanTextContent:
    def test_empty(self, optimizer):
        assert optimizer.clean_text_content("") == ""

    def test_control_chars_removed(self, optimizer):
        text = "hello\x00world\x07"
        result = optimizer.clean_text_content(text)
        assert "\x00" not in result
        assert "\x07" not in result

    def test_normal_text_unchanged(self, optimizer):
        assert optimizer.clean_text_content("Normal text") == "Normal text"


class TestExtractPaginationInfo:
    def test_valid_pagination(self, optimizer):
        result = optimizer.extract_pagination_info("1 / 10")
        assert result["current"] == 1
        assert result["total"] == 10

    def test_no_pagination(self, optimizer):
        result = optimizer.extract_pagination_info("no numbers here")
        assert result["current"] is None
        assert result["total"] is None

    def test_cn_pagination(self, optimizer):
        result = optimizer.extract_pagination_info("共10页")
        assert result["total"] == 10


class TestValidateStockCode:
    def test_valid(self, optimizer):
        assert optimizer.validate_stock_code("300470") is True

    def test_empty(self, optimizer):
        assert optimizer.validate_stock_code("") is False

    def test_padded_short_valid(self, optimizer):
        # "12345" standardizes to "012345" which is valid
        assert optimizer.validate_stock_code("12345") is True

    def test_too_long(self, optimizer):
        assert optimizer.validate_stock_code("1234567") is False


class TestGetStats:
    def test_returns_dict(self, optimizer):
        stats = optimizer.get_stats()
        assert isinstance(stats, dict)
        assert "compiled_patterns" in stats
