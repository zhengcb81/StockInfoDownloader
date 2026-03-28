#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
组织ID映射单元测试
测试MappingManager类的功能
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.mapping import MappingManager


class TestMappingManager:
    """组织ID映射管理器测试类"""

    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.mapping_file = os.path.join(self.temp_dir, "test_mapping.json")

        # 创建测试数据
        self.test_data = {
            "300470": {"orgId": "9900023856", "name": "中密控股"},
            "301611": {"orgId": "9900041611", "name": "珂玛科技"},
            "000001": {"orgId": "9900000001", "name": "平安银行"},
        }

        # 写入测试文件
        with open(self.mapping_file, "w", encoding="utf-8") as f:
            json.dump(self.test_data, f, ensure_ascii=False, indent=2)

    def teardown_method(self):
        """测试清理"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_with_valid_file(self):
        """测试使用有效文件初始化"""
        manager = MappingManager(self.mapping_file)
        assert str(manager.mapping_file) == self.mapping_file
        # 检查映射是否正确加载
        assert len(manager._mappings) == len(self.test_data)

    def test_init_with_invalid_file(self):
        """测试使用无效文件初始化"""
        invalid_file = os.path.join(self.temp_dir, "nonexistent.json")
        manager = MappingManager(invalid_file)
        assert str(manager.mapping_file) == invalid_file
        assert manager.mapping_data == {}

    def test_get_org_id_success(self):
        """测试成功获取组织ID"""
        manager = MappingManager(self.mapping_file)

        # 测试存在的股票代码
        org_id = manager.get_org_id("300470")
        assert org_id == "9900023856"

        org_id = manager.get_org_id("301611")
        assert org_id == "9900041611"

    def test_get_org_id_not_found(self):
        """测试获取不存在的股票代码"""
        manager = MappingManager(self.mapping_file)

        # 测试不存在的股票代码
        org_id = manager.get_org_id("999999")
        assert org_id is None

    def test_get_org_id_empty_mapping(self):
        """测试空映射不从网络获取（禁用auto_fetch）"""
        empty_file = os.path.join(self.temp_dir, "empty.json")
        with open(empty_file, "w", encoding="utf-8") as f:
            json.dump({}, f)

        # 禁用自动获取
        manager = MappingManager(empty_file, auto_fetch=False)
        # 空映射且禁用auto_fetch时返回None
        org_id = manager.get_org_id("300470")
        assert org_id is None

    @pytest.mark.network
    def test_get_org_id_empty_mapping_with_network(self):
        """测试空映射时从网络获取（需要网络）"""
        empty_file = os.path.join(self.temp_dir, "empty.json")
        with open(empty_file, "w", encoding="utf-8") as f:
            json.dump({}, f)

        # 启用自动获取
        manager = MappingManager(empty_file, auto_fetch=True)
        org_id = manager.get_org_id("300470")
        assert org_id == "9900023856"

    def test_get_stock_name_success(self):
        """测试成功获取股票名称"""
        manager = MappingManager(self.mapping_file)

        # 测试存在的股票代码
        name = manager.get_stock_name("300470")
        assert name == "中密控股"

        name = manager.get_stock_name("301611")
        assert name == "珂玛科技"

    def test_get_stock_name_not_found(self):
        """测试获取不存在的股票名称"""
        manager = MappingManager(self.mapping_file)

        # 测试不存在的股票代码
        name = manager.get_stock_name("999999")
        assert name is None

    def test_get_all_stock_codes(self):
        """测试获取所有股票代码"""
        manager = MappingManager(self.mapping_file)

        stock_codes = manager.get_all_stock_codes()
        expected_codes = {"300470", "301611", "000001"}
        assert set(stock_codes) == expected_codes

    def test_add_mapping(self):
        """测试添加映射"""
        manager = MappingManager(self.mapping_file)

        # 添加新映射
        success = manager.add_mapping("600519", "9900010519", "贵州茅台")
        assert success

        # 验证添加成功
        org_id = manager.get_org_id("600519")
        assert org_id == "9900010519"

        name = manager.get_stock_name("600519")
        assert name == "贵州茅台"

    def test_add_duplicate_mapping(self):
        """测试添加重复映射"""
        manager = MappingManager(self.mapping_file)

        # 尝试添加已存在的映射
        success = manager.add_mapping("300470", "9999999999", "测试公司")
        assert not success  # 应该失败

        # 原映射应该保持不变
        org_id = manager.get_org_id("300470")
        assert org_id == "9900023856"

    def test_remove_mapping(self):
        """测试删除映射（禁用auto_fetch）"""
        # 禁用自动获取
        manager = MappingManager(self.mapping_file, auto_fetch=False)

        # 删除存在的映射
        success = manager.remove_mapping("300470")
        assert success

        # 删除后返回None（不从网络获取）
        org_id = manager.get_org_id("300470")
        assert org_id is None

        name = manager.get_stock_name("300470")
        assert name is None

    @pytest.mark.network
    def test_remove_mapping_with_network(self):
        """测试删除映射后可从网络重新获取（需要网络）"""
        manager = MappingManager(self.mapping_file, auto_fetch=True)

        # 删除存在的映射
        success = manager.remove_mapping("300470")
        assert success

        # 删除后会从网络重新获取
        org_id = manager.get_org_id("300470")
        assert org_id == "9900023856"

        name = manager.get_stock_name("300470")
        assert name == "中密控股"

    def test_remove_nonexistent_mapping(self):
        """测试删除不存在的映射"""
        manager = MappingManager(self.mapping_file)

        # 尝试删除不存在的映射
        success = manager.remove_mapping("999999")
        assert not success

    @patch("src.data.mapping.JsonStorage")
    def test_reload_mapping(self, mock_storage):
        """测试重新加载映射"""
        mock_instance = mock_storage.return_value
        mock_instance.load.return_value = self.test_data

        manager = MappingManager(self.mapping_file)

        # 模拟文件内容改变
        new_data = self.test_data.copy()
        new_data["600000"] = {"orgId": "new_org", "name": "New Name"}
        mock_instance.load.return_value = new_data

        assert manager.reload_mapping() is True
        assert "600000" in manager.get_all_stock_codes()

    def test_reload_invalid_file(self):
        """测试重新加载无效文件"""
        manager = MappingManager(self.mapping_file)

        # 破坏文件
        with open(self.mapping_file, "w", encoding="utf-8") as f:
            f.write("invalid json content")

        # 尝试重新加载
        success = manager.reload_mapping()
        assert not success

        # 原数据应该保持不变
        org_id = manager.get_org_id("300470")
        assert org_id == "9900023856"

    def test_mapping_file_not_writable(self):
        """测试映射文件不可写的情况"""
        # 创建只读文件
        readonly_file = os.path.join(self.temp_dir, "readonly.json")
        with open(readonly_file, "w", encoding="utf-8") as f:
            json.dump(self.test_data, f, ensure_ascii=False, indent=2)

        # 设置为只读
        os.chmod(readonly_file, 0o444)

        try:
            manager = MappingManager(readonly_file)

            # 尝试添加映射应该失败
            success = manager.add_mapping("600519", "9900010519", "贵州茅台")
            assert not success
        finally:
            # 恢复权限以便清理
            os.chmod(readonly_file, 0o666)

    def test_get_org_info(self):
        """测试获取完整组织信息"""
        manager = MappingManager(self.mapping_file)

        # 测试存在的股票代码
        info = manager.get_org_info("300470")
        assert info is not None
        assert info["org_id"] == "9900023856"
        assert info["stock_name"] == "中密控股"
        assert "source" in info
        assert "confidence" in info
        assert "last_updated" in info

        # 测试不存在的股票代码
        info = manager.get_org_info("999999")
        assert info is None

    def test_mapping_data_validation(self):
        """测试映射数据验证"""
        manager = MappingManager(self.mapping_file)

        # 测试有效数据
        valid_data = {"600519": {"org_id": "9900010519", "name": "贵州茅台"}}
        assert manager._validate_mapping_data(valid_data)

        # 测试无效数据 - 缺少org_id
        invalid_data1 = {"600519": {"name": "贵州茅台"}}
        assert not manager._validate_mapping_data(invalid_data1)

        # 测试无效数据 - 缺少name
        invalid_data2 = {"600519": {"org_id": "9900010519"}}
        assert not manager._validate_mapping_data(invalid_data2)

        # 测试无效数据 - org_id格式错误
        invalid_data3 = {"600519": {"org_id": "invalid", "name": "贵州茅台"}}
        assert not manager._validate_mapping_data(invalid_data3)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
