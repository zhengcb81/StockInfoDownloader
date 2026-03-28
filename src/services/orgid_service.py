#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
组织ID服务模块
提供组织ID获取和管理功能
"""

import re
from typing import Optional, cast

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..core.logger import get_logger
from ..utils.string_optimizer import standardize_stock_code
from ..web.anti_crawler_py import AntiCrawlerStrategy
from ..web.driver import WebDriverManager

logger = get_logger(__name__)


class OrgIdService:
    """组织ID获取服务"""

    def __init__(self):
        """初始化组织ID服务"""
        self.driver_manager = WebDriverManager()
        self.anti_crawler = AntiCrawlerStrategy()
        self.base_url = "https://www.cninfo.com.cn"

    def get_org_id(self, stock_code: str, headless: bool = True) -> Optional[str]:
        """
        获取股票对应的组织ID

        Args:
            stock_code: 股票代码
            headless: 是否使用无头模式

        Returns:
            Optional[str]: 组织ID，获取失败返回None
        """
        try:
            standardized_code = standardize_stock_code(stock_code)
            if not standardized_code:
                logger.warning(f"无效的股票代码格式: {stock_code}")
                return None
            stock_code = standardized_code

            # 设置WebDriver参数
            self.driver_manager.headless = headless

            with self.driver_manager as driver:
                self.anti_crawler.apply_anti_detection(driver)

                return self._crawl_org_id(driver, stock_code)

        except Exception as e:
            logger.error(f"获取组织ID失败: {e}")
            return None

    def _crawl_org_id(self, driver, stock_code: str) -> Optional[str]:
        """
        从巨潮资讯网爬取组织ID

        使用搜索页面查找公司介绍链接，从中提取orgId
        """
        try:
            # 访问搜索结果页
            search_url = f"{self.base_url}/new/fulltextSearch?notautosubmit=&keyWord={stock_code}"

            logger.info(f"访问搜索页面: {search_url}")
            driver.get(search_url)

            # 等待页面加载
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # 应用反爬虫策略
            self.anti_crawler.random_delay(2, 4)
            self.anti_crawler.simulate_human_behavior(driver)

            # 方法1: 从"公司介绍"链接中提取orgId
            try:
                company_links = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, "//a[contains(text(), '公司介绍')]")
                    )
                )

                for link in company_links:
                    href = link.get_attribute("href")
                    if href and "orgId=" in href:
                        org_id_match = re.search(r"orgId=([^&]+)", href)
                        if org_id_match:
                            org_id = org_id_match.group(1)
                            if org_id.isdigit() or org_id.startswith("gssz"):
                                logger.info(f"从公司介绍链接中提取到组织ID: {org_id}")
                                return org_id
            except Exception as e:
                logger.debug(f"从链接提取orgId失败: {e}")

            # 方法2: 从页面源代码中提取
            page_source = driver.page_source
            patterns = [
                r'orgId["\s:=]+([0-9a-zA-Z]+)',
                r'"orgId"\s*:\s*"?([0-9a-zA-Z]+)"?',
                r"orgId=([0-9a-zA-Z]+)",
            ]

            for pattern in patterns:
                match = re.search(pattern, page_source)
                if match:
                    org_id = match.group(1)
                    if (org_id.isdigit() and len(org_id) >= 8) or org_id.startswith(
                        "gssz"
                    ):
                        logger.info(f"从页面源代码中提取到组织ID: {org_id}")
                        return org_id

            logger.warning(f"未能从页面提取到组织ID: {stock_code}")
            return None

        except TimeoutException:
            logger.error("页面加载超时")
            return None
        except Exception as e:
            logger.error(f"爬取组织ID失败: {e}")
            return None
        except Exception as e:
            logger.error(f"爬取组织ID失败: {e}")
            return None

    def _extract_org_id_from_url(self, url: str) -> Optional[str]:
        """从URL中提取组织ID"""
        try:
            # 使用正则表达式提取orgId参数
            match = re.search(r"orgId=(\d+)", url)
            if match:
                org_id = match.group(1)
                logger.info(f"提取到组织ID: {org_id}")
                return org_id

            logger.warning("未在URL中找到组织ID")
            return None

        except Exception as e:
            logger.error(f"提取组织ID失败: {e}")
            return None

    def _extract_org_id_from_page(self, driver) -> Optional[str]:
        """从页面内容中提取组织ID"""
        try:
            # 查找包含组织ID的脚本或隐藏字段
            scripts = driver.find_elements(By.TAG_NAME, "script")

            for script in scripts:
                script_content = script.get_attribute("innerHTML")
                if script_content:
                    # 查找orgId相关的内容
                    match = re.search(
                        r'["\']orgId["\']:\s*["\'](\d+)["\']', script_content
                    )
                    if match:
                        org_id = match.group(1)
                        logger.info(f"从页面提取到组织ID: {org_id}")
                        return org_id

            # 查找页面中的隐藏字段
            hidden_inputs = driver.find_elements(
                By.CSS_SELECTOR, "input[type='hidden']"
            )
            for hidden in hidden_inputs:
                name = hidden.get_attribute("name")
                if name and "org" in name.lower():
                    value = hidden.get_attribute("value")
                    if value and value.isdigit():
                        logger.info(f"从隐藏字段提取到组织ID: {value}")
                        return cast(str, value)

            logger.warning("未在页面中找到组织ID")
            return None

        except Exception as e:
            logger.error(f"从页面提取组织ID失败: {e}")
            return None
