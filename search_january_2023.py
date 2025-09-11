#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
搜索2023年1月的文档
"""

import sys
import os
import time
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.logger import get_logger
from src.web.driver import WebDriverManager
from src.web.scraper import WebScraper
from selenium.webdriver.common.by import By

logger = get_logger(__name__)

def search_january_2023_docs():
    """搜索2023年1月的文档"""
    logger.info("开始搜索2023年1月的文档...")
    
    # 创建WebDriver管理器
    driver_manager = WebDriverManager(
        headless=False,
        download_dir="debug_test",
        page_load_timeout=15,
        implicit_wait=5
    )
    
    try:
        with driver_manager as driver:
            # 测试股票代码 300470 (中密控股)
            stock_code = "300470"
            org_id = "9900023856"
            
            # 构建调研页面URL
            base_url = "https://www.cninfo.com.cn"
            url = f"{base_url}/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#research"
            
            logger.info(f"访问页面: {url}")
            
            # 访问页面
            driver.get(url)
            time.sleep(8)
            
            # 创建网页抓取器
            scraper = WebScraper(driver)
            
            # 搜索所有包含"2023"和"1月"的元素
            logger.info("=== 搜索2023年1月文档 ===")
            
            january_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '2023') and contains(text(), '1月')]")
            logger.info(f"找到 {len(january_elements)} 个包含'2023'和'1月'的元素")
            
            for i, element in enumerate(january_elements):
                try:
                    text = element.text.strip()
                    if text and len(text) > 10:
                        logger.info(f"2023年1月元素 {i+1}: '{text[:80]}...'")
                        
                        # 检查是否包含投资者关系
                        if "投资者关系" in text or "投关" in text:
                            logger.info(f"  -> 投资者关系文档!")
                            
                except Exception as e:
                    logger.debug(f"处理元素时出错: {e}")
                    continue
            
            # 如果没找到，尝试搜索更多页面
            if not january_elements:
                logger.info("第1页未找到2023年1月文档，尝试搜索更多页面...")
                
                # 获取页面信息
                page_info = scraper.get_current_page_info()
                logger.info(f"页面信息: {page_info}")
                
                # 尝试搜索前5页
                for page_num in range(2, 6):
                    if not page_info.get("has_next", False):
                        break
                        
                    logger.info(f"\n=== 搜索第{page_num}页 ===")
                    
                    # 尝试翻页
                    if scraper.go_to_page(page_num):
                        time.sleep(3)
                        
                        # 搜索当前页
                        january_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '2023') and contains(text(), '1月')]")
                        logger.info(f"第{page_num}页找到 {len(january_elements)} 个包含'2023'和'1月'的元素")
                        
                        for i, element in enumerate(january_elements):
                            try:
                                text = element.text.strip()
                                if text and len(text) > 10:
                                    logger.info(f"第{page_num}页2023年1月元素 {i+1}: '{text[:80]}...'")
                                    
                                    # 检查是否包含投资者关系
                                    if "投资者关系" in text or "投关" in text:
                                        logger.info(f"  -> 投资者关系文档!")
                                        
                            except Exception as e:
                                logger.debug(f"处理元素时出错: {e}")
                                continue
                        
                        # 更新页面信息
                        page_info = scraper.get_current_page_info()
                    else:
                        logger.warning(f"无法跳转到第{page_num}页")
                        break
            
            return True
            
    except Exception as e:
        logger.error(f"搜索过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        logger.info("搜索完成")

if __name__ == "__main__":
    search_january_2023_docs()