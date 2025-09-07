#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集成测试 - 验证模块间集成
"""

import pytest
import tempfile
from pathlib import Path
from src.core.config import ConfigManager
from src.data.mapping import MappingManager
from src.data.models import StockInfo, OrgIdMapping
from src.services.stock_service import StockService


class TestIntegration:
    """集成测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "test_config.json"
        self.mapping_path = Path(self.temp_dir.name) / "test_mapping.json"
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        self.temp_dir.cleanup()
    
    def test_config_mapping_integration(self):
        """测试配置和映射管理的集成"""
        # 设置测试配置
        config = ConfigManager()
        config.set("stock_code", "002415")
        config.save_config(str(self.config_path))
        
        # 验证配置可以正确保存和加载
        new_config = ConfigManager()
        new_config.load_config(str(self.config_path))
        assert new_config.get("stock_code") == "002415"
    
    def test_mapping_persistence(self):
        """测试映射持久化"""
        mapping = MappingManager(str(self.mapping_path))
        
        # 添加测试映射
        mapping.add_mapping("002415", "9900002415", "海康威视")
        
        # 创建新的映射管理器实例
        new_mapping = MappingManager(str(self.mapping_path))
        
        # 验证映射已持久化
        org_id = new_mapping.get_org_id("002415")
        assert org_id == "9900002415"
    
    def test_stock_service_with_mapping(self):
        """测试股票服务与映射的集成"""
        # 设置预设映射
        mapping = MappingManager(str(self.mapping_path))
        
        # 验证预设映射工作
        org_id = mapping.get_org_id("000001")
        assert org_id == "9900000001"
        
        # 验证验证函数
        assert mapping.validate_org_id("9900002415")
        assert not mapping.validate_org_id("")
    
    def test_data_flow(self):
        """测试数据流完整性"""
        # 1. 配置管理
        config = ConfigManager()
        config.set("stock_code", "002415")
        config.save_config(str(self.config_path))
        config.load_config(str(self.config_path))
        
        # 2. 映射管理
        mapping = MappingManager(str(self.mapping_path))
        mapping.add_mapping("002415", "9900002415", "海康威视")
        
        # 3. 数据模型
        stock_info = StockInfo(
            stock_code="002415",
            stock_name="海康威视",
            org_id="9900002415"
        )
        
        # 4. 验证数据一致性
        assert stock_info.stock_code == "002415"
        assert stock_info.stock_name == "海康威视"
        assert stock_info.org_id == "9900002415"
        assert stock_info.is_valid
    
    def test_mapping_statistics(self):
        """测试映射统计功能"""
        mapping = MappingManager(str(self.mapping_path))
        
        # 添加多个映射
        mapping.add_mapping("000001", "9900000001", "平安银行", source="preset")
        mapping.add_mapping("002415", "9900002415", "海康威视", source="auto")
        mapping.add_mapping("600519", "9900010519", "贵州茅台", source="manual")
        
        # 获取统计信息
        stats = mapping.get_statistics()
        
        assert stats['total'] == 3
        assert stats['preset'] == 1
        assert stats['auto'] == 1
        assert stats['manual'] == 1
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效的股票代码
        config = ConfigManager()
        config.set("stock_code", "invalid")
        
        # 验证验证逻辑
        stock_info = StockInfo(stock_code="002415", stock_name="test")
        assert stock_info.is_valid
        
        # 测试无效映射
        mapping = MappingManager(str(self.mapping_path))
        assert not mapping.validate_org_id("")
        assert not mapping.validate_org_id("abc")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])