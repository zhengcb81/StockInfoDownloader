"""
Selenium浏览器自动化策略实现
"""

import os
import random
import time
import subprocess
import platform
import shutil
from pathlib import Path
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
from ..utils.browser_utils import (
    is_test_environment,
    get_default_user_agents,
    get_common_chrome_args,
    get_default_window_size_string
)
from ..utils.cleanup_utils import safe_cleanup
from ..core.constants import (
    TimeoutConfig, BrowserConfig, USER_AGENTS, FileSizeThreshold, SelectorConfig
)

logger = get_logger(__name__)


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

        # 使用常量配置
        self.window_size = self.config.get('window_size', BrowserConfig.DEFAULT_WINDOW_SIZE)

        # BaseDownloader的timeout是秒，需要转换为秒（Selenium使用秒）
        timeout_seconds = self.config.get('timeout', TimeoutConfig.PAGE_LOAD)
        self.page_load_timeout = self.config.get('page_load_timeout', timeout_seconds)
        self.implicit_wait = self.config.get('implicit_wait', BrowserConfig.IMPLICIT_WAIT)
        self.max_downloads_per_session = self.config.get('max_downloads_per_session', BrowserConfig.MAX_DOWNLOADS_PER_SESSION)

        # 使用常量用户代理
        self._user_agents = self.config.get('user_agents', USER_AGENTS)
    
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
                time.sleep(TimeoutConfig.RETRY_DELAY)
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

        except Exception as e:
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

    def initialize(self) -> bool:
        """
        初始化浏览器（兼容IBrowserStrategy接口）

        Returns:
            bool: 初始化是否成功
        """
        try:
            if not self.driver:
                self.create_driver()
            return self.driver is not None
        except Exception as e:
            logger.error(f"初始化失败: {e}")

            # 清理失败的driver
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None

            return False
    
    def _build_chrome_options(self) -> Options:
        """构建Chrome选项"""
        chrome_options = Options()

        # 基础设置
        if self.headless:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument(f'--window-size={self.window_size}')

        # 使用公共工具获取通用Chrome参数
        for arg in get_common_chrome_args():
            chrome_options.add_argument(arg)

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
                "download_restrictions": 0,  # 允许所有下载
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

            time.sleep(TimeoutConfig.BROWSER_CLOSE)

        except Exception as e:
            logger.debug(f"清理Chrome进程时发生错误: {e}")
    
    def get_driver(self) -> Any:
        """获取当前驱动实例"""
        return self.driver

    def cleanup(self) -> None:
        """
        清理浏览器资源（实现接口）
        """
        try:
            self.close()
        except Exception as e:
            logger.error(f"Selenium清理失败: {e}")

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

    def navigate_to_page(self, url: str) -> bool:
        """
        导航到指定页面（兼容IBrowserStrategy接口）

        Args:
            url: 目标URL

        Returns:
            bool: 导航是否成功
        """
        return self.navigate(url)

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
            by_method = getattr(By, by.upper(), By.CSS_SELECTOR)
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
        """关闭浏览器（优化版）"""
        if self.driver:
            safe_cleanup(self.driver.quit, "关闭WebDriver失败")

        # 重置状态
        self.driver = None
        self.download_count = 0

        logger.info("Selenium WebDriver已关闭")
    
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

    def download_file(self, url: str, save_path: str, timeout: int = 10) -> bool:
        """
        下载文件到指定路径（重构版）

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
            # 1. 准备下载
            if not self._prepare_download():
                return False

            # 2. 导航到详情页并等待
            if not self._navigate_to_detail_page(url):
                return False

            # 3. 点击下载按钮
            if not self._click_download_button():
                return False

            # 4. 等待并移动文件
            return self._wait_and_move_file(save_path, timeout)

        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return False

    def _prepare_download(self) -> bool:
        """
        准备下载：记录下载前的文件状态

        Returns:
            bool: 是否准备成功
        """
        # 记录下载前的文件列表 - 检查根目录和所有子目录
        logger.debug(f"download_dir type: {type(self.download_dir)}, value: {self.download_dir}")
        self._before_files = set()

        if self.download_dir and os.path.exists(self.download_dir):
            # 递归检查所有目录，包括子目录
            for root, dirs, files in os.walk(self.download_dir):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        file_path = os.path.join(root, file)
                        self._before_files.add(file_path)

        logger.debug(f"before_files (all directories): {self._before_files}")
        return True

    def _navigate_to_detail_page(self, url: str) -> bool:
        """
        导航到详情页并等待页面准备就绪

        Args:
            url: 目标URL

        Returns:
            bool: 导航是否成功
        """
        # 导航到详情页
        if not self.navigate(url):
            logger.error(f"无法导航到详情页: {url}")
            return False

        # 等待页面加载
        if not self._wait_for_page_ready():
            return False

        # 检查当前URL，处理SPA应用
        current_url = self.get_current_url()
        logger.info(f"当前URL: {current_url}")
        logger.info(f"目标URL: {url}")

        # 如果URL不匹配，可能是SPA应用，尝试直接访问详情页
        if current_url != url and "/new/disclosure/detail" in url:
            logger.info("检测到SPA导航问题，尝试直接访问详情页")
            self.driver.get(url)

            # 添加固定等待时间，确保页面完全加载（参考测试通过版本）
            time.sleep(5)

            if not self._wait_for_page_ready():
                return False

            # 再次检查URL
            current_url = self.get_current_url()
            logger.info(f"直接访问后URL: {current_url}")

        return True

    def _wait_for_page_ready(self) -> bool:
        """
        等待页面准备就绪

        Returns:
            bool: 页面是否准备就绪
        """
        # 尝试等待下载按钮出现，超时5秒
        if self.wait_for_element("//button[contains(., '公告下载')]", timeout=5, by="xpath", condition="visible"):
            return True

        # 如果下载按钮未出现，等待页面标题包含"巨潮资讯网"
        logger.info("下载按钮未立即出现，等待页面加载完成")
        start_time = time.time()
        while time.time() - start_time < 5:
            if "巨潮资讯网" in self.get_page_title():
                return True
            time.sleep(TimeoutConfig.SHORT_WAIT)

        logger.warning("页面加载超时，但继续尝试")
        return True  # 即使超时也继续，让后续逻辑处理

    def _click_download_button(self) -> bool:
        """
        查找并点击下载按钮（使用WebDriverWait确保按钮可点击）

        Returns:
            bool: 是否成功点击
        """
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            from selenium.common.exceptions import TimeoutException

            # 使用WebDriverWait等待按钮可点击（30秒超时，与测试通过版本一致）
            download_btn = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., '公告下载')]"))
            )

            # 点击下载按钮
            download_btn.click()
            logger.info("已点击下载按钮，等待文件下载...")
            return True

        except TimeoutException:
            logger.error("等待下载按钮超时（30秒），尝试替代选择器")

            # 尝试其他选择器
            alternative_selectors = [
                "//button[contains(., '下载')]",
                "//a[contains(., '公告下载')]",
                "//a[contains(., '下载')]",
                "//button[contains(., 'PDF')]",
                "//a[contains(., 'PDF')]",
                ".download-btn",
                ".pdf-download"
            ]

            for selector in alternative_selectors:
                try:
                    by_method = By.XPATH if "//" in selector else By.CSS_SELECTOR
                    download_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((by_method, selector))
                    )
                    download_btn.click()
                    logger.info(f"使用替代选择器找到并点击下载按钮: {selector}")
                    return True
                except TimeoutException:
                    continue

            logger.error("所有选择器都未找到可点击的下载按钮")
            return False

        except Exception as e:
            logger.error(f"点击下载按钮失败: {e}")
            return False

    def _wait_and_move_file(self, save_path: str, timeout: int) -> bool:
        """
        等待文件下载完成并移动到目标位置

        Args:
            save_path: 目标保存路径
            timeout: 超时时间（秒）

        Returns:
            bool: 是否成功下载并移动
        """
        start_time = time.time()
        check_interval = 0.5

        while time.time() - start_time < timeout:
            time.sleep(check_interval)
            check_interval = min(check_interval * 1.2, 2.0)

            # 检查新文件
            downloaded_file = self._check_for_new_file()
            if downloaded_file:
                if self._handle_downloaded_file(downloaded_file, save_path):
                    return True

            # 检查目标文件是否已存在（可能被其他进程移动）
            if self._check_target_file_exists(save_path):
                return True

            # 输出进度信息
            self._log_download_progress(start_time)

        # 超时处理
        return self._handle_timeout(save_path, start_time)

    def _check_for_new_file(self):
        """
        检查是否有新下载的文件

        Returns:
            Path or None: 新下载的文件路径
        """
        if not self.download_dir or not os.path.exists(self.download_dir):
            return None

        after_files = set()
        # 递归检查所有目录，包括子目录
        for root, dirs, files in os.walk(self.download_dir):
            for file in files:
                # 检查PDF文件和临时文件
                if file.lower().endswith('.pdf') or file.endswith('.tmp'):
                    file_path = os.path.join(root, file)
                    after_files.add(Path(file_path))

        logger.debug(f"after_files (all directories): {after_files}")
        logger.debug(f"before_files: {self._before_files}")

        new_files = after_files - self._before_files
        logger.debug(f"new_files: {new_files}")

        if not new_files:
            return None

        # 找到最大的新文件（通常是最新的下载）
        downloaded_file = None
        max_size = 0
        for f in new_files:
            if f.exists():
                try:
                    size = f.stat().st_size
                    if size > max_size:
                        max_size = size
                        downloaded_file = f
                except:
                    pass

        return downloaded_file

    def _handle_downloaded_file(self, downloaded_file: Path, save_path: str) -> bool:
        """
        处理已下载的文件

        Args:
            downloaded_file: 下载的文件路径
            save_path: 目标保存路径

        Returns:
            bool: 是否处理成功
        """
        if not downloaded_file or not downloaded_file.exists():
            return False

        file_size = downloaded_file.stat().st_size
        if file_size <= FileSizeThreshold.MIN_VALID_PDF:
            logger.debug(f"文件大小过小: {file_size} bytes")
            return False

        # 处理临时文件
        if downloaded_file.suffix == '.tmp':
            if not self._wait_for_temp_file_completion(downloaded_file):
                return False

        # 移动文件到目标位置
        return self._move_file_to_target(downloaded_file, save_path)

    def _find_download_button(self):
        """查找下载按钮"""
        # 主选择器
        download_button = self.find_element("//button[contains(., '公告下载')]", by="xpath")
        if download_button:
            return download_button

        # 备选选择器
        for selector in SelectorConfig.DOWNLOAD_BUTTON_ALTERNATIVES:
            download_button = self.find_element(selector, by="xpath" if "//" in selector else "css")
            if download_button:
                logger.info(f"使用替代选择器找到下载按钮: {selector}")
                return download_button

        return None

    def _get_pdf_files_in_download_dir(self) -> set:
        """获取下载目录中的PDF文件集合"""
        if not self.download_dir or not os.path.exists(self.download_dir):
            return set()

        files = set()
        # 递归检查所有目录，包括子目录
        for root, dirs, file_list in os.walk(self.download_dir):
            for file in file_list:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path) and file.lower().endswith('.pdf'):
                    files.add(file_path)
        return files

    def _wait_for_temp_file_completion(self, temp_file: Path) -> bool:
        """
        等待临时文件下载完成

        Args:
            temp_file: 临时文件路径

        Returns:
            bool: 是否完成
        """
        # 检查临时文件是否稳定（不再增长）
        time.sleep(FileSizeThreshold.DOWNLOAD_STABILITY_WAIT)
        current_size = temp_file.stat().st_size
        time.sleep(FileSizeThreshold.DOWNLOAD_STABILITY_WAIT)
        new_size = temp_file.stat().st_size

        if current_size == new_size and current_size > FileSizeThreshold.MIN_VALID_PDF:
            # 临时文件下载完成，重命名为PDF
            pdf_file = temp_file.with_suffix('.pdf')
            try:
                temp_file.rename(pdf_file)
                return True
            except Exception as e:
                logger.warning(f"重命名临时文件失败: {e}")
                return False
        else:
            # 文件还在下载中
            return False

    def _move_file_to_target(self, source_file: Path, save_path: str) -> bool:
        """
        移动文件到目标位置

        Args:
            source_file: 源文件路径
            save_path: 目标保存路径

        Returns:
            bool: 是否移动成功
        """
        logger.debug(f"save_path type: {type(save_path)}, value: {save_path}")
        logger.debug(f"downloaded_file: {source_file}")

        # 确保目标目录存在
        target_dir = Path(save_path).parent
        target_dir.mkdir(parents=True, exist_ok=True)

        # 检查源文件和目标文件是否相同
        target_path = Path(save_path)
        if source_file.resolve() == target_path.resolve():
            logger.debug(f"源文件和目标文件相同，无需移动: {source_file}")
            # 但仍然需要验证文件大小
            if source_file.stat().st_size > FileSizeThreshold.MIN_VALID_PDF:
                logger.info(f"文件已就位: {save_path}")
                return True
            else:
                logger.debug(f"文件大小无效: {source_file.stat().st_size}")
                return False

        try:
            # 检查源文件是否存在且可访问
            if not source_file.exists() or source_file.stat().st_size <= FileSizeThreshold.MIN_VALID_PDF:
                logger.debug(f"源文件无效: 不存在或大小过小")
                return False

            logger.debug(f"准备移动文件: {source_file} -> {save_path}")

            # 尝试移动文件
            shutil.move(str(source_file), save_path)

            # 验证移动是否成功
            if target_path.exists() and target_path.stat().st_size > FileSizeThreshold.MIN_VALID_PDF:
                logger.debug(f"文件移动成功: {save_path}")
                logger.info(f"文件下载成功: {save_path}")

                # 清理可能残留的源文件（如果shutil.move创建了副本）
                if source_file.exists():
                    try:
                        source_file.unlink()
                        logger.debug(f"清理残留源文件: {source_file}")
                    except:
                        pass

                return True
            else:
                logger.debug(f"文件移动失败: 目标文件不存在或大小异常")
                return False

        except Exception as move_error:
            logger.debug(f"文件移动异常: {move_error}")
            return False

    def _check_target_file_exists(self, save_path: str) -> bool:
        """
        检查目标文件是否已存在

        Args:
            save_path: 目标路径

        Returns:
            bool: 文件是否存在
        """
        logger.debug(f"save_path type: {type(save_path)}, value: {save_path}")
        if os.path.exists(save_path) and os.path.getsize(save_path) > FileSizeThreshold.MIN_VALID_PDF:
            logger.info(f"文件已下载: {save_path}")
            return True
        return False

    def _log_download_progress(self, start_time: float):
        """
        记录下载进度信息

        Args:
            start_time: 开始时间
        """
        # 检查临时文件（递归检查所有目录）
        temp_files = []
        if self.download_dir and os.path.exists(self.download_dir):
            for root, dirs, files in os.walk(self.download_dir):
                for file in files:
                    if file.endswith('.crdownload') or file.endswith('.tmp'):
                        temp_files.append(os.path.join(root, file))

        # 输出进度信息
        elapsed = time.time() - start_time
        if elapsed > 10 and elapsed % 10 < 1:  # 每10秒输出一次状态
            logger.info(f"下载状态: 已等待 {elapsed:.1f}s, 临时文件数: {len(temp_files)}")
            if self.download_dir and os.path.exists(self.download_dir):
                current_files = list(Path(self.download_dir).rglob("*"))
                logger.info(f"当前下载目录文件数: {len(current_files)}")

    def _handle_timeout(self, save_path: str, start_time: float) -> bool:
        """
        处理下载超时

        Args:
            save_path: 目标保存路径
            start_time: 开始时间

        Returns:
            bool: 始终返回False
        """
        elapsed = time.time() - start_time
        logger.error(f"文件下载超时 ({elapsed:.1f}s): {save_path}")

        # 检查是否有部分下载的文件
        if os.path.exists(save_path):
            file_size = os.path.getsize(save_path)
            logger.error(f"文件已存在但大小异常: {file_size} bytes")

        # 检查下载目录状态
        if self.download_dir and os.path.exists(self.download_dir):
            all_files = list(Path(self.download_dir).rglob("*"))
            logger.error(f"下载目录文件列表: {[str(f) for f in all_files]}")

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
            from ..utils.debug_marker import DebugMarker

            # DEBUG MARKER: Start pagination attempt
            marker = DebugMarker("pagination")
            marker.add_step("pagination_start", "开始翻页操作", {
                "current_url": self.driver.current_url if self.driver else "no_driver"
            })

            next_selectors = [
                # Primary selector - verified by diagnostic results
                ".el-pager li.number.active + li.number",
                # Element UI pagination buttons
                "button.el-pagination__next:not(.is-disabled)",
                # Alternative Element UI patterns
                ".el-pager li.active + li.number",
                ".el-pager li.number.active + li",
                # Backup selectors
                "button.el-pagination__next:not([disabled])",
                ".pagination .next:not(.disabled)",
                "a[aria-label='下一页']:not(.disabled)"
            ]

            marker.add_step("selectors_defined", "选择器列表已定义", {
                "selectors_count": len(next_selectors)
            })

            for idx, selector in enumerate(next_selectors):
                try:
                    marker.add_step(f"try_selector_{idx}", f"尝试选择器 {idx}", {
                        "selector": selector
                    })

                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    marker.add_step(f"found_element_{idx}", f"找到元素 {idx}", {
                        "selector": selector,
                        "enabled": next_button.is_enabled() if next_button else None,
                        "displayed": next_button.is_displayed() if next_button else None,
                        "text": next_button.text if next_button else None
                    })

                    if next_button and next_button.is_enabled() and next_button.is_displayed():
                        # 滚动到元素位置
                        self.driver.execute_script("arguments[0].scrollIntoView();", next_button)
                        time.sleep(TimeoutConfig.SCROLL_DELAY)

                        marker.add_step(f"clicking_{idx}", f"点击下一页按钮 {idx}", {
                            "selector": selector,
                            "button_text": next_button.text
                        })

                        # 点击下一页
                        next_button.click()

                        marker.add_step(f"clicked_{idx}", f"已点击 {idx}", {
                            "selector": selector,
                            "url_before_click": self.driver.current_url
                        })

                        # 等待页面加载（独立try-catch，不影响整体成功）
                        try:
                            WebDriverWait(self.driver, timeout).until(
                                EC.staleness_of(next_button)
                            )
                            marker.add_step(f"page_loaded_{idx}", f"页面已加载 {idx}", {
                                "selector": selector
                            })
                        except TimeoutException:
                            marker.add_step(f"page_load_timeout_{idx}", f"页面加载超时 {idx} (但点击成功)", {
                                "selector": selector
                            })
                            # 点击已成功，即使等待超时也返回True

                        # CRITICAL: Add extra wait and URL verification
                        time.sleep(TimeoutConfig.CLICK_STABILIZATION)  # Additional wait for page stabilization
                        url_after_click = self.driver.current_url
                        marker.add_step(f"url_after_click_{idx}", f"点击后URL状态", {
                            "selector": selector,
                            "url_after_click": url_after_click,
                            "url_changed": url_after_click != self.driver.current_url if hasattr(self, '_last_url') else "unknown"
                        })

                        # Store current URL for next comparison
                        self._last_url = url_after_click

                        marker.add_step("pagination_success", "翻页成功", {
                            "selector_used": selector,
                            "final_url": url_after_click
                        })
                        marker.save()
                        return True

                except (NoSuchElementException, TimeoutException) as e:
                    marker.add_step(f"selector_failed_{idx}", f"选择器 {idx} 失败", {
                        "selector": selector,
                        "error": str(e)
                    })
                    continue
                except Exception as e:
                    marker.add_step(f"unexpected_error_{idx}", f"选择器 {idx} 异常", {
                        "selector": selector,
                        "error": str(e)
                    })
                    continue

            marker.add_step("pagination_failed", "未找到下一页按钮或已到达最后一页", {})
            marker.save()
            logger.info("没有找到下一页按钮或已到达最后一页")
            return False

        except Exception as e:
            marker.add_step("pagination_exception", "翻页操作异常", {
                "error": str(e)
            })
            marker.save()
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
                                time.sleep(TimeoutConfig.SCROLL_DELAY)

                                # 点击页码按钮
                                page_button.click()

                                # 等待页面加载
                                time.sleep(TimeoutConfig.LONG_WAIT)
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
            from ..utils.debug_marker import DebugMarker
            import time

            # DEBUG MARKER: Start has_next_page check
            marker = DebugMarker("has_next_page")
            current_url = self.driver.current_url if self.driver else "no_driver"
            marker.add_step("check_start", "开始检查下一页", {
                "current_url": current_url,
                "timestamp": time.time()
            })

            # CRITICAL FIX: Add wait mechanism to ensure DOM is ready after previous pagination
            # This is the key difference from go_to_next_page() that was causing validation failures
            marker.add_step("wait_for_stability", "等待页面稳定", {})
            time.sleep(TimeoutConfig.MEDIUM_WAIT)  # Wait for DOM to stabilize

            # Also wait for any pending network requests or DOM updates
            try:
                WebDriverWait(self.driver, 2).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                marker.add_step("dom_ready", "DOM已就绪", {
                    "current_url_after_wait": self.driver.current_url if self.driver else "no_driver"
                })
            except TimeoutException:
                marker.add_step("dom_wait_timeout", "DOM等待超时，继续尝试", {
                    "current_url_after_timeout": self.driver.current_url if self.driver else "no_driver"
                })

            # DEBUG: Check page content before selector search
            try:
                page_source_preview = self.driver.page_source[:500] if self.driver else ""
                marker.add_step("page_source_check", "页面源码预览", {
                    "length": len(page_source_preview),
                    "has_pagination": "el-pager" in page_source_preview or "pagination" in page_source_preview,
                    "current_url_final": self.driver.current_url if self.driver else "no_driver"
                })
            except:
                pass

            next_selectors = [
                # Primary selector - verified by diagnostic results
                ".el-pager li.number.active + li.number",
                # Element UI pagination buttons
                "button.el-pagination__next:not(.is-disabled)",
                # Alternative Element UI patterns
                ".el-pager li.active + li.number",
                ".el-pager li.number.active + li",
                # Backup selectors
                "button.el-pagination__next:not([disabled])",
                ".pagination .next:not(.disabled)",
                "a[aria-label='下一页']:not(.disabled)"
            ]

            marker.add_step("selectors_defined", "选择器列表已定义", {
                "selectors_count": len(next_selectors)
            })

            for idx, selector in enumerate(next_selectors):
                try:
                    # Add small wait between selector attempts
                    if idx > 0:
                        time.sleep(TimeoutConfig.SELECTOR_RETRY)

                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    marker.add_step(f"check_selector_{idx}", f"检查选择器 {idx}", {
                        "selector": selector,
                        "found": next_button is not None,
                        "enabled": next_button.is_enabled() if next_button else None,
                        "displayed": next_button.is_displayed() if next_button else None
                    })

                    if next_button and next_button.is_enabled() and next_button.is_displayed():
                        marker.add_step("has_next_page_true", "检测到下一页按钮", {
                            "selector": selector
                        })
                        marker.save()
                        return True
                except (NoSuchElementException, TimeoutException):
                    marker.add_step(f"selector_not_found_{idx}", f"选择器 {idx} 未找到", {
                        "selector": selector
                    })
                    continue
                except Exception as e:
                    marker.add_step(f"selector_error_{idx}", f"选择器 {idx} 异常", {
                        "selector": selector,
                        "error": str(e)
                    })
                    continue

            marker.add_step("has_next_page_false", "未找到下一页按钮", {})
            marker.save()
            return False

        except Exception as e:
            marker.add_step("check_exception", "检查下一页异常", {
                "error": str(e)
            })
            marker.save()
            logger.warning(f"检查下一页失败: {e}")
            return False