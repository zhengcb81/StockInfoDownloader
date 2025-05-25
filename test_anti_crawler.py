#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试改进后的反爬虫机制
"""

import json
import logging
from cninfo_activity_downloader import CninfoDownloader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_anti_crawler')

def test_download():
    """测试下载功能"""
    # 读取测试配置
    with open('config_test.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    stock_code = config.get('stock_code')
    save_dir = config.get('save_dir', 'downloads_test')
    headless = config.get('headless', False)
    
    logger.info(f"开始测试股票代码: {stock_code}")
    logger.info(f"保存目录: {save_dir}")
    logger.info(f"无头模式: {headless}")
    
    # 创建下载器
    downloader = CninfoDownloader(save_dir=save_dir)
    
    # 测试下载（只下载少量文件进行测试）
    downloader.max_downloads_per_session = 3  # 设置较小的值进行测试
    
    try:
        success = downloader.download_activity_records(
            stock_code=stock_code, 
            headless=headless,
            max_retries=2  # 减少重试次数以加快测试
        )
        
        if success:
            logger.info("✅ 测试成功！反爬虫机制工作正常")
        else:
            logger.error("❌ 测试失败")
            
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")

if __name__ == "__main__":
    test_download() 