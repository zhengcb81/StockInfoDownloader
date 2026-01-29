"""
Universal Web Scraper
Provides general web data scraping functionality
"""

import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..core.logger import get_logger

logger = get_logger(__name__)


class WebScraper:
    """Universal Web Scraper"""

    def __init__(self, driver):
        """
        Initialize WebScraper

        Args:
            driver: WebDriver instance
        """
        self.driver = driver

    def find_elements_by_css(self, css_selector: str, timeout: int = 10) -> List:
        """
        Find elements by CSS selector

        Args:
            css_selector: CSS selector
            timeout: Timeout in seconds

        Returns:
            List: List of elements
        """
        try:
            elements = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, css_selector))
            )
            return elements
        except TimeoutException:
            logger.warning(f"Element not found: {css_selector}")
            return []

    def find_element_by_css(
        self, css_selector: str, timeout: int = 10
    ) -> Optional[Any]:
        """
        Find single element by CSS selector

        Args:
            css_selector: CSS selector
            timeout: Timeout in seconds

        Returns:
            Optional: Element or None
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
            )
            return element
        except TimeoutException:
            logger.warning(f"Element not found: {css_selector}")
            return None

    def find_elements_by_xpath(self, xpath: str, timeout: int = 10) -> List:
        """
        Find elements by XPath

        Args:
            xpath: XPath expression
            timeout: Timeout in seconds

        Returns:
            List: List of elements
        """
        try:
            elements = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((By.XPATH, xpath))
            )
            return elements
        except TimeoutException:
            logger.warning(f"Element not found: {xpath}")
            return []

    def get_text_by_css(self, css_selector: str, timeout: int = 10) -> Optional[str]:
        """
        Get text content by CSS selector

        Args:
            css_selector: CSS selector
            timeout: Timeout in seconds

        Returns:
            Optional[str]: Text content
        """
        element = self.find_element_by_css(css_selector, timeout)
        return element.text if element else None

    def get_attribute_by_css(
        self, css_selector: str, attribute: str, timeout: int = 10
    ) -> Optional[str]:
        """
        Get attribute value by CSS selector

        Args:
            css_selector: CSS selector
            attribute: Attribute name
            timeout: Timeout in seconds

        Returns:
            Optional[str]: Attribute value
        """
        element = self.find_element_by_css(css_selector, timeout)
        return element.get_attribute(attribute) if element else None

    def extract_links(
        self, css_selector: str = "a", base_url: str = None
    ) -> List[Dict[str, str]]:
        """
        Extract links from page

        Args:
            css_selector: CSS selector, default is all links
            base_url: Base URL for relative paths

        Returns:
            List[Dict[str, str]]: List of links with text and href
        """
        links = []

        try:
            elements = self.find_elements_by_css(css_selector)

            for element in elements:
                text = element.text.strip()
                href = element.get_attribute("href")

                if href:
                    # Handle relative paths
                    if base_url and not href.startswith("http"):
                        href = urljoin(base_url, href)

                    links.append({"text": text, "href": href})

        except Exception as e:
            logger.error(f"Failed to extract links: {e}")

        return links

    def extract_table_data(self, table_selector: str = "table") -> List[List[str]]:
        """
        Extract table data

        Args:
            table_selector: Table CSS selector

        Returns:
            List[List[str]]: Table data
        """
        try:
            table = self.find_element_by_css(table_selector)
            if not table:
                return []

            rows = table.find_elements(By.CSS_SELECTOR, "tr")
            table_data = []

            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                row_data = [cell.text.strip() for cell in cells]
                if row_data:  # Skip empty rows
                    table_data.append(row_data)

            return table_data

        except Exception as e:
            logger.error(f"Failed to extract table data: {e}")
            return []

    def extract_form_data(self, form_selector: str = "form") -> Dict[str, str]:
        """
        Extract form data

        Args:
            form_selector: Form CSS selector

        Returns:
            Dict[str, str]: Form data
        """
        try:
            form = self.find_element_by_css(form_selector)
            if not form:
                return {}

            inputs = form.find_elements(By.CSS_SELECTOR, "input, select, textarea")
            form_data = {}

            for input_element in inputs:
                name = input_element.get_attribute("name")
                value = input_element.get_attribute("value")

                if name:
                    form_data[name] = value or ""

            return form_data

        except Exception as e:
            logger.error(f"Failed to extract form data: {e}")
            return {}

    def wait_for_element_clickable(self, css_selector: str, timeout: int = 10) -> bool:
        """
        Wait for element to be clickable

        Args:
            css_selector: CSS selector
            timeout: Timeout in seconds

        Returns:
            bool: Whether clickable
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
            )
            return True
        except TimeoutException:
            logger.warning(f"Element not clickable: {css_selector}")
            return False

    def scroll_to_element(self, css_selector: str) -> bool:
        """
        Scroll to specified element

        Args:
            css_selector: CSS selector

        Returns:
            bool: Whether successful
        """
        try:
            element = self.find_element_by_css(css_selector)
            if element:
                self.driver.execute_script("arguments[0].scrollIntoView();", element)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to scroll to element: {e}")
            return False

    def get_page_source(self) -> str:
        """
        Get page source

        Returns:
            str: Page source
        """
        try:
            return self.driver.page_source
        except Exception as e:
            logger.error(f"Failed to get page source: {e}")
            return ""

    def has_next_page(self, timeout: int = 5) -> bool:
        """
        Check if next page exists

        Args:
            timeout: Timeout in seconds

        Returns:
            bool: Whether next page exists
        """
        try:
            # CNINFO pagination selectors
            next_selectors = [
                "button.el-pagination__next:not(.is-disabled)",
                ".pagination .next:not(.disabled)",
                "a[aria-label='下一页']:not(.disabled)",
                ".el-pager li.number.active + li.number",
                "button[aria-label='Next page']:not([disabled])",
            ]

            for selector in next_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element and element.is_enabled() and element.is_displayed():
                        return True
                except NoSuchElementException:
                    continue

            return False

        except Exception as e:
            logger.warning(f"Failed to check next page: {e}")
            return False

    def go_to_next_page(self, timeout: int = 10) -> bool:
        """
        Go to next page

        Args:
            timeout: Timeout in seconds

        Returns:
            bool: Whether successful
        """
        try:
            next_selectors = [
                "button.el-pagination__next:not(.is-disabled)",
                ".pagination .next:not(.disabled)",
                "a[aria-label='下一页']:not(.disabled)",
                ".el-pager li.number.active + li.number",
                "button[aria-label='Next page']:not([disabled])",
            ]

            for selector in next_selectors:
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if (
                        next_button
                        and next_button.is_enabled()
                        and next_button.is_displayed()
                    ):
                        # Scroll to element
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView();", next_button
                        )
                        time.sleep(0.5)  # Wait for animation

                        # Click next page
                        next_button.click()

                        # Wait for page load
                        WebDriverWait(self.driver, timeout).until(
                            EC.staleness_of(next_button)
                        )
                        return True

                except (NoSuchElementException, TimeoutException):
                    continue

            logger.info("No next page button found or reached last page")
            return False

        except Exception as e:
            logger.error(f"Failed to go to next page: {e}")
            return False

    def get_current_page_info(self) -> Dict[str, Any]:
        """
        Get current page info

        Returns:
            Dict: Info containing current page, total pages, etc.
        """
        try:
            page_info = {
                "current_page": 1,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False,
            }

            # CNINFO pagination info selectors
            info_selectors = [".el-pagination__total", ".pagination-info", ".page-info"]

            for selector in info_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    text = element.text

                    # Parse formats like "1/10" or "Total 10 pages"
                    match = re.search(r"(\d+)\s*/\s*(\d+)", text)
                    if match:
                        page_info["current_page"] = int(match.group(1))
                        page_info["total_pages"] = int(match.group(2))
                    else:
                        match = re.search(r"共\s*(\d+)\s*页", text)
                        if match:
                            page_info["total_pages"] = int(match.group(1))

                    break
                except NoSuchElementException:
                    continue

            page_info["has_next"] = self.has_next_page()

            return page_info

        except Exception as e:
            logger.warning(f"Failed to get page info: {e}")
            return {
                "current_page": 1,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False,
            }

    def go_to_page(self, page_number: int, timeout: int = 10) -> bool:
        """
        Go to specified page number

        Args:
            page_number: Target page number
            timeout: Timeout in seconds

        Returns:
            bool: Whether successful
        """
        try:
            # Method 1: Find page input and go button
            page_input_selectors = [
                "input.el-pagination__editor",
                "input.page-input",
                "input[type='number']",
                "input.pagination-input",
            ]

            go_button_selectors = [
                "button.el-pagination__jump",
                "button.page-go",
                "button:contains('跳转')",
                "button:contains('Go')",
            ]

            for input_selector, button_selector in zip(
                page_input_selectors, go_button_selectors
            ):
                try:
                    # Find page input
                    page_input = self.driver.find_element(
                        By.CSS_SELECTOR, input_selector
                    )
                    if not page_input.is_enabled() or not page_input.is_displayed():
                        continue

                    # Find go button
                    go_button = self.driver.find_element(
                        By.CSS_SELECTOR, button_selector
                    )
                    if not go_button.is_enabled() or not go_button.is_displayed():
                        continue

                    # Clear and type page number
                    page_input.clear()
                    page_input.send_keys(str(page_number))

                    # Click go button
                    go_button.click()

                    # Wait for page load
                    WebDriverWait(self.driver, timeout).until(
                        EC.staleness_of(page_input)
                    )

                    logger.info(f"Successfully jumped to page {page_number}")
                    return True

                except (NoSuchElementException, TimeoutException):
                    continue

            # Method 2: Click page number button directly
            page_button_selectors = [
                f".el-pager li.number:not(.active)",
                f".pagination li:not(.active)",
                f"a:not(.active)",
                f"button:not([disabled])",
            ]

            for selector in page_button_selectors:
                try:
                    page_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for page_button in page_buttons:
                        if page_button.is_enabled() and page_button.is_displayed():
                            button_text = page_button.text.strip()
                            if button_text == str(page_number):
                                # Scroll to element
                                self.driver.execute_script(
                                    "arguments[0].scrollIntoView();", page_button
                                )
                                time.sleep(0.5)

                                # Click page button
                                page_button.click()

                                # Wait for page load - enhanced AJAX mechanism
                                logger.info(
                                    f"Waiting for page {page_number} content..."
                                )

                                # Step 1: Base wait
                                time.sleep(3)

                                # Step 2: Wait for ready state
                                try:
                                    WebDriverWait(self.driver, timeout).until(
                                        lambda driver: driver.execute_script(
                                            "return document.readyState"
                                        )
                                        == "complete"
                                    )
                                except TimeoutException:
                                    logger.warning(
                                        "document.readyState timeout, continuing"
                                    )

                                # Step 3: Wait for content change
                                try:
                                    # Record initial content
                                    initial_table_content = ""
                                    try:
                                        table = self.driver.find_element(
                                            By.CSS_SELECTOR,
                                            ".el-table__body, .table-body, tbody",
                                        )
                                        initial_table_content = table.text[:300]
                                    except:
                                        initial_table_content = (
                                            self.driver.find_element(
                                                By.TAG_NAME, "body"
                                            ).text[:300]
                                        )

                                    logger.info(
                                        f"Initial content length: {len(initial_table_content)}"
                                    )

                                    # Wait for change
                                    WebDriverWait(self.driver, timeout).until(
                                        lambda driver: self._has_table_content_changed(
                                            initial_table_content
                                        )
                                    )
                                    logger.info("Table content changed detected")

                                except TimeoutException:
                                    logger.warning(
                                        f"No content change detected in {timeout}s"
                                    )
                                    time.sleep(2)

                                # Step 4: Final stabilization
                                time.sleep(2)
                                logger.info(f"Page {page_number} loaded")

                                return True

                except (NoSuchElementException, TimeoutException):
                    continue

            logger.warning(f"Failed to jump to page {page_number}")
            return False

        except Exception as e:
            logger.error(f"Failed to jump to specified page: {e}")
            return False

    def _has_table_content_changed(self, initial_content: str) -> bool:
        """Check if table content changed"""
        try:
            try:
                table = self.driver.find_element(
                    By.CSS_SELECTOR, ".el-table__body, .table-body, tbody"
                )
                current_content = table.text[:300]
            except:
                current_content = self.driver.find_element(By.TAG_NAME, "body").text[
                    :300
                ]

            # Change > 10% or just different
            length_change = abs(len(current_content) - len(initial_content))
            if length_change > len(initial_content) * 0.1:
                return True

            return current_content != initial_content

        except Exception as e:
            logger.debug(f"Check content change failed: {e}")
            return False

    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """
        Wait for page load completion

        Args:
            timeout: Timeout in seconds

        Returns:
            bool: Whether successful
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState")
                == "complete"
            )
            return True
        except TimeoutException:
            logger.warning(f"Page load timeout: {timeout}s")
            return False
