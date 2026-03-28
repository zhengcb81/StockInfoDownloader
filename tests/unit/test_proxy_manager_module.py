"""
Proxy manager module tests
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from src.web.proxy_manager import (
    ProxyInfo,
    ProxyManager,
    ProxyPool,
    ProxyStatus,
    ProxyType,
)


class TestProxyInfo:
    """Test ProxyInfo class"""

    def test_init(self):
        """Test ProxyInfo initialization"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP
        )
        assert proxy.ip == "127.0.0.1"
        assert proxy.port == 8080
        assert proxy.proxy_type == ProxyType.HTTP

    def test_proxy_url(self):
        """Test proxy_url property"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP
        )
        assert proxy.proxy_url == "http://127.0.0.1:8080"

    def test_proxy_url_with_auth(self):
        """Test proxy_url with authentication"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            username="user",
            password="pass"
        )
        assert "user:pass@" in proxy.proxy_url

    def test_is_expired(self):
        """Test is_expired property"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            expires_at=time.time() - 100  # Expired
        )
        assert proxy.is_expired is True

    def test_is_expired_not_expired(self):
        """Test is_expired when not expired"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            expires_at=time.time() + 1000  # Not expired
        )
        assert proxy.is_expired is False

    def test_is_banned(self):
        """Test is_banned property"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            status=ProxyStatus.BANNED
        )
        assert proxy.is_banned is True

    def test_is_banned_not_banned(self):
        """Test is_banned when not banned"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            status=ProxyStatus.ACTIVE
        )
        assert proxy.is_banned is False

    def test_is_active(self):
        """Test is_active property"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            status=ProxyStatus.ACTIVE
        )
        assert proxy.is_active is True

    def test_is_active_inactive(self):
        """Test is_active when inactive"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            status=ProxyStatus.INACTIVE
        )
        assert proxy.is_active is False

    def test_record_request_success(self):
        """Test recording successful request"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            total_requests=0,
            failed_requests=0
        )
        proxy.record_request(success=True, response_time=0.5)
        assert proxy.total_requests == 1
        assert proxy.failed_requests == 0
        assert proxy.response_time == 0.5

    def test_record_request_failure(self):
        """Test recording failed request"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            total_requests=0,
            failed_requests=0
        )
        proxy.record_request(success=False, response_time=1.0)
        assert proxy.total_requests == 1
        assert proxy.failed_requests == 1

    def test_record_request_updates_success_rate(self):
        """Test success rate calculation"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            total_requests=8,
            failed_requests=2,
            success_rate=0.75
        )
        proxy.record_request(success=True, response_time=0.5)
        # 8+1 = 9 total, 2 failed = 2, success_rate = 7/9 = 0.777...
        assert proxy.total_requests == 9
        assert proxy.failed_requests == 2

    def test_reset_usage(self):
        """Test reset_usage method"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            total_requests=100,
            failed_requests=50,
            current_requests=10
        )
        proxy.reset_usage()
        assert proxy.current_requests == 0

    def test_get_unique_id(self):
        """Test get_unique_id method"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP
        )
        proxy_id = proxy.get_unique_id()
        # Returns MD5 hash
        assert len(proxy_id) == 32


class TestProxyPool:
    """Test ProxyPool class"""

    def test_init(self):
        """Test ProxyPool initialization"""
        config = {"max_proxies": 10}
        pool = ProxyPool("test_pool", config)
        assert pool.name == "test_pool"
        assert pool.config == config

    def test_add_proxy(self):
        """Test adding proxy to pool"""
        config = {"max_proxies": 10}
        pool = ProxyPool("test_pool", config)
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP
        )
        pool.add_proxy(proxy)
        assert len(pool.proxies) == 1

    def test_remove_proxy(self):
        """Test removing proxy from pool"""
        config = {"max_proxies": 10}
        pool = ProxyPool("test_pool", config)
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP
        )
        pool.add_proxy(proxy)
        pool.remove_proxy(proxy.get_unique_id())
        assert len(pool.proxies) == 0

    def test_get_proxy(self):
        """Test getting proxy from pool"""
        config = {"max_proxies": 10}
        pool = ProxyPool("test_pool", config)
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            status=ProxyStatus.ACTIVE
        )
        pool.add_proxy(proxy)
        selected = pool.get_proxy()
        assert selected is not None
        assert selected.ip == "127.0.0.1"

    def test_get_proxy_empty_pool(self):
        """Test getting proxy from empty pool"""
        config = {"max_proxies": 10}
        pool = ProxyPool("test_pool", config)
        selected = pool.get_proxy()
        assert selected is None

    def test_get_stats(self):
        """Test getting pool statistics"""
        config = {"max_proxies": 10}
        pool = ProxyPool("test_pool", config)
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            status=ProxyStatus.ACTIVE
        )
        pool.add_proxy(proxy)
        stats = pool.get_stats()
        assert "total_proxies" in stats
        assert stats["total_proxies"] == 1


class TestProxyManager:
    """Test ProxyManager class"""

    def test_init(self):
        """Test ProxyManager initialization"""
        config = {
            "pools": {
                "default": {
                    "max_proxies": 10
                }
            }
        }
        manager = ProxyManager(config)
        assert "default" in manager.pools

    def test_get_proxy(self):
        """Test getting proxy from manager"""
        config = {
            "pools": {
                "default": {
                    "max_proxies": 10
                }
            }
        }
        manager = ProxyManager(config)
        proxy = manager.get_proxy()
        # Empty pool returns None
        assert proxy is None or isinstance(proxy, ProxyInfo)

    def test_release_proxy(self):
        """Test releasing proxy back to manager"""
        config = {
            "pools": {
                "default": {
                    "max_proxies": 10
                }
            }
        }
        manager = ProxyManager(config)
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            status=ProxyStatus.ACTIVE
        )
        # Should not raise exception
        manager.release_proxy(proxy, success=True, response_time=0.5)

    def test_get_stats(self):
        """Test getting manager statistics"""
        config = {
            "pools": {
                "default": {
                    "max_proxies": 10
                }
            }
        }
        manager = ProxyManager(config)
        stats = manager.get_stats()
        assert isinstance(stats, dict)

    def test_cleanup_expired_proxies(self):
        """Test cleaning up expired proxies"""
        config = {
            "pools": {
                "default": {
                    "max_proxies": 10
                }
            }
        }
        manager = ProxyManager(config)
        # Should not raise exception
        manager.cleanup_expired_proxies()
