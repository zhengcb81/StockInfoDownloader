"""
Selenium Driver Factory Module Tests
Tests for Chrome driver factory functionality
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.constants import BrowserConfig, TimeoutConfig
from src.web.selenium.driver_factory import ChromeDriverFactory


class TestChromeDriverFactory:
    """ChromeDriverFactory class tests"""

    def test_init_default(self):
        """Test initialization with default values"""
        factory = ChromeDriverFactory()
        assert factory.headless is True
        assert factory.download_dir is None
        assert factory.config == {}
        assert factory.window_size == BrowserConfig.DEFAULT_WINDOW_SIZE
        assert factory._user_agents is not None

    def test_init_with_params(self):
        """Test initialization with custom parameters"""
        config = {
            "window_size": "1280,720",
            "timeout": 60,
            "implicit_wait": 5,
            "user_agents": ["Test/1.0"],
        }
        factory = ChromeDriverFactory(
            headless=False,
            download_dir="/tmp/downloads",
            config=config
        )
        assert factory.headless is False
        assert factory.download_dir == "/tmp/downloads"
        assert factory.config == config
        assert factory.window_size == "1280,720"
        assert factory.page_load_timeout == 60
        assert factory.implicit_wait == 5

    def test_init_with_partial_config(self):
        """Test initialization with partial config"""
        config = {"window_size": "800,600"}
        factory = ChromeDriverFactory(config=config)
        assert factory.window_size == "800,600"
        # Should use defaults for missing values
        assert factory.page_load_timeout == TimeoutConfig.PAGE_LOAD
        assert factory.implicit_wait == BrowserConfig.IMPLICIT_WAIT

    def test_build_chrome_options_headless(self):
        """Test building chrome options with headless"""
        factory = ChromeDriverFactory(headless=True)
        with patch("src.web.selenium.driver_factory.get_common_chrome_args", return_value=["--test-arg"]):
            options = factory._build_chrome_options()
            assert options is not None
            # Verify headless argument was added
            args = options.arguments
            assert "--headless=new" in args

    def test_build_chrome_options_not_headless(self):
        """Test building chrome options without headless"""
        factory = ChromeDriverFactory(headless=False)
        with patch("src.web.selenium.driver_factory.get_common_chrome_args", return_value=["--test-arg"]):
            options = factory._build_chrome_options()
            args = options.arguments
            assert "--headless=new" not in args

    def test_build_chrome_options_window_size(self):
        """Test building chrome options with window size"""
        factory = ChromeDriverFactory(config={"window_size": "1280,720"})
        with patch("src.web.selenium.driver_factory.get_common_chrome_args", return_value=[]):
            options = factory._build_chrome_options()
            args = options.arguments
            assert "--window-size=1280,720" in args

    def test_build_chrome_options_excludes_automation_switches(self):
        """Test building chrome options excludes automation switches"""
        factory = ChromeDriverFactory()
        with patch("src.web.selenium.driver_factory.get_common_chrome_args", return_value=[]):
            options = factory._build_chrome_options()
            experimental_options = options.experimental_options
            assert "excludeSwitches" in experimental_options
            assert "enable-automation" in experimental_options["excludeSwitches"]

    def test_build_chrome_options_disables_automation_extension(self):
        """Test building chrome options disables automation extension"""
        factory = ChromeDriverFactory()
        with patch("src.web.selenium.driver_factory.get_common_chrome_args", return_value=[]):
            options = factory._build_chrome_options()
            experimental_options = options.experimental_options
            assert experimental_options.get("useAutomationExtension") is False

    def test_build_chrome_options_with_download_dir(self):
        """Test building chrome options with download directory"""
        import platform
        with patch("os.makedirs"), \
             patch("os.path.abspath", return_value="/abs/path/downloads"), \
             patch("src.web.selenium.driver_factory.get_common_chrome_args", return_value=[]):
            factory = ChromeDriverFactory(download_dir="downloads")
            options = factory._build_chrome_options()

            experimental_options = options.experimental_options
            assert "prefs" in experimental_options
            prefs = experimental_options["prefs"]
            # On Windows, paths are converted to backslashes
            expected_path = "\\abs\\path\\downloads" if platform.system() == "Windows" else "/abs/path/downloads"
            assert prefs["download.default_directory"] == expected_path
            assert prefs["download.prompt_for_download"] is False

    @patch("platform.system", return_value="Windows")
    def test_build_chrome_options_windows_path(self, mock_platform):
        """Test building chrome options on Windows"""
        with patch("os.makedirs"), \
             patch("os.path.abspath", return_value="C:\\Downloads"), \
             patch("src.web.selenium.driver_factory.get_common_chrome_args", return_value=[]):
            factory = ChromeDriverFactory(download_dir="downloads")
            options = factory._build_chrome_options()

            prefs = options.experimental_options.get("prefs", {})
            # Windows path should be used
            assert "download.default_directory" in prefs

    def test_build_chrome_options_user_agent(self):
        """Test building chrome options adds user agent"""
        factory = ChromeDriverFactory(config={"user_agents": ["TestAgent/1.0"]})
        with patch("src.web.selenium.driver_factory.get_common_chrome_args", return_value=[]):
            with patch("random.choice", return_value="TestAgent/1.0"):
                options = factory._build_chrome_options()
                args = options.arguments
                assert any("--user-agent=TestAgent/1.0" in arg for arg in args)

    def test_cleanup_chrome_processes_test_environment(self):
        """Test cleanup skips in test environment"""
        with patch("src.web.selenium.driver_factory.is_test_environment", return_value=True):
            factory = ChromeDriverFactory()
            factory._cleanup_chrome_processes()
            # Should return early without running subprocess

    @patch("src.web.selenium.driver_factory.is_test_environment", return_value=False)
    @patch("platform.system", return_value="Linux")
    def test_cleanup_chrome_processes_linux(self, mock_platform, mock_test_env):
        """Test cleanup on Linux"""
        with patch("subprocess.run") as mock_run, \
             patch("time.sleep"):
            factory = ChromeDriverFactory()
            factory._cleanup_chrome_processes()

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args == ["pkill", "-f", "chromedriver"]

    @patch("src.web.selenium.driver_factory.is_test_environment", return_value=False)
    @patch("platform.system", return_value="Windows")
    def test_cleanup_chrome_processes_windows(self, mock_platform, mock_test_env):
        """Test cleanup on Windows"""
        with patch("subprocess.run") as mock_run, \
             patch("time.sleep"):
            factory = ChromeDriverFactory()
            factory._cleanup_chrome_processes()

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args == ["taskkill", "/f", "/im", "chromedriver.exe"]

    @patch("src.web.selenium.driver_factory.is_test_environment", return_value=False)
    def test_cleanup_handles_exceptions(self, mock_test_env):
        """Test cleanup handles exceptions gracefully"""
        with patch("subprocess.run", side_effect=Exception("Cleanup error")):
            factory = ChromeDriverFactory()
            # Should not raise exception
            factory._cleanup_chrome_processes()

    def test_create_driver_mock(self):
        """Test create driver with mocked webdriver"""
        mock_driver = MagicMock()
        mock_driver_instance = MagicMock()

        with patch("selenium.webdriver.Chrome", return_value=mock_driver_instance), \
             patch("src.web.selenium.driver_factory.is_test_environment", return_value=True), \
             patch("src.web.selenium.driver_factory.get_common_chrome_args", return_value=[]):
            factory = ChromeDriverFactory()
            result = factory.create_driver()

            assert result is mock_driver_instance
            # Verify driver was configured
            mock_driver_instance.set_page_load_timeout.assert_called_once()
            mock_driver_instance.implicitly_wait.assert_called_once()

    def test_create_driver_with_retry_on_failure(self):
        """Test create driver retries on failure"""
        mock_driver = MagicMock()
        mock_driver_instance = MagicMock()

        # Fail first time, succeed second time
        with patch("selenium.webdriver.Chrome", side_effect=[Exception("First error"), mock_driver_instance]), \
             patch("src.web.selenium.driver_factory.is_test_environment", return_value=True), \
             patch("src.web.selenium.driver_factory.get_common_chrome_args", return_value=[]), \
             patch("time.sleep"):
            factory = ChromeDriverFactory()
            result = factory.create_driver()

            assert result is mock_driver_instance

    def test_cleanup_processes_before_create(self):
        """Test that cleanup is called before creating driver in non-test env"""
        with patch("selenium.webdriver.Chrome") as mock_chrome, \
             patch("src.web.selenium.driver_factory.is_test_environment", return_value=False), \
             patch("src.web.selenium.driver_factory.get_common_chrome_args", return_value=[]), \
             patch.object(ChromeDriverFactory, "_cleanup_chrome_processes") as mock_cleanup:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver

            factory = ChromeDriverFactory()
            factory.create_driver()

            # Cleanup should be called first
            assert mock_cleanup.call_count >= 1

    def test_page_source_url_config(self):
        """Test driver navigates to blank page after creation"""
        mock_driver = MagicMock()
        mock_driver_instance = MagicMock()

        with patch("selenium.webdriver.Chrome", return_value=mock_driver_instance), \
             patch("src.web.selenium.driver_factory.is_test_environment", return_value=True), \
             patch("src.web.selenium.driver_factory.get_common_chrome_args", return_value=[]):
            factory = ChromeDriverFactory()
            factory.create_driver()

            # Should navigate to blank page
            mock_driver_instance.get.assert_called()

    def test_experimental_prefs_download_settings(self):
        """Test download settings in experimental prefs"""
        with patch("os.makedirs"), \
             patch("os.path.abspath", return_value="/test/path"), \
             patch("src.web.selenium.driver_factory.get_common_chrome_args", return_value=[]):
            factory = ChromeDriverFactory(download_dir="/test")
            options = factory._build_chrome_options()

            prefs = options.experimental_options.get("prefs", {})
            # Verify download-related preferences
            assert "download.default_directory" in prefs
            assert "download.prompt_for_download" in prefs
            assert "plugins.always_open_pdf_externally" in prefs
            assert "credentials_enable_service" in prefs
            assert "password_manager_enabled" in prefs
