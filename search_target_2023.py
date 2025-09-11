#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
搜索目标2023年1月31日文档
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

def search_target_2023_document():
    """搜索目标2023年1月31日文档"""
    logger.info("开始搜索目标2023年1月31日文档...")
    
    # 使用可见模式以便调试
    driver_manager = WebDriverManager(
        headless=False,
        download_dir="search_target_2023",
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
            
            # 目标文档标题
            target_title = "中密控股：2023年1月31日投资者关系活动记录表"
            
            # 搜索多页
            max_pages = 5
            for page_num in range(1, max_pages + 1):
                logger.info(f"\n=== 搜索第{page_num}页 ===")
                
                if page_num > 1:
                    # 导航到指定页
                    success = scraper.go_to_page(page_num, timeout=15)
                    if not success:
                        logger.warning(f"无法跳转到第{page_num}页")
                        break
                    
                    # 等待页面加载
                    time.sleep(3)
                
                # 获取当前页面信息
                page_info = scraper.get_current_page_info()
                logger.info(f"页面信息: {page_info}")
                
                # 搜索目标文档
                logger.info(f"搜索目标文档: '{target_title}'")
                
                # 查找所有文档标题
                title_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '投资者关系活动记录表')]")
                
                found_documents = []
                for element in title_elements:
                    text = element.text.strip()
                    if text and '2023年1月31日' in text:
                        found_documents.append(text)
                        logger.info(f"找到目标文档: {text}")
                        
                        # 检查是否是我们要找的文档
                        if target_title in text:
                            logger.info(f"✅ 找到完全匹配的目标文档！")
                            logger.info(f"文档: {text}")
                            
                            # 尝试获取下载链接
                            try:
                                # 查找父元素中的链接
                                parent = element.find_element(By.XPATH, "./ancestor::tr[1]").find_element(By.TAG_NAME, "a")
                                download_url = parent.get_attribute("href")
                                logger.info(f"下载链接: {download_url}")
                                return True
                            except Exception as e:
                                logger.warning(f"无法获取下载链接: {e}")
                                return True
                
                if found_documents:
                    logger.info(f"第{page_num}页找到 {len(found_documents)} 个相关文档")
                else:
                    logger.info(f"第{page_num}页未找到相关文档")
                
                # 检查是否还有更多页面
                if page_info.get('has_next', False) == False:
                    logger.info("已到达最后一页")
                    break
            
            logger.info("搜索完成，未找到目标文档")
            return False
            
    except Exception as e:
        logger.error(f"搜索过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        logger.info("目标文档搜索完成")

if __name__ == "__main__":
    success = search_target_2023_document()
    if success:
        logger.info("✅ 找到目标文档!")
    else:
        logger.info("❌ 未找到目标文档")
    sys.exit(0 if success else 1)