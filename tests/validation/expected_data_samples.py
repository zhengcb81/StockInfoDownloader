#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
期待数据样本库
提供标准化的期待数据样本，用于测试验证框架
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class SampleType(Enum):
    """样本类型枚举"""
    BASIC = "basic"           # 基础样本
    COMPLETE = "complete"     # 完整样本
    PARTIAL = "partial"       # 部分样本
    CORRUPTED = "corrupted"   # 损坏样本
    EXTRA = "extra"           # 额外样本
    MISSING = "missing"       # 缺失样本


@dataclass
class ExpectedDataSample:
    """期待数据样本类"""
    name: str
    description: str
    sample_type: SampleType
    stock_codes: List[str]
    expected_files_per_stock: int
    file_sizes: Dict[str, int]  # 文件名模式 -> 文件大小
    validation_rules: Dict[str, Any]


class ExpectedDataSampleLibrary:
    """期待数据样本库"""
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        初始化样本库
        
        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir) if base_dir else Path(tempfile.mkdtemp())
        self.samples_dir = self.base_dir / "samples"
        self.samples_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化样本定义
        self.samples = self._initialize_samples()
        
        # 为每个样本创建数据
        self._create_sample_data()
    
    def _initialize_samples(self) -> Dict[str, ExpectedDataSample]:
        """初始化样本定义"""
        return {
            "basic_sample": ExpectedDataSample(
                name="basic_sample",
                description="基础样本 - 包含标准股票数据的完整文件集",
                sample_type=SampleType.BASIC,
                stock_codes=["300470", "000001", "002415"],
                expected_files_per_stock=4,
                file_sizes={
                    "*一季度报告.pdf": 50 * 1024,  # 50KB
                    "*半年报.pdf": 80 * 1024,     # 80KB
                    "*年报.pdf": 120 * 1024,      # 120KB
                    "*投资者关系活动.pdf": 30 * 1024  # 30KB
                },
                validation_rules={
                    "required_files": 4,
                    "min_file_size": 20 * 1024,
                    "max_file_size": 150 * 1024,
                    "allowed_keywords": ["一季度报告", "半年报", "年报", "投资者关系活动"]
                }
            ),
            "complete_sample": ExpectedDataSample(
                name="complete_sample",
                description="完整样本 - 包含多种股票类型和文件格式",
                sample_type=SampleType.COMPLETE,
                stock_codes=["300470", "000001", "002415", "600519", "601318"],
                expected_files_per_stock=6,
                file_sizes={
                    "*一季度报告.pdf": 45 * 1024,
                    "*半年报.pdf": 75 * 1024,
                    "*年报.pdf": 110 * 1024,
                    "*投资者关系活动.pdf": 25 * 1024,
                    "*临时公告.pdf": 15 * 1024,
                    "*业绩预告.pdf": 20 * 1024
                },
                validation_rules={
                    "required_files": 6,
                    "min_file_size": 10 * 1024,
                    "max_file_size": 130 * 1024,
                    "allowed_keywords": ["一季度报告", "半年报", "年报", "投资者关系活动", "临时公告", "业绩预告"]
                }
            ),
            "partial_sample": ExpectedDataSample(
                name="partial_sample",
                description="部分样本 - 只包含部分文件，用于测试缺失文件场景",
                sample_type=SampleType.PARTIAL,
                stock_codes=["300470", "000001"],
                expected_files_per_stock=2,
                file_sizes={
                    "*一季度报告.pdf": 40 * 1024,
                    "*半年报.pdf": 70 * 1024
                },
                validation_rules={
                    "required_files": 2,
                    "min_file_size": 30 * 1024,
                    "max_file_size": 80 * 1024,
                    "allowed_keywords": ["一季度报告", "半年报"]
                }
            ),
            "corrupted_sample": ExpectedDataSample(
                name="corrupted_sample",
                description="损坏样本 - 包含大小或内容不匹配的文件",
                sample_type=SampleType.CORRUPTED,
                stock_codes=["300470"],
                expected_files_per_stock=4,
                file_sizes={
                    "*一季度报告.pdf": 25 * 1024,  # 比标准小
                    "*半年报.pdf": 100 * 1024,    # 比标准大
                    "*年报.pdf": 120 * 1024,
                    "*投资者关系活动.pdf": 30 * 1024
                },
                validation_rules={
                    "required_files": 4,
                    "min_file_size": 20 * 1024,
                    "max_file_size": 150 * 1024,
                    "allowed_keywords": ["一季度报告", "半年报", "年报", "投资者关系活动"]
                }
            ),
            "extra_sample": ExpectedDataSample(
                name="extra_sample",
                description="额外样本 - 包含额外文件和目录",
                sample_type=SampleType.EXTRA,
                stock_codes=["300470", "000001"],
                expected_files_per_stock=4,
                file_sizes={
                    "*一季度报告.pdf": 50 * 1024,
                    "*半年报.pdf": 80 * 1024,
                    "*年报.pdf": 120 * 1024,
                    "*投资者关系活动.pdf": 30 * 1024,
                    "*额外文件.pdf": 10 * 1024  # 额外文件
                },
                validation_rules={
                    "required_files": 4,
                    "min_file_size": 20 * 1024,
                    "max_file_size": 150 * 1024,
                    "allowed_keywords": ["一季度报告", "半年报", "年报", "投资者关系活动"]
                }
            ),
            "missing_sample": ExpectedDataSample(
                name="missing_sample",
                description="缺失样本 - 缺少某些股票目录",
                sample_type=SampleType.MISSING,
                stock_codes=["300470"],  # 只包含一个股票
                expected_files_per_stock=4,
                file_sizes={
                    "*一季度报告.pdf": 50 * 1024,
                    "*半年报.pdf": 80 * 1024,
                    "*年报.pdf": 120 * 1024,
                    "*投资者关系活动.pdf": 30 * 1024
                },
                validation_rules={
                    "required_files": 4,
                    "min_file_size": 20 * 1024,
                    "max_file_size": 150 * 1024,
                    "allowed_keywords": ["一季度报告", "半年报", "年报", "投资者关系活动"]
                }
            )
        }
    
    def _create_sample_data(self):
        """为每个样本创建数据"""
        for sample_name, sample in self.samples.items():
            sample_dir = self.samples_dir / sample_name
            sample_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建样本配置
            config_file = sample_dir / "sample_config.json"
            config_data = {
                "name": sample.name,
                "description": sample.description,
                "sample_type": sample.sample_type.value,
                "stock_codes": sample.stock_codes,
                "expected_files_per_stock": sample.expected_files_per_stock,
                "file_sizes": sample.file_sizes,
                "validation_rules": sample.validation_rules
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            # 创建期待数据
            expected_dir = sample_dir / "expected_data"
            expected_dir.mkdir(parents=True, exist_ok=True)
            
            self._create_expected_data(expected_dir, sample)
    
    def _create_expected_data(self, expected_dir: Path, sample: ExpectedDataSample):
        """创建期待数据"""
        # 股票名称映射
        stock_names = {
            "300470": "中密控股",
            "000001": "平安银行",
            "002415": "海康威视",
            "600519": "贵州茅台",
            "601318": "中国平安"
        }
        
        for stock_code in sample.stock_codes:
            stock_name = stock_names.get(stock_code, f"测试公司{stock_code}")
            stock_dir = expected_dir / stock_name
            stock_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建文件
            file_patterns = list(sample.file_sizes.keys())
            
            for i, pattern in enumerate(file_patterns):
                if i >= sample.expected_files_per_stock:
                    break
                
                # 替换通配符
                filename = pattern.replace("*", f"{stock_name}：{stock_code}")
                filepath = stock_dir / filename
                
                # 获取文件大小
                file_size = sample.file_sizes[pattern]
                
                # 创建文件内容
                self._create_sample_file(filepath, stock_name, stock_code, file_size)
    
    def _create_sample_file(self, filepath: Path, stock_name: str, stock_code: str, file_size: int):
        """创建样本文件"""
        # 基础PDF结构
        pdf_header = b"%PDF-1.4\n"
        pdf_footer = b"%%EOF\n"
        
        # 创建内容
        content = f"""
        {stock_name} ({stock_code}) 测试报告
        文件大小: {file_size} 字节
        创建时间: 2025-01-01
        样本类型: 测试数据
        """.encode('utf-8')
        
        # 填充到指定大小
        padding_size = file_size - len(pdf_header) - len(content) - len(pdf_footer)
        if padding_size > 0:
            padding = b" " * padding_size
        else:
            padding = b""
        
        # 写入文件
        with open(filepath, 'wb') as f:
            f.write(pdf_header)
            f.write(content)
            f.write(padding)
            f.write(pdf_footer)
    
    def get_sample(self, sample_name: str) -> Optional[ExpectedDataSample]:
        """获取样本"""
        return self.samples.get(sample_name)
    
    def get_all_samples(self) -> List[ExpectedDataSample]:
        """获取所有样本"""
        return list(self.samples.values())
    
    def get_sample_path(self, sample_name: str) -> Optional[Path]:
        """获取样本路径"""
        if sample_name not in self.samples:
            return None
        return self.samples_dir / sample_name
    
    def get_expected_data_path(self, sample_name: str) -> Optional[Path]:
        """获取期待数据路径"""
        sample_path = self.get_sample_path(sample_name)
        if not sample_path:
            return None
        return sample_path / "expected_data"
    
    def create_test_scenario(self, sample_name: str, actual_data_dir: str) -> Dict[str, Any]:
        """创建测试场景"""
        sample = self.get_sample(sample_name)
        if not sample:
            return {}
        
        expected_data_path = self.get_expected_data_path(sample_name)
        if not expected_data_path:
            return {}
        
        return {
            "sample_name": sample_name,
            "sample_type": sample.sample_type.value,
            "description": sample.description,
            "expected_data_dir": str(expected_data_path),
            "actual_data_dir": actual_data_dir,
            "stock_codes": sample.stock_codes,
            "validation_rules": sample.validation_rules
        }
    
    def export_sample(self, sample_name: str, export_dir: str) -> str:
        """导出样本"""
        sample_path = self.get_sample_path(sample_name)
        if not sample_path:
            return ""
        
        export_path = Path(export_dir) / sample_name
        export_path.mkdir(parents=True, exist_ok=True)
        
        # 复制样本数据
        shutil.copytree(sample_path, export_path, dirs_exist_ok=True)
        
        return str(export_path)
    
    def export_all_samples(self, export_dir: str) -> str:
        """导出所有样本"""
        export_path = Path(export_dir) / "expected_data_samples"
        export_path.mkdir(parents=True, exist_ok=True)
        
        # 导出样本库配置
        library_config = {
            "total_samples": len(self.samples),
            "samples": {}
        }
        
        for sample_name, sample in self.samples.items():
            library_config["samples"][sample_name] = {
                "name": sample.name,
                "description": sample.description,
                "sample_type": sample.sample_type.value,
                "stock_codes": sample.stock_codes,
                "expected_files_per_stock": sample.expected_files_per_stock
            }
            
            # 导出单个样本
            self.export_sample(sample_name, str(export_path))
        
        # 保存库配置
        config_file = export_path / "library_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(library_config, f, ensure_ascii=False, indent=2)
        
        return str(export_path)
    
    def cleanup(self):
        """清理样本库"""
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)


# 全局样本库实例
expected_data_sample_library = ExpectedDataSampleLibrary()