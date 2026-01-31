"""
Fake Browser Strategy for Testing

Provides in-memory browser simulation as an alternative to MagicMock,
making tests closer to real behavior.
"""

from typing import Any, Dict, List, Optional

from src.web.browser_strategy import BrowserAutomationStrategy


class FakeBrowserStrategy(BrowserAutomationStrategy):
    """
    Fake browser strategy for testing

    Simulates browser behavior without requiring a real browser instance
    """

    def __init__(
        self,
        headless: bool = True,
        download_dir: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize Fake browser strategy"""
        self.headless = headless
        self.download_dir = download_dir
        self.config = config or {}

        # Simulate state
        self._current_url: Optional[str] = None
        self._page_content: str = ""
        self._elements: Dict[str, List[Dict[str, Any]]] = {}
        self._downloads: List[str] = []
        self._is_closed = False
        self._download_count = 0
        self._healthy = True

        # Configurable behavior
        self.should_fail_navigation = False
        self.should_fail_download = False
        self.simulate_crashes = False
        self.crash_after_downloads = -1  # -1 means no crash

    def create_driver(self) -> Any:
        """Create simulated browser driver"""
        return self

    def get_driver(self) -> Any:
        """Get current driver instance"""
        return self

    def navigate(self, url: str) -> bool:
        """Simulate navigation to URL"""
        if self.should_fail_navigation:
            return False
        if self.simulate_crashes and self._download_count >= self.crash_after_downloads >= 0:
            raise Exception("Simulated browser crash")

        self._current_url = url
        self._page_content = f"<html><body>Mock page for {url}</body></html>"
        return True

    def find_elements(self, selector: str, by: str = "css") -> List[Dict[str, Any]]:
        """Find elements"""
        return self._elements.get(selector, [])

    def find_element(self, selector: str, by: str = "css") -> Optional[Dict[str, Any]]:
        """Find single element"""
        elements = self.find_elements(selector, by)
        return elements[0] if elements else None

    def click(self, element: Any) -> bool:
        """Click element"""
        if isinstance(element, dict):
            element["clicked"] = True
            return True
        return False

    def get_text(self, element: Any) -> str:
        """Get element text"""
        if isinstance(element, dict):
            return element.get("text", "")
        return ""

    def get_attribute(self, element: Any, attribute: str) -> Optional[str]:
        """Get element attribute"""
        if isinstance(element, dict):
            return element.get(attribute)
        return None

    def execute_script(self, script: str, *args) -> Any:
        """Execute JavaScript"""
        return None

    def wait_for_element(
        self,
        selector: str,
        timeout: int = 10,
        by: str = "css",
        condition: str = "visible",
    ) -> bool:
        """Wait for element to appear"""
        return self.find_element(selector, by) is not None

    def get_page_source(self) -> str:
        """Get page source code"""
        return self._page_content

    def get_current_url(self) -> str:
        """Get current URL"""
        return self._current_url or ""

    def close(self) -> None:
        """Close browser"""
        self._is_closed = True
        self._healthy = False

    def is_healthy(self) -> bool:
        """Check if browser is healthy"""
        return self._healthy and not self._is_closed

    def restart(self) -> bool:
        """Restart browser"""
        self._is_closed = False
        self._healthy = True
        self._download_count = 0
        return True

    def take_screenshot(self, save_path: Optional[str] = None) -> Optional[bytes]:
        """Take screenshot"""
        return b"fake_screenshot_data"

    def download_file(self, url: str, save_path: str, timeout: int = 30) -> bool:
        """
        Download file to specified path

        Args:
            url: URL to download
            save_path: File save path
            timeout: Timeout in seconds

        Returns:
            bool: Whether download was successful
        """
        if self.should_fail_download:
            return False
        if self.simulate_crashes and self._download_count >= self.crash_after_downloads >= 0:
            raise Exception("Simulated browser crash during download")

        self._download_count += 1
        self._downloads.append(save_path)
        return True

    def go_to_next_page(self, timeout: int = 10) -> bool:
        """
        Go to next page

        Args:
            timeout: Timeout in seconds

        Returns:
            bool: Whether navigation was successful
        """
        return True

    def go_to_page(self, page_number: int, timeout: int = 10) -> bool:
        """
        Go to specified page number

        Args:
            page_number: Target page number
            timeout: Timeout in seconds

        Returns:
            bool: Whether navigation was successful
        """
        return True

    def has_next_page(self, timeout: int = 5) -> bool:
        """
        Check if there is a next page

        Args:
            timeout: Timeout in seconds

        Returns:
            bool: Whether there is a next page
        """
        return False

    # Test helper methods

    def add_mock_element(self, selector: str, element: Dict[str, Any]) -> None:
        """Add mock element"""
        if selector not in self._elements:
            self._elements[selector] = []
        self._elements[selector].append(element)

    def set_page_content(self, content: str) -> None:
        """Set page content"""
        self._page_content = content

    def get_downloads(self) -> List[str]:
        """Get all downloaded files"""
        return self._downloads.copy()

    def reset(self) -> None:
        """Reset state"""
        self._current_url = None
        self._page_content = ""
        self._elements.clear()
        self._downloads.clear()
        self._is_closed = False
        self._download_count = 0
        self._healthy = True

    def is_closed(self) -> bool:
        """Check if browser is closed"""
        return self._is_closed
