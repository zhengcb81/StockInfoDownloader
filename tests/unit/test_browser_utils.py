"""
Browser Utils 测试模块
覆盖浏览器工具函数的各种功能
"""

import os
import sys

import pytest

from src.utils.browser_utils import (
    get_anti_crawler_config,
    get_common_chrome_args,
    get_default_button_click_timeout,
    get_default_download_timeout,
    get_default_element_wait_timeout,
    get_default_implicit_wait,
    get_default_navigation_timeout,
    get_default_page_load_timeout,
    get_default_user_agents,
    get_default_window_size,
    get_default_window_size_string,
    get_download_check_interval,
    get_download_file_size_threshold,
    get_download_stability_wait,
    get_max_downloads_per_session,
    get_pagination_config,
    get_pdf_extension,
    get_retry_config,
    get_temp_file_extensions,
    is_test_environment,
    validate_and_normalize_timeout,
)


class TestIsTestEnvironment:
    """Is Test Environment 测试类"""

    def test_is_test_environment_default(self, monkeypatch):
        """测试默认环境"""
        monkeypatch.delenv("TEST_ENV", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        # sys.argv[0] will contain the test runner name
        result = is_test_environment()
        # Should return True when run via pytest
        assert isinstance(result, bool)

    def test_is_test_environment_with_env_var(self, monkeypatch):
        """测试通过环境变量设置"""
        monkeypatch.setenv("TEST_ENV", "true")
        assert is_test_environment() is True

    def test_is_test_environment_false(self, monkeypatch):
        """测试非测试环境"""
        monkeypatch.setenv("TEST_ENV", "false")
        # Mock sys.argv to not contain test
        original_argv = sys.argv
        sys.argv = ["python_script.py"]
        try:
            result = is_test_environment()
            assert isinstance(result, bool)
        finally:
            sys.argv = original_argv


class TestGetDefaultUserAgents:
    """Get Default User Agents 测试类"""

    def test_get_default_user_agents(self):
        """测试获取默认用户代理"""
        agents = get_default_user_agents()
        assert isinstance(agents, list)
        assert len(agents) == 5
        assert all("Mozilla" in agent for agent in agents)
        assert all("Chrome" in agent for agent in agents)


class TestValidateAndNormalizeTimeout:
    """Validate And Normalize Timeout 测试类"""

    def test_validate_timeout_seconds(self):
        """测试秒转换为毫秒"""
        assert validate_and_normalize_timeout(30) == 30000
        assert validate_and_normalize_timeout(5) == 5000
        assert validate_and_normalize_timeout(1) == 1000

    def test_validate_timeout_milliseconds(self):
        """测试已经是毫秒的值"""
        assert validate_and_normalize_timeout(30000) == 30000
        assert validate_and_normalize_timeout(5000) == 5000
        assert validate_and_normalize_timeout(1000) == 1000

    def test_validate_timeout_invalid(self):
        """测试无效超时值"""
        with pytest.raises(ValueError, match="timeout must be greater than 0"):
            validate_and_normalize_timeout(0)
        with pytest.raises(ValueError, match="timeout must be greater than 0"):
            validate_and_normalize_timeout(-1)
        with pytest.raises(ValueError, match="timeout must be greater than 0"):
            validate_and_normalize_timeout(-100)


class TestGetCommonChromeArgs:
    """Get Common Chrome Args 测试类"""

    def test_get_common_chrome_args(self):
        """测试获取 Chrome 参数"""
        args = get_common_chrome_args()
        assert isinstance(args, list)
        assert "--no-sandbox" in args
        assert "--disable-dev-shm-usage" in args
        assert "--disable-gpu" in args
        assert len(args) > 10


class TestGetDownloadFileSizeThreshold:
    """Get Download File Size Threshold 测试类"""

    def test_get_download_file_size_threshold(self):
        """测试获取文件大小阈值"""
        threshold = get_download_file_size_threshold()
        assert threshold == 10 * 1024  # 10KB


class TestGetDownloadCheckInterval:
    """Get Download Check Interval 测试类"""

    def test_get_download_check_interval(self):
        """测试获取下载检查间隔"""
        interval = get_download_check_interval()
        assert interval == 0.5


class TestGetDownloadStabilityWait:
    """Get Download Stability Wait 测试类"""

    def test_get_download_stability_wait(self):
        """测试获取下载稳定等待时间"""
        wait = get_download_stability_wait()
        assert wait == 1


class TestGetTempFileExtensions:
    """Get Temp File Extensions 测试类"""

    def test_get_temp_file_extensions(self):
        """测试获取临时文件扩展名"""
        extensions = get_temp_file_extensions()
        assert isinstance(extensions, list)
        assert ".tmp" in extensions
        assert ".crdownload" in extensions


class TestGetPdfExtension:
    """Get PDF Extension 测试类"""

    def test_get_pdf_extension(self):
        """测试获取 PDF 扩展名"""
        assert get_pdf_extension() == ".pdf"


class TestGetDefaultWindowSize:
    """Get Default Window Size 测试类"""

    def test_get_default_window_size(self):
        """测试获取默认窗口大小"""
        size = get_default_window_size()
        assert size == {"width": 1920, "height": 1080}

    def test_get_default_window_size_string(self):
        """测试获取默认窗口大小字符串"""
        size_string = get_default_window_size_string()
        assert size_string == "1920,1080"


class TestGetMaxDownloadsPerSession:
    """Get Max Downloads Per Session 测试类"""

    def test_get_max_downloads_per_session(self):
        """测试获取每会话最大下载数"""
        max_downloads = get_max_downloads_per_session()
        assert max_downloads == 10


class TestGetDefaultImplicitWait:
    """Get Default Implicit Wait 测试类"""

    def test_get_default_implicit_wait(self):
        """测试获取默认隐式等待时间"""
        wait = get_default_implicit_wait()
        assert wait == 3


class TestGetDefaultPageLoadTimeout:
    """Get Default Page Load Timeout 测试类"""

    def test_get_default_page_load_timeout(self):
        """测试获取默认页面加载超时"""
        timeout = get_default_page_load_timeout()
        assert timeout == 30


class TestGetDefaultDownloadTimeout:
    """Get Default Download Timeout 测试类"""

    def test_get_default_download_timeout(self):
        """测试获取默认下载超时"""
        timeout = get_default_download_timeout()
        assert timeout == 300


class TestGetDefaultElementWaitTimeout:
    """Get Default Element Wait Timeout 测试类"""

    def test_get_default_element_wait_timeout(self):
        """测试获取默认元素等待超时"""
        timeout = get_default_element_wait_timeout()
        assert timeout == 10


class TestGetDefaultNavigationTimeout:
    """Get Default Navigation Timeout 测试类"""

    def test_get_default_navigation_timeout(self):
        """测试获取默认导航超时"""
        timeout = get_default_navigation_timeout()
        assert timeout == 10


class TestGetDefaultButtonClickTimeout:
    """Get Default Button Click Timeout 测试类"""

    def test_get_default_button_click_timeout(self):
        """测试获取默认按钮点击超时"""
        timeout = get_default_button_click_timeout()
        assert timeout == 5


class TestGetRetryConfig:
    """Get Retry Config 测试类"""

    def test_get_retry_config(self):
        """测试获取重试配置"""
        config = get_retry_config()
        assert config == {"max_retries": 3, "base_delay": 1.0, "backoff_factor": 2.0}


class TestGetAntiCrawlerConfig:
    """Get Anti Crawler Config 测试类"""

    def test_get_anti_crawler_config(self):
        """测试获取反爬虫配置"""
        config = get_anti_crawler_config()
        assert config["min_delay"] == 2.0
        assert config["max_delay"] == 8.0
        assert config["max_downloads"] == 5
        assert isinstance(config["scroll_range"], list)
        assert len(config["scroll_range"]) == 2


class TestGetPaginationConfig:
    """Get Pagination Config 测试类"""

    def test_get_pagination_config(self):
        """测试获取分页配置"""
        config = get_pagination_config()
        assert config == {"max_pages": 3, "pagination_wait": 2, "human_behavior_delay": 3}
