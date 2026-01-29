"""
Fake Browser Strategy for Testing

提供内存中的浏览器模拟，替代 MagicMock，使测试更接近真实行为。
"""

from typing import Any, Dict, List, Optional

from src.web.browser_strategy import BrowserAutomationStrategy


class FakeBrowserStrategy(BrowserAutomationStrategy):
    """
    用于测试的 Fake 浏览器策略

    模拟浏览器行为，无需真实浏览器实例
    """

    def __init__(self, headless: bool = True, download_dir: Optional[str] = None, **kwargs):
        """初始化 Fake 浏览器策略"""
        self.headless = headless
        self.download_dir = download_dir
        self.config = kwargs or {}

        # 模拟状态
        self._current_url: Optional[str] = None
        self._page_content: str = ""
        self._elements: Dict[str, List[Dict[str, Any]]] = {}
        self._downloads: List[str] = []
        self._is_closed = False
        self._download_count = 0

        # 可配置的行为
        self.should_fail_navigation = False
        self.should_fail_download = False
        self.simulate_crashes = False
        self.crash_after_downloads = -1  # -1 表示不崩溃

    def create_driver(self) -> Any:
        """创建模拟的浏览器驱动"""
        return self

    def navigate(self, url: str) -> bool:
        """模拟导航到 URL"""
        if self.should_fail_navigation:
            return False
        if self.simulate_crashes and self._download_count >= self.crash_after_downloads >= 0:
            raise Exception("Simulated browser crash")

        self._current_url = url
        self._page_content = f"<html><body>Mock page for {url}</body></html>"
        return True

    def get_page_source(self) -> str:
        """获取页面源代码"""
        return self._page_content

    def find_elements(self, selector: str, by: str = "xpath") -> List[Dict[str, Any]]:
        """查找元素"""
        return self._elements.get(selector, [])

    def find_element(self, selector: str, by: str = "xpath", timeout: int = 10) -> Optional[Dict[str, Any]]:
        """查找单个元素"""
        elements = self.find_elements(selector, by)
        return elements[0] if elements else None

    def click_element(self, selector: str, by: str = "xpath") -> bool:
        """点击元素"""
        element = self.find_element(selector, by)
        if element:
            element["clicked"] = True
            return True
        return False

    def download_file(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """模拟文件下载"""
        if self.should_fail_download:
            return None
        if self.simulate_crashes and self._download_count >= self.crash_after_downloads >= 0:
            raise Exception("Simulated browser crash during download")

        self._download_count += 1
        download_path = f"{self.download_dir}/{filename or 'download.pdf'}"
        self._downloads.append(download_path)
        return download_path

    def wait_for_element(self, selector: str, by: str = "xpath", timeout: int = 10) -> bool:
        """等待元素出现"""
        return self.find_element(selector, by) is not None

    def execute_script(self, script: str, *args) -> Any:
        """执行 JavaScript"""
        return None

    def close(self) -> None:
        """关闭浏览器"""
        self._is_closed = True

    def is_closed(self) -> bool:
        """检查浏览器是否已关闭"""
        return self._is_closed

    # 测试辅助方法

    def add_mock_element(self, selector: str, element: Dict[str, Any]) -> None:
        """添加模拟元素"""
        if selector not in self._elements:
            self._elements[selector] = []
        self._elements[selector].append(element)

    def set_page_content(self, content: str) -> None:
        """设置页面内容"""
        self._page_content = content

    def get_downloads(self) -> List[str]:
        """获取所有下载的文件"""
        return self._downloads.copy()

    def reset(self) -> None:
        """重置状态"""
        self._current_url = None
        self._page_content = ""
        self._elements.clear()
        self._downloads.clear()
        self._is_closed = False
        self._download_count = 0
