"""
WebDriver管理模块
提供统一的WebDriver创建、管理和生命周期控制
"""

import os
import random
import logging
import time
import subprocess
import platform
from typing import Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from ..core.exceptions import WebDriverError
from ..core.logger import get_logger
from ..core.config import ConfigManager

logger = get_logger(__name__)


class WebDriverManager:
    """WebDriver管理器，提供统一的WebDriver创建和管理"""
    
    def __init__(self, 
                 headless: bool = True,
                 window_size: str = "1920,1080",
                 page_load_timeout: int = 30,
                 implicit_wait: int = 5,
                 download_dir: Optional[str] = None,
                 max_downloads_per_session: int = 5,
                 config_file: Optional[str] = None):
        """
        初始化WebDriver管理器
        
        Args:
            headless: 是否使用无头模式
            window_size: 浏览器窗口大小
            page_load_timeout: 页面加载超时时间(秒)
            implicit_wait: 隐式等待时间(秒)
            download_dir: 下载文件保存目录
            max_downloads_per_session: 每个会话最大下载数
            config_file: 配置文件路径
        """
        # 初始化配置管理器
        self.config_manager = ConfigManager(config_file)
        
        # 从配置获取参数，如果未提供则使用默认值
        self.headless = headless if headless is not None else self.config_manager.get('webdriver.headless', True)
        self.window_size = window_size if window_size is not None else self.config_manager.get('webdriver.window_size', '1920,1080')
        self.page_load_timeout = page_load_timeout if page_load_timeout is not None else self.config_manager.get('timeout.page_load', 60)
        self.implicit_wait = implicit_wait if implicit_wait is not None else self.config_manager.get('timeout.element_wait', 10)
        self.download_dir = download_dir
        self.driver = None
        self.download_count = 0
        self.max_downloads_per_session = max_downloads_per_session if max_downloads_per_session is not None else self.config_manager.get('download.max_downloads_per_session', 5)
        self._user_agents = self.config_manager.get('webdriver.user_agents', [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ])
    
    def create_driver(self, custom_options: Optional[Dict[str, Any]] = None, download_dir: Optional[str] = None) -> webdriver.Chrome:
        """
        创建新的WebDriver实例，包含重试机制和进程清理
        
        Args:
            custom_options: 自定义Chrome选项
            download_dir: 下载目录
            
        Returns:
            webdriver.Chrome: Chrome WebDriver实例
            
        Raises:
            WebDriverError: WebDriver创建失败
        """
        # 确保之前的driver完全关闭
        if self.driver:
            self.close_driver()
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.info(f"正在初始化WebDriver (尝试 {attempt + 1}/{max_attempts})...")
                
                # 清理可能存在的僵尸进程
                self._cleanup_chrome_processes()
                
                chrome_options = Options()
                
                # 基础设置
                if self.headless:
                    chrome_options.add_argument('--headless=new')  # 使用新的headless模式
                chrome_options.add_argument(f'--window-size={self.window_size}')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--disable-extensions')
                chrome_options.add_argument('--disable-web-security')
                chrome_options.add_argument('--disable-features=VizDisplayCompositor')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_argument('--remote-debugging-port=0')
                
                # 性能优化：从配置读取页面加载策略
                page_load_strategy = self.config_manager.get_page_load_strategy()
                chrome_options.page_load_strategy = page_load_strategy
                
                # 增加稳定性选项 - 防止标签页崩溃
                chrome_options.add_argument('--disable-software-rasterizer')
                chrome_options.add_argument('--disable-background-timer-throttling')
                chrome_options.add_argument('--disable-backgrounding-occluded-windows')
                chrome_options.add_argument('--disable-renderer-backgrounding')
                chrome_options.add_argument('--no-first-run')
                chrome_options.add_argument('--no-default-browser-check')
                chrome_options.add_argument('--disable-sync')
                chrome_options.add_argument('--disable-translate')
                chrome_options.add_argument('--disable-default-apps')
                chrome_options.add_argument('--disable-notifications')
                chrome_options.add_argument('--disable-popup-blocking')
                chrome_options.add_argument('--disable-logging')
                chrome_options.add_argument('--log-level=3')  # 只记录错误
                
                # 防止标签页崩溃的额外选项
                chrome_options.add_argument('--disable-features=TranslateUI')
                chrome_options.add_argument('--disable-ipc-flooding-protection')
                chrome_options.add_argument('--disable-extensions-except=test')
                chrome_options.add_argument('--disable-component-extensions-with-background-pages')
                chrome_options.add_argument('--disable-component-update')
                chrome_options.add_argument('--disable-domain-reliability')
                chrome_options.add_argument('--disable-background-mode')
                chrome_options.add_argument('--disable-background-timer-throttling')
                chrome_options.add_argument('--disable-renderer-backgrounding')
                chrome_options.add_argument('--disable-ipc-flooding-protection')
                
                # 内存管理优化
                chrome_options.add_argument('--max_old_space_size=128')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-setuid-sandbox')
                # 移除单进程模式，使用多进程提高稳定性
            
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                
                # 设置下载目录（如果提供了）
                if download_dir:
                    prefs = {
                        "download.default_directory": os.path.abspath(download_dir),
                        "download.prompt_for_download": False,
                        "download.directory_upgrade": True,
                        "plugins.always_open_pdf_externally": True
                    }
                    chrome_options.add_experimental_option("prefs", prefs)
                
                # 增加内存和性能优化
                chrome_options.add_argument('--memory-pressure-off')
                chrome_options.add_argument('--disable-device-discovery-notifications')
                
                # 随机User-Agent
                user_agent = random.choice(self._user_agents)
                chrome_options.add_argument(f'--user-agent={user_agent}')
                
                # 自定义选项
                if custom_options:
                    for key, value in custom_options.items():
                        if value is True:
                            chrome_options.add_argument(key)
                        elif value is not False:
                            chrome_options.add_argument(f'{key}={value}')
                
                # 创建driver
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.set_page_load_timeout(self.page_load_timeout)
                self.driver.implicitly_wait(self.implicit_wait)
                
                # 执行反检测脚本
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                # 测试driver是否正常工作
                self.driver.get("about:blank")
                
                logger.info("WebDriver初始化成功")
                return self.driver
                
            except Exception as e:
                logger.warning(f"WebDriver初始化尝试 {attempt + 1} 失败: {e}")
                
                # 清理失败的driver
                if hasattr(self, 'driver') and self.driver:
                    try:
                        self.driver.quit()
                    except Exception:
                        pass
                    self.driver = None
                
                if attempt < max_attempts - 1:
                    wait_time = random.uniform(3, 8)
                    logger.info(f"等待 {wait_time:.2f} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"WebDriver初始化失败，已尝试所有重试次数")
                    raise WebDriverError(f"WebDriver初始化失败: {e}")
        
        # 如果所有尝试都失败
        logger.error("WebDriver初始化失败，已尝试所有重试次数")
        raise WebDriverError("WebDriver初始化失败，已尝试所有重试次数")
    
    def get_driver(self) -> Optional[webdriver.Chrome]:
        """
        获取当前WebDriver实例
        
        Returns:
            webdriver.Chrome: WebDriver实例，如果未创建则返回None
        """
        return self.driver
    
    def _cleanup_chrome_processes(self):
        """清理可能存在的Chrome僵尸进程（从旧下载器复制）"""
        try:
            # 只清理chromedriver进程，不清理chrome浏览器进程
            if platform.system() == "Windows":
                # Windows系统只清理chromedriver进程
                try:
                    subprocess.run(['taskkill', '/f', '/im', 'chromedriver.exe'], 
                                 capture_output=True, timeout=10)
                except Exception:
                    pass
            else:
                # Linux/Mac系统只清理chromedriver进程
                try:
                    subprocess.run(['pkill', '-f', 'chromedriver'], 
                                 capture_output=True, timeout=10)
                except Exception:
                    pass
                    
            time.sleep(1)  # 等待进程完全结束
            
        except Exception as e:
            logger.debug(f"清理Chrome进程时发生错误: {e}")
    
    def is_driver_healthy(self) -> bool:
        """检查driver是否健康（从旧下载器复制）"""
        try:
            if not self.driver:
                return False
            
            # 尝试获取当前URL来测试driver是否响应
            current_url = self.driver.current_url
            return True
            
        except Exception as e:
            logger.debug(f"Driver健康检查失败: {e}")
            return False
    
    def restart_driver(self, custom_options: Optional[Dict[str, Any]] = None) -> bool:
        """重启WebDriver（从旧下载器复制增强版）"""
        logger.info("正在重启WebDriver...")
        
        # 彻底关闭当前driver
        self.close_driver()
        
        # 等待更长时间确保进程完全结束
        wait_time = random.uniform(5, 12)
        logger.info(f"等待 {wait_time:.2f} 秒确保进程完全结束...")
        time.sleep(wait_time)
        
        # 尝试多次重启
        max_restart_attempts = 3
        for attempt in range(max_restart_attempts):
            try:
                logger.info(f"尝试重启WebDriver (第 {attempt + 1}/{max_restart_attempts} 次)...")
                self.create_driver(custom_options)
                logger.info("WebDriver重启成功")
                return True
                
            except Exception as e:
                logger.error(f"WebDriver重启尝试 {attempt + 1} 异常: {e}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_restart_attempts - 1:
                retry_wait = random.uniform(8, 15)
                logger.info(f"等待 {retry_wait:.2f} 秒后重试...")
                time.sleep(retry_wait)
        
        logger.error("WebDriver重启失败，已尝试所有重试次数")
        return False
    
    def close_driver(self) -> None:
        """关闭WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver已关闭")
            except Exception as e:
                logger.error(f"关闭WebDriver时发生错误: {e}")
            finally:
                self.driver = None
    
    def restart_driver(self) -> webdriver.Chrome:
        """
        重启WebDriver
        
        Returns:
            webdriver.Chrome: 新的WebDriver实例
        """
        self.close_driver()
        return self.create_driver()
    
    def wait_for_element(self, 
                        by: str, 
                        value: str, 
                        timeout: int = 10,
                        condition: str = "presence") -> bool:
        """
        等待元素出现
        
        Args:
            by: 查找方式(By.ID, By.CLASS_NAME等)
            value: 查找值
            timeout: 超时时间(秒)
            condition: 等待条件(presence, visible, clickable)
            
        Returns:
            bool: 是否找到元素
        """
        if not self.driver:
            return False
        
        try:
            wait = WebDriverWait(self.driver, timeout)
            
            if condition == "presence":
                wait.until(EC.presence_of_element_located((getattr(By, by.upper()), value)))
            elif condition == "visible":
                wait.until(EC.visibility_of_element_located((getattr(By, by.upper()), value)))
            elif condition == "clickable":
                wait.until(EC.element_to_be_clickable((getattr(By, by.upper()), value)))
            
            return True
            
        except Exception:
            return False
    
    def is_driver_active(self) -> bool:
        """检查WebDriver是否活跃"""
        if not self.driver:
            return False
        
        try:
            # 尝试访问一个简单页面来检查driver是否可用
            self.driver.title
            return True
        except Exception:
            return False
    
    def __enter__(self):
        """上下文管理器入口"""
        return self.create_driver()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close_driver()