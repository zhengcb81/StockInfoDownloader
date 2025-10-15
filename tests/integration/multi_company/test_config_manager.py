#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多公司配置管理器测试
测试配置管理器的多公司支持功能
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import ConfigManager


class TestConfigManagerMultiCompany:
    """测试配置管理器的多公司支持"""

    @pytest.fixture
    def temp_config_file(self):
        """创建临时配置文件"""
        config_data = {
            "environment": "test",
            "save_dir": "test_downloads",
            "companies": [
                {
                    "stock_code": "300470",
                    "company_name": "中密控股",
                    "enabled": True,
                    "priority": 1,
                    "custom_pages": None
                },
                {
                    "stock_code": "301611",
                    "company_name": "珂玛科技",
                    "enabled": True,
                    "priority": 2,
                    "custom_pages": [
                        {"name": "自定义页面", "suffix": "custom", "allowed_keywords": ["测试"]}
                    ]
                },
                {
                    "stock_code": "000001",
                    "company_name": "测试公司",
                    "enabled": False,
                    "priority": 3,
                    "custom_pages": None
                }
            ],
            "parallel_download": {
                "enabled": True,
                "max_workers": 5,
                "task_timeout": 300
            },
            "proxy_management": {
                "enabled": True,
                "pools": {
                    "test_pool": {
                        "enabled": True,
                        "max_size": 10
                    }
                }
            }
        }

        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        json.dump(config_data, temp_file, ensure_ascii=False, indent=2)
        temp_file.close()

        yield temp_file.name

        # 清理
        Path(temp_file.name).unlink(missing_ok=True)

    @pytest.fixture
    def config_manager(self, temp_config_file):
        """配置管理器fixture"""
        return ConfigManager(temp_config_file)

    def test_get_companies(self, config_manager):
        """测试获取公司列表"""
        companies = config_manager.get_companies()

        assert len(companies) == 2  # 只有启用的公司
        assert companies[0]['stock_code'] == '300470'  # 按优先级排序
        assert companies[1]['stock_code'] == '301611'
        assert companies[0]['company_name'] == '中密控股'
        assert companies[1]['company_name'] == '珂玛科技'

    def test_get_company_config(self, config_manager):
        """测试获取特定公司配置"""
        company = config_manager.get_company_config('301611')
        assert company is not None
        assert company['stock_code'] == '301611'
        assert company['company_name'] == '珂玛科技'
        assert company['custom_pages'] is not None
        assert len(company['custom_pages']) == 1

    def test_add_company(self, config_manager):
        """测试添加公司"""
        success = config_manager.add_company('000002', '新测试公司', priority=4)
        assert success

        companies = config_manager.get_companies()
        assert len(companies) == 3
        assert any(c['stock_code'] == '000002' for c in companies)

    def test_remove_company(self, config_manager):
        """测试移除公司"""
        success = config_manager.remove_company('300470')
        assert success

        companies = config_manager.get_companies()
        assert len(companies) == 1
        assert not any(c['stock_code'] == '300470' for c in companies)

    def test_enable_disable_company(self, config_manager):
        """测试启用/禁用公司"""
        # 禁用公司
        success = config_manager.disable_company('301611')
        assert success

        companies = config_manager.get_companies()
        assert len(companies) == 1  # 只有一个启用
        assert not any(c['stock_code'] == '301611' for c in companies)

        # 重新启用
        success = config_manager.enable_company('301611')
        assert success

        companies = config_manager.get_companies()
        assert len(companies) == 2

    def test_validate_companies_config(self, config_manager):
        """测试验证公司配置"""
        is_valid, errors = config_manager.validate_companies_config()
        assert is_valid
        assert len(errors) == 0

    def test_validate_invalid_config(self, config_manager):
        """测试验证无效配置"""
        # 添加无效配置
        config_manager.add_company('invalid', '无效公司')

        is_valid, errors = config_manager.validate_companies_config()
        assert not is_valid
        assert any('股票代码格式错误' in error for error in errors)

    def test_get_companies_summary(self, config_manager):
        """测试获取公司配置摘要"""
        summary = config_manager.get_companies_summary()

        assert summary['total_companies'] == 3  # 总公司数（包括禁用的）
        assert summary['enabled_companies'] == 2  # 启用公司数
        assert summary['disabled_companies'] == 1  # 禁用公司数
        assert '300470' in summary['stock_codes']
        assert '301611' in summary['stock_codes']
        assert summary['parallel_download_enabled'] is True
        assert summary['proxy_enabled'] is True
        assert summary['max_workers'] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])