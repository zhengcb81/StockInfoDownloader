#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
组织ID服务模块
提供组织ID获取和管理功能
"""

import re
import time
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from ..core.exceptions import OrgIdError
from ..core.logger import get_logger
from ..data.models import OrgIdMapping
from ..web.driver import WebDriverManager
from ..web.anti_crawler import AntiCrawlerStrategy

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
            stock_code = stock_code.strip().zfill(6)
            
            # 设置WebDriver参数
            self.driver_manager.headless = headless
            
            with self.driver_manager as driver:
                self.anti_crawler.apply_anti_detection(driver)
                
                return self._crawl_org_id(driver, stock_code)
                
        except Exception as e:
            logger.error(f"获取组织ID失败: {e}")
            return None
    
    def _crawl_org_id(self, driver, stock_code: str) -> Optional[str]:
        """爬取组织ID"""
        try:
            # 构建URL
            url = f"{self.base_url}/new/investor/investor?stockCode={stock_code}"
            
            logger.info(f"访问页面: {url}")
            driver.get(url)
            
            # 等待页面加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 应用反爬虫策略
            self.anti_crawler.random_delay(2, 4)
            self.anti_crawler.simulate_human_behavior(driver)
            
            # 从URL中提取组织ID
            return self._extract_org_id_from_url(driver.current_url)
            
        except TimeoutException:
            logger.error("页面加载超时")
            return None
        except Exception as e:
            logger.error(f"爬取组织ID失败: {e}")
            return None
    
    def _extract_org_id_from_url(self, url: str) -> Optional[str]:
        """从URL中提取组织ID"""
        try:
            # 使用正则表达式提取orgId参数
            match = re.search(r'orgId=(\d+)', url)
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
                    match = re.search(r'["\']orgId["\']:\s*["\'](\d+)["\']', script_content)
                    if match:
                        org_id = match.group(1)
                        logger.info(f"从页面提取到组织ID: {org_id}")
                        return org_id
            
            # 查找页面中的隐藏字段
            hidden_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='hidden']")
            for hidden in hidden_inputs:
                name = hidden.get_attribute("name")
                if name and "org" in name.lower():
                    value = hidden.get_attribute("value")
                    if value and value.isdigit():
                        logger.info(f"从隐藏字段提取到组织ID: {value}")
                        return value
            
            logger.warning("未在页面中找到组织ID")
            return None
            
        except Exception as e:
            logger.error(f"从页面提取组织ID失败: {e}")
            return None