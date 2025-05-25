#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简单的下载测试脚本
"""

import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('simple_test')

def test_simple_download():
    """简单的下载测试"""
    logger.info("开始简单测试...")
    
    # 设置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # 创建下载目录
    save_dir = os.path.abspath('downloads_simple')
    os.makedirs(save_dir, exist_ok=True)
    
    # 设置下载目录
    prefs = {
        "download.default_directory": save_dir,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    driver = None
    try:
        # 创建WebDriver
        logger.info("正在初始化WebDriver...")
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        logger.info("WebDriver初始化成功")
        
        # 访问测试页面
        test_url = "https://www.cninfo.com.cn/new/disclosure/stock?orgId=9900008267&stockCode=300010#research"
        logger.info(f"访问页面: {test_url}")
        driver.get(test_url)
        
        # 等待页面加载
        time.sleep(10)
        logger.info("页面加载完成")
        
        # 查找投资者关系活动记录表链接
        links = driver.find_elements(By.TAG_NAME, 'a')
        found_links = []
        
        for link in links:
            try:
                text = link.text.strip()
                href = link.get_attribute('href')
                
                if (text and '投资者关系活动记录表' in text
                    and href and '/new/disclosure/detail' in href):
                    found_links.append({'text': text, 'href': href})
            except Exception:
                continue
        
        logger.info(f"找到 {len(found_links)} 个投资者关系活动记录表链接")
        
        if found_links:
            logger.info("✅ 测试成功！能够正常访问页面并找到下载链接")
            for i, link in enumerate(found_links[:3], 1):  # 只显示前3个
                logger.info(f"  {i}. {link['text']}")
        else:
            logger.warning("⚠️ 未找到投资者关系活动记录表链接")
        
        return len(found_links) > 0
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False
        
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("WebDriver已关闭")
            except Exception as e:
                logger.error(f"关闭WebDriver时发生错误: {e}")

if __name__ == "__main__":
    success = test_simple_download()
    if success:
        print("\n🎉 测试通过！基础功能正常")
    else:
        print("\n❌ 测试失败，请检查环境配置") 