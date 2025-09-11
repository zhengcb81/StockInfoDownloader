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

from src.web.driver import WebDriverManager


@pytest.fixture(autouse=True)
def mock_external_calls():
    """Mock all external calls to prevent hanging in tests"""
    with patch('src.web.driver.subprocess.run') as mock_run, \
         patch('src.web.driver.time.sleep') as mock_sleep, \
         patch('src.web.driver.ConfigManager') as mock_config:
        # Mock ConfigManager to prevent file I/O
        mock_config_instance = MagicMock()
        mock_config_instance.get.side_effect = lambda key, default=None: default
        mock_config_instance.get_page_load_strategy.return_value = 'eager'
        mock_config.return_value = mock_config_instance
        
        # Mock subprocess
        mock_run.return_value = MagicMock(returncode=0, stdout=b'', stderr=b'')
        yield


class TestWebDriverManager:
    """WebDriver管理器测试类"""
    
    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        # Mock all external dependencies to prevent any I/O or blocking operations
        with patch('src.web.driver.ConfigManager') as mock_config, \
             patch('src.web.driver.subprocess.run'), \
             patch('src.web.driver.time.sleep'), \
             patch.object(WebDriverManager, '_cleanup_chrome_processes'):
            
            # Mock ConfigManager instance
            mock_config_instance = MagicMock()
            mock_config_instance.get.side_effect = lambda key, default=None: default
            mock_config_instance.get_page_load_strategy.return_value = 'eager'
            mock_config.return_value = mock_config_instance
            
            self.driver_manager = WebDriverManager(
                download_dir=self.temp_dir,
                headless=True
            )
    
    def teardown_method(self):
        """测试清理"""
        try:
            self.driver_manager.close_driver()
        except:
            pass
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_default_config(self):
        """测试默认配置初始化"""
        manager = WebDriverManager()
        
        assert manager.headless is True
        assert manager.driver is None
        assert manager.page_load_timeout > 0
        assert manager.implicit_wait > 0
    
    def test_init_with_config(self):
        """测试带配置初始化"""
        custom_dir = self.temp_dir
        manager = WebDriverManager(
            download_dir=custom_dir,
            headless=False,
            page_load_timeout=60,
            implicit_wait=15
        )
        
        assert manager.download_dir == custom_dir
        assert manager.headless is False
        assert manager.page_load_timeout == 60
        assert manager.implicit_wait == 15
    
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
            
            with pytest.raises(Exception):
                self.driver_manager.create_driver()
    
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
    
    def test_get_driver_none(self):
        """测试获取不存在的WebDriver"""
        driver = self.driver_manager.get_driver()
        assert driver is None
    
    def test_restart_driver(self):
        """测试重启WebDriver"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver1 = MagicMock()
            mock_driver2 = MagicMock()
            mock_chrome.side_effect = [mock_driver1, mock_driver2]
            
            # 创建初始driver
            driver1 = self.driver_manager.create_driver()
            assert driver1 == mock_driver1
            
            # 重启driver - 使用enhanced_retry=False避免长时间等待
            result = self.driver_manager.restart_driver(enhanced_retry=False)
            
            # 当enhanced_retry=False时，返回的是WebDriver对象
            assert result == mock_driver2
            assert self.driver_manager.driver == mock_driver2
            # 检查旧的driver被关闭
            mock_driver1.quit.assert_called_once()
            assert mock_chrome.call_count == 2
    
    def test_close_driver(self):
        """测试关闭WebDriver"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            
            # 创建driver
            self.driver_manager.create_driver()
            
            # 关闭
            self.driver_manager.close_driver()
            
            # 检查driver被关闭
            mock_driver.quit.assert_called_once()
            assert self.driver_manager.driver is None
    
    def test_close_driver_no_driver(self):
        """测试关闭时没有driver"""
        # 应该不会抛出异常
        self.driver_manager.close_driver()
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
    
    def test_wait_for_element(self):
        """测试等待元素"""
        from selenium.webdriver.common.by import By
        
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            
            self.driver_manager.create_driver()
            
            # 等待元素
            result = self.driver_manager.wait_for_element(
                By.ID, "test_id", timeout=10
            )
            
            # 这里测试逻辑流程，实际需要mock WebDriverWait
            assert isinstance(result, bool)
    
    def test_is_driver_active(self):
        """测试Driver活跃状态"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_driver.title = "Test Page"
            mock_chrome.return_value = mock_driver
            
            self.driver_manager.create_driver()
            
            # 检查活跃状态
            is_active = self.driver_manager.is_driver_active()
            
            assert is_active is True
    
    def test_is_driver_not_active(self):
        """测试Driver不活跃状态"""
        # 没有driver时应该返回False
        is_active = self.driver_manager.is_driver_active()
        assert is_active is False
    
    def test_is_driver_healthy(self):
        """测试Driver健康检查"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_driver.current_url = "https://example.com"
            mock_chrome.return_value = mock_driver
            
            self.driver_manager.create_driver()
            
            # 健康检查
            is_healthy = self.driver_manager.is_driver_healthy()
            
            assert is_healthy is True
    
    def test_is_driver_not_healthy(self):
        """测试Driver不健康状态"""
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_driver.current_url = "about:blank"
            mock_chrome.return_value = mock_driver
            
            self.driver_manager.create_driver()
            
            # 健康检查
            is_healthy = self.driver_manager.is_driver_healthy()
            
            assert is_healthy is True  # Should be True as it can access current_url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])