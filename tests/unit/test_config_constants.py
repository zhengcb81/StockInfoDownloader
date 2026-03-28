"""Tests for src.core.config_constants.ConfigConstants"""

import pytest

from src.core.config_constants import ConfigConstants


class TestConfigConstantsUrls:
    def test_base_url(self):
        assert ConfigConstants.BASE_URL == "https://www.cninfo.com.cn"

    def test_detail_url_pattern(self):
        assert "/detail" in ConfigConstants.DETAIL_URL_PATTERN

    def test_stock_page_url_template_contains_placeholders(self):
        template = ConfigConstants.STOCK_PAGE_URL_TEMPLATE
        assert "{stock_code}" in template
        assert "{org_id}" in template


class TestConfigConstantsTimeouts:
    def test_default_timeouts_is_dict(self):
        assert isinstance(ConfigConstants.DEFAULT_TIMEOUTS, dict)

    def test_required_timeout_keys(self):
        required = ["page_load", "element_wait", "download"]
        for key in required:
            assert key in ConfigConstants.DEFAULT_TIMEOUTS

    def test_all_timeout_values_positive(self):
        for key, val in ConfigConstants.DEFAULT_TIMEOUTS.items():
            assert val > 0, f"Timeout {key} must be positive"


class TestConfigConstantsBrowser:
    def test_default_browser_config(self):
        config = ConfigConstants.DEFAULT_BROWSER_CONFIG
        assert "headless" in config
        assert config["headless"] is True

    def test_browser_launch_args_not_empty(self):
        assert len(ConfigConstants.BROWSER_LAUNCH_ARGS) > 0

    def test_anti_detection_script_not_empty(self):
        assert len(ConfigConstants.ANTI_DETECTION_SCRIPT.strip()) > 0


class TestConfigConstantsFileConfig:
    def test_allowed_extensions(self):
        exts = ConfigConstants.FILE_CONFIG["allowed_extensions"]
        assert ".pdf" in exts


class TestConfigConstantsSharedRefs:
    def test_browser_launch_args_is_chrome_launch_args(self):
        from src.core.constants import CHROME_LAUNCH_ARGS

        assert ConfigConstants.BROWSER_LAUNCH_ARGS is CHROME_LAUNCH_ARGS
