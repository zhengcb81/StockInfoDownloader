"""
Selenium浏览器自动化策略实现
"""

import os
import random
import time
import subprocess
import platform
from typing import Optional, List, Any, Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from .browser_strategy import BrowserAutomationStrategy
from ..core.exceptions import (
    WebDriverError, WebDriverInitError, WebDriverTimeoutError, WebDriverCrashError,
    ErrorCode, ErrorSeverity, RecoveryStrategy, with_error_handling
)
from ..core.logger import get_logger
from ..core.config import ConfigManager

logger = get_logger(__name__)


def is_test_environment():
    """检测是否为测试环境"""
    import sys
    return (
        os.environ.get('TEST_ENV') == 'true' or
        'test' in sys.argv[0].lower() or
        'pytest' in sys.argv[0].lower() or
        os.environ.get('PYTEST_CURRENT_TEST') is not None
    )


class SeleniumStrategy(BrowserAutomationStrategy):
    """Selenium浏览器自动化策略"""
    
    def __init__(self, headless: bool = True, download_dir: Optional[str] = None, 
                 config: Optional[Dict[str, Any]] = None):
        """初始化Selenium策略"""
        self.headless = headless
        self.download_dir = download_dir
        self.config = config or {}
        self.driver = None
        self.download_count = 0
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        
        # 从配置获取参数
        self.window_size = self.config.get('window_size', '1920,1080')
        self.page_load_timeout = self.config.get('page_load_timeout', 15)
        self.implicit_wait = self.config.get('implicit_wait', 3)
        self.max_downloads_per_session = self.config.get('max_downloads_per_session', 10)
        
        self._user_agents = self.config.get('user_agents', [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        ])
    
    @with_error_handling(
        error_code=ErrorCode.WEBDRIVER_INIT_ERROR,
        severity=ErrorSeverity.CRITICAL,
        recovery_strategy=RecoveryStrategy.RETRY,
        max_retries=3
    )
    def create_driver(self) -> Any:
        """创建WebDriver实例"""
        # 确保之前的driver完全关闭
        if self.driver:
            self.close()
        
        logger.info("正在初始化Selenium WebDriver...")
        
        # 只有在非测试环境才清理进程
        if not is_test_environment():
            self._cleanup_chrome_processes()
        
        try:
            chrome_options = self._build_chrome_options()
            
            # 创建driver
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
            except Exception as create_error:
                logger.error(f"ChromeDriver创建失败: {create_error}")
                # 尝试清理并重新创建
                self._cleanup_chrome_processes()
                time.sleep(2)
                self.driver = webdriver.Chrome(options=chrome_options)
            
            # 配置driver
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.implicitly_wait(self.implicit_wait)
            
            # 执行反检测脚本
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 测试driver是否正常工作
            self.driver.get("about:blank")
            
            logger.info("Selenium WebDriver初始化成功")
            return self.driver
            
        except WebDriverException as e:
            error_msg = f"WebDriver创建失败: {e}"
            logger.error(error_msg)
            
            # 清理失败的driver
            if self.driver:
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
    
    def _build_chrome_options(self) -> Options:
        """构建Chrome选项"""
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
        
        # 稳定性选项
        stability_options = [
            '--no-first-run', '--no-default-browser-check',
            '--disable-background-timer-throttling', '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding', '--disable-sync', '--disable-translate',
            '--disable-default-apps', '--disable-notifications', '--disable-popup-blocking',
            '--log-level=3', '--disable-features=TranslateUI',
            '--disable-component-extensions-with-background-pages',
            '--disable-domain-reliability', '--disable-setuid-sandbox',
            '--disable-features=VizDisplayCompositor', '--disable-ipc-flooding-protection',
        ]
        
        for option in stability_options:
            chrome_options.add_argument(option)
        
        # 反自动化检测
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 设置下载目录
        if self.download_dir:
            abs_download_dir = os.path.abspath(self.download_dir)
            os.makedirs(abs_download_dir, exist_ok=True)
            
            if platform.system() == "Windows":
                abs_download_dir = abs_download_dir.replace("/", "\\")
            
            prefs = {
                "download.default_directory": abs_download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True,
                "safebrowsing.enabled": True,
                "profile.default_content_settings.popups": 0,
                "profile.default_content_setting_values.automatic_downloads": 1,
                "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,
                "download_restrictions": 3,
                "credentials_enable_service": False,
                "password_manager_enabled": False
            }
            chrome_options.add_experimental_option("prefs", prefs)
            logger.info(f"设置下载目录: {abs_download_dir}")
        
        # 随机User-Agent
        user_agent = random.choice(self._user_agents)
        chrome_options.add_argument(f'--user-agent={user_agent}')
        
        return chrome_options
    
    def _cleanup_chrome_processes(self):
        """清理Chrome进程"""
        try:
            if is_test_environment():
                return
                
            timeout_value = 5
            
            if platform.system() == "Windows":
                subprocess.run(['taskkill', '/f', '/im', 'chromedriver.exe'], 
                             capture_output=True, timeout=timeout_value, check=False)
            else:
                subprocess.run(['pkill', '-f', 'chromedriver'], 
                             capture_output=True, timeout=timeout_value, check=False)
            
            time.sleep(0.5)
            
        except Exception as e:
            logger.debug(f"清理Chrome进程时发生错误: {e}")
    
    def get_driver(self) -> Any:
        """获取当前驱动实例"""
        return self.driver
    
    def navigate(self, url: str) -> bool:
        """导航到指定URL"""
        if not self.driver:
            return False
        
        try:
            self.driver.get(url)
            return True
        except Exception as e:
            logger.error(f"导航到 {url} 失败: {e}")
            return False
    
    def find_elements(self, selector: str, by: str = "css") -> List[Any]:
        """查找元素"""
        if not self.driver:
            return []
        
        try:
            by_method = getattr(By, by.upper(), By.CSS_SELECTOR)
            return self.driver.find_elements(by_method, selector)
        except Exception as e:
            logger.error(f"查找元素失败: {e}")
            return []
    
    def find_element(self, selector: str, by: str = "css") -> Optional[Any]:
        """查找单个元素"""
        elements = self.find_elements(selector, by)
        return elements[0] if elements else None
    
    def click(self, element: Any) -> bool:
        """点击元素"""
        if not element:
            return False
        
        try:
            element.click()
            return True
        except Exception as e:
            logger.error(f"点击元素失败: {e}")
            return False
    
    def get_text(self, element: Any) -> str:
        """获取元素文本"""
        if not element:
            return ""
        
        try:
            return element.text
        except Exception as e:
            logger.error(f"获取元素文本失败: {e}")
            return ""
    
    def get_attribute(self, element: Any, attribute: str) -> Optional[str]:
        """获取元素属性"""
        if not element:
            return None
        
        try:
            return element.get_attribute(attribute)
        except Exception as e:
            logger.error(f"获取元素属性失败: {e}")
            return None
    
    def execute_script(self, script: str, *args) -> Any:
        """执行JavaScript脚本"""
        if not self.driver:
            return None
        
        try:
            return self.driver.execute_script(script, *args)
        except Exception as e:
            logger.error(f"执行脚本失败: {e}")
            return None
    
    def wait_for_element(self, selector: str, timeout: int = 10, 
                        by: str = "css", condition: str = "visible") -> bool:
        """等待元素出现"""
        if not self.driver:
            return False
        
        try:
            by_method = getattr(By, by.upper() if hasattr(By, by.upper()) else By.CSS_SELECTOR)
            wait = WebDriverWait(self.driver, timeout)
            
            if condition == "presence":
                wait.until(EC.presence_of_element_located((by_method, selector)))
            elif condition == "visible":
                wait.until(EC.visibility_of_element_located((by_method, selector)))
            elif condition == "clickable":
                wait.until(EC.element_to_be_clickable((by_method, selector)))
            
            return True
            
        except Exception:
            return False
    
    def get_page_source(self) -> str:
        """获取页面源代码"""
        if not self.driver:
            return ""
        
        try:
            return self.driver.page_source
        except Exception as e:
            logger.error(f"获取页面源代码失败: {e}")
            return ""
    
    def get_current_url(self) -> str:
        """获取当前URL"""
        if not self.driver:
            return ""
        
        try:
            return self.driver.current_url
        except Exception as e:
            logger.error(f"获取当前URL失败: {e}")
            return ""

    def get_page_title(self) -> str:
        """获取页面标题"""
        if not self.driver:
            return ""
        
        try:
            return self.driver.title
        except Exception as e:
            logger.error(f"获取页面标题失败: {e}")
            return ""
    
    def close(self) -> None:
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium WebDriver已关闭")
            except Exception as e:
                logger.error(f"关闭WebDriver时发生错误: {e}")
            finally:
                self.driver = None
                self.download_count = 0
    
    def is_healthy(self) -> bool:
        """检查浏览器是否健康"""
        if not self.driver:
            return False
        
        try:
            self.driver.current_url
            return True
        except Exception:
            return False
    
    def restart(self) -> bool:
        """重启浏览器"""
        logger.info("正在重启Selenium WebDriver...")
        
        self.close()
        
        # 增强重试机制
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.info(f"尝试重启WebDriver (第 {attempt + 1}/{max_attempts} 次)...")
                self.create_driver()
                logger.info("WebDriver重启成功")
                return True
                
            except Exception as e:
                logger.error(f"WebDriver重启尝试 {attempt + 1} 异常: {e}")
                
                if attempt < max_attempts - 1:
                    retry_wait = random.uniform(2, 4)
                    logger.info(f"等待 {retry_wait:.2f} 秒后重试...")
                    time.sleep(retry_wait)
        
        logger.error("WebDriver重启失败，已尝试所有重试次数")
        return False
    
    def take_screenshot(self, save_path: Optional[str] = None) -> Optional[bytes]:
        """截取屏幕截图"""
        if not self.driver:
            return None
        
        try:
            screenshot_data = self.driver.get_screenshot_as_png()
            
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(screenshot_data)
            
            return screenshot_data
        except Exception as e:
            logger.error(f"截取屏幕截图失败: {e}")
            return None

    def download_file(self, url: str, save_path: str, timeout: int = 30) -> bool:
        """
        下载文件到指定路径
        
        Args:
            url: 要下载的URL
            save_path: 文件保存路径
            timeout: 超时时间（秒）
            
        Returns:
            bool: 下载是否成功
        """
        if not self.driver:
            logger.error("浏览器未初始化，无法下载文件")
            return False
        
        try:
            
            # 记录下载前的文件列表 - 递归检查所有PDF文件
            before_files = set()
            if os.path.exists(self.download_dir):
                for root, dirs, files in os.walk(self.download_dir):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            before_files.add(os.path.join(root, file))
            
            # 导航到详情页
            if not self.navigate(url):
                logger.error(f"无法导航到详情页: {url}")
                return False
            
            # 等待页面加载
            time.sleep(3)
            
            # 查找并点击下载按钮（公告下载）
            download_button = self.find_element("//button[contains(., '公告下载')]", by="xpath")
            if not download_button:
                logger.error("未找到下载按钮")
                return False
            
            # 点击下载按钮
            if not self.click(download_button):
                logger.error("点击下载按钮失败")
                return False
            
            logger.info("已点击下载按钮，等待文件下载...")
            
            # 等待文件下载完成
            start_time = time.time()
            check_interval = 0.5

            while time.time() - start_time < timeout:
                time.sleep(check_interval)
                check_interval = min(check_interval * 1.2, 2.0)

                # 检查新文件 - 增强检测逻辑
                if os.path.exists(self.download_dir):
                    after_files = set()
                    # 递归检查所有子目录
                    for root, dirs, files in os.walk(self.download_dir):
                        for file in files:
                            if file.lower().endswith('.pdf'):
                                after_files.add(os.path.join(root, file))

                    new_files = after_files - before_files

                    for file_path in new_files:
                        downloaded_file = Path(file_path)
                        if downloaded_file.exists() and downloaded_file.stat().st_size > 10 * 1024:
                            # 移动文件到目标位置
                            target_dir = Path(save_path).parent
                            target_dir.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(downloaded_file), save_path)
                            logger.info(f"文件下载成功: {save_path}")
                            return True

                # 检查目标文件是否已存在（可能被其他进程移动）
                if os.path.exists(save_path) and os.path.getsize(save_path) > 10 * 1024:
                    logger.info(f"文件已下载: {save_path}")
                    return True

                # 检查临时文件（Chrome下载时可能使用临时文件名）
                temp_files = []
                if os.path.exists(self.download_dir):
                    for file in os.listdir(self.download_dir):
                        if file.endswith('.crdownload') or file.endswith('.tmp'):
                            temp_files.append(file)
                            logger.debug(f"发现临时文件: {file}")

            logger.error(f"文件下载超时: {save_path}")
            # 检查是否有部分下载的文件
            if os.path.exists(save_path):
                file_size = os.path.getsize(save_path)
                logger.error(f"文件已存在但大小异常: {file_size} bytes")
            return False
            
        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return False

    def go_to_next_page(self, timeout: int = 10) -> bool:
        """
        跳转到下一页

        Args:
            timeout: 超时时间（秒）

        Returns:
            bool: 是否成功跳转
        """
        if not self.driver:
            logger.error("浏览器未初始化，无法翻页")
            return False

        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            from selenium.common.exceptions import TimeoutException, NoSuchElementException

            next_selectors = [
                "button.el-pagination__next:not(.is-disabled)",
                ".pagination .next:not(.disabled)",
                "a[aria-label='下一页']:not(.disabled)",
                ".el-pager li.number.active + li.number",
                "button[aria-label='Next page']:not([disabled])"
            ]

            for selector in next_selectors:
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_button and next_button.is_enabled() and next_button.is_displayed():
                        # 滚动到元素位置
                        self.driver.execute_script("arguments[0].scrollIntoView();", next_button)
                        time.sleep(0.5)

                        # 点击下一页
                        next_button.click()

                        # 等待页面加载
                        WebDriverWait(self.driver, timeout).until(
                            EC.staleness_of(next_button)
                        )
                        return True

                except (NoSuchElementException, TimeoutException):
                    continue

            logger.info("没有找到下一页按钮或已到达最后一页")
            return False

        except Exception as e:
            logger.error(f"跳转到下一页失败: {e}")
            return False

    def go_to_page(self, page_number: int, timeout: int = 10) -> bool:
        """
        跳转到指定页码

        Args:
            page_number: 目标页码
            timeout: 超时时间（秒）

        Returns:
            bool: 是否成功跳转
        """
        if not self.driver:
            logger.error("浏览器未初始化，无法翻页")
            return False

        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            from selenium.common.exceptions import TimeoutException, NoSuchElementException

            # 方法1: 查找页码输入框和跳转按钮
            page_input_selectors = [
                "input.el-pagination__editor",
                "input.page-input",
                "input[type='number']",
                "input.pagination-input"
            ]

            go_button_selectors = [
                "button.el-pagination__jump",
                "button.page-go",
                "button:contains('跳转')",
                "button:contains('Go')"
            ]

            for input_selector, button_selector in zip(page_input_selectors, go_button_selectors):
                try:
                    # 查找页码输入框
                    page_input = self.driver.find_element(By.CSS_SELECTOR, input_selector)
                    if not page_input.is_enabled() or not page_input.is_displayed():
                        continue

                    # 查找跳转按钮
                    go_button = self.driver.find_element(By.CSS_SELECTOR, button_selector)
                    if not go_button.is_enabled() or not go_button.is_displayed():
                        continue

                    # 清空输入框并输入页码
                    page_input.clear()
                    page_input.send_keys(str(page_number))

                    # 点击跳转按钮
                    go_button.click()

                    # 等待页面加载
                    WebDriverWait(self.driver, timeout).until(
                        EC.staleness_of(page_input)
                    )

                    logger.info(f"成功跳转到第{page_number}页")
                    return True

                except (NoSuchElementException, TimeoutException):
                    continue

            # 方法2: 直接点击页码按钮
            page_button_selectors = [
                f".el-pager li.number:not(.active)",
                f".pagination li:not(.active)",
                f"a:not(.active)",
                f"button:not([disabled])"
            ]

            for selector in page_button_selectors:
                try:
                    page_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for page_button in page_buttons:
                        if page_button.is_enabled() and page_button.is_displayed():
                            button_text = page_button.text.strip()
                            if button_text == str(page_number):
                                # 滚动到元素位置
                                self.driver.execute_script("arguments[0].scrollIntoView();", page_button)
                                time.sleep(0.5)

                                # 点击页码按钮
                                page_button.click()

                                # 等待页面加载
                                time.sleep(3)
                                logger.info(f"成功跳转到第{page_number}页")
                                return True

                except (NoSuchElementException, TimeoutException):
                    continue

            logger.warning(f"无法跳转到第{page_number}页")
            return False

        except Exception as e:
            logger.error(f"跳转到指定页码失败: {e}")
            return False

    def has_next_page(self, timeout: int = 5) -> bool:
        """
        检查是否有下一页

        Args:
            timeout: 超时时间（秒）

        Returns:
            bool: 是否有下一页
        """
        if not self.driver:
            logger.error("浏览器未初始化，无法检查翻页")
            return False

        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            from selenium.common.exceptions import TimeoutException, NoSuchElementException

            next_selectors = [
                "button.el-pagination__next:not(.is-disabled)",
                ".pagination .next:not(.disabled)",
                "a[aria-label='下一页']:not(.disabled)",
                ".el-pager li.number.active + li.number",
                "button[aria-label='Next page']:not([disabled])"
            ]

            for selector in next_selectors:
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_button and next_button.is_enabled() and next_button.is_displayed():
                        return True
                except (NoSuchElementException, TimeoutException):
                    continue

            return False

        except Exception as e:
            logger.warning(f"检查下一页失败: {e}")
            return False