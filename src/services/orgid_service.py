#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
组织ID服务模块
提供组织ID获取和管理功能
支持通过 BrowserStrategy 抽象接口使用 Selenium 或 Playwright
"""

import re
import time
from typing import Any, Dict, Optional

from ..core.logger import get_logger
from ..utils.string_optimizer import standardize_stock_code
from ..web.anti_crawler_py import AntiCrawlerStrategy
from ..web.browser_strategy import BrowserStrategy, BrowserStrategyFactory

logger = get_logger(__name__)


class OrgIdService:
    """
    组织ID获取服务

    支持通过 BrowserStrategy 抽象接口使用 Selenium 或 Playwright。
    配置的选择与用户选择的下载方式保持一致。
    """

    def __init__(
        self,
        browser_strategy: Optional[BrowserStrategy] = None,
        strategy_type: str = "selenium",
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化组织ID服务

        Args:
            browser_strategy: 浏览器策略实例，优先使用
            strategy_type: 浏览器策略类型（"selenium" 或 "playwright"），
                           仅在 browser_strategy 为 None 时使用
            config: 传递给 BrowserStrategy 的配置
        """
        if browser_strategy is not None:
            self._strategy = browser_strategy
        else:
            self._strategy = BrowserStrategyFactory.create_strategy(
                strategy_type, headless=True, config=config or {}
            )
        self.anti_crawler = AntiCrawlerStrategy()
        self.base_url = "https://www.cninfo.com.cn"

    def get_org_id(self, stock_code: str, headless: bool = True) -> Optional[str]:
        """
        获取股票对应的组织ID

        Args:
            stock_code: 股票代码
            headless: 是否使用无头模式（仅在通过工厂创建策略时生效）

        Returns:
            Optional[str]: 组织ID，获取失败返回None
        """
        try:
            standardized_code = standardize_stock_code(stock_code)
            if not standardized_code:
                logger.warning(f"无效的股票代码格式: {stock_code}")
                return None
            stock_code = standardized_code

            # 初始化浏览器
            self._strategy.initialize()

            try:
                return self._crawl_org_id(stock_code)
            finally:
                self._strategy.cleanup()

        except Exception as e:
            logger.error(f"获取组织ID失败: {e}")
            return None

    def _crawl_org_id(self, stock_code: str) -> Optional[str]:
        """
        从巨潮资讯网爬取组织ID

        使用搜索页面查找公司介绍链接，从中提取orgId。
        通过 BrowserStrategy 抽象接口操作浏览器。
        """
        try:
            # 访问搜索结果页
            search_url = f"{self.base_url}/new/fulltextSearch?notautosubmit=&keyWord={stock_code}"

            logger.info(f"访问搜索页面: {search_url}")
            if not self._strategy.navigate(search_url):
                logger.error(f"导航到搜索页面失败: {search_url}")
                return None

            # 等待页面加载
            self._strategy.wait_for_element("body", by="tag", timeout=15)

            # 应用反爬虫延迟（仅使用无 driver 依赖的方法）
            self.anti_crawler.random_delay(2, 4)

            # 方法1: 从"公司介绍"链接中提取orgId
            try:
                # 等待元素出现，然后查找所有匹配的链接
                self._strategy.wait_for_element(
                    "//a[contains(text(), '公司介绍')]",
                    by="xpath",
                    timeout=10,
                )
                company_links = self._strategy.find_elements(
                    "//a[contains(text(), '公司介绍')]", by="xpath"
                )

                for link in company_links:
                    href = self._strategy.get_attribute(link, "href")
                    if href and "orgId=" in href:
                        org_id_match = re.search(r"orgId=([^&]+)", href)
                        if org_id_match:
                            org_id = org_id_match.group(1)
                            if self._is_valid_org_id(org_id):
                                logger.info(f"从公司介绍链接中提取到组织ID: {org_id}")
                                return org_id
            except Exception as e:
                logger.debug(f"从链接提取orgId失败: {e}")

            # 方法2: 从页面源代码中提取
            page_source = self._strategy.get_page_source()
            if page_source:
                patterns = [
                    r'orgId["\s:=]+([0-9a-zA-Z]+)',
                    r'"orgId"\s*:\s*"?([0-9a-zA-Z]+)"?',
                    r"orgId=([0-9a-zA-Z]+)",
                ]

                for pattern in patterns:
                    match = re.search(pattern, page_source)
                    if match:
                        org_id = match.group(1)
                        if self._is_valid_org_id(org_id):
                            logger.info(f"从页面源代码中提取到组织ID: {org_id}")
                            return org_id

            logger.warning(f"未能从页面提取到组织ID: {stock_code}")
            return None

        except Exception as e:
            logger.error(f"爬取组织ID失败: {e}")
            return None

    def _extract_org_id_from_url(self, url: str) -> Optional[str]:
        """从URL中提取组织ID"""
        try:
            # 使用正则表达式提取orgId参数（支持字母数字组合）
            match = re.search(r"orgId=([0-9a-zA-Z]+)", url)
            if match:
                org_id = match.group(1)
                if self._is_valid_org_id(org_id):
                    logger.info(f"提取到组织ID: {org_id}")
                    return org_id

            logger.warning("未在URL中找到组织ID")
            return None

        except Exception as e:
            logger.error(f"提取组织ID失败: {e}")
            return None

    @staticmethod
    def _is_valid_org_id(org_id: str) -> bool:
        """
        校验 orgId 是否为有效格式

        巨潮资讯网的 orgId 有多种格式：
        - 纯数字：9900023856
        - gssz 前缀：gssz0000001
        - gssh 前缀：gssh0600519
        - GD 前缀：GD165627
        """
        if not org_id or not isinstance(org_id, str):
            return False
        # 必须是字母数字组合，长度 6-20
        if not re.match(r"^[0-9a-zA-Z]{6,20}$", org_id):
            return False
        return True
