#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
检查下载的文件
"""

import sys
import os
import time
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.logger import get_logger
from src.services.downloader import DownloadService

logger = get_logger(__name__)

def check_downloaded_files():
    """检查下载的文件"""
    logger.info("检查下载的文件...")
    
    # 创建临时目录
    test_dir = "temp_check_results"
    os.makedirs(test_dir, exist_ok=True)
    
    # 创建下载服务
    service = DownloadService(save_dir=test_dir)
    
    try:
        # 测试300470调研报告
        result = service.download_stock_pdfs("300470", [{"suffix": "research"}], max_retries=1)
        
        logger.info(f"下载结果: {len(result)} 条记录")
        
        for record in result:
            logger.info(f"文件: {record.filename}")
            logger.info(f"路径: {record.file_path}")
            logger.info(f"大小: {record.file_size} bytes")
            logger.info(f"URL: {record.source_url}")
            logger.info("---")
        
        # 检查目录中的实际文件
        pdf_files = list(Path(test_dir).rglob("*.pdf"))
        logger.info(f"目录中找到 {len(pdf_files)} 个PDF文件:")
        
        for pdf_file in pdf_files:
            logger.info(f"  - {pdf_file.name}")
            
        return True
            
    except Exception as e:
        logger.error(f"检查过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理临时目录
        import shutil
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        logger.info("检查完成")

if __name__ == "__main__":
    check_downloaded_files()