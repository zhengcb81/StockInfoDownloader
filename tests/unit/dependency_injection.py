#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试依赖注入容器
提供依赖注入模式，提高测试的可测试性和可维护性
"""

from typing import Any, Callable, Dict, Optional, Type
from unittest.mock import Mock


class DependencyContainer:
    """依赖注入容器"""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}

    def register_service(self, name: str, service: Any) -> None:
        """注册服务实例"""
        self._services[name] = service

    def register_factory(self, name: str, factory: Callable) -> None:
        """注册工厂函数"""
        self._factories[name] = factory

    def register_singleton(self, name: str, singleton: Any) -> None:
        """注册单例实例"""
        self._singletons[name] = singleton

    def get(self, name: str) -> Any:
        """获取依赖实例"""
        # 优先检查单例
        if name in self._singletons:
            return self._singletons[name]

        # 检查服务实例
        if name in self._services:
            return self._services[name]

        # 检查工厂函数
        if name in self._factories:
            return self._factories[name]()

        raise KeyError(f"依赖 '{name}' 未注册")

    def create_mock_service(self, name: str, **kwargs) -> Mock:
        """创建mock服务"""
        mock_service = Mock(**kwargs)
        self.register_service(name, mock_service)
        return mock_service

    def clear(self) -> None:
        """清空容器"""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()


class TestServiceBuilder:
    """测试服务构建器"""

    def __init__(self, container: DependencyContainer):
        self.container = container

    def build_stock_service(
        self, mock_responses: Optional[Dict[str, Any]] = None
    ) -> Mock:
        """构建StockService mock"""
        mock_stock_service = Mock()

        # 设置默认mock响应
        if mock_responses is None:
            mock_responses = {
                "get_stock_name": "测试股票",
                "get_stock_info": {
                    "stock_code": "300470",
                    "stock_name": "测试股票",
                    "market": "SZ",
                },
                "validate_stock_code": True,
            }

        # 配置mock方法
        for method_name, return_value in mock_responses.items():
            if hasattr(mock_stock_service, method_name):
                getattr(mock_stock_service, method_name).return_value = return_value

        self.container.register_service("stock_service", mock_stock_service)
        return mock_stock_service

    def build_orgid_service(
        self, mock_responses: Optional[Dict[str, Any]] = None
    ) -> Mock:
        """构建OrgIdService mock"""
        mock_orgid_service = Mock()

        # 设置默认mock响应
        if mock_responses is None:
            mock_responses = {
                "get_org_id": "9900023856",
                "_extract_org_id_from_url": "9900023856",
                "_extract_org_id_from_page": "9900023856",
            }

        # 配置mock方法
        for method_name, return_value in mock_responses.items():
            if hasattr(mock_orgid_service, method_name):
                getattr(mock_orgid_service, method_name).return_value = return_value

        self.container.register_service("orgid_service", mock_orgid_service)
        return mock_orgid_service

    def build_download_service(
        self, mock_responses: Optional[Dict[str, Any]] = None
    ) -> Mock:
        """构建DownloadService mock"""
        mock_download_service = Mock()

        # 设置默认mock响应
        if mock_responses is None:
            mock_responses = {
                "download_stock_info": True,
                "_get_stock_info": {"stock_code": "300470", "org_id": "9900023856"},
                "_matches_keywords": True,
            }

        # 配置mock方法
        for method_name, return_value in mock_responses.items():
            if hasattr(mock_download_service, method_name):
                getattr(mock_download_service, method_name).return_value = return_value

        self.container.register_service("download_service", mock_download_service)
        return mock_download_service

    def build_file_service(
        self, mock_responses: Optional[Dict[str, Any]] = None
    ) -> Mock:
        """构建FileService mock"""
        mock_file_service = Mock()

        # 设置默认mock响应
        if mock_responses is None:
            mock_responses = {
                "save_file": True,
                "read_file": "测试文件内容",
                "file_exists": True,
            }

        # 配置mock方法
        for method_name, return_value in mock_responses.items():
            if hasattr(mock_file_service, method_name):
                getattr(mock_file_service, method_name).return_value = return_value

        self.container.register_service("file_service", mock_file_service)
        return mock_file_service


class TestDependencyManager:
    """测试依赖管理器"""

    def __init__(self):
        self.container = DependencyContainer()
        self.builder = TestServiceBuilder(self.container)

    def setup_standard_services(self) -> None:
        """设置标准测试服务"""
        # 构建标准mock服务
        self.builder.build_stock_service()
        self.builder.build_orgid_service()
        self.builder.build_download_service()
        self.builder.build_file_service()

        # 注册其他常用服务
        self.container.register_service("logger", Mock())
        self.container.register_service("config", Mock())

    def get_service(self, name: str) -> Any:
        """获取服务实例"""
        return self.container.get(name)

    def inject_dependencies(self, target: Any, dependencies: Dict[str, str]) -> None:
        """注入依赖到目标对象"""
        for attr_name, service_name in dependencies.items():
            service = self.container.get(service_name)
            setattr(target, attr_name, service)

    def create_test_instance(
        self, class_type: Type, dependencies: Dict[str, str], **kwargs
    ) -> Any:
        """创建测试实例并注入依赖"""
        # 创建实例
        instance = class_type(**kwargs)

        # 注入依赖
        self.inject_dependencies(instance, dependencies)

        return instance

    def reset(self) -> None:
        """重置依赖管理器"""
        self.container.clear()


# 全局依赖管理器实例
test_dependency_manager = TestDependencyManager()


# 依赖注入装饰器
def inject_dependencies(dependencies: Dict[str, str]):
    """依赖注入装饰器"""

    def decorator(test_method):
        def wrapper(self, *args, **kwargs):
            # 注入依赖到测试实例
            test_dependency_manager.inject_dependencies(self, dependencies)
            return test_method(self, *args, **kwargs)

        return wrapper

    return decorator


# 测试基类，支持依赖注入
class DependencyInjectionTestBase:
    """依赖注入测试基类"""

    def setup_method(self):
        """测试设置"""
        self.dependency_manager = TestDependencyManager()
        self.dependency_manager.setup_standard_services()

    def teardown_method(self):
        """测试清理"""
        self.dependency_manager.reset()

    def get_service(self, name: str) -> Any:
        """获取服务"""
        return self.dependency_manager.get_service(name)

    def create_test_instance(
        self, class_type: Type, dependencies: Dict[str, str], **kwargs
    ) -> Any:
        """创建测试实例"""
        return self.dependency_manager.create_test_instance(
            class_type, dependencies, **kwargs
        )
