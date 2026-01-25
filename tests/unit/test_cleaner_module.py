#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试清理工具的测试模块
"""

import os
import shutil
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Import from the new location
from tests.utils.cleaner_tool import (
    CleanerTool, 
    clean_test_files,
    get_test_directory_status,
    create_test_backup,
    restore_test_backup,
    cleanup_old_backups
)

if __name__ == "__main__":
    # 测试代码
    test_dir = "test_cleanup_test"
    os.makedirs(test_dir, exist_ok=True)
    
    # 创建测试文件
    (Path(test_dir) / "CompanyA").mkdir()
    (Path(test_dir) / "CompanyB").mkdir()
    (Path(test_dir) / "CompanyA" / "file1.pdf").write_text("test")
    (Path(test_dir) / "CompanyB" / "file2.pdf").write_text("test")
    (Path(test_dir) / "root_file.pdf").write_text("test")
    
    # 测试清理
    preserve_cases = [
        {"stock_code": "001", "delete_later": False},
        {"stock_code": "002", "delete_later": True}
    ]
    
    cleaner = CleanerTool(test_dir)
    result = cleaner.clean_test_directory(preserve_cases, dry_run=True)
    
    print("清理结果:", json.dumps(result, ensure_ascii=False, indent=2))
    
    # 清理测试目录
    shutil.rmtree(test_dir)