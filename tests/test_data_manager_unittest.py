#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试数据管理器的单元测试
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from tests.test_data_manager import (
    DataManagerTool,
    StockDataModel,
    ScenarioModel,
    ComparisonMode
)


class TestTestDataManager:
    """测试数据管理器测试类"""
    
    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.data_manager = TestDataManager(self.temp_dir)
    
    def teardown_method(self):
        """测试清理"""
        self.data_manager.cleanup()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """测试初始化"""
        assert self.data_manager.base_test_dir.exists()
        assert self.data_manager.expected_data_dir.exists()
        assert self.data_manager.actual_data_dir.exists()
        assert self.data_manager.temp_data_dir.exists()
        
        # 验证测试股票数据
        assert len(self.data_manager.test_stocks) == 3
        assert "300470" in self.data_manager.test_stocks
        assert "000001" in self.data_manager.test_stocks
        assert "002415" in self.data_manager.test_stocks
        
        # 验证测试场景
        assert len(self.data_manager.test_scenarios) == 3
        assert "basic_validation" in self.data_manager.test_scenarios
        assert "multi_stock_validation" in self.data_manager.test_scenarios
        assert "content_only_validation" in self.data_manager.test_scenarios
    
    def test_get_stock_data(self):
        """测试获取股票数据"""
        stock_data = self.data_manager.get_stock_data("300470")
        assert stock_data is not None
        assert stock_data.code == "300470"
        assert stock_data.name == "中密控股"
        assert stock_data.org_id == "9900023856"
        assert len(stock_data.expected_files) == 4
        assert len(stock_data.validation_keywords) == 4
        
        # 测试不存在的股票
        nonexistent_stock = self.data_manager.get_stock_data("999999")
        assert nonexistent_stock is None
    
    def test_get_all_stocks(self):
        """测试获取所有股票数据"""
        all_stocks = self.data_manager.get_all_stocks()
        assert len(all_stocks) == 3
        
        stock_codes = [stock.code for stock in all_stocks]
        assert "300470" in stock_codes
        assert "000001" in stock_codes
        assert "002415" in stock_codes
    
    def test_get_scenario(self):
        """测试获取测试场景"""
        scenario = self.data_manager.get_scenario("basic_validation")
        assert scenario is not None
        assert scenario.name == "basic_validation"
        assert scenario.description == "基础验证场景 - 单个股票完整验证"
        assert len(scenario.stocks) == 1
        assert scenario.stocks[0].code == "300470"
        assert scenario.comparison_mode == ComparisonMode.STRICT
        
        # 测试不存在的场景
        nonexistent_scenario = self.data_manager.get_scenario("nonexistent")
        assert nonexistent_scenario is None
    
    def test_get_all_scenarios(self):
        """测试获取所有测试场景"""
        all_scenarios = self.data_manager.get_all_scenarios()
        assert len(all_scenarios) == 3
        
        scenario_names = [scenario.name for scenario in all_scenarios]
        assert "basic_validation" in scenario_names
        assert "multi_stock_validation" in scenario_names
        assert "content_only_validation" in scenario_names
    
    def test_simulate_download(self):
        """测试模拟下载"""
        stock_codes = ["300470", "000001"]
        downloaded_files = self.data_manager.simulate_download(stock_codes)
        
        assert len(downloaded_files) == 2
        assert "300470" in downloaded_files
        assert "000001" in downloaded_files
        
        # 验证每个股票下载的文件数量
        assert len(downloaded_files["300470"]) == 4
        assert len(downloaded_files["000001"]) == 4
        
        # 验证文件确实被创建
        for stock_code, files in downloaded_files.items():
            for file_path in files:
                assert Path(file_path).exists()
    
    def test_simulate_partial_download(self):
        """测试模拟部分下载"""
        downloaded_files = self.data_manager.simulate_partial_download("300470", 2)
        
        assert len(downloaded_files) == 2
        
        # 验证文件确实被创建
        for file_path in downloaded_files:
            assert Path(file_path).exists()
    
    def test_simulate_download_with_extra_files(self):
        """测试模拟下载包含额外文件"""
        extra_files = ["额外文件1.pdf", "额外文件2.pdf"]
        downloaded_files = self.data_manager.simulate_download_with_extra_files("300470", extra_files)
        
        # 应该下载4个期待文件 + 2个额外文件
        assert len(downloaded_files) == 6
        
        # 验证文件确实被创建
        for file_path in downloaded_files:
            assert Path(file_path).exists()
    
    def test_validate_scenario_success(self):
        """测试验证成功的测试场景"""
        # 先模拟下载数据
        self.data_manager.simulate_download(["300470"])
        
        # 执行验证
        result = self.data_manager.validate_scenario("basic_validation")
        
        # 验证结果
        assert result.overall_success is True
        assert result.total_files_compared > 0
        assert result.files_matched == result.total_files_compared
        assert result.files_mismatched == 0
        assert result.files_missing == 0
        assert result.files_extra == 0
        assert result.success_rate == 100.0
    
    def test_validate_scenario_nonexistent(self):
        """测试验证不存在的测试场景"""
        result = self.data_manager.validate_scenario("nonexistent_scenario")
        
        assert result.overall_success is False
        assert len(result.error_messages) > 0
        assert "测试场景不存在" in result.error_messages[0]
    
    def test_validate_single_stock_success(self):
        """测试验证单个股票成功"""
        # 先模拟下载数据
        self.data_manager.simulate_download(["300470"])
        
        # 执行验证
        result = self.data_manager.validate_single_stock("300470")
        
        # 验证结果
        assert result.overall_success is True
        assert result.total_files_compared > 0
        assert result.files_matched == result.total_files_compared
        assert result.success_rate == 100.0
    
    def test_validate_single_stock_nonexistent(self):
        """测试验证不存在的股票"""
        result = self.data_manager.validate_single_stock("999999")
        
        assert result.overall_success is False
        assert len(result.error_messages) > 0
        assert "股票不存在" in result.error_messages[0]
    
    def test_validate_single_stock_with_different_modes(self):
        """测试使用不同比较模式验证单个股票"""
        # 先模拟下载数据
        self.data_manager.simulate_download(["300470"])
        
        # 测试严格模式
        result_strict = self.data_manager.validate_single_stock("300470", ComparisonMode.STRICT)
        assert result_strict.overall_success is True
        
        # 测试宽松模式
        result_lenient = self.data_manager.validate_single_stock("300470", ComparisonMode.LENIENT)
        assert result_lenient.overall_success is True
        
        # 测试仅内容模式
        result_content = self.data_manager.validate_single_stock("300470", ComparisonMode.CONTENT_ONLY)
        assert result_content.overall_success is True
    
    def test_cleanup(self):
        """测试清理功能"""
        # 创建一些测试文件
        test_file = self.data_manager.base_test_dir / "test_file.txt"
        with open(test_file, 'w') as f:
            f.write("test content")
        
        assert test_file.exists()
        
        # 执行清理
        self.data_manager.cleanup()
        
        # 验证目录被清理
        assert not self.data_manager.base_test_dir.exists()
    
    def test_export_test_data(self):
        """测试导出测试数据"""
        export_dir = Path(self.temp_dir) / "export"
        
        # 执行导出
        export_path = self.data_manager.export_test_data(str(export_dir))
        
        # 验证导出目录存在
        assert Path(export_path).exists()
        
        # 验证配置文件存在
        config_file = Path(export_path) / "test_data_config.json"
        assert config_file.exists()
        
        # 验证期待数据目录存在
        expected_export_dir = Path(export_path) / "expected_data"
        assert expected_export_dir.exists()
        
        # 验证期待数据文件存在
        for stock_data in self.data_manager.test_stocks.values():
            stock_export_dir = expected_export_dir / stock_data.name
            assert stock_export_dir.exists()
            
            for expected_file in stock_data.expected_files:
                file_path = stock_export_dir / expected_file
                assert file_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])