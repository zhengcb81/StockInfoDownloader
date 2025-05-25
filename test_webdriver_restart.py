#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebDriver重启功能测试脚本

用于测试修复后的WebDriver重启功能是否正常工作
"""

import time
import logging
from cninfo_activity_downloader import CninfoDownloader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('webdriver_test')

def test_webdriver_restart():
    """测试WebDriver重启功能"""
    logger.info("开始测试WebDriver重启功能...")
    
    downloader = CninfoDownloader()
    
    try:
        # 第一次初始化
        logger.info("第一次初始化WebDriver...")
        if not downloader.setup_driver(headless=True):
            logger.error("第一次初始化失败")
            return False
        
        logger.info("第一次初始化成功，访问测试页面...")
        downloader.driver.get("https://www.cninfo.com.cn")
        time.sleep(3)
        
        # 测试重启功能
        logger.info("测试WebDriver重启功能...")
        if not downloader.restart_driver(headless=True):
            logger.error("WebDriver重启失败")
            return False
        
        logger.info("WebDriver重启成功，再次访问测试页面...")
        downloader.driver.get("https://www.cninfo.com.cn")
        time.sleep(3)
        
        # 再次测试重启
        logger.info("再次测试WebDriver重启功能...")
        if not downloader.restart_driver(headless=True):
            logger.error("第二次WebDriver重启失败")
            return False
        
        logger.info("第二次WebDriver重启成功")
        
        # 测试健康检查
        logger.info("测试driver健康检查...")
        if downloader._is_driver_healthy():
            logger.info("Driver健康检查通过")
        else:
            logger.warning("Driver健康检查失败")
        
        logger.info("所有测试通过！")
        return True
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        return False
        
    finally:
        # 清理资源
        downloader.close_driver()

if __name__ == "__main__":
    success = test_webdriver_restart()
    if success:
        logger.info("WebDriver重启功能测试成功！")
    else:
        logger.error("WebDriver重启功能测试失败！") 