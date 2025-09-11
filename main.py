#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
股票信息下载器主程序
使用重构后的模块化架构
"""

import sys
import locale

# 设置控制台编码为UTF-8
if sys.platform == 'win32':
    try:
        # Windows下设置控制台编码为UTF-8
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        # 如果设置失败，忽略错误
        pass

import sys
import json
import os
import argparse
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.config import ConfigManager
from src.core.logger import get_logger
from src.core.performance_monitor import log_performance_stats, get_performance_stats
from src.services.downloader import DownloadService
from src.data.mapping import MappingManager

# 导入股票名称获取函数
try:
    from get_stock_name import get_stock_name
except ImportError:
    # 如果导入失败，使用备选方案
    def get_stock_name(stock_code, mapping_file='stock_orgid_mapping.json'):
        mapping_manager = MappingManager(mapping_file)
        return mapping_manager.get_stock_name(stock_code) or f"股票{stock_code}"


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='股票信息下载器')
    parser.add_argument('--config', default='config.json', help='配置文件路径 (默认: config.json)')
    args = parser.parse_args()
    
    # 初始化日志
    logger = get_logger(__name__)
    
    try:
        logger.info("启动股票信息下载器...")
        
        # 加载配置
        config_manager = ConfigManager()
        try:
            config = config_manager.load_config(args.config)
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            return 1
        
        # 获取股票代码 - 必须提供
        stock_code = config.get('stock_code')
        if not stock_code:
            logger.error("配置文件缺少必需的stock_code参数")
            return 1
        
        logger.info(f"开始处理股票代码: {stock_code}")
        
        # 初始化服务
        mapping_manager = MappingManager()
        save_dir = config.get('save_dir', 'downloads')
        download_service = DownloadService(save_dir=save_dir)
        
        # 验证股票代码
        if not stock_code.isdigit() or len(stock_code) != 6:
            logger.error(f"无效的股票代码: {stock_code}")
            return 1
        
        # 获取组织ID
        org_id = mapping_manager.get_org_id(stock_code)
        if not org_id:
            logger.error(f"无法获取股票 {stock_code} 的组织ID")
            return 1
        
        # 获取股票名称
        stock_name = get_stock_name(stock_code)
        if not stock_name or stock_name.startswith('错误') or stock_name.startswith('网络'):
            # 使用预设名称作为备选
            preset_names = config.get('preset_stock_names', {})
            stock_name = preset_names.get(stock_code, f"股票{stock_code}")
            logger.warning(f"使用预设股票名称: {stock_name}")
        
        logger.info(f"股票信息: {stock_code} - {stock_name}")
        logger.info(f"组织ID: {org_id}")
        
        # 获取页面配置
        pages = config.get('pages', [
            {'name': '调研', 'suffix': 'research', 'allowed_keywords': None},
            {'name': '定期公告', 'suffix': 'periodicReports', 'allowed_keywords': None},
            {'name': '最新公告', 'suffix': 'latestAnnouncement', 'allowed_keywords': ["招股说明书"]}
        ])
        
        # 执行下载
        success = False
        for page_config in pages:
            page_name = page_config.get('name', '未知页面')
            suffix = page_config.get('suffix', '')
            allowed_keywords = page_config.get('allowed_keywords')
            
            logger.info(f"开始下载页面: {page_name}")
            
            try:
                # 构建目标页面列表（新下载器需要字典格式）
                if suffix:
                    target_pages = [{'suffix': suffix, 'allowed_keywords': allowed_keywords}]
                else:
                    target_pages = [{'suffix': 'research', 'allowed_keywords': None}]
                
                # 设置过滤关键词
                if allowed_keywords:
                    logger.info(f"关键词过滤: {allowed_keywords}")
                
                result = download_service.download_stock_pdfs(
                    stock_code=stock_code,
                    target_pages=target_pages,
                    max_retries=config.get('max_retries', 3)
                )
                
                if result and len(result) > 0:
                    success = True
                    logger.info(f"页面 {page_name} 下载完成，下载了 {len(result)} 个文件")
                else:
                    logger.warning(f"页面 {page_name} 下载失败或没有新文件")
                    
            except Exception as e:
                logger.error(f"下载页面 {page_name} 时发生错误: {e}")
                logger.error(f"错误详情: {str(e)}", exc_info=True)
            
            # 页面间延迟 - 优化为0.5秒
            import time
            time.sleep(0.5)
        
        if success:
            logger.info("所有下载任务完成")
            # 输出性能报告
            logger.info("=== 性能统计报告 ===")
            log_performance_stats()
            return 0
        else:
            logger.warning("没有下载任何新文件，但程序运行正常")
            # 输出性能报告
            logger.info("=== 性能统计报告 ===")
            log_performance_stats()
            return 0  # 没有下载新文件不算失败
            
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        return 0
    except Exception as e:
        logger.error(f"程序运行失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)