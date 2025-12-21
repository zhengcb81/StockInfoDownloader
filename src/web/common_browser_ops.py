#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
通用浏览器操作模块

提供与具体浏览器框架（Selenium/Playwright）无关的通用操作和配置。
减少代码重复，统一行为标准。
"""

import random
from typing import Dict, Any, List, Optional


# 基础浏览器启动参数（Selenium和Playwright通用）
BROWSER_BASE_ARGS = [
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


# 默认User-Agent列表
DEFAULT_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
]


class CommonBrowserConfig:
    """通用浏览器配置管理器"""

    @staticmethod
    def get_base_args() -> List[str]:
        """获取基础浏览器启动参数"""
        return BROWSER_BASE_ARGS.copy()

    @staticmethod
    def get_default_user_agents() -> List[str]:
        """获取默认User-Agent列表"""
        return DEFAULT_USER_AGENTS.copy()

    @staticmethod
    def get_random_user_agent(user_agents: Optional[List[str]] = None) -> str:
        """获取随机User-Agent"""
        agents = user_agents or DEFAULT_USER_AGENTS
        return random.choice(agents)

    @staticmethod
    def normalize_window_size(size: Any) -> Dict[str, int]:
        """
        标准化窗口大小配置

        Args:
            size: 窗口大小，可以是字符串"1920,1080"、字典{'width': 1920, 'height': 1080}或None

        Returns:
            标准化的字典格式 {'width': 1920, 'height': 1080}
        """
        if size is None:
            return {'width': 1920, 'height': 1080}

        if isinstance(size, str):
            # "1920,1080" -> {'width': 1920, 'height': 1080}
            try:
                w, h = size.split(',')
                return {'width': int(w.strip()), 'height': int(h.strip())}
            except (ValueError, AttributeError):
                return {'width': 1920, 'height': 1080}

        if isinstance(size, dict):
            # 确保键名正确
            width = size.get('width', 1920)
            height = size.get('height', 1080)
            return {'width': int(width), 'height': int(height)}

        if isinstance(size, (list, tuple)) and len(size) >= 2:
            return {'width': int(size[0]), 'height': int(size[1])}

        return {'width': 1920, 'height': 1080}

    @staticmethod
    def normalize_timeout(timeout: Any) -> int:
        """
        标准化超时配置（秒）

        Args:
            timeout: 超时时间，可以是秒数或毫秒数

        Returns:
            秒数
        """
        if timeout is None:
            return 180

        timeout = int(timeout)

        # 如果值很大（> 1000），假设是毫秒
        if timeout > 1000:
            return timeout // 1000

        return timeout

    @staticmethod
    def build_selenium_preferences(download_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        构建Selenium下载偏好设置

        Args:
            download_dir: 下载目录路径

        Returns:
            Chrome preferences字典
        """
        if not download_dir:
            return {}

        import os
        import platform

        abs_download_dir = os.path.abspath(download_dir)
        os.makedirs(abs_download_dir, exist_ok=True)

        if platform.system() == "Windows":
            abs_download_dir = abs_download_dir.replace("/", "\\")

        return {
            "download.default_directory": abs_download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True,
            "profile.default_content_settings.popups": 0,
            "profile.default_content_setting_values.automatic_downloads": 1,
            "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,
            "download_restrictions": 0,
            "credentials_enable_service": False,
            "password_manager_enabled": False,
        }

    @staticmethod
    def build_playwright_context_options(download_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        构建Playwright上下文选项

        Args:
            download_dir: 下载目录路径

        Returns:
            Playwright context options字典
        """
        import os

        options = {
            'java_script_enabled': True,
            'ignore_https_errors': False,
        }

        if download_dir:
            abs_download_dir = os.path.abspath(download_dir)
            os.makedirs(abs_download_dir, exist_ok=True)
            options['accept_downloads'] = True

        return options


class CommonBrowserOperations:
    """通用浏览器操作 - 与具体框架无关"""

    def __init__(self, strategy):
        """
        初始化通用操作器

        Args:
            strategy: 浏览器策略实例（SeleniumStrategy或PlaywrightStrategy）
        """
        self.strategy = strategy

    def find_and_click(self, selector: str, by: str = "css", timeout: int = 10) -> bool:
        """
        查找并点击元素（通用操作）

        Args:
            selector: 选择器
            by: 选择器类型（css, xpath, id）
            timeout: 等待超时（秒）

        Returns:
            是否成功点击
        """
        try:
            element = self.strategy.wait_for_element(selector, timeout, by)
            if element:
                return self.strategy.click(element)
            return False
        except Exception as e:
            print(f"[CommonOps] find_and_click失败: {e}")
            return False

    def get_element_text(self, selector: str, by: str = "css", timeout: int = 10) -> str:
        """
        获取元素文本（通用操作）

        Args:
            selector: 选择器
            by: 选择器类型
            timeout: 等待超时（秒）

        Returns:
            元素文本，失败返回空字符串
        """
        try:
            element = self.strategy.wait_for_element(selector, timeout, by)
            if element:
                return self.strategy.get_text(element)
            return ""
        except Exception as e:
            print(f"[CommonOps] get_element_text失败: {e}")
            return ""

    def navigate_and_wait(self, url: str, wait_selector: str = "body", timeout: int = 30) -> bool:
        """
        导航到页面并等待加载（通用操作）

        Args:
            url: 目标URL
            wait_selector: 等待的选择器
            timeout: 等待超时（秒）

        Returns:
            是否成功导航并等待
        """
        try:
            if self.strategy.navigate_to_page(url):
                return self.strategy.wait_for_element(wait_selector, timeout) is not None
            return False
        except Exception as e:
            print(f"[CommonOps] navigate_and_wait失败: {e}")
            return False

    def get_elements_by_text(self, text: str, timeout: int = 5) -> List[Any]:
        """
        根据文本内容查找元素（通用操作）

        Args:
            text: 要查找的文本
            timeout: 等待超时（秒）

        Returns:
            匹配的元素列表
        """
        try:
            # 使用XPath查找包含指定文本的元素
            xpath = f"//*[contains(text(), '{text}')]"
            return self.strategy.find_elements(xpath, by="xpath")
        except Exception as e:
            print(f"[CommonOps] get_elements_by_text失败: {e}")
            return []

    def click_element_by_text(self, text: str, timeout: int = 5) -> bool:
        """
        根据文本点击元素（通用操作）

        Args:
            text: 要点击的文本
            timeout: 等待超时（秒）

        Returns:
            是否成功点击
        """
        try:
            elements = self.get_elements_by_text(text, timeout)
            if elements:
                return self.strategy.click(elements[0])
            return False
        except Exception as e:
            print(f"[CommonOps] click_element_by_text失败: {e}")
            return False

    def wait_for_url_contains(self, substring: str, timeout: int = 10) -> bool:
        """
        等待URL包含指定子串（通用操作）

        Args:
            substring: URL中应该包含的子串
            timeout: 等待超时（秒）

        Returns:
            是否成功
        """
        import time

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                current_url = self.strategy.get_current_url()
                if substring in current_url:
                    return True
            except:
                pass
            time.sleep(0.5)
        return False

    def get_page_content(self) -> str:
        """
        获取页面内容（通用操作）

        Returns:
            页面HTML内容
        """
        try:
            # 尝试获取body的innerHTML
            elements = self.strategy.find_elements("body", by="css")
            if elements:
                return self.strategy.get_text(elements[0]) or ""
            return ""
        except Exception as e:
            print(f"[CommonOps] get_page_content失败: {e}")
            return ""

    def is_element_visible(self, selector: str, by: str = "css", timeout: int = 5) -> bool:
        """
        检查元素是否可见（通用操作）

        Args:
            selector: 选择器
            by: 选择器类型
            timeout: 等待超时（秒）

        Returns:
            元素是否可见
        """
        try:
            element = self.strategy.wait_for_element(selector, timeout, by)
            return element is not None
        except:
            return False


class BrowserConfigNormalizer:
    """浏览器配置标准化器"""

    @staticmethod
    def normalize_for_selenium(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        将通用配置标准化为Selenium格式

        Args:
            config: 通用配置字典

        Returns:
            Selenium专用配置
        """
        normalized = {}

        # 窗口大小
        window_size = CommonBrowserConfig.normalize_window_size(config.get('window_size'))
        normalized['window_size'] = f"{window_size['width']},{window_size['height']}"

        # 超时
        timeout = CommonBrowserConfig.normalize_timeout(config.get('timeout'))
        normalized['timeout'] = timeout
        normalized['page_load_timeout'] = timeout
        normalized['implicit_wait'] = config.get('implicit_wait', 3)

        # User-Agent
        normalized['user_agents'] = config.get('user_agents', CommonBrowserConfig.get_default_user_agents())

        # 下载目录
        normalized['download_dir'] = config.get('download_dir')

        # 其他配置
        normalized['max_downloads_per_session'] = config.get('max_downloads_per_session', 10)

        return normalized

    @staticmethod
    def normalize_for_playwright(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        将通用配置标准化为Playwright格式

        Args:
            config: 通用配置字典

        Returns:
            Playwright专用配置
        """
        normalized = {}

        # 窗口大小
        normalized['window_size'] = CommonBrowserConfig.normalize_window_size(config.get('window_size'))

        # 超时（转换为毫秒）
        timeout = CommonBrowserConfig.normalize_timeout(config.get('timeout'))
        normalized['timeout'] = timeout * 1000  # Playwright使用毫秒

        # User-Agent
        normalized['user_agents'] = config.get('user_agents', CommonBrowserConfig.get_default_user_agents())

        # 下载目录
        normalized['download_dir'] = config.get('download_dir')

        # 其他配置
        normalized['max_downloads_per_session'] = config.get('max_downloads_per_session', 10)

        return normalized


# 便捷函数
def get_common_config() -> CommonBrowserConfig:
    """获取通用配置管理器实例"""
    return CommonBrowserConfig()


def create_common_operations(strategy) -> CommonBrowserOperations:
    """创建通用操作器"""
    return CommonBrowserOperations(strategy)


def normalize_config_for_engine(engine: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据引擎类型标准化配置

    Args:
        engine: 引擎类型（'selenium' 或 'playwright'）
        config: 原始配置

    Returns:
        标准化后的配置
    """
    if engine == 'selenium':
        return BrowserConfigNormalizer.normalize_for_selenium(config)
    elif engine == 'playwright':
        return BrowserConfigNormalizer.normalize_for_playwright(config)
    else:
        raise ValueError(f"不支持的引擎: {engine}")