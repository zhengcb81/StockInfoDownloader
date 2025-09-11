#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专门搜索2023年目标文档
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

def search_2023_target():
    """专门搜索2023年目标文档"""
    logger.info("开始专门搜索2023年目标文档...")
    
    # 创建WebDriver管理器
    driver_manager = WebDriverManager(
        headless=False,
        download_dir="debug_search",
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
            target_keyword = "2023年1月31日投资者关系活动记录表"
            
            logger.info(f"目标关键词: {target_keyword}")
            
            # 搜索前10页
            max_pages_to_search = 10
            found = False
            
            for page_num in range(1, max_pages_to_search + 1):
                logger.info(f"\n=== 搜索第{page_num}页 ===")
                
                if page_num > 1:
                    # 跳转到下一页
                    if not scraper.go_to_page(page_num):
                        logger.warning(f"无法跳转到第{page_num}页，停止搜索")
                        break
                    time.sleep(3)
                
                # 获取当前页面所有文本
                all_text = driver.find_elements(By.XPATH, "//*[text()]")
                logger.info(f"第{page_num}页文本元素数量: {len(all_text)}")
                
                # 搜索包含关键词的元素
                matching_elements = []
                for element in all_text:
                    try:
                        text = element.text.strip()
                        if text and target_keyword in text:
                            matching_elements.append((element, text))
                            logger.info(f"找到匹配元素: '{text}'")
                    except:
                        continue
                
                logger.info(f"第{page_num}页找到 {len(matching_elements)} 个匹配元素")
                
                for i, (element, text) in enumerate(matching_elements):
                    logger.info(f"匹配元素 {i+1}: '{text}'")
                    
                    # 尝试找到对应的链接
                    parent = element
                    link_found = False
                    for _ in range(5):  # 向上查找5层父元素
                        try:
                            parent = parent.find_element(By.XPATH, "..")
                            links = parent.find_elements(By.TAG_NAME, "a")
                            for link in links:
                                href = link.get_attribute("href") or ""
                                if "/new/disclosure/detail" in href:
                                    logger.info(f"  -> 详情页链接: {href}")
                                    link_found = True
                                    found = True
                                    break
                            if link_found:
                                break
                        except:
                            continue
                
                if found:
                    logger.info(f"在第{page_num}页找到目标文档!")
                    return True
                
                # 检查是否还有下一页
                page_info = scraper.get_current_page_info()
                if not page_info.get("has_next", False):
                    logger.info("没有更多页面了")
                    break
            
            if not found:
                logger.warning("在所有页面中未找到目标文档")
                
                # 显示所有包含"2023"和"1月"的元素作为参考
                logger.info("\n=== 参考信息: 所有2023年1月相关元素 ===")
                jan_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '2023') and contains(text(), '1月')]")
                logger.info(f"找到 {len(jan_elements)} 个2023年1月相关元素")
                
                for i, element in enumerate(jan_elements[:10]):
                    try:
                        text = element.text.strip()
                        if text and len(text) > 10:
                            logger.info(f"2023年1月元素 {i+1}: '{text}'")
                    except:
                        continue
            
            return found
            
    except Exception as e:
        logger.error(f"搜索过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        logger.info("搜索完成")

if __name__ == "__main__":
    found = search_2023_target()
    if found:
        logger.info("成功找到目标文档!")
    else:
        logger.info("未找到目标文档")