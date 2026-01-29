"""
Playwright异步浏览器自动化策略实现
使用异步API避免与同步环境的冲突
"""

import asyncio
import os
import random
from typing import Any, Dict, List, Optional

from ..core.config import ConfigManager
from ..core.exceptions import (
    ErrorCode,
    ErrorSeverity,
    RecoveryStrategy,
    WebDriverInitError,
    WebDriverTimeoutError,
    with_error_handling,
)
from ..core.logger import get_logger
from .browser_strategy import BrowserAutomationStrategy

logger = get_logger(__name__)


class PlaywrightAsyncStrategy(BrowserAutomationStrategy):
    """Playwright异步浏览器自动化策略"""

    def __init__(
        self,
        headless: bool = True,
        download_dir: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """初始化Playwright异步策略"""
        self.headless = headless
        self.download_dir = download_dir
        self.config = config or {}
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        # 初始化配置管理器
        self.config_manager = ConfigManager()

        # 从配置获取参数
        self.window_size = self.config.get("window_size", "1920,1080")
        self.timeout = self.config.get("page_load_timeout", 30) * 1000  # 转换为毫秒
        self.implicit_wait = self.config.get("implicit_wait", 3)
        self.max_downloads_per_session = self.config.get(
            "max_downloads_per_session", 10
        )

        self._user_agents = self.config.get(
            "user_agents",
            [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            ],
        )

    @with_error_handling(
        error_code=ErrorCode.WEBDRIVER_INIT_ERROR,
        severity=ErrorSeverity.CRITICAL,
        recovery_strategy=RecoveryStrategy.RETRY,
        max_retries=3,
    )
    async def create_driver(self) -> Any:
        """创建Playwright浏览器实例（异步）"""
        # 确保之前的实例完全关闭
        if self.browser:
            await self.close()

        logger.info("正在初始化Playwright异步浏览器...")

        try:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()

            # 构建浏览器启动选项
            launch_options = self._build_launch_options()

            # 启动浏览器
            self.browser = await self.playwright.chromium.launch(**launch_options)

            # 创建浏览器上下文
            context_options = self._build_context_options()
            self.context = await self.browser.new_context(**context_options)

            # 创建页面
            self.page = await self.context.new_page()

            # 设置超时
            self.page.set_default_timeout(self.timeout)

            # 执行反检测脚本
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']})
            """)

            # 测试页面是否正常工作
            await self.page.goto("about:blank", wait_until="domcontentloaded")

            logger.info("Playwright异步浏览器初始化成功")
            return self.browser

        except ImportError:
            raise WebDriverInitError(
                "Playwright未安装，请运行: pip install playwright && playwright install chromium",
                context={"phase": "initialization", "error_type": "missing_dependency"},
            )
        except Exception as e:
            error_msg = f"Playwright异步浏览器创建失败: {e}"
            logger.error(error_msg)

            # 清理失败的实例
            await self.close()

            if "timeout" in str(e).lower():
                raise WebDriverTimeoutError(
                    error_msg,
                    context={
                        "phase": "initialization",
                        "timeout_type": "creation_timeout",
                    },
                    original_exception=e,
                )
            else:
                raise WebDriverInitError(
                    error_msg,
                    context={"phase": "initialization", "error_details": str(e)},
                    original_exception=e,
                )

    def _build_launch_options(self) -> Dict[str, Any]:
        """构建浏览器启动选项"""
        launch_options = {
            "headless": self.headless,
            "args": [
                f"--window-size={self.window_size}",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-blink-features=AutomationControlled",
                "--remote-debugging-port=0",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-sync",
                "--disable-translate",
                "--disable-default-apps",
                "--disable-notifications",
                "--disable-popup-blocking",
                "--log-level=3",
                "--disable-features=TranslateUI",
                "--disable-component-extensions-with-background-pages",
                "--disable-domain-reliability",
                "--disable-setuid-sandbox",
                "--disable-features=VizDisplayCompositor",
                "--disable-ipc-flooding-protection",
            ],
        }

        # 随机User-Agent
        user_agent = random.choice(self._user_agents)
        launch_options["args"].append(f"--user-agent={user_agent}")

        return launch_options

    def _build_context_options(self) -> Dict[str, Any]:
        """构建浏览器上下文选项"""
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": random.choice(self._user_agents),
            "ignore_https_errors": True,
            "bypass_csp": True,
        }

        # 设置下载目录
        if self.download_dir:
            abs_download_dir = os.path.abspath(self.download_dir)
            os.makedirs(abs_download_dir, exist_ok=True)

            context_options["accept_downloads"] = True

        return context_options

    def get_driver(self) -> Any:
        """获取当前驱动实例"""
        return self.page

    async def navigate(self, url: str) -> bool:
        """导航到指定URL"""
        if not self.page:
            return False

        try:
            await self.page.goto(url, wait_until="domcontentloaded")
            return True
        except Exception as e:
            logger.error(f"导航到 {url} 失败: {e}")
            return False

    async def find_elements(self, selector: str, by: str = "css") -> List[Any]:
        """查找元素"""
        if not self.page:
            return []

        try:
            if by.lower() == "xpath":
                return await self.page.query_selector_all(f"xpath={selector}")
            else:
                return await self.page.query_selector_all(selector)
        except Exception as e:
            logger.error(f"查找元素失败: {e}")
            return []

    async def find_element(self, selector: str, by: str = "css") -> Optional[Any]:
        """查找单个元素"""
        elements = await self.find_elements(selector, by)
        return elements[0] if elements else None

    async def click(self, element: Any) -> bool:
        """点击元素"""
        if not element:
            return False

        try:
            await element.click()
            return True
        except Exception as e:
            logger.error(f"点击元素失败: {e}")
            return False

    async def get_text(self, element: Any) -> str:
        """获取元素文本"""
        if not element:
            return ""

        try:
            return await element.text_content() or ""
        except Exception as e:
            logger.error(f"获取元素文本失败: {e}")
            return ""

    async def get_attribute(self, element: Any, attribute: str) -> Optional[str]:
        """获取元素属性"""
        if not element:
            return None

        try:
            return await element.get_attribute(attribute)
        except Exception as e:
            logger.error(f"获取元素属性失败: {e}")
            return None

    async def execute_script(self, script: str, *args) -> Any:
        """执行JavaScript脚本"""
        if not self.page:
            return None

        try:
            return await self.page.evaluate(script, *args)
        except Exception as e:
            logger.error(f"执行脚本失败: {e}")
            return None

    async def wait_for_element(
        self,
        selector: str,
        timeout: int = 10,
        by: str = "css",
        condition: str = "visible",
    ) -> bool:
        """等待元素出现"""
        if not self.page:
            return False

        try:
            if by.lower() == "xpath":
                selector = f"xpath={selector}"

            if condition == "presence":
                await self.page.wait_for_selector(selector, timeout=timeout * 1000)
            elif condition == "visible":
                await self.page.wait_for_selector(
                    selector, timeout=timeout * 1000, state="visible"
                )
            elif condition == "clickable":
                await self.page.wait_for_selector(
                    selector, timeout=timeout * 1000, state="visible"
                )

            return True

        except Exception:
            return False

    async def get_page_source(self) -> str:
        """获取页面源代码"""
        if not self.page:
            return ""

        try:
            return await self.page.content()
        except Exception as e:
            logger.error(f"获取页面源代码失败: {e}")
            return ""

    async def get_current_url(self) -> str:
        """获取当前URL"""
        if not self.page:
            return ""

        try:
            return self.page.url
        except Exception as e:
            logger.error(f"获取当前URL失败: {e}")
            return ""

    async def get_page_title(self) -> str:
        """获取页面标题"""
        if not self.page:
            return ""

        try:
            return await self.page.title()
        except Exception as e:
            logger.error(f"获取页面标题失败: {e}")
            return ""

    async def close(self) -> None:
        """关闭浏览器"""
        try:
            if self.browser:
                await self.browser.close()
                logger.info("Playwright异步浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器时发生错误: {e}")
        finally:
            self.playwright = None
            self.browser = None
            self.context = None
            self.page = None

    async def is_healthy(self) -> bool:
        """检查浏览器是否健康"""
        if not self.page:
            return False

        try:
            await self.page.title()
            return True
        except Exception:
            return False

    async def restart(self) -> bool:
        """重启浏览器"""
        logger.info("正在重启Playwright异步浏览器...")

        await self.close()

        # 增强重试机制
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.info(f"尝试重启浏览器 (第 {attempt + 1}/{max_attempts} 次)...")
                await self.create_driver()
                logger.info("浏览器重启成功")
                return True

            except Exception as e:
                logger.error(f"浏览器重启尝试 {attempt + 1} 异常: {e}")

                if attempt < max_attempts - 1:
                    retry_wait = random.uniform(2, 4)
                    logger.info(f"等待 {retry_wait:.2f} 秒后重试...")
                    await asyncio.sleep(retry_wait)

        logger.error("浏览器重启失败，已尝试所有重试次数")
        return False

    async def take_screenshot(self, save_path: Optional[str] = None) -> Optional[bytes]:
        """截取屏幕截图"""
        if not self.page:
            return None

        try:
            screenshot_data = await self.page.screenshot()

            if save_path:
                with open(save_path, "wb") as f:
                    f.write(screenshot_data)

            return screenshot_data
        except Exception as e:
            logger.error(f"截取屏幕截图失败: {e}")
            return None

    async def download_file(self, url: str, save_path: str, timeout: int = 30) -> bool:
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
            if not await self.navigate(url):
                logger.error(f"无法导航到详情页: {url}")
                return False

            # 等待页面加载
            await self.page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)

            # 查找下载按钮（公告下载）
            download_button = await self.find_element("button:has-text('公告下载')")
            if not download_button:
                logger.error("未找到下载按钮")
                return False

            # 设置下载事件监听
            async with self.page.expect_download(
                timeout=timeout * 1000
            ) as download_info:
                # 点击下载按钮
                if not await self.click(download_button):
                    logger.error("点击下载按钮失败")
                    return False

                logger.info("已点击下载按钮，等待文件下载...")

            # 获取下载对象
            download = await download_info.value

            # 保存文件到指定路径
            await download.save_as(save_path)
            logger.info(f"文件下载成功: {save_path}")
            return True

        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return False
