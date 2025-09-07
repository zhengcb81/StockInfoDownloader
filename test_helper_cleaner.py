#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试清理工具模块
提供端到端测试后的清理功能
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCleaner:
    """测试清理器 - 负责清理测试目录中的文件和目录"""
    
    def __init__(self, base_dir: str):
        """
        初始化清理器
        
        Args:
            base_dir: 测试基础目录
        """
        self.base_dir = Path(base_dir)
        
    def clean_test_directory(self, 
                           preserve_files: List[Dict[str, Any]] = None,
                           dry_run: bool = False) -> Dict[str, Any]:
        """
        清理测试目录，保留指定的文件
        
        Args:
            preserve_files: 需要保留的文件列表，每个文件包含stock_code和delete_later信息
            dry_run: 是否只是模拟运行，不实际删除
            
        Returns:
            清理结果统计
        """
        if not self.base_dir.exists():
            logger.info(f"测试目录不存在: {self.base_dir}")
            return {"status": "no_directory", "cleaned_files": 0, "cleaned_dirs": 0}
        
        # 确定需要保留的文件
        files_to_preserve = self._get_files_to_preserve(preserve_files or [])
        
        # 统计信息
        cleaned_files = 0
        cleaned_dirs = 0
        preserved_files = 0
        
        logger.info(f"开始清理测试目录: {self.base_dir}")
        logger.info(f"需要保留的文件数量: {len(files_to_preserve)}")
        
        # 首先处理文件
        for file_path in self.base_dir.rglob("*.pdf"):
            relative_path = file_path.relative_to(self.base_dir)
            
            if self._should_preserve_file(file_path, files_to_preserve):
                logger.info(f"保留文件: {relative_path}")
                preserved_files += 1
            else:
                if dry_run:
                    logger.info(f"[模拟] 删除文件: {relative_path}")
                else:
                    try:
                        file_path.unlink()
                        logger.info(f"删除文件: {relative_path}")
                        cleaned_files += 1
                    except Exception as e:
                        logger.error(f"删除文件失败: {relative_path}, 错误: {e}")
        
        # 然后处理空目录（保留有文件的目录）
        dirs_to_check = list(self.base_dir.rglob("*"))
        dirs_to_check.sort(key=lambda x: len(x.parts), reverse=True)  # 从深层目录开始
        
        for dir_path in dirs_to_check:
            if dir_path.is_dir() and dir_path != self.base_dir:
                # 检查目录是否为空或只包含子目录
                contents = list(dir_path.iterdir())
                pdf_files = [f for f in contents if f.is_file() and f.suffix.lower() == '.pdf']
                
                if not pdf_files:
                    # 检查这个目录是否需要保留（基于preserve_files）
                    if self._should_preserve_directory(dir_path, files_to_preserve):
                        logger.info(f"保留空目录: {dir_path.relative_to(self.base_dir)}")
                    else:
                        if dry_run:
                            logger.info(f"[模拟] 删除空目录: {dir_path.relative_to(self.base_dir)}")
                        else:
                            try:
                                dir_path.rmdir()
                                logger.info(f"删除空目录: {dir_path.relative_to(self.base_dir)}")
                                cleaned_dirs += 1
                            except Exception as e:
                                logger.error(f"删除目录失败: {dir_path.relative_to(self.base_dir)}, 错误: {e}")
        
        # 清理根目录中的非PDF文件
        for item in self.base_dir.iterdir():
            if item.is_file() and item.suffix.lower() != '.pdf':
                if dry_run:
                    logger.info(f"[模拟] 删除非PDF文件: {item.name}")
                else:
                    try:
                        item.unlink()
                        logger.info(f"删除非PDF文件: {item.name}")
                        cleaned_files += 1
                    except Exception as e:
                        logger.error(f"删除非PDF文件失败: {item.name}, 错误: {e}")
        
        result = {
            "status": "success",
            "cleaned_files": cleaned_files,
            "cleaned_dirs": cleaned_dirs,
            "preserved_files": preserved_files,
            "dry_run": dry_run
        }
        
        logger.info(f"清理完成: 删除 {cleaned_files} 个文件, {cleaned_dirs} 个目录, 保留 {preserved_files} 个文件")
        return result
    
    def _get_files_to_preserve(self, preserve_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        获取需要保留的文件列表
        
        Args:
            preserve_files: 测试用例列表
            
        Returns:
            需要保留的文件信息列表
        """
        files_to_preserve = []
        
        for test_case in preserve_files:
            if not test_case.get("delete_later", True):  # delete_later=False 的文件需要保留
                stock_code = test_case["stock_code"]
                
                # 获取股票名称
                stock_name = self._get_stock_name(stock_code)
                
                # 方法1：通过股票名称查找目录
                company_dir = self.base_dir / stock_name
                if company_dir.exists():
                    for pdf_file in company_dir.glob("*.pdf"):
                        files_to_preserve.append({
                            "file_path": pdf_file,
                            "stock_code": stock_code,
                            "stock_name": stock_name,
                            "test_case": test_case
                        })
                
                # 方法2：如果股票名称查找失败，扫描所有目录查找包含股票代码的目录
                else:
                    for dir_path in self.base_dir.iterdir():
                        if dir_path.is_dir():
                            # 检查目录名是否包含股票代码（处理编码问题）
                            if stock_code in dir_path.name:
                                logger.info(f"通过股票代码找到匹配目录: {dir_path.name} (stock_code: {stock_code})")
                                for pdf_file in dir_path.glob("*.pdf"):
                                    files_to_preserve.append({
                                        "file_path": pdf_file,
                                        "stock_code": stock_code,
                                        "stock_name": dir_path.name,
                                        "test_case": test_case
                                    })
                                break
                
                # 方法3：如果还是没找到，扫描所有PDF文件
                if not any(f["stock_code"] == stock_code for f in files_to_preserve):
                    for pdf_file in self.base_dir.rglob("*.pdf"):
                        # 检查文件名是否包含股票代码
                        if stock_code in pdf_file.name:
                            logger.info(f"通过文件名找到匹配文件: {pdf_file.name} (stock_code: {stock_code})")
                            files_to_preserve.append({
                                "file_path": pdf_file,
                                "stock_code": stock_code,
                                "stock_name": pdf_file.parent.name,
                                "test_case": test_case
                            })
                            break
        
        return files_to_preserve
    
    def _should_preserve_file(self, file_path: Path, files_to_preserve: List[Dict[str, Any]]) -> bool:
        """
        判断文件是否应该保留
        
        Args:
            file_path: 文件路径
            files_to_preserve: 需要保留的文件列表
            
        Returns:
            是否应该保留
        """
        for preserve_info in files_to_preserve:
            if file_path == preserve_info["file_path"]:
                return True
        return False
    
    def _should_preserve_directory(self, dir_path: Path, files_to_preserve: List[Dict[str, Any]]) -> bool:
        """
        判断目录是否应该保留（即使为空）
        
        Args:
            dir_path: 目录路径
            files_to_preserve: 需要保留的文件列表
            
        Returns:
            是否应该保留
        """
        for preserve_info in files_to_preserve:
            if dir_path == preserve_info["file_path"].parent:
                return True
        return False
    
    def _get_stock_name(self, stock_code: str) -> str:
        """
        获取股票名称
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票名称
        """
        try:
            # 尝试使用get_stock_name模块
            from get_stock_name import get_stock_name
            stock_name = get_stock_name(stock_code)
            
            # 如果获取失败或返回错误信息，使用股票代码
            if not stock_name or stock_name.startswith('错误') or stock_name.startswith('网络'):
                return f"股票{stock_code}"
            
            return stock_name
        except Exception:
            # 如果导入或调用失败，使用股票代码
            return f"股票{stock_code}"
    
    def get_directory_status(self) -> Dict[str, Any]:
        """
        获取当前目录状态
        
        Returns:
            目录状态信息
        """
        if not self.base_dir.exists():
            return {"exists": False, "files": 0, "dirs": 0, "size": 0}
        
        files = list(self.base_dir.rglob("*.pdf"))
        dirs = [d for d in self.base_dir.rglob("*") if d.is_dir() and d != self.base_dir]
        
        total_size = sum(f.stat().st_size for f in files if f.exists())
        
        return {
            "exists": True,
            "files": len(files),
            "dirs": len(dirs),
            "size": total_size,
            "file_list": [str(f.relative_to(self.base_dir)) for f in files],
            "dir_list": [str(d.relative_to(self.base_dir)) for d in dirs]
        }


def clean_test_files(base_dir: str, 
                    preserve_files: List[Dict[str, Any]] = None,
                    dry_run: bool = False) -> Dict[str, Any]:
    """
    便捷函数：清理测试文件
    
    Args:
        base_dir: 测试基础目录
        preserve_files: 需要保留的文件列表
        dry_run: 是否只是模拟运行
        
    Returns:
        清理结果
    """
    cleaner = TestCleaner(base_dir)
    return cleaner.clean_test_directory(preserve_files, dry_run)


def get_test_directory_status(base_dir: str) -> Dict[str, Any]:
    """
    便捷函数：获取测试目录状态
    
    Args:
        base_dir: 测试基础目录
        
    Returns:
        目录状态
    """
    cleaner = TestCleaner(base_dir)
    return cleaner.get_directory_status()


if __name__ == "__main__":
    # 测试代码
    import json
    
    # 示例配置
    test_config = {
        "save_dir": "end2end_test/test_results",
        "test_cases": [
            {"stock_code": "301611", "delete_later": False},
            {"stock_code": "300470", "delete_later": True}
        ]
    }
    
    print("=== 测试清理工具 ===")
    
    # 获取清理前状态
    status_before = get_test_directory_status(test_config["save_dir"])
    print(f"清理前状态: {status_before}")
    
    # 执行清理（模拟运行）
    print("\n=== 模拟清理 ===")
    result_dry = clean_test_files(test_config["save_dir"], test_config["test_cases"], dry_run=True)
    print(f"模拟清理结果: {result_dry}")
    
    # 执行实际清理
    print("\n=== 实际清理 ===")
    result_real = clean_test_files(test_config["save_dir"], test_config["test_cases"], dry_run=False)
    print(f"实际清理结果: {result_real}")
    
    # 获取清理后状态
    status_after = get_test_directory_status(test_config["save_dir"])
    print(f"清理后状态: {status_after}")