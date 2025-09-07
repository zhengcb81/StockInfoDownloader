#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
orgid_utils 模块单元测试
"""

import unittest
import tempfile
import json
import os
import sys
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orgid_utils import get_org_id_by_code, _load_mapping, _save_to_mapping
from tests.test_config import TestEnvironment, TEST_ORG_IDS, create_test_mapping

def is_valid_stock_code(code):
    """验证股票代码是否有效"""
    if not code or not isinstance(code, str):
        return False
    return len(code) == 6 and code.isdigit()

def load_mapping(file_path):
    """公共接口：加载映射文件"""
    return _load_mapping(file_path)

def save_mapping(mapping, file_path):
    """公共接口：保存映射文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

class TestOrgidUtils(unittest.TestCase):
    """orgid_utils 模块测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_env = TestEnvironment()
        self.test_mapping = create_test_mapping()
        
        # 创建测试映射文件
        self.mapping_file = self.test_env.create_temp_file(
            suffix=".json",
            content=json.dumps({
                code: {"orgId": org_id, "name": f"测试股票{code}"}
                for code, org_id in TEST_ORG_IDS.items()
            }, ensure_ascii=False, indent=2)
        )
    
    def tearDown(self):
        """测试后清理"""
        self.test_env.cleanup()
    
    def test_is_valid_stock_code(self):
        """测试股票代码验证函数"""
        # 测试有效的股票代码
        valid_codes = ["000001", "000002", "002415", "600036", "600519"]
        for code in valid_codes:
            with self.subTest(code=code):
                self.assertTrue(is_valid_stock_code(code), f"股票代码 {code} 应该是有效的")
        
        # 测试无效的股票代码
        invalid_codes = ["", "123", "0000001", "abc123", "12345", None]
        for code in invalid_codes:
            with self.subTest(code=code):
                self.assertFalse(is_valid_stock_code(code), f"股票代码 {code} 应该是无效的")
    
    def test_load_mapping_success(self):
        """测试成功加载映射文件"""
        mapping = load_mapping(self.mapping_file)
        self.assertIsInstance(mapping, dict)
        self.assertEqual(len(mapping), len(TEST_ORG_IDS))
        
        for code in TEST_ORG_IDS:
            self.assertIn(code, mapping)
            self.assertIn("orgId", mapping[code])
    
    def test_load_mapping_file_not_found(self):
        """测试加载不存在的映射文件"""
        non_existent_file = "non_existent_file.json"
        mapping = load_mapping(non_existent_file)
        self.assertEqual(mapping, {})
    
    def test_load_mapping_invalid_json(self):
        """测试加载无效JSON文件"""
        invalid_json_file = self.test_env.create_temp_file(
            suffix=".json",
            content="invalid json content"
        )
        mapping = load_mapping(invalid_json_file)
        self.assertEqual(mapping, {})
    
    def test_save_mapping_success(self):
        """测试成功保存映射文件"""
        temp_file = self.test_env.create_temp_file(suffix=".json")
        test_data = {"test_code": {"orgId": "test_org_id"}}
        
        result = save_mapping(test_data, temp_file)
        self.assertTrue(result)
        
        # 验证文件内容
        with open(temp_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, test_data)
    
    def test_save_mapping_permission_error(self):
        """测试保存映射文件权限错误"""
        # 使用不存在的目录路径
        invalid_path = "/invalid/path/mapping.json"
        test_data = {"test": "data"}
        
        result = save_mapping(test_data, invalid_path)
        self.assertFalse(result)
    
    def test_get_org_id_by_code_from_mapping(self):
        """测试从映射文件获取组织ID"""
        for code, expected_org_id in TEST_ORG_IDS.items():
            with self.subTest(code=code):
                org_id = get_org_id_by_code(code, mapping_file=self.mapping_file)
                self.assertEqual(org_id, expected_org_id)
    
    def test_get_org_id_by_code_invalid_code(self):
        """测试获取无效股票代码的组织ID"""
        invalid_codes = ["", "invalid", "123456"]
        for code in invalid_codes:
            with self.subTest(code=code):
                org_id = get_org_id_by_code(code, mapping_file=self.mapping_file)
                self.assertIsNone(org_id)
    
    def test_get_org_id_by_code_not_in_mapping(self):
        """测试获取映射中不存在的股票代码的组织ID"""
        code = "999999"  # 不存在的股票代码
        org_id = get_org_id_by_code(code, mapping_file=self.mapping_file)
        self.assertIsNone(org_id)
    
    @patch('orgid_utils._crawl_org_id')
    def test_get_org_id_by_code_force_run(self, mock_crawl):
        """测试强制重新爬取组织ID"""
        mock_crawl.return_value = "new_org_id"
        
        code = "000001"
        org_id = get_org_id_by_code(code, force_run=True, mapping_file=self.mapping_file)
        
        # 验证调用了爬虫
        mock_crawl.assert_called_once()
        self.assertEqual(org_id, "new_org_id")
    
    @patch('orgid_utils._crawl_org_id')
    def test_get_org_id_by_code_crawler_failure(self, mock_crawl):
        """测试爬虫获取组织ID失败"""
        mock_crawl.return_value = None
        
        code = "999999"  # 不存在的股票代码
        org_id = get_org_id_by_code(code, force_run=True, mapping_file=self.mapping_file)
        
        mock_crawl.assert_called_once()
        self.assertIsNone(org_id)

class TestOrgidUtilsIntegration(unittest.TestCase):
    """orgid_utils 模块集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_env = TestEnvironment()
    
    def tearDown(self):
        """测试后清理"""
        self.test_env.cleanup()
    
    def test_mapping_file_lifecycle(self):
        """测试映射文件的完整生命周期"""
        mapping_file = self.test_env.create_temp_file(suffix=".json")
        
        # 1. 初始状态：空映射
        mapping = load_mapping(mapping_file)
        self.assertEqual(mapping, {})
        
        # 2. 添加数据并保存
        test_data = create_test_mapping()
        result = save_mapping(test_data, mapping_file)
        self.assertTrue(result)
        
        # 3. 重新加载验证
        loaded_mapping = load_mapping(mapping_file)
        self.assertEqual(loaded_mapping, test_data)
        
        # 4. 获取组织ID
        for code, expected_data in test_data.items():
            org_id = get_org_id_by_code(code, mapping_file=mapping_file)
            self.assertEqual(org_id, expected_data["org_id"])

if __name__ == "__main__":
    unittest.main() 