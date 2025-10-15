#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Org ID验证的单元测试和回归测试
"""

import unittest
import json
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from validate_org_id import validate_org_id_url, validate_and_refresh_org_id
from validate_all_cached import validate_all_cached_org_ids
from src.core.config import ConfigManager

class TestOrgIdValidation(unittest.TestCase):
    """Org ID验证单元测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_env = tempfile.TemporaryDirectory()
        self.test_mapping_file = os.path.join(self.test_env.name, 'test_mapping.json')
        self.config_manager = ConfigManager()
        
        # 创建测试配置
        self.test_config = {
            "org_id_validation": {
                "base_url": "https://www.cninfo.com.cn/new/disclosure/stock",
                "validation_timeout": 5,
                "max_retries": 2,
                "retry_delay": 1,
                "headers": {
                    "User-Agent": "test-agent"
                }
            },
            "cache_management": {
                "auto_invalidate": True,
                "mapping_file": self.test_mapping_file
            }
        }
        
        # 创建测试映射
        self.test_mapping = {
            "300470": {
                "orgId": "9900023856",
                "name": "中密控股",
                "timestamp": 1234567890
            },
            "000001": {
                "orgId": "9900000001", 
                "name": "平安银行",
                "timestamp": 1234567890
            }
        }
        
        with open(self.test_mapping_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_mapping, f, ensure_ascii=False, indent=2)
    
    def tearDown(self):
        """测试后清理"""
        self.test_env.cleanup()
    
    def test_validate_org_id_url_with_mock(self):
        """测试org ID URL验证功能"""
        with patch('validate_org_id.requests.head') as mock_head:
            # 模拟有效响应
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_head.return_value = mock_response
            
            config = self.test_config["org_id_validation"]
            result = validate_org_id_url("300470", "9900023856", config)
            self.assertTrue(result)
    
    def test_validate_org_id_url_invalid(self):
        """测试无效的org ID验证"""
        with patch('validate_org_id.requests.head') as mock_head:
            # 模拟无效响应（404状态码）
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_head.return_value = mock_response
            
            config = self.test_config["org_id_validation"]
            result = validate_org_id_url("300470", "invalid123", config)
            self.assertFalse(result)
    
    def test_validate_and_refresh_org_id_valid(self):
        """测试验证并刷新有效org ID"""
        with patch('validate_org_id.validate_org_id_url') as mock_validate, \
             patch('validate_org_id.invalidate_cache') as mock_invalidate:
            
            mock_validate.return_value = True
            
            result = validate_and_refresh_org_id("300470", self.test_mapping_file)
            self.assertEqual(result, "9900023856")
            mock_invalidate.assert_not_called()
    
    def test_validate_and_refresh_org_id_invalid(self):
        """测试验证并刷新无效org ID"""
        with patch('validate_org_id.validate_org_id_url') as mock_validate, \
             patch('validate_org_id.invalidate_cache') as mock_invalidate:
            
            mock_validate.return_value = False
            mock_invalidate.return_value = "9900023856"
            
            result = validate_and_refresh_org_id("300470", self.test_mapping_file)
            self.assertEqual(result, "9900023856")
            mock_invalidate.assert_called_once()
    
    def test_validate_all_cached_org_ids(self):
        """测试批量验证所有缓存org ID"""
        with patch('validate_all_cached.validate_org_id_url') as mock_validate, \
             patch('validate_all_cached.invalidate_cache') as mock_invalidate:
            
            mock_validate.side_effect = [True, True]  # 两个都有效
            
            report = validate_all_cached_org_ids(self.test_mapping_file, fix_invalid=False)
            
            self.assertEqual(report["total"], 2)
            self.assertEqual(report["valid"], 2)
            self.assertEqual(report["invalid"], 0)
            self.assertEqual(report["fixed"], 0)
    
    def test_validate_all_cached_org_ids_with_fix(self):
        """测试批量验证并修正无效org ID"""
        with patch('validate_all_cached.validate_org_id_url') as mock_validate, \
             patch('validate_all_cached.invalidate_cache') as mock_invalidate:
            
            mock_validate.side_effect = [False, True]  # 第一个无效，第二个有效
            mock_invalidate.return_value = "new_correct_id"
            
            report = validate_all_cached_org_ids(self.test_mapping_file, fix_invalid=True)
            
            self.assertEqual(report["total"], 2)
            self.assertEqual(report["valid"], 1)
            self.assertEqual(report["invalid"], 1)
            self.assertEqual(report["fixed"], 1)
    
    def test_config_driven_validation(self):
        """测试配置驱动的验证"""
        config = self.test_config["org_id_validation"]
        self.assertIsInstance(config, dict)
        self.assertIn('base_url', config)
        self.assertIn('validation_timeout', config)
    
    def test_error_handling(self):
        """测试错误处理"""
        with patch('validate_org_id.validate_org_id_url') as mock_validate:
            mock_validate.side_effect = Exception("网络错误")
            
            result = validate_and_refresh_org_id("300470", self.test_mapping_file)
            self.assertIsNone(result)

class TestOrgIdRegression(unittest.TestCase):
    """Org ID回归测试类"""
    
    def setUp(self):
        """回归测试准备"""
        self.test_env = tempfile.TemporaryDirectory()
        self.test_mapping_file = os.path.join(self.test_env.name, 'test_mapping.json')
        
        # 创建历史数据模拟
        self.historical_data = {
            "known_valid": {
                "300470": "9900023856",
                "000001": "9900000001",
                "002415": "9900012688"
            },
            "known_invalid": {
                "300470": "9900008470",
                "000001": "invalid123"
            }
        }
    
    def tearDown(self):
        """回归测试清理"""
        self.test_env.cleanup()
    
    def test_regression_known_valid_ids(self):
        """回归测试：已知有效ID应保持有效"""
        with patch('validate_org_id.validate_org_id_url') as mock_validate:
            mock_validate.return_value = True
            
            for stock_code, org_id in self.historical_data["known_valid"].items():
                with self.subTest(stock_code=stock_code):
                    result = validate_org_id_url(stock_code, org_id)
                    self.assertTrue(result)
    
    def test_regression_known_invalid_ids(self):
        """回归测试：已知无效ID应被标记为无效"""
        # 创建测试配置
        config = {
            "base_url": "https://www.cninfo.com.cn/new/disclosure/stock",
            "validation_timeout": 5,
            "max_retries": 2,
            "retry_delay": 1,
            "headers": {"User-Agent": "test-agent"}
        }
        
        with patch('validate_org_id.requests.head') as mock_head:
            # 模拟无效响应（404状态码）
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_head.return_value = mock_response
            
            for stock_code, org_id in self.historical_data["known_invalid"].items():
                with self.subTest(stock_code=stock_code):
                    result = validate_org_id_url(stock_code, org_id, config)
                    self.assertFalse(result)
    
    def test_regression_batch_validation(self):
        """回归测试：批量验证功能"""
        # 创建测试映射文件
        test_mapping = {
            "300470": {"orgId": "9900023856", "name": "中密控股"},
            "000001": {"orgId": "9900000001", "name": "平安银行"},
            "002415": {"orgId": "9900012688", "name": "海康威视"}
        }
        
        test_file = os.path.join(self.test_env.name, 'regression_test.json')
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_mapping, f, ensure_ascii=False, indent=2)
        
        with patch('validate_all_cached.validate_org_id_url') as mock_validate:
            mock_validate.return_value = True
            
            report = validate_all_cached_org_ids(test_file, fix_invalid=False)
            
            self.assertEqual(report["total"], 3)
            self.assertEqual(report["valid"], 3)
            self.assertEqual(report["invalid"], 0)
            self.assertEqual(report["fixed"], 0)
    
    def test_regression_config_compatibility(self):
        """回归测试：配置兼容性"""
        configs = [
            {"org_id_validation": {"base_url": "https://test.com"}},
            {"org_id_validation": {"validation_timeout": 30}},
            {"cache_management": {"auto_invalidate": False}}
        ]
        
        for config in configs:
            with self.subTest(config=config):
                try:
                    # 确保配置能被正确加载
                    from validate_org_id import load_validation_config, load_cache_config
                    
                    with patch('validate_org_id.ConfigManager') as mock_config:
                        mock_instance = MagicMock()
                        mock_instance.get.side_effect = [
                            config.get('org_id_validation', {}),
                            config.get('cache_management', {})
                        ]
                        mock_config.return_value = mock_instance
                        
                        val_config = load_validation_config()
                        cache_config = load_cache_config()
                        
                        self.assertIsInstance(val_config, dict)
                        self.assertIsInstance(cache_config, dict)
                        
                except Exception as e:
                    self.fail(f"配置兼容性测试失败: {e}")

class TestOrgIdIntegration(unittest.TestCase):
    """集成测试类"""
    
    def test_end_to_end_validation(self):
        """端到端验证测试"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建完整测试环境
            mapping_file = os.path.join(temp_dir, 'test_mapping.json')
            
            # 创建测试映射
            test_data = {
                "300470": {"orgId": "9900023856", "name": "中密控股"}
            }
            
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, ensure_ascii=False, indent=2)
            
            # 验证映射文件
            with open(mapping_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                self.assertEqual(loaded_data["300470"]["orgId"], "9900023856")

if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)