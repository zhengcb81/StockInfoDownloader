#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速验证翻页内容变化
"""

import sys
import os
import time
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.logger import get_logger
from src.core.config import ConfigManager
from src.web.driver import WebDriverManager
from src.web.scraper import WebScraper
from selenium.webdriver.common.by import By

logger = get_logger(__name__)
config_manager = ConfigManager()

def quick_validate_pages():
    """快速验证翻页内容变化"""
    logger.info("开始快速验证翻页内容变化...")
    
    driver_manager = WebDriverManager(
        headless=False,
        download_dir="quick_validate",
        page_load_timeout=20,
        implicit_wait=5
    )
    
    try:
        with driver_manager as driver:
            # 从配置获取测试股票信息
            test_stock = config_manager.get_test_stock("300470")
            stock_code = test_stock.get('code', '300470')
            org_id = test_stock.get('org_id', '9900023856')
            base_url = config_manager.get('base_url', 'https://www.cninfo.com.cn')
            url = f"{base_url}/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#research"
            
            logger.info(f"访问页面: {url}")
            driver.get(url)
            time.sleep(6)
            
            scraper = WebScraper(driver)
            
            # 快速获取每页的前5个文档进行对比
            all_pages_content = {}
            
            for page_num in range(1, 4):
                logger.info(f"\n=== 第{page_num}页 ===")
                
                if page_num > 1:
                    success = scraper.go_to_page(page_num, timeout=10)
                    if not success:
                        logger.error(f"无法跳转到第{page_num}页")
                        break
                    time.sleep(3)
                
                # 快速获取前5个文档
                docs = get_quick_documents(driver)
                all_pages_content[page_num] = docs
                
                logger.info(f"第{page_num}页前5个文档:")
                for i, doc in enumerate(docs[:5]):
                    logger.info(f"  {i+1}. {doc}")
            
            # 快速对比
            logger.info(f"\n=== 快速对比结果 ===")
            compare_quickly(all_pages_content)
            
    except Exception as e:
        logger.error(f"快速验证失败: {e}")
        return False
    
    finally:
        logger.info("快速验证完成")

def get_quick_documents(driver):
    """快速获取文档列表"""
    try:
        # 使用简单的方法获取文档
        rows = driver.find_elements(By.CSS_SELECTOR, ".el-table__row, .table-row")
        documents = []
        
        for row in rows[:10]:  # 只取前10个
            text = row.text.strip()
            if text and len(text) > 20:
                # 提取标题（通常在第一行）
                lines = text.split('\n')
                if lines:
                    title = lines[0].strip()
                    documents.append(title)
        
        return documents
    except Exception as e:
        logger.error(f"快速获取文档失败: {e}")
        return []

def compare_quickly(all_pages_content):
    """快速对比页面内容"""
    if len(all_pages_content) < 2:
        return
    
    # 对比第1页和第2页
    if 1 in all_pages_content and 2 in all_pages_content:
        page1 = all_pages_content[1][:5]
        page2 = all_pages_content[2][:5]
        
        logger.info(f"第1页前5个: {page1}")
        logger.info(f"第2页前5个: {page2}")
        
        if page1 == page2:
            logger.error("❌ 第1页和第2页内容完全相同！")
        else:
            logger.info("✅ 第1页和第2页内容不同")
    
    # 对比第2页和第3页
    if 2 in all_pages_content and 3 in all_pages_content:
        page2 = all_pages_content[2][:5]
        page3 = all_pages_content[3][:5]
        
        logger.info(f"第2页前5个: {page2}")
        logger.info(f"第3页前5个: {page3}")
        
        if page2 == page3:
            logger.error("❌ 第2页和第3页内容完全相同！")
        else:
            logger.info("✅ 第2页和第3页内容不同")

if __name__ == "__main__":
    success = quick_validate_pages()
    if success:
        logger.info("✅ 快速验证完成")
    else:
        logger.info("❌ 快速验证失败")
    sys.exit(0 if success else 1)