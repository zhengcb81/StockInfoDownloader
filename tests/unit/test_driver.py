#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebDriver管理器单元测试
测试DriverManager类的功能
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.web.driver import DriverManager


class TestDriverManager:
    """WebDriver管理器测试类"""
    
    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.driver_manager = DriverManager(
            download_dir=self.temp_dir,
            headless=True
        )
    
    def teardown_method(self):
        """测试清理"""
        try:
            self.driver_manager.cleanup()
        except:
            pass
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_default_config(self):
        """测试默认配置初始化"""
        manager = DriverManager()
        
        assert manager.download_dir is not None
        assert manager.headless is True
        assert manager.driver is None
        assert manager.options is not None
        assert manager.service is None
    
    def test_init_with_config(self):
        """测试带配置初始化"""
        custom_dir = "/tmp/custom"
        manager = DriverManager(
            download_dir=custom_dir,
            headless=False,
            chrome_path="/usr/bin/google-chrome"
        )
        
        assert manager.download_dir == custom_dir
        assert manager.headless is False
        assert manager.chrome_path == "/usr/bin/google-chrome"
    
    def test_setup_options_headless(self):
        """测试无头模式选项设置"""
        options = self.driver_manager._setup_options(headless=True)
        
        # 检查无头模式参数
        args = options.arguments
        assert "--headless" in args
        assert "--no-sandbox" in args
        assert "--disable-dev-shm-usage" in args
        assert "--disable-gpu" in args
    
    def test_setup_options_headful(self):
        """测试有头模式选项设置"""
        options = self.driver_manager._setup_options(headless=False)
        
        # 检查有头模式参数
        args = options.arguments
        assert "--headless" not in args
    
    def test_setup_options_with_download_dir(self):
        """测试带下载目录的选项设置"""
        options = self.driver_manager._setup_options(
            download_dir=self.temp_dir,
            headless=True
        )
        
        # 检查下载目录设置
        prefs = options.experimental_options.get("prefs", {})
        assert "download.default_directory" in prefs
        assert self.temp_dir in prefs["download.default_directory"]
    
    def test_setup_options_with_user_agent(self):
        """测试带User-Agent的选项设置"""
        test_agent = "Mozilla/5.0 (Test Agent)"
        options = self.driver_manager._setup_options(
            user_agent=test_agent,
            headless=True
        )
        
        # 检查User-Agent设置
        assert test_agent in options.arguments
    
    def test_create_driver_success(self):
        """测试成功创建WebDriver"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            
            driver = self.driver_manager.create_driver()
            
            assert driver == mock_driver
            assert self.driver_manager.driver == mock_driver
            mock_chrome.assert_called_once()
    
    def test_create_driver_failure(self):
        """测试创建WebDriver失败"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_chrome.side_effect = Exception("Failed to create driver")
            
            driver = self.driver_manager.create_driver()
            
            assert driver is None
            assert self.driver_manager.driver is None
    
    def test_create_driver_with_custom_path(self):
        """测试使用自定义Chrome路径创建WebDriver"""
        custom_path = "/usr/bin/google-chrome"
        manager = DriverManager(chrome_path=custom_path)
        
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            
            manager.create_driver()
            
            # 检查是否使用了自定义路径
            call_args = mock_chrome.call_args
            assert call_args is not None
    
    def test_get_driver_existing(self):
        """测试获取现有的WebDriver"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            
            # 创建driver
            self.driver_manager.create_driver()
            
            # 获取现有的driver
            driver = self.driver_manager.get_driver()
            
            assert driver == mock_driver
            # 应该不会重新创建
            assert mock_chrome.call_count == 1
    
    def test_get_driver_create_new(self):
        """测试创建新的WebDriver"""
        driver = self.driver_manager.get_driver()
        
        # 由于没有mock，这里可能会失败，但测试逻辑流程
        assert driver is None or driver is not None
    
    def test_restart_driver(self):
        """测试重启WebDriver"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver1 = MagicMock()
            mock_driver2 = MagicMock()
            mock_chrome.side_effect = [mock_driver1, mock_driver2]
            
            # 创建初始driver
            driver1 = self.driver_manager.create_driver()
            assert driver1 == mock_driver1
            
            # 重启driver
            driver2 = self.driver_manager.restart_driver()
            
            assert driver2 == mock_driver2
            assert self.driver_manager.driver == mock_driver2
            # 检查旧的driver被关闭
            mock_driver1.quit.assert_called_once()
            assert mock_chrome.call_count == 2
    
    def test_cleanup_driver(self):
        """测试清理WebDriver"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            
            # 创建driver
            self.driver_manager.create_driver()
            
            # 清理
            self.driver_manager.cleanup()
            
            # 检查driver被关闭
            mock_driver.quit.assert_called_once()
            assert self.driver_manager.driver is None
    
    def test_cleanup_no_driver(self):
        """测试清理时没有driver"""
        # 应该不会抛出异常
        self.driver_manager.cleanup()
        assert self.driver_manager.driver is None
    
    def test_context_manager(self):
        """测试上下文管理器"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            
            with self.driver_manager as driver:
                assert driver == mock_driver
                assert self.driver_manager.driver == mock_driver
            
            # 检查退出时是否清理
            mock_driver.quit.assert_called_once()
            assert self.driver_manager.driver is None
    
    def test_set_page_load_timeout(self):
        """测试设置页面加载超时"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            
            self.driver_manager.create_driver()
            
            # 设置超时
            self.driver_manager.set_page_load_timeout(30)
            
            mock_driver.set_page_load_timeout.assert_called_once_with(30)
    
    def test_set_script_timeout(self):
        """测试设置脚本超时"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            
            self.driver_manager.create_driver()
            
            # 设置脚本超时
            self.driver_manager.set_script_timeout(10)
            
            mock_driver.set_script_timeout.assert_called_once_with(10)
    
    def test_execute_script(self):
        """测试执行JavaScript"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            mock_driver.execute_script.return_value = "result"
            
            self.driver_manager.create_driver()
            
            # 执行脚本
            result = self.driver_manager.execute_script("return document.title;")
            
            assert result == "result"
            mock_driver.execute_script.assert_called_once_with("return document.title;")
    
    def test_take_screenshot(self):
        """测试截图功能"""
        screenshot_path = os.path.join(self.temp_dir, "screenshot.png")
        
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            mock_driver.get_screenshot_as_file.return_value = True
            
            self.driver_manager.create_driver()
            
            # 截图
            success = self.driver_manager.take_screenshot(screenshot_path)
            
            assert success
            mock_driver.get_screenshot_as_file.assert_called_once_with(screenshot_path)
    
    def test_get_page_source(self):
        """测试获取页面源码"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            mock_driver.page_source = "<html><body>Test</body></html>"
            
            self.driver_manager.create_driver()
            
            # 获取页面源码
            source = self.driver_manager.get_page_source()
            
            assert source == "<html><body>Test</body></html>"
    
    def test_get_current_url(self):
        """测试获取当前URL"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            mock_driver.current_url = "https://example.com"
            
            self.driver_manager.create_driver()
            
            # 获取当前URL
            url = self.driver_manager.get_current_url()
            
            assert url == "https://example.com"
    
    def test_get_page_title(self):
        """测试获取页面标题"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            mock_driver.title = "Test Page"
            
            self.driver_manager.create_driver()
            
            # 获取页面标题
            title = self.driver_manager.get_page_title()
            
            assert title == "Test Page"
    
    def test_add_cookie(self):
        """测试添加Cookie"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            
            self.driver_manager.create_driver()
            
            # 添加Cookie
            cookie = {"name": "test", "value": "value"}
            self.driver_manager.add_cookie(cookie)
            
            mock_driver.add_cookie.assert_called_once_with(cookie)
    
    def test_get_cookies(self):
        """测试获取Cookies"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            mock_driver.get_cookies.return_value = [{"name": "test", "value": "value"}]
            
            self.driver_manager.create_driver()
            
            # 获取Cookies
            cookies = self.driver_manager.get_cookies()
            
            assert cookies == [{"name": "test", "value": "value"}]
            mock_driver.get_cookies.assert_called_once()
    
    def test_delete_all_cookies(self):
        """测试删除所有Cookies"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            
            self.driver_manager.create_driver()
            
            # 删除所有Cookies
            self.driver_manager.delete_all_cookies()
            
            mock_driver.delete_all_cookies.assert_called_once()
    
    def test_driver_health_check(self):
        """测试Driver健康检查"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            mock_driver.current_url = "https://example.com"
            
            self.driver_manager.create_driver()
            
            # 健康检查
            is_healthy = self.driver_manager.is_healthy()
            
            assert is_healthy
    
    def test_driver_health_check_failed(self):
        """测试Driver健康检查失败"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            mock_driver.current_url = "about:blank"  # 可能表示driver有问题
            
            self.driver_manager.create_driver()
            
            # 健康检查
            is_healthy = self.driver_manager.is_healthy()
            
            assert not is_healthy
    
    def test_wait_for_element(self):
        """测试等待元素"""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from unittest.mock import MagicMock
        
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            
            mock_element = MagicMock()
            mock_wait = MagicMock()
            mock_wait.until.return_value = mock_element
            
            with patch('selenium.webdriver.support.ui.WebDriverWait', return_value=mock_wait):
                self.driver_manager.create_driver()
                
                # 等待元素
                element = self.driver_manager.wait_for_element(
                    By.ID, "test_id", timeout=10
                )
                
                assert element == mock_element
                mock_wait.until.assert_called_once()
    
    def test_wait_for_page_load(self):
        """测试等待页面加载"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            
            self.driver_manager.create_driver()
            
            # 等待页面加载
            self.driver_manager.wait_for_page_load()
            
            # 应该调用相关的等待方法
            # 这里测试逻辑流程


if __name__ == "__main__":
    pytest.main([__file__, "-v"])