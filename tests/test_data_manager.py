#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强的测试数据管理器
支持期待数据验证框架，提供统一的测试数据管理
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from tests.validation.expected_data_validator import (
    ExpectedDataValidator, 
    ComparisonMode, 
    ValidationResult
)


@dataclass
class StockDataModel:
    """测试股票数据模型"""
    code: str
    name: str
    org_id: str
    expected_files: List[str]
    validation_keywords: List[str]


@dataclass
class ScenarioModel:
    """测试场景模型"""
    name: str
    description: str
    stocks: List[StockDataModel]
    comparison_mode: ComparisonMode
    expected_data_dir: str
    actual_data_dir: str


class DataManagerTool:
    """增强的测试数据管理器工具"""
    
    def __init__(self, base_test_dir: Optional[str] = None):
        """
        初始化测试数据管理器
        
        Args:
            base_test_dir: 基础测试目录路径
        """
        self.base_test_dir = Path(base_test_dir) if base_test_dir else Path(tempfile.mkdtemp())
        self.expected_data_dir = self.base_test_dir / "expected_data"
        self.actual_data_dir = self.base_test_dir / "actual_data"
        self.temp_data_dir = self.base_test_dir / "temp_data"
        
        # 创建目录结构
        self.expected_data_dir.mkdir(parents=True, exist_ok=True)
        self.actual_data_dir.mkdir(parents=True, exist_ok=True)
        self.temp_data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化验证器
        self.validator = ExpectedDataValidator()
        
        # 测试股票数据
        self.test_stocks = self._initialize_test_stocks()
        self.test_scenarios = self._initialize_test_scenarios()
    
    def _initialize_test_stocks(self) -> Dict[str, StockDataModel]:
        """初始化测试股票数据"""
        stocks_data = {
            "300470": StockDataModel(
                code="300470",
                name="中密控股",
                org_id="9900023856",
                expected_files=[
                    "中密控股：300470一季度报告.pdf",
                    "中密控股：300470半年报.pdf",
                    "中密控股：300470年报.pdf",
                    "中密控股：300470投资者关系活动.pdf"
                ],
                validation_keywords=["一季度报告", "半年报", "年报", "投资者关系活动"]
            ),
            "000001": StockDataModel(
                code="000001",
                name="平安银行",
                org_id="9900000001",
                expected_files=[
                    "平安银行：000001一季度报告.pdf",
                    "平安银行：000001半年报.pdf",
                    "平安银行：000001年报.pdf",
                    "平安银行：000001投资者关系活动.pdf"
                ],
                validation_keywords=["一季度报告", "半年报", "年报", "投资者关系活动"]
            ),
            "002415": StockDataModel(
                code="002415",
                name="海康威视",
                org_id="9900002415",
                expected_files=[
                    "海康威视：002415一季度报告.pdf",
                    "海康威视：002415半年报.pdf",
                    "海康威视：002415年报.pdf",
                    "海康威视：002415投资者关系活动.pdf"
                ],
                validation_keywords=["一季度报告", "半年报", "年报", "投资者关系活动"]
            )
        }
        
        # 为每个股票创建期待数据目录和文件
        for stock_data in stocks_data.values():
            self._create_expected_data_for_stock(stock_data)
        
        return stocks_data
    
    def _initialize_test_scenarios(self) -> Dict[str, ScenarioModel]:
        """初始化测试场景"""
        return {
            "basic_validation": ScenarioModel(
                name="basic_validation",
                description="基础验证场景 - 单个股票完整验证",
                stocks=[self.test_stocks["300470"]],
                comparison_mode=ComparisonMode.STRICT,
                expected_data_dir=str(self.expected_data_dir),
                actual_data_dir=str(self.actual_data_dir)
            ),
            "multi_stock_validation": ScenarioModel(
                name="multi_stock_validation",
                description="多股票验证场景 - 多个股票并行验证",
                stocks=[self.test_stocks["300470"], self.test_stocks["000001"]],
                comparison_mode=ComparisonMode.LENIENT,
                expected_data_dir=str(self.expected_data_dir),
                actual_data_dir=str(self.actual_data_dir)
            ),
            "content_only_validation": ScenarioModel(
                name="content_only_validation",
                description="仅内容验证场景 - 忽略文件大小和哈希",
                stocks=[self.test_stocks["002415"]],
                comparison_mode=ComparisonMode.CONTENT_ONLY,
                expected_data_dir=str(self.expected_data_dir),
                actual_data_dir=str(self.actual_data_dir)
            )
        }
    
    def _create_expected_data_for_stock(self, stock_data: StockDataModel):
        """为股票创建期待数据"""
        stock_dir = self.expected_data_dir / stock_data.name
        stock_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建模拟的PDF文件
        for filename in stock_data.expected_files:
            filepath = stock_dir / filename
            self._create_mock_pdf_file(filepath, stock_data)
    
    def _create_mock_pdf_file(self, filepath: Path, stock_data: StockDataModel):
        """创建模拟的PDF文件"""
        # 创建包含股票信息的模拟PDF内容
        content = f"""
        %PDF-1.4
        1 0 obj
        <<
        /Type /Catalog
        /Pages 2 0 R
        >>
        endobj
        
        2 0 obj
        <<
        /Type /Pages
        /Kids [3 0 R]
        /Count 1
        >>
        endobj
        
        3 0 obj
        <<
        /Type /Page
        /Parent 2 0 R
        /MediaBox [0 0 612 792]
        /Contents 4 0 R
        /Resources <<
            /Font <<
                /F1 5 0 R
            >>
        >>
        >>
        endobj
        
        4 0 obj
        <<
        /Length 100
        >>
        stream
        BT
        /F1 12 Tf
        50 700 Td
        ({stock_data.name} ({stock_data.code}) 测试报告) Tj
        ET
        endstream
        endobj
        
        5 0 obj
        <<
        /Type /Font
        /Subtype /Type1
        /BaseFont /Helvetica
        >>
        endobj
        
        xref
        0 6
        0000000000 65535 f 
        0000000009 00000 n 
        0000000058 00000 n 
        0000000115 00000 n 
        0000000234 00000 n 
        0000000415 00000 n 
        trailer
        <<
        /Size 6
        /Root 1 0 R
        >>
        startxref
        500
        %%EOF
        """.encode('utf-8')
        
        with open(filepath, 'wb') as f:
            f.write(content)
    
    def get_stock_data(self, stock_code: str) -> Optional[StockDataModel]:
        """获取股票数据"""
        return self.test_stocks.get(stock_code)
    
    def get_all_stocks(self) -> List[StockDataModel]:
        """获取所有股票数据"""
        return list(self.test_stocks.values())
    
    def get_scenario(self, scenario_name: str) -> Optional[ScenarioModel]:
        """获取测试场景"""
        return self.test_scenarios.get(scenario_name)
    
    def get_all_scenarios(self) -> List[ScenarioModel]:
        """获取所有测试场景"""
        return list(self.test_scenarios.values())
    
    def simulate_download(self, stock_codes: List[str]) -> Dict[str, List[str]]:
        """模拟下载过程"""
        downloaded_files = {}
        
        for stock_code in stock_codes:
            stock_data = self.get_stock_data(stock_code)
            if not stock_data:
                continue
            
            # 创建股票目录
            stock_dir = self.actual_data_dir / stock_data.name
            stock_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制期待数据文件作为模拟下载
            expected_stock_dir = self.expected_data_dir / stock_data.name
            stock_files = []
            
            for expected_file in expected_stock_dir.glob("*.pdf"):
                actual_file = stock_dir / expected_file.name
                shutil.copy2(expected_file, actual_file)
                stock_files.append(str(actual_file))
            
            downloaded_files[stock_code] = stock_files
        
        return downloaded_files
    
    def simulate_partial_download(self, stock_code: str, file_count: int) -> List[str]:
        """模拟部分下载"""
        stock_data = self.get_stock_data(stock_code)
        if not stock_data:
            return []
        
        # 创建股票目录
        stock_dir = self.actual_data_dir / stock_data.name
        stock_dir.mkdir(parents=True, exist_ok=True)
        
        # 只下载部分文件
        expected_stock_dir = self.expected_data_dir / stock_data.name
        downloaded_files = []
        
        for i, expected_file in enumerate(expected_stock_dir.glob("*.pdf")):
            if i >= file_count:
                break
            
            actual_file = stock_dir / expected_file.name
            shutil.copy2(expected_file, actual_file)
            downloaded_files.append(str(actual_file))
        
        return downloaded_files
    
    def simulate_download_with_extra_files(self, stock_code: str, extra_files: List[str]) -> List[str]:
        """模拟下载包含额外文件"""
        stock_data = self.get_stock_data(stock_code)
        if not stock_data:
            return []
        
        # 创建股票目录
        stock_dir = self.actual_data_dir / stock_data.name
        stock_dir.mkdir(parents=True, exist_ok=True)
        
        # 下载所有期待文件
        downloaded_files = []
        expected_stock_dir = self.expected_data_dir / stock_data.name
        
        for expected_file in expected_stock_dir.glob("*.pdf"):
            actual_file = stock_dir / expected_file.name
            shutil.copy2(expected_file, actual_file)
            downloaded_files.append(str(actual_file))
        
        # 添加额外文件
        for extra_filename in extra_files:
            extra_file = stock_dir / extra_filename
            with open(extra_file, 'wb') as f:
                f.write(b"Extra file content")
            downloaded_files.append(str(extra_file))
        
        return downloaded_files
    
    def validate_scenario(self, scenario_name: str) -> ValidationResult:
        """验证测试场景"""
        scenario = self.get_scenario(scenario_name)
        if not scenario:
            return ValidationResult(
                overall_success=False,
                comparison_mode=ComparisonMode.STRICT,
                directory_results=[],
                total_files_compared=0,
                files_matched=0,
                files_mismatched=0,
                files_missing=0,
                files_extra=0,
                error_messages=[f"测试场景不存在: {scenario_name}"]
            )
        
        # 设置验证器模式
        self.validator.comparison_mode = scenario.comparison_mode
        
        # 执行验证
        return self.validator.validate_expected_data(
            Path(scenario.expected_data_dir),
            Path(scenario.actual_data_dir)
        )
    
    def validate_single_stock(self, stock_code: str, comparison_mode: ComparisonMode = ComparisonMode.STRICT) -> ValidationResult:
        """验证单个股票"""
        stock_data = self.get_stock_data(stock_code)
        if not stock_data:
            return ValidationResult(
                overall_success=False,
                comparison_mode=comparison_mode,
                directory_results=[],
                total_files_compared=0,
                files_matched=0,
                files_mismatched=0,
                files_missing=0,
                files_extra=0,
                error_messages=[f"股票不存在: {stock_code}"]
            )
        
        # 设置验证器模式
        self.validator.comparison_mode = comparison_mode
        
        # 定义测试用例
        test_case = {
            "stock_code": stock_code,
            "suffix": "research",
            "allowed_keywords": stock_data.validation_keywords
        }
        
        # 执行验证
        return self.validator.validate_single_test_case(
            test_case,
            Path(self.expected_data_dir),
            Path(self.actual_data_dir)
        )
    
    def cleanup(self):
        """清理测试数据"""
        if self.base_test_dir.exists():
            shutil.rmtree(self.base_test_dir)
    
    def export_test_data(self, export_dir: str) -> str:
        """导出测试数据"""
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)
        
        # 导出配置
        config_data = {
            "test_stocks": {
                code: {
                    "name": data.name,
                    "org_id": data.org_id,
                    "expected_files": data.expected_files,
                    "validation_keywords": data.validation_keywords
                }
                for code, data in self.test_stocks.items()
            },
            "test_scenarios": {
                name: {
                    "description": scenario.description,
                    "stocks": [s.code for s in scenario.stocks],
                    "comparison_mode": scenario.comparison_mode.value,
                    "expected_data_dir": scenario.expected_data_dir,
                    "actual_data_dir": scenario.actual_data_dir
                }
                for name, scenario in self.test_scenarios.items()
            }
        }
        
        config_file = export_path / "test_data_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        # 复制期待数据
        expected_export_dir = export_path / "expected_data"
        if self.expected_data_dir.exists():
            shutil.copytree(self.expected_data_dir, expected_export_dir, dirs_exist_ok=True)
        
        return str(export_path)


# 全局测试数据管理器实例
test_data_manager = DataManagerTool()