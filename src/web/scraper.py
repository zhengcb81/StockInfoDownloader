"""
通用网页抓取器
提供通用的网页数据抓取功能
"""

import re
import time
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from ..core.logger import get_logger

logger = get_logger(__name__)


class WebScraper:
    """通用网页抓取器"""
    
    def __init__(self, driver):
        """
        初始化网页抓取器
        
        Args:
            driver: WebDriver实例
        """
        self.driver = driver
    
    def find_elements_by_css(self, css_selector: str, timeout: int = 10) -> List:
        """
        通过CSS选择器查找元素
        
        Args:
            css_selector: CSS选择器
            timeout: 超时时间
            
        Returns:
            List: 元素列表
        """
        try:
            elements = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, css_selector))
            )
            return elements
        except TimeoutException:
            logger.warning(f"未找到元素: {css_selector}")
            return []
    
    def find_element_by_css(self, css_selector: str, timeout: int = 10) -> Optional[Any]:
        """
        通过CSS选择器查找单个元素
        
        Args:
            css_selector: CSS选择器
            timeout: 超时时间
            
        Returns:
            Optional: 元素或None
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
            )
            return element
        except TimeoutException:
            logger.warning(f"未找到元素: {css_selector}")
            return None
    
    def find_elements_by_xpath(self, xpath: str, timeout: int = 10) -> List:
        """
        通过XPath查找元素
        
        Args:
            xpath: XPath表达式
            timeout: 超时时间
            
        Returns:
            List: 元素列表
        """
        try:
            elements = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((By.XPATH, xpath))
            )
            return elements
        except TimeoutException:
            logger.warning(f"未找到元素: {xpath}")
            return []
    
    def get_text_by_css(self, css_selector: str, timeout: int = 10) -> Optional[str]:
        """
        通过CSS选择器获取文本内容
        
        Args:
            css_selector: CSS选择器
            timeout: 超时时间
            
        Returns:
            Optional[str]: 文本内容
        """
        element = self.find_element_by_css(css_selector, timeout)
        return element.text if element else None
    
    def get_attribute_by_css(self, css_selector: str, attribute: str, timeout: int = 10) -> Optional[str]:
        """
        通过CSS选择器获取属性值
        
        Args:
            css_selector: CSS选择器
            attribute: 属性名
            timeout: 超时时间
            
        Returns:
            Optional[str]: 属性值
        """
        element = self.find_element_by_css(css_selector, timeout)
        return element.get_attribute(attribute) if element else None
    
    def extract_links(self, css_selector: str = "a", base_url: str = None) -> List[Dict[str, str]]:
        """
        提取页面中的链接
        
        Args:
            css_selector: CSS选择器，默认为所有链接
            base_url: 基础URL，用于处理相对路径
            
        Returns:
            List[Dict[str, str]]: 链接列表，包含text和href
        """
        links = []
        
        try:
            elements = self.find_elements_by_css(css_selector)
            
            for element in elements:
                text = element.text.strip()
                href = element.get_attribute("href")
                
                if href:
                    # 处理相对路径
                    if base_url and not href.startswith("http"):
                        href = urljoin(base_url, href)
                    
                    links.append({
                        "text": text,
                        "href": href
                    })
            
        except Exception as e:
            logger.error(f"提取链接失败: {e}")
        
        return links
    
    def extract_table_data(self, table_selector: str = "table") -> List[List[str]]:
        """
        提取表格数据
        
        Args:
            table_selector: 表格CSS选择器
            
        Returns:
            List[List[str]]: 表格数据
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
                if row_data:  # 跳过空行
                    table_data.append(row_data)
            
            return table_data
            
        except Exception as e:
            logger.error(f"提取表格数据失败: {e}")
            return []
    
    def extract_form_data(self, form_selector: str = "form") -> Dict[str, str]:
        """
        提取表单数据
        
        Args:
            form_selector: 表单CSS选择器
            
        Returns:
            Dict[str, str]: 表单数据
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
            logger.error(f"提取表单数据失败: {e}")
            return {}
    
    def wait_for_element_clickable(self, css_selector: str, timeout: int = 10) -> bool:
        """
        等待元素可点击
        
        Args:
            css_selector: CSS选择器
            timeout: 超时时间
            
        Returns:
            bool: 是否可点击
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
            )
            return True
        except TimeoutException:
            logger.warning(f"元素不可点击: {css_selector}")
            return False
    
    def scroll_to_element(self, css_selector: str) -> bool:
        """
        滚动到指定元素
        
        Args:
            css_selector: CSS选择器
            
        Returns:
            bool: 是否成功
        """
        try:
            element = self.find_element_by_css(css_selector)
            if element:
                self.driver.execute_script("arguments[0].scrollIntoView();", element)
                return True
            return False
        except Exception as e:
            logger.error(f"滚动到元素失败: {e}")
            return False
    
    def get_page_source(self) -> str:
        """
        获取页面源码
        
        Returns:
            str: 页面源码
        """
        try:
            return self.driver.page_source
        except Exception as e:
            logger.error(f"获取页面源码失败: {e}")
            return ""
    
    def has_next_page(self, timeout: int = 5) -> bool:
        """
        检查是否存在下一页
        
        Args:
            timeout: 超时时间
            
        Returns:
            bool: 是否存在下一页
        """
        try:
            # CNINFO网站的分页控件选择器
            next_selectors = [
                "button.el-pagination__next:not(.is-disabled)",
                ".pagination .next:not(.disabled)",
                "a[aria-label='下一页']:not(.disabled)",
                ".el-pager li.number.active + li.number",
                "button[aria-label='Next page']:not([disabled])"
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
            logger.warning(f"检查下一页失败: {e}")
            return False
    
    def go_to_next_page(self, timeout: int = 10) -> bool:
        """
        跳转到下一页
        
        Args:
            timeout: 超时时间
            
        Returns:
            bool: 是否成功跳转
        """
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
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_button and next_button.is_enabled() and next_button.is_displayed():
                        # 滚动到元素位置
                        self.driver.execute_script("arguments[0].scrollIntoView();", next_button)
                        time.sleep(0.5)  # 短暂等待动画完成
                        
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
    
    def get_current_page_info(self) -> Dict[str, Any]:
        """
        获取当前页面信息
        
        Returns:
            Dict: 包含当前页码、总页数等信息
        """
        try:
            page_info = {
                "current_page": 1,
                "total_pages": 1,
                "has_next": False,
                "has_previous": False
            }
            
            # CNINFO分页信息选择器
            info_selectors = [
                ".el-pagination__total",
                ".pagination-info",
                ".page-info"
            ]
            
            for selector in info_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    text = element.text
                    
                    # 解析类似 "共 10 页" 或 "1/10" 的格式
                    match = re.search(r'(\d+)\s*/\s*(\d+)', text)
                    if match:
                        page_info["current_page"] = int(match.group(1))
                        page_info["total_pages"] = int(match.group(2))
                    else:
                        match = re.search(r'共\s*(\d+)\s*页', text)
                        if match:
                            page_info["total_pages"] = int(match.group(1))
                    
                    break
                except NoSuchElementException:
                    continue
            
            page_info["has_next"] = self.has_next_page()
            
            return page_info
            
        except Exception as e:
            logger.warning(f"获取页面信息失败: {e}")
            return {"current_page": 1, "total_pages": 1, "has_next": False, "has_previous": False}
    
    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """
        等待页面加载完成
        
        Args:
            timeout: 超时时间
            
        Returns:
            bool: 是否加载成功
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            return True
        except TimeoutException:
            logger.warning(f"页面加载超时: {timeout}秒")
            return False