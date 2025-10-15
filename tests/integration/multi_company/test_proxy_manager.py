#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
代理管理器测试
测试代理管理器的功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.web.proxy_manager import ProxyManager


class TestProxyManager:
    """测试代理管理器"""

    @pytest.fixture
    def proxy_config(self):
        """代理配置fixture"""
        return {
            'enabled': True,
            'pools': {
                'test_pool': {
                    'enabled': True,
                    'max_size': 5,
                    'health_check_interval': 30
                }
            },
            'static_proxies': [
                {
                    'ip': '127.0.0.1',
                    'port': 8080,
                    'type': 'http',
                    'pool': 'test_pool'
                },
                {
                    'ip': '127.0.0.1',
                    'port': 1080,
                    'type': 'socks5',
                    'pool': 'test_pool'
                }
            ]
        }

    def test_proxy_manager_initialization(self, proxy_config):
        """测试代理管理器初始化"""
        manager = ProxyManager(proxy_config)
        assert manager is not None
        assert len(manager.pools) == 1
        assert 'test_pool' in manager.pools

    def test_get_proxy(self, proxy_config):
        """测试获取代理"""
        manager = ProxyManager(proxy_config)
        proxy = manager.get_proxy()

        # 由于是测试代理，可能无法连接，但应该返回代理对象
        # 在实际环境中，这里会返回真实的代理
        assert proxy is not None

    def test_proxy_stats(self, proxy_config):
        """测试代理统计信息"""
        manager = ProxyManager(proxy_config)
        stats = manager.get_stats()

        assert 'total_pools' in stats
        assert 'pools' in stats
        assert stats['total_pools'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])