#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集成测试 - 验证模块间集成
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.core.config import ConfigManager
from src.data.mapping import MappingManager
from src.data.models import StockInfo


class TestIntegration:
    """集成测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "test_config.json"
        self.mapping_path = Path(self.temp_dir.name) / "test_mapping.json"

        # 加载测试配置
        test_config_path = Path(__file__).parent / "test_config.json"
        with open(test_config_path, "r", encoding="utf-8") as f:
            self.test_config = json.load(f)

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

        # 使用配置文件中的测试数据
        test_mapping = self.test_config["test_mappings"][0]
        mapping.add_mapping(
            test_mapping["stock_code"],
            test_mapping["org_id"],
            test_mapping["stock_name"],
            source="test",
        )

        # 验证预设映射工作
        org_id = mapping.get_org_id(test_mapping["stock_code"])
        assert org_id == test_mapping["org_id"]

        # 使用配置文件中的验证测试用例
        validation_case = self.test_config["validation_test_cases"][0]
        assert (
            mapping.validate_org_id(validation_case["org_id"])
            == validation_case["expected"]
        )

        # 测试无效情况
        invalid_case = self.test_config["validation_test_cases"][2]
        assert (
            mapping.validate_org_id(invalid_case["org_id"]) == invalid_case["expected"]
        )

    def test_data_flow(self):
        """测试数据流完整性"""
        # 使用配置文件中的测试数据
        test_mapping = self.test_config["test_mappings"][0]

        # 1. 配置管理
        config = ConfigManager()
        config.set("stock_code", test_mapping["stock_code"])
        config.save_config(str(self.config_path))
        config.load_config(str(self.config_path))

        # 2. 映射管理
        mapping = MappingManager(str(self.mapping_path))
        mapping.add_mapping(
            test_mapping["stock_code"],
            test_mapping["org_id"],
            test_mapping["stock_name"],
        )

        # 3. 数据模型
        stock_info = StockInfo(
            stock_code=test_mapping["stock_code"],
            stock_name=test_mapping["stock_name"],
            org_id=test_mapping["org_id"],
        )

        # 4. 验证数据一致性
        assert stock_info.stock_code == test_mapping["stock_code"]
        assert stock_info.stock_name == test_mapping["stock_name"]
        assert stock_info.org_id == test_mapping["org_id"]
        assert stock_info.is_valid

    def test_mapping_statistics(self):
        """测试映射统计功能"""
        mapping = MappingManager(str(self.mapping_path))

        # 使用配置文件中的测试数据添加多个映射
        test_mappings = self.test_config["test_mappings"][:3]  # 取前3个
        sources = ["preset", "auto", "manual"]

        for i, test_mapping in enumerate(test_mappings):
            mapping.add_mapping(
                test_mapping["stock_code"],
                test_mapping["org_id"],
                test_mapping["stock_name"],
                source=sources[i],
            )

        # 获取统计信息
        stats = mapping.get_statistics()

        assert stats["total"] == 3
        # Source distribution is nested in source_distribution dict
        source_dist = stats.get("source_distribution", {})
        assert source_dist.get("preset", 0) == 1
        assert source_dist.get("auto", 0) == 1
        assert source_dist.get("manual", 0) == 1

    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效的股票代码
        config = ConfigManager()
        config.set("stock_code", "invalid")

        # 验证验证逻辑 - 使用配置文件中的测试数据
        test_mapping = self.test_config["test_mappings"][0]
        stock_info = StockInfo(
            stock_code=test_mapping["stock_code"], stock_name=test_mapping["stock_name"]
        )
        assert stock_info.is_valid

        # 测试无效映射 - 使用配置文件中的验证测试用例
        mapping = MappingManager(str(self.mapping_path))

        # 使用配置文件中的无效测试用例
        invalid_cases = [
            case
            for case in self.test_config["validation_test_cases"]
            if not case["expected"]
        ]
        for case in invalid_cases:
            assert not mapping.validate_org_id(case["org_id"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
