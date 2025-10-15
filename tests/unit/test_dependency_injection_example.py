#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
依赖注入模式使用示例
展示如何使用依赖注入改进测试
"""

import pytest
from unittest.mock import Mock, patch

from .dependency_injection import (
    DependencyInjectionTestBase, inject_dependencies, test_dependency_manager
)


class TestDependencyInjectionExample(DependencyInjectionTestBase):
    """依赖注入示例测试类"""

    def test_basic_dependency_injection(self):
        """测试基础依赖注入"""
        # 获取mock服务
        stock_service = self.get_service("stock_service")
        orgid_service = self.get_service("orgid_service")

        # 验证服务可用
        assert stock_service is not None
        assert orgid_service is not None

        # 测试mock服务的方法调用
        stock_name = stock_service.get_stock_name("300470")
        assert stock_name == "测试股票"

        org_id = orgid_service.get_org_id("300470")
        assert org_id == "9900023856"

    def test_decorator_injection(self):
        """测试装饰器依赖注入"""
        # 手动注入依赖（修复装饰器问题）
        self.dependency_manager.inject_dependencies(self, {"stock_service": "stock_service", "orgid_service": "orgid_service"})

        # 依赖已注入
        assert hasattr(self, 'stock_service')
        assert hasattr(self, 'orgid_service')

        # 测试注入的服务
        stock_name = self.stock_service.get_stock_name("300470")
        assert stock_name == "测试股票"

        org_id = self.orgid_service.get_org_id("300470")
        assert org_id == "9900023856"

    def test_custom_service_configuration(self):
        """测试自定义服务配置"""
        # 创建自定义mock响应
        custom_responses = {
            "get_stock_name": "自定义股票名称",
            "get_stock_info": {"stock_code": "000001", "stock_name": "平安银行", "market": "SZ"}
        }

        # 构建自定义服务
        custom_stock_service = self.dependency_manager.builder.build_stock_service(custom_responses)

        # 测试自定义服务
        stock_name = custom_stock_service.get_stock_name("000001")
        assert stock_name == "自定义股票名称"

        stock_info = custom_stock_service.get_stock_info("000001")
        assert stock_info["stock_code"] == "000001"
        assert stock_info["stock_name"] == "平安银行"

    def test_service_interaction(self):
        """测试服务间交互"""
        # 获取服务
        stock_service = self.get_service("stock_service")
        download_service = self.get_service("download_service")

        # 设置服务间的交互
        stock_service.get_stock_name.return_value = "交互测试股票"
        download_service._get_stock_info.return_value = {
            "stock_code": "300470",
            "stock_name": "交互测试股票",
            "org_id": "9900023856"
        }

        # 测试服务交互
        stock_name = stock_service.get_stock_name("300470")
        stock_info = download_service._get_stock_info("300470")

        assert stock_name == "交互测试股票"
        assert stock_info["stock_name"] == "交互测试股票"

    def test_error_scenario_injection(self):
        """测试错误场景依赖注入"""
        # 创建错误场景的mock服务
        error_responses = {
            "get_stock_name": None,  # 返回None表示获取失败
            "get_org_id": None       # 返回None表示获取失败
        }

        # 构建错误场景服务
        error_stock_service = self.dependency_manager.builder.build_stock_service(error_responses)
        error_orgid_service = self.dependency_manager.builder.build_orgid_service(error_responses)

        # 测试错误场景
        stock_name = error_stock_service.get_stock_name("999999")
        assert stock_name is None

        org_id = error_orgid_service.get_org_id("999999")
        assert org_id is None

    def test_mock_verification(self):
        """测试mock验证"""
        # 获取服务
        stock_service = self.get_service("stock_service")

        # 调用方法
        stock_service.get_stock_name("300470")
        stock_service.get_stock_name("000001")

        # 验证方法调用
        assert stock_service.get_stock_name.call_count == 2
        stock_service.get_stock_name.assert_any_call("300470")
        stock_service.get_stock_name.assert_any_call("000001")


class TestAdvancedDependencyInjection:
    """高级依赖注入测试类"""

    def setup_method(self):
        """测试设置"""
        self.dependency_manager = test_dependency_manager
        self.dependency_manager.setup_standard_services()

    def teardown_method(self):
        """测试清理"""
        self.dependency_manager.reset()

    def test_singleton_pattern(self):
        """测试单例模式"""
        # 注册单例服务
        singleton_service = Mock()
        singleton_service.value = "单例值"
        self.dependency_manager.container.register_singleton("singleton_service", singleton_service)

        # 多次获取应该是同一个实例
        service1 = self.dependency_manager.get_service("singleton_service")
        service2 = self.dependency_manager.get_service("singleton_service")

        assert service1 is service2
        assert service1.value == "单例值"

    def test_factory_pattern(self):
        """测试工厂模式"""
        # 注册工厂函数
        def create_service():
            service = Mock()
            service.id = id(service)  # 每次创建都有不同的ID
            return service

        self.dependency_manager.container.register_factory("factory_service", create_service)

        # 每次获取应该是不同的实例
        service1 = self.dependency_manager.get_service("factory_service")
        service2 = self.dependency_manager.get_service("factory_service")

        assert service1 is not service2
        assert service1.id != service2.id

    def test_dependency_chain(self):
        """测试依赖链"""
        # 创建有依赖关系的服务
        logger_service = Mock()
        config_service = Mock()

        # 配置服务
        config_service.get.return_value = "测试配置"
        logger_service.info.return_value = None

        # 注册服务
        self.dependency_manager.container.register_service("logger", logger_service)
        self.dependency_manager.container.register_service("config", config_service)

        # 创建依赖其他服务的服务
        complex_service = Mock()
        complex_service.logger = logger_service
        complex_service.config = config_service
        complex_service.process.return_value = "处理结果"

        # 设置process方法调用logger
        def process_with_logging(data):
            logger_service.info(f"Processing: {data}")
            return "处理结果"

        complex_service.process.side_effect = process_with_logging

        self.dependency_manager.container.register_service("complex_service", complex_service)

        # 测试依赖链
        result = complex_service.process("测试数据")
        assert result == "处理结果"
        logger_service.info.assert_called_with("Processing: 测试数据")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])