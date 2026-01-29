"""
分页功能的单元测试
"""

from unittest.mock import Mock, patch

import pytest

from src.web.scraper import WebScraper


@pytest.fixture(autouse=True)
def mock_time_calls():
    """Mock time.sleep and WebDriverWait calls to prevent hanging in tests"""
    with patch("src.web.scraper.time.sleep") as mock_sleep, patch(
        "src.web.scraper.WebDriverWait"
    ) as mock_wait:
        # Mock WebDriverWait to return immediately
        mock_wait.return_value.wait.return_value = None
        mock_wait.return_value.until.return_value = None
        yield


class TestWebScraperPagination:
    """测试WebScraper的分页功能"""

    def test_has_next_page_found(self):
        """测试找到下一页按钮"""
        mock_driver = Mock()
        mock_element = Mock()
        mock_element.is_enabled.return_value = True
        mock_element.is_displayed.return_value = True

        # 模拟找到下一页按钮
        mock_driver.find_element.return_value = mock_element

        scraper = WebScraper(mock_driver)
        result = scraper.has_next_page()

        assert result is True

    def test_has_next_page_not_found(self):
        """测试未找到下一页按钮"""
        mock_driver = Mock()

        # 模拟未找到元素
        from selenium.common.exceptions import NoSuchElementException

        mock_driver.find_element.side_effect = NoSuchElementException()

        scraper = WebScraper(mock_driver)
        result = scraper.has_next_page()

        assert result is False

    def test_go_to_next_page_success(self):
        """测试成功跳转到下一页"""
        mock_driver = Mock()
        mock_element = Mock()
        mock_element.is_enabled.return_value = True
        mock_element.is_displayed.return_value = True

        # 模拟找到并点击下一页按钮
        mock_driver.find_element.return_value = mock_element
        mock_driver.execute_script.return_value = None

        with patch("selenium.webdriver.support.wait.WebDriverWait"):
            scraper = WebScraper(mock_driver)
            result = scraper.go_to_next_page()

            assert result is True
            mock_element.click.assert_called_once()

    def test_go_to_next_page_failed(self):
        """测试跳转下一页失败"""
        mock_driver = Mock()

        # 模拟未找到下一页按钮
        from selenium.common.exceptions import NoSuchElementException

        mock_driver.find_element.side_effect = NoSuchElementException()

        scraper = WebScraper(mock_driver)
        result = scraper.go_to_next_page()

        assert result is False

    def test_get_current_page_info(self):
        """测试获取当前页面信息"""
        mock_driver = Mock()
        mock_element = Mock()
        mock_element.text = "共 10 页"

        # 模拟找到分页信息
        mock_driver.find_element.return_value = mock_element

        # 模拟has_next_page返回False
        with patch.object(WebScraper, "has_next_page", return_value=False):
            scraper = WebScraper(mock_driver)
            info = scraper.get_current_page_info()

            assert info["current_page"] == 1
            assert info["total_pages"] == 10
            assert info["has_next"] is False

    def test_wait_for_page_load_success(self):
        """测试等待页面加载成功"""
        mock_driver = Mock()
        mock_driver.execute_script.return_value = "complete"

        with patch("selenium.webdriver.support.wait.WebDriverWait"):
            scraper = WebScraper(mock_driver)
            result = scraper.wait_for_page_load()

            assert result is True

    def test_wait_for_page_load_timeout(self):
        """测试等待页面加载超时"""
        mock_driver = Mock()

        # 模拟超时异常 - 补丁与fixture相同的路径
        from selenium.common.exceptions import TimeoutException

        with patch("src.web.scraper.WebDriverWait", side_effect=TimeoutException()):
            scraper = WebScraper(mock_driver)
            result = scraper.wait_for_page_load()

            assert result is False

    def test_pagination_selectors_fallback(self):
        """测试分页选择器的回退机制"""
        mock_driver = Mock()

        # 模拟所有选择器都失败
        from selenium.common.exceptions import NoSuchElementException

        mock_driver.find_element.side_effect = NoSuchElementException()

        scraper = WebScraper(mock_driver)

        # 测试has_next_page
        result = scraper.has_next_page()
        assert result is False

        # 测试go_to_next_page
        result = scraper.go_to_next_page()
        assert result is False

    def test_page_info_parsing_formats(self):
        """测试不同格式的页面信息解析"""
        mock_driver = Mock()
        scraper = WebScraper(mock_driver)

        # 测试 "共 10 页" 格式
        with patch.object(WebScraper, "has_next_page", return_value=False):
            mock_element = Mock()
            mock_element.text = "共 10 页"
            mock_driver.find_element.return_value = mock_element

            info = scraper.get_current_page_info()
            assert info["total_pages"] == 10
            assert info["current_page"] == 1

            # 测试 "1/10" 格式
            mock_element.text = "1/10"
            info = scraper.get_current_page_info()
            assert info["current_page"] == 1
            assert info["total_pages"] == 10

    def test_exception_handling(self):
        """测试异常处理"""
        mock_driver = Mock()
        mock_driver.find_element.side_effect = Exception("Unexpected error")

        scraper = WebScraper(mock_driver)

        # 异常应该被捕获并返回安全值
        result = scraper.has_next_page()
        assert result is False

        info = scraper.get_current_page_info()
        assert info["current_page"] == 1
        assert info["total_pages"] == 1
        assert info["has_next"] is False
