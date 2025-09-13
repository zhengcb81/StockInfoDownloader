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
import sys
from typing import Dict, Any, Optional, Union
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from ..core.exceptions import (
    WebDriverError, WebDriverInitError, WebDriverTimeoutError, 
    WebDriverCrashError, ErrorCode, ErrorSeverity, RecoveryStrategy,
    with_error_handling, handle_error
)
from ..core.logger import get_logger
from ..core.config import ConfigManager
from ..core.performance_monitor import monitor_performance, monitor_operation, performance_monitor

logger = get_logger(__name__)


def is_test_environment():
    """检测是否为测试环境"""
    return (
        os.environ.get('TEST_ENV') == 'true' or
        'test' in sys.argv[0].lower() or
        'pytest' in sys.argv[0].lower() or
        os.environ.get('PYTEST_CURRENT_TEST') is not None
    )


class WebDriverManager:
    """WebDriver管理器，提供统一的WebDriver创建和管理"""
    
    def __init__(self, 
                 headless: bool = True,
                 window_size: str = "1920,1080",
                 page_load_timeout: int = 15,
                 implicit_wait: int = 3,
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
        self.page_load_timeout = page_load_timeout if page_load_timeout is not None else self.config_manager.get('timeout.page_load', 8)
        self.implicit_wait = implicit_wait if implicit_wait is not None else self.config_manager.get('timeout.element_wait', 2)
        self.download_dir = download_dir
        self.driver = None
        self.download_count = 0
        self.max_downloads_per_session = max_downloads_per_session if max_downloads_per_session is not None else self.config_manager.get('download.max_downloads_per_session', 10)
        self._user_agents = self.config_manager.get('webdriver.user_agents', [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ])
    
    @monitor_performance("WebDriverManager.create_driver")
    @with_error_handling(
        error_code=ErrorCode.WEBDRIVER_INIT_ERROR,
        severity=ErrorSeverity.CRITICAL,
        recovery_strategy=RecoveryStrategy.RETRY,
        max_retries=3
    )
    def create_driver(self, custom_options: Optional[Dict[str, Any]] = None, download_dir: Optional[str] = None) -> webdriver.Chrome:
        """
        创建新的WebDriver实例，包含重试机制和进程清理
        
        Args:
            custom_options: 自定义Chrome选项
            download_dir: 下载目录
            
        Returns:
            webdriver.Chrome: Chrome WebDriver实例
            
        Raises:
            WebDriverInitError: WebDriver创建失败
        """
        # 确保之前的driver完全关闭
        if self.driver:
            self.close_driver()
        
        logger.info("正在初始化WebDriver...")
        
        # 只有在非测试环境才清理进程
        if not is_test_environment():
            self._cleanup_chrome_processes()
        
        try:
            chrome_options = self._build_chrome_options(custom_options, download_dir)
            
            # 创建driver - 添加更好的错误处理
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
            except Exception as create_error:
                logger.error(f"ChromeDriver创建失败: {create_error}")
                # 尝试清理并重新创建
                self._cleanup_chrome_processes()
                time.sleep(2)
                self.driver = webdriver.Chrome(options=chrome_options)
            
            try:
                self.driver.set_page_load_timeout(self.page_load_timeout)
                self.driver.implicitly_wait(self.implicit_wait)
                
                # 执行反检测脚本
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                # 测试driver是否正常工作 - 使用更安全的测试
                self.driver.get("about:blank")
                
                logger.info("WebDriver初始化成功")
                return self.driver
            except Exception as setup_error:
                logger.error(f"WebDriver配置失败: {setup_error}")
                # 如果配置失败，尝试重新启动
                self._cleanup_chrome_processes()
                raise setup_error
            
        except WebDriverException as e:
            error_msg = f"WebDriver创建失败: {e}"
            logger.error(error_msg)
            
            # 清理失败的driver
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
            
            # 根据错误类型抛出不同的异常
            if "tab crashed" in str(e).lower():
                raise WebDriverCrashError(
                    error_msg,
                    context={"phase": "initialization", "crash_type": "tab_crashed"},
                    original_exception=e
                )
            elif "timeout" in str(e).lower():
                raise WebDriverTimeoutError(
                    error_msg,
                    context={"phase": "initialization", "timeout_type": "creation_timeout"},
                    original_exception=e
                )
            else:
                raise WebDriverInitError(
                    error_msg,
                    context={"phase": "initialization", "error_details": str(e)},
                    original_exception=e
                )
        except Exception as e:
            error_msg = f"WebDriver初始化过程中发生未知错误: {e}"
            logger.error(error_msg)
            raise WebDriverInitError(
                error_msg,
                context={"phase": "initialization", "error_type": "unknown"},
                original_exception=e
            )
    
    def _build_chrome_options(self, custom_options: Optional[Dict[str, Any]] = None, 
                             download_dir: Optional[str] = None) -> Options:
        """构建Chrome选项"""
        try:
            chrome_options = Options()
            
            # 基础设置
            if self.headless:
                chrome_options.add_argument('--headless=new')
            chrome_options.add_argument(f'--window-size={self.window_size}')
            
            # 必要的Chrome选项
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--remote-debugging-port=0')
            
            # 精简的稳定性选项（移除冗余和冲突的选项）
            essential_stability_options = [
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-sync',
                '--disable-translate',
                '--disable-default-apps',
                '--disable-notifications',
                '--disable-popup-blocking',
                '--log-level=3',
                '--disable-features=TranslateUI',
                '--disable-component-extensions-with-background-pages',
                '--disable-domain-reliability',
                '--disable-setuid-sandbox',
                # 网络性能优化
                '--disable-features=VizDisplayCompositor',
                '--disable-ipc-flooding-protection',
            ]
            
            for option in essential_stability_options:
                chrome_options.add_argument(option)
            
            # 性能优化：从配置读取页面加载策略
            page_load_strategy = self.config_manager.get_page_load_strategy()
            chrome_options.page_load_strategy = page_load_strategy
            
            # 反自动化检测
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 设置下载目录（如果提供了）
            if download_dir:
                abs_download_dir = os.path.abspath(download_dir)
                # 确保下载目录存在
                os.makedirs(abs_download_dir, exist_ok=True)
                
                # Windows系统需要使用反斜杠路径分隔符
                if platform.system() == "Windows":
                    abs_download_dir = abs_download_dir.replace("/", "\\")
                
                prefs = {
                    "download.default_directory": abs_download_dir,
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "plugins.always_open_pdf_externally": True,
                    "safebrowsing.enabled": True,  # 改为True，某些Chrome版本需要
                    "profile.default_content_settings.popups": 0,
                    "profile.default_content_setting_values.automatic_downloads": 1,
                    "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,
                    # 添加更多必要的下载偏好设置
                    "download_restrictions": 3,  # 允许所有下载
                    "credentials_enable_service": False,
                    "password_manager_enabled": False
                }
                chrome_options.add_experimental_option("prefs", prefs)
                logger.info(f"设置下载目录: {abs_download_dir}")
            
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
            
            return chrome_options
            
        except Exception as e:
            raise WebDriverInitError(
                f"构建Chrome选项失败: {e}",
                context={"phase": "option_building", "custom_options": str(custom_options)},
                original_exception=e
            )
    
    def get_driver(self) -> Optional[webdriver.Chrome]:
        """
        获取当前WebDriver实例
        
        Returns:
            webdriver.Chrome: WebDriver实例，如果未创建则返回None
        """
        return self.driver
    
    def _cleanup_chrome_processes(self):
        """清理可能存在的Chrome僵尸进程（优化版本）"""
        try:
            # 只在非测试环境执行清理
            if is_test_environment():
                return
                
            # 设置合理的超时时间
            timeout_value = 5
            
            # 清理chromedriver进程
            if platform.system() == "Windows":
                # Windows系统 - 只清理chromedriver进程
                try:
                    subprocess.run(['taskkill', '/f', '/im', 'chromedriver.exe'], 
                                 capture_output=True, timeout=timeout_value, check=False)
                except Exception:
                    pass
            else:
                # Linux/Mac系统
                try:
                    subprocess.run(['pkill', '-f', 'chromedriver'], 
                                 capture_output=True, timeout=timeout_value, check=False)
                except Exception:
                    pass
            
            # 短暂等待确保进程结束
            time.sleep(0.5)
            
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
    
    @monitor_performance("WebDriverManager.restart_driver")
    @with_error_handling(
        error_code=ErrorCode.WEBDRIVER_SESSION_ERROR,
        severity=ErrorSeverity.ERROR,
        recovery_strategy=RecoveryStrategy.RETRY,
        max_retries=3
    )
    def restart_driver(self, custom_options: Optional[Dict[str, Any]] = None, 
                   enhanced_retry: bool = True) -> Union[webdriver.Chrome, bool]:
        """
        重启WebDriver，支持增强的重试机制
        
        Args:
            custom_options: 自定义Chrome选项
            enhanced_retry: 是否使用增强的重试机制（多次尝试、随机延迟）
            
        Returns:
            webdriver.Chrome: 如果enhanced_retry=False，返回新的WebDriver实例
            bool: 如果enhanced_retry=True，返回是否重启成功
        """
        logger.info("正在重启WebDriver...")
        
        # 彻底关闭当前driver
        self.close_driver()
        
        if enhanced_retry:
            # 增强重试模式：多次尝试、随机延迟
            wait_time = random.uniform(2, 4)  # 减少到2-4秒
            logger.info(f"等待 {wait_time:.2f} 秒确保进程完全结束...")
            time.sleep(wait_time)
            
            max_restart_attempts = 3
            for attempt in range(max_restart_attempts):
                try:
                    logger.info(f"尝试重启WebDriver (第 {attempt + 1}/{max_restart_attempts} 次)...")
                    self.create_driver(custom_options)
                    logger.info("WebDriver重启成功")
                    return True
                    
                except WebDriverError as e:
                    logger.error(f"WebDriver重启尝试 {attempt + 1} 异常: {e}")
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < max_restart_attempts - 1:
                    retry_wait = random.uniform(2, 4)
                    logger.info(f"等待 {retry_wait:.2f} 秒后重试...")
                    time.sleep(retry_wait)
            
            logger.error("WebDriver重启失败，已尝试所有重试次数")
            return False
        else:
            # 简单重启模式：直接创建新的driver
            try:
                return self.create_driver(custom_options)
            except WebDriverError as e:
                logger.error(f"WebDriver简单重启失败: {e}")
                if not enhanced_retry:
                    raise
                return False
    
    def close_driver(self) -> None:
        """关闭WebDriver（优化版本）"""
        if self.driver:
            try:
                # 简单直接地关闭driver
                self.driver.quit()
                logger.info("WebDriver已关闭")
                
            except Exception as e:
                logger.error(f"关闭WebDriver时发生错误: {e}")
            finally:
                self.driver = None
                # 重置下载计数
                self.download_count = 0
    
    def force_cleanup(self) -> None:
        """强制清理所有WebDriver相关资源"""
        try:
            # 关闭当前driver
            self.close_driver()
            
            # 强制清理Chrome进程
            self._cleanup_chrome_processes()
            
            # 强制垃圾回收
            import gc
            for _ in range(3):
                gc.collect()
            
            logger.info("强制清理完成")
            
        except Exception as e:
            logger.error(f"强制清理失败: {e}")
    
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
        """上下文管理器出口，包含强制清理"""
        try:
            self.close_driver()
        except Exception as e:
            logger.error(f"上下文管理器关闭失败: {e}")
            # 即使关闭失败，也尝试强制清理
            self.force_cleanup()


# 为向后兼容性提供 DriverManager 别名
DriverManager = WebDriverManager