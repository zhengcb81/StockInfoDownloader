"""
Playwright浏览器自动化策略实现
"""

import os
import random
import time
from typing import Optional, List, Any, Dict
from pathlib import Path

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


class PlaywrightStrategy(BrowserAutomationStrategy):
    """Playwright浏览器自动化策略"""
    
    def __init__(self, headless: bool = True, download_dir: Optional[str] = None, 
                 config: Optional[Dict[str, Any]] = None):
        """初始化Playwright策略"""
        self.headless = headless
        self.download_dir = download_dir
        self.config = config or {}
        self.browser = None
        self.page = None
        self.context = None
        self.download_count = 0
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        
        # 从配置获取参数
        self.window_size = self.config.get('window_size', {'width': 1920, 'height': 1080})
        self.timeout = self.config.get('timeout', 30000)  # Playwright使用毫秒
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
        """创建Playwright浏览器实例"""
        # 确保之前的实例完全关闭
        if self.browser:
            self.close()
        
        logger.info("正在初始化Playwright浏览器...")
        
        try:
            import playwright
            from playwright.sync_api import sync_playwright
            
            self.playwright = sync_playwright().start()
            
            # 构建浏览器启动选项
            launch_options = self._build_launch_options()
            
            # 启动浏览器
            self.browser = self.playwright.chromium.launch(**launch_options)
            
            # 创建浏览器上下文
            context_options = self._build_context_options()
            self.context = self.browser.new_context(**context_options)
            
            # 创建页面
            self.page = self.context.new_page()
            
            # 设置超时
            self.page.set_default_timeout(self.timeout)
            
            # 执行反检测脚本
            self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']})
            """)
            
            # 测试页面是否正常工作
            self.page.goto('about:blank', wait_until='domcontentloaded')
            
            logger.info("Playwright浏览器初始化成功")
            return self.browser
            
        except ImportError:
            raise WebDriverInitError(
                "Playwright未安装，请运行: pip install playwright && playwright install chromium",
                context={"phase": "initialization", "error_type": "missing_dependency"}
            )
        except Exception as e:
            error_msg = f"Playwright浏览器创建失败: {e}"
            logger.error(error_msg)
            
            # 清理失败的实例
            self.close()
            
            if "timeout" in str(e).lower():
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
    
    def _build_launch_options(self) -> Dict[str, Any]:
        """构建浏览器启动选项"""
        launch_options = {
            'headless': self.headless,
            'args': [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-blink-features=AutomationControlled',
                '--remote-debugging-port=0',
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
                '--disable-features=VizDisplayCompositor',
                '--disable-ipc-flooding-protection',
            ]
        }
        
        # 添加窗口大小
        if isinstance(self.window_size, dict):
            launch_options['args'].append(f'--window-size={self.window_size["width"]},{self.window_size["height"]}')
        
        # 随机User-Agent
        user_agent = random.choice(self._user_agents)
        launch_options['args'].append(f'--user-agent={user_agent}')
        
        return launch_options
    
    def _build_context_options(self) -> Dict[str, Any]:
        """构建浏览器上下文选项"""
        context_options = {
            'viewport': self.window_size if isinstance(self.window_size, dict) else {'width': 1920, 'height': 1080},
            'user_agent': random.choice(self._user_agents),
            'java_script_enabled': True,
            'ignore_https_errors': False,
        }
        
        # 设置下载目录
        if self.download_dir:
            abs_download_dir = os.path.abspath(self.download_dir)
            os.makedirs(abs_download_dir, exist_ok=True)
            
            context_options['accept_downloads'] = True
            # Playwright使用不同的下载处理方式，不需要downloads_path参数
            logger.info(f"设置下载目录: {abs_download_dir}")
        
        return context_options
    
    def get_driver(self) -> Any:
        """获取当前浏览器实例"""
        return self.browser
    
    def navigate(self, url: str) -> bool:
        """导航到指定URL"""
        if not self.page:
            return False
        
        try:
            self.page.goto(url, wait_until='domcontentloaded')
            return True
        except Exception as e:
            logger.error(f"导航到 {url} 失败: {e}")
            return False
    
    def find_elements(self, selector: str, by: str = "css") -> List[Any]:
        """查找元素"""
        if not self.page:
            return []
        
        try:
            # Playwright主要使用CSS选择器，也支持XPath
            if by.lower() == "xpath":
                return self.page.query_selector_all(f'xpath={selector}')
            else:
                return self.page.query_selector_all(selector)
        except Exception as e:
            logger.error(f"查找元素失败: {e}")
            return []
    
    def find_element(self, selector: str, by: str = "css") -> Optional[Any]:
        """查找单个元素"""
        if not self.page:
            return None
        
        try:
            if by.lower() == "xpath":
                return self.page.query_selector(f'xpath={selector}')
            else:
                return self.page.query_selector(selector)
        except Exception as e:
            logger.error(f"查找元素失败: {e}")
            return None
    
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
            # 使用JavaScript获取文本，确保能获取到动态加载的内容
            if hasattr(element, 'evaluate'):
                text = element.evaluate('element => element.textContent?.trim() || ""')
                return text or ""
            else:
                return element.text_content() or ""
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
        if not self.page:
            return None
        
        try:
            return self.page.evaluate(script, *args)
        except Exception as e:
            logger.error(f"执行脚本失败: {e}")
            return None
    
    def wait_for_element(self, selector: str, timeout: int = 10, 
                        by: str = "css", condition: str = "visible") -> bool:
        """等待元素出现"""
        if not self.page:
            return False
        
        try:
            timeout_ms = timeout * 1000  # 转换为毫秒
            
            if condition == "visible":
                self.page.wait_for_selector(selector, state='visible', timeout=timeout_ms)
            elif condition == "hidden":
                self.page.wait_for_selector(selector, state='hidden', timeout=timeout_ms)
            else:
                self.page.wait_for_selector(selector, timeout=timeout_ms)
            
            return True
            
        except Exception:
            return False
    
    def get_page_source(self) -> str:
        """获取页面源代码"""
        if not self.page:
            return ""
        
        try:
            return self.page.content()
        except Exception as e:
            logger.error(f"获取页面源代码失败: {e}")
            return ""
    
    def get_current_url(self) -> str:
        """获取当前URL"""
        if not self.page:
            return ""
        
        try:
            return self.page.url
        except Exception as e:
            logger.error(f"获取当前URL失败: {e}")
            return ""

    def get_page_title(self) -> str:
        """获取页面标题"""
        if not self.page:
            return ""
        
        try:
            return self.page.title()
        except Exception as e:
            logger.error(f"获取页面标题失败: {e}")
            return ""
    
    def close(self) -> None:
        """关闭浏览器"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if hasattr(self, 'playwright') and self.playwright:
                self.playwright.stop()
            
            logger.info("Playwright浏览器已关闭")
            
        except Exception as e:
            logger.error(f"关闭Playwright浏览器时发生错误: {e}")
        finally:
            self.browser = None
            self.context = None
            self.page = None
            self.download_count = 0
    
    def is_healthy(self) -> bool:
        """检查浏览器是否健康"""
        if not self.page:
            return False
        
        try:
            # 尝试获取页面URL来测试是否响应
            self.page.url
            return True
        except Exception:
            return False
    
    def restart(self) -> bool:
        """重启浏览器"""
        logger.info("正在重启Playwright浏览器...")
        
        self.close()
        
        # 增强重试机制
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.info(f"尝试重启浏览器 (第 {attempt + 1}/{max_attempts} 次)...")
                self.create_driver()
                logger.info("浏览器重启成功")
                return True
                
            except Exception as e:
                logger.error(f"浏览器重启尝试 {attempt + 1} 异常: {e}")
                
                if attempt < max_attempts - 1:
                    retry_wait = random.uniform(2, 4)
                    logger.info(f"等待 {retry_wait:.2f} 秒后重试...")
                    time.sleep(retry_wait)
        
        logger.error("浏览器重启失败，已尝试所有重试次数")
        return False
    
    def take_screenshot(self, save_path: Optional[str] = None) -> Optional[bytes]:
        """截取屏幕截图"""
        if not self.page:
            return None
        
        try:
            screenshot_data = self.page.screenshot()
            
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(screenshot_data)
            
            return screenshot_data
        except Exception as e:
            logger.error(f"截取屏幕截图失败: {e}")
            return None
    
    # Playwright特有方法
    def wait_for_download(self, timeout: int = 30) -> Optional[Any]:
        """等待下载完成（Playwright特有）"""
        if not self.page:
            return None
        
        try:
            download = self.page.wait_for_event('download', timeout=timeout * 1000)
            return download
        except Exception as e:
            logger.error(f"等待下载失败: {e}")
            return None
    
    def wait_for_navigation(self, timeout: int = 30) -> bool:
        """等待导航完成（Playwright特有）"""
        if not self.page:
            return False
        
        try:
            self.page.wait_for_load_state('domcontentloaded', timeout=timeout * 1000)
            return True
        except Exception as e:
            logger.error(f"等待导航失败: {e}")
            return False

    def go_to_next_page(self, timeout: int = 10) -> bool:
        """
        跳转到下一页

        Args:
            timeout: 超时时间（秒）

        Returns:
            bool: 是否成功跳转
        """
        if not self.page:
            logger.error("页面未初始化，无法翻页")
            return False

        try:
            next_selectors = [
                "button.el-pagination__next:not(.is-disabled)",
                ".pagination .next:not(.disabled)",
                "a[aria-label='下一页']:not(.disabled)",
                ".el-pager li.number.active + li.number",
                "button[aria-label='Next page']:not([disabled])"
            ]

            for selector in next_selectors:
                try:
                    next_button = self.page.query_selector(selector)
                    if next_button and next_button.is_enabled():
                        # 点击下一页
                        next_button.click()

                        # 等待页面加载
                        self.page.wait_for_load_state('domcontentloaded', timeout=timeout * 1000)
                        time.sleep(1)  # 额外等待确保内容加载

                        logger.info("成功跳转到下一页")
                        return True

                except Exception:
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
        if not self.page:
            logger.error("页面未初始化，无法翻页")
            return False

        try:
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
                "button:has-text('跳转')",
                "button:has-text('Go')"
            ]

            for input_selector, button_selector in zip(page_input_selectors, go_button_selectors):
                try:
                    # 查找页码输入框
                    page_input = self.page.query_selector(input_selector)
                    if not page_input or not page_input.is_enabled():
                        continue

                    # 查找跳转按钮
                    go_button = self.page.query_selector(button_selector)
                    if not go_button or not go_button.is_enabled():
                        continue

                    # 清空输入框并输入页码
                    page_input.fill("")
                    page_input.type(str(page_number))

                    # 点击跳转按钮
                    go_button.click()

                    # 等待页面加载
                    self.page.wait_for_load_state('domcontentloaded', timeout=timeout * 1000)
                    time.sleep(1)

                    logger.info(f"成功跳转到第{page_number}页")
                    return True

                except Exception:
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
                    page_buttons = self.page.query_selector_all(selector)
                    for page_button in page_buttons:
                        if page_button and page_button.is_enabled():
                            button_text = page_button.text_content().strip()
                            if button_text == str(page_number):
                                # 点击页码按钮
                                page_button.click()

                                # 等待页面加载
                                self.page.wait_for_load_state('domcontentloaded', timeout=timeout * 1000)
                                time.sleep(1)

                                logger.info(f"成功跳转到第{page_number}页")
                                return True

                except Exception:
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
        if not self.page:
            logger.error("页面未初始化，无法检查翻页")
            return False

        try:
            next_selectors = [
                "button.el-pagination__next:not(.is-disabled)",
                ".pagination .next:not(.disabled)",
                "a[aria-label='下一页']:not(.disabled)",
                ".el-pager li.number.active + li.number",
                "button[aria-label='Next page']:not([disabled])"
            ]

            for selector in next_selectors:
                try:
                    next_button = self.page.query_selector(selector)
                    if next_button and next_button.is_enabled():
                        return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.warning(f"检查下一页失败: {e}")
            return False

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
        if not self.page:
            logger.error("页面未初始化，无法下载文件")
            return False
        
        try:
            
            # 导航到详情页
            if not self.navigate(url):
                logger.error(f"无法导航到详情页: {url}")
                return False
            
            # 等待页面加载
            self.page.wait_for_load_state('domcontentloaded')
            time.sleep(2)
            
            # 查找下载按钮（公告下载）
            download_button = self.find_element("button:has-text('公告下载')")
            if not download_button:
                logger.error("未找到下载按钮")
                return False
            
            # 设置下载事件监听
            with self.page.expect_download(timeout=timeout * 1000) as download_info:
                # 点击下载按钮
                if not self.click(download_button):
                    logger.error("点击下载按钮失败")
                    return False
                
                logger.info("已点击下载按钮，等待文件下载...")
            
            # 获取下载对象
            download = download_info.value
            
            # 保存文件到指定路径
            download.save_as(save_path)
            logger.info(f"文件下载成功: {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return False