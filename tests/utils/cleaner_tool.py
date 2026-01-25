#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试清理工具
提供测试文件和目录的清理功能
"""

import os
import shutil
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class CleanerTool:
    """测试清理器工具"""

    def __init__(self, base_dir: str):
        """
        初始化清理器
        
        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
    
    def clean_test_directory(self, preserve_cases: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, Any]:
        """
        清理测试目录，保留指定的文件
        
        Args:
            preserve_cases: 需要保留的测试用例列表
            dry_run: 是否为模拟运行（不实际删除）
            
        Returns:
            Dict: 清理结果
        """
        if not self.base_dir.exists():
            return {
                "status": "success",
                "message": "目录不存在，无需清理",
                "dry_run": dry_run
            }
        
        # 加载映射文件
        mapping = self._load_mapping()
        
        # 获取要保留的关键词（股票代码和公司名称）
        preserve_keywords = set()
        for case in preserve_cases:
            if not case.get("delete_later", True):
                stock_code = case["stock_code"]
                preserve_keywords.add(stock_code)
                # 尝试查找对应的公司名称
                if stock_code in mapping:
                    company_name = mapping[stock_code].get("name")
                    if company_name:
                        preserve_keywords.add(company_name)
        
        # 统计信息
        total_files = 0
        deleted_files = 0
        preserved_files = 0
        deleted_dirs = 0
        
        # 遍历目录
        for item in self.base_dir.iterdir():
            if item.is_file():
                total_files += 1
                # 检查文件是否需要保留
                if self._should_preserve_file(item, preserve_keywords):
                    preserved_files += 1
                else:
                    if not dry_run:
                        try:
                            item.unlink()
                            deleted_files += 1
                        except Exception:
                            pass
                    else:
                        deleted_files += 1
            
            elif item.is_dir():
                # 检查目录是否需要保留
                if self._should_preserve_dir(item, preserve_keywords):
                    # 保留目录，统计其中的文件
                    for file_item in item.rglob("*"):
                        if file_item.is_file():
                            preserved_files += 1
                else:
                    if not dry_run:
                        try:
                            shutil.rmtree(item)
                            deleted_dirs += 1
                        except Exception:
                            pass
                    else:
                        deleted_dirs += 1
        
        return {
            "status": "success",
            "total_files": total_files,
            "deleted_files": deleted_files,
            "preserved_files": preserved_files,
            "deleted_dirs": deleted_dirs,
            "preserve_keywords": list(preserve_keywords),
            "dry_run": dry_run
        }
    
    def _load_mapping(self) -> Dict[str, Any]:
        """加载股票代码映射"""
        possible_paths = [
            Path("configs/stock_orgid_mapping.json"),
            Path("stock_orgid_mapping.json"),
            Path("../configs/stock_orgid_mapping.json"),
            Path("../../configs/stock_orgid_mapping.json")
        ]
        
        for path in possible_paths:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception:
                    continue
        return {}

    def _should_preserve_file(self, file_path: Path, preserve_keywords: set) -> bool:
        """
        判断文件是否需要保留
        
        Args:
            file_path: 文件路径
            preserve_keywords: 需要保留的关键词集合
            
        Returns:
            bool: 是否需要保留
        """
        # 检查文件名是否包含保留的关键词
        filename = file_path.name.lower()
        for keyword in preserve_keywords:
            if keyword.lower() in filename:
                return True
        
        # 检查父目录名是否包含保留的关键词
        parent_name = file_path.parent.name.lower()
        for keyword in preserve_keywords:
            if keyword.lower() in parent_name:
                return True
        
        return False
    
    def _should_preserve_dir(self, dir_path: Path, preserve_keywords: set) -> bool:
        """
        判断目录是否需要保留
        
        Args:
            dir_path: 目录路径
            preserve_keywords: 需要保留的关键词集合
            
        Returns:
            bool: 是否需要保留
        """
        dir_name = dir_path.name.lower()
        for keyword in preserve_keywords:
            if keyword.lower() in dir_name:
                return True
        return False
    
    def get_directory_status(self) -> Dict[str, Any]:
        """
        获取目录状态信息
        
        Returns:
            Dict: 目录状态信息
        """
        if not self.base_dir.exists():
            return {
                "exists": False,
                "files": 0,
                "directories": 0,
                "file_list": [],
                "dir_list": []
            }
        
        files = []
        directories = []
        
        for item in self.base_dir.iterdir():
            if item.is_file():
                files.append({
                    "name": item.name,
                    "size": item.stat().st_size,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                })
            elif item.is_dir():
                dir_files = list(item.rglob("*"))
                file_count = len([f for f in dir_files if f.is_file()])
                directories.append({
                    "name": item.name,
                    "file_count": file_count,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                })
        
        return {
            "exists": True,
            "files": len(files),
            "directories": len(directories),
            "file_list": files,
            "dir_list": directories
        }


def clean_test_files(base_dir: str, preserve_cases: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, Any]:
    """
    清理测试文件的便捷函数
    
    Args:
        base_dir: 基础目录路径
        preserve_cases: 需要保留的测试用例列表
        dry_run: 是否为模拟运行
        
    Returns:
        Dict: 清理结果
    """
    cleaner = CleanerTool(base_dir)
    return cleaner.clean_test_directory(preserve_cases, dry_run)


def get_test_directory_status(base_dir: str) -> Dict[str, Any]:
    """
    获取测试目录状态的便捷函数
    
    Args:
        base_dir: 基础目录路径
        
    Returns:
        Dict: 目录状态信息
    """
    cleaner = CleanerTool(base_dir)
    return cleaner.get_directory_status()


def create_test_backup(base_dir: str, backup_suffix: str = None) -> Optional[str]:
    """
    创建测试目录备份
    
    Args:
        base_dir: 基础目录路径
        backup_suffix: 备份后缀，如果为None则使用时间戳
        
    Returns:
        Optional[str]: 备份目录路径，失败时返回None
    """
    base_path = Path(base_dir)
    if not base_path.exists():
        return None
    
    if backup_suffix is None:
        backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    backup_path = base_path.parent / f"{base_path.name}_backup_{backup_suffix}"
    
    try:
        shutil.copytree(base_path, backup_path)
        return str(backup_path)
    except Exception:
        return None


def restore_test_backup(backup_path: str, target_path: str) -> bool:
    """
    恢复测试目录备份
    
    Args:
        backup_path: 备份目录路径
        target_path: 目标目录路径
        
    Returns:
        bool: 是否成功
    """
    backup = Path(backup_path)
    target = Path(target_path)
    
    if not backup.exists():
        return False
    
    try:
        # 如果目标目录存在，先删除
        if target.exists():
            shutil.rmtree(target)
        
        # 移动备份目录到目标位置
        shutil.move(str(backup), str(target))
        return True
    except Exception:
        return False


def cleanup_old_backups(base_dir: str, days: int = 7) -> int:
    """
    清理旧的备份目录
    
    Args:
        base_dir: 基础目录路径
        days: 保留天数
        
    Returns:
        int: 清理的备份数量
    """
    from datetime import datetime, timedelta
    
    base_path = Path(base_dir)
    cutoff_date = datetime.now() - timedelta(days=days)
    cleaned_count = 0
    
    # 查找所有备份目录
    for backup_dir in base_path.parent.glob(f"{base_path.name}_backup_*"):
        if backup_dir.is_dir():
            # 从目录名提取时间戳
            try:
                timestamp_str = backup_dir.name.split("_backup_")[-1]
                backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                if backup_date < cutoff_date:
                    shutil.rmtree(backup_dir)
                    cleaned_count += 1
            except Exception:
                pass
    
    return cleaned_count
