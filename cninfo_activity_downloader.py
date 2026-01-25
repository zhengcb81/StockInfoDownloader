#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
巨潮资讯网投资者关系活动记录表下载器 (Refactored Entry Point)

本程序用于自动下载巨潮资讯网上的投资者关系活动记录表PDF文件。
支持通过股票代码查询，自动从映射表中查找组织ID，下载PDF格式的投资者关系活动记录表。

This script is now a facade that delegates to the modern unified downloader architecture
while maintaining backward compatibility.

作者: Manus
日期: 2025-05-17
更新: 2026-01-24 (Refactored)
"""

import sys
import json
import os
from pathlib import Path

# 添加src到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.logger import get_logger
from src.factory.downloader_factory import downloader_factory
from src.adapters.legacy_downloader_adapter import CninfoDownloaderAdapter as CninfoDownloader
from selenium import webdriver

# Backward compatibility functions for tests
def get_org_id_by_code(stock_code):
    from src.data.mapping import MappingManager
    return MappingManager().get_org_id(stock_code)

def standardize_stock_code(stock_code):
    from src.utils.string_optimizer import standardize_stock_code as std
    return std(stock_code)

# 初始化结构化日志记录器
logger = get_logger('cninfo_downloader', 'logs/cninfo_downloader.log')

def main():
    """主函数"""
    # 设置控制台编码为UTF-8
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass

    # 读取配置文件
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            # 如果没有config.json，尝试使用默认配置或从命令行参数获取（此处简化处理）
            logger.warning("config.json not found, utilizing internal defaults")
            config = {}
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        sys.exit(1)
    
    stock_code = config.get('stock_code')
    save_dir = config.get('save_dir', 'downloads')
    headless = config.get('headless', True)
    max_retries = config.get('max_retries', 3)
    
    if not stock_code:
        # 尝试从命令行参数获取
        if len(sys.argv) > 1:
            stock_code = sys.argv[1]
        else:
            logger.error("未指定股票代码 (Not specified in config.json or CLI args)")
            sys.exit(1)
    
    logger.info(f"开始处理股票代码: {stock_code}")
    
    # 创建下载器 (使用遗留适配器)
    try:
        downloader = downloader_factory.create_legacy_adapter(
            'cninfo',
            save_dir=save_dir
        )
    except Exception as e:
        logger.error(f"Failed to initialize downloader: {e}")
        sys.exit(1)
    
    # 处理多个页面配置
    pages = config.get('pages', [])
    total_success = False
    
    if pages:
        logger.info(f"发现 {len(pages)} 个页面配置，开始逐个处理")
        for page_config in pages:
            page_name = page_config.get('name', '未知页面')
            suffix = page_config.get('suffix', '')
            allowed_keywords = page_config.get('allowed_keywords')
            max_pages = page_config.get('max_pages', 5)
            
            logger.info(f"开始处理页面: {page_name} (suffix: {suffix})")
            if allowed_keywords:
                logger.info(f"关键词过滤: {allowed_keywords}")
            
            success = downloader.download_activity_records(
                stock_code, 
                headless=headless, 
                max_retries=max_retries,
                suffix=suffix,
                allowed_keywords=allowed_keywords,
                max_pages=max_pages
            )
            total_success = total_success or success
            
    else:
        # 向后兼容：如果没有页面配置，使用默认行为
        logger.info("使用默认下载行为")
        total_success = downloader.download_activity_records(stock_code, headless=headless, max_retries=max_retries)
    
    if total_success:
        logger.info("所有下载任务完成")
    else:
        logger.error("部分或全部下载任务失败")
        sys.exit(1)

if __name__ == "__main__":
    main()