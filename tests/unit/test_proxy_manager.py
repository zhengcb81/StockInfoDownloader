"""
Proxy Manager Tests
Tests for proxy manager functionality
"""

import time

import pytest

from src.web.proxy_manager import (
    ProxyInfo,
    ProxyManager,
    ProxyPool,
    ProxyStatus,
    ProxyType,
)


class TestProxyType:
    """ProxyType enum tests"""

    def test_proxy_type_values(self):
        """Test proxy type enum values"""
        assert ProxyType.HTTP.value == "http"
        assert ProxyType.HTTPS.value == "https"
        assert ProxyType.SOCKS4.value == "socks4"
        assert ProxyType.SOCKS5.value == "socks5"
        assert ProxyType.RESIDENTIAL.value == "residential"
        assert ProxyType.DATA_CENTER.value == "data_center"
        assert ProxyType.ELITE.value == "elite"


class TestProxyStatus:
    """ProxyStatus enum tests"""

    def test_proxy_status_values(self):
        """Test proxy status enum values"""
        assert ProxyStatus.ACTIVE.value == "active"
        assert ProxyStatus.INACTIVE.value == "inactive"
        assert ProxyStatus.TESTING.value == "testing"
        assert ProxyStatus.BANNED.value == "banned"
        assert ProxyStatus.EXPIRED.value == "expired"


class TestProxyInfo:
    """ProxyInfo dataclass tests"""

    def test_init_basic(self):
        """Test basic initialization"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP
        )
        assert proxy.ip == "127.0.0.1"
        assert proxy.port == 8080
        assert proxy.proxy_type == ProxyType.HTTP
        assert proxy.status == ProxyStatus.ACTIVE
        assert proxy.score == 100.0

    def test_init_with_credentials(self):
        """Test initialization with credentials"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            username="user",
            password="pass"
        )
        assert proxy.username == "user"
        assert proxy.password == "pass"

    def test_proxy_url_without_auth(self):
        """Test proxy URL without authentication"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP
        )
        assert proxy.proxy_url == "http://127.0.0.1:8080"

    def test_proxy_url_with_auth(self):
        """Test proxy URL with authentication"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTPS,
            username="user",
            password="pass"
        )
        assert proxy.proxy_url == "https://user:pass@127.0.0.1:8080"

    def test_is_expired_no_expiration(self):
        """Test proxy without expiration time"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP
        )
        assert proxy.is_expired is False

    def test_is_expired_with_future_time(self):
        """Test proxy with future expiration"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            expires_at=time.time() + 3600
        )
        assert proxy.is_expired is False

    def test_is_expired_with_past_time(self):
        """Test expired proxy"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            expires_at=time.time() - 1
        )
        assert proxy.is_expired is True

    def test_is_banned(self):
        """Test banned status"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            status=ProxyStatus.BANNED
        )
        assert proxy.is_banned is True

    def test_is_active(self):
        """Test active status"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            status=ProxyStatus.ACTIVE
        )
        assert proxy.is_active is True

    def test_is_active_when_banned(self):
        """Test banned proxy is not active"""
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP,
            status=ProxyStatus.BANNED
        )
        assert proxy.is_active is False


class TestProxyPool:
    """ProxyPool class tests"""

    def test_init(self):
        """Test initialization"""
        config = {"max_retries": 3, "timeout": 30}
        pool = ProxyPool("test_pool", config)
        assert pool.name == "test_pool"
        assert len(pool.proxies) == 0

    def test_add_proxy(self):
        """Test adding proxy"""
        config = {"max_retries": 3, "timeout": 30}
        pool = ProxyPool("test_pool", config)
        proxy = ProxyInfo(
            ip="127.0.0.1",
            port=8080,
            proxy_type=ProxyType.HTTP
        )
        pool.add_proxy(proxy)
        assert len(pool.proxies) == 1

    def test_get_stats(self):
        """Test getting pool statistics"""
        config = {"max_retries": 3, "timeout": 30}
        pool = ProxyPool("test_pool", config)
        stats = pool.get_stats()

        assert "total_proxies" in stats
        assert "name" in stats
        assert stats["name"] == "test_pool"


class TestProxyManager:
    """ProxyManager class tests"""

    def test_init(self):
        """Test initialization"""
        config = {}
        manager = ProxyManager(config)
        assert manager.config == config
        assert manager.pools is not None

    def test_get_stats(self):
        """Test getting statistics"""
        config = {}
        manager = ProxyManager(config)
        stats = manager.get_stats()

        assert "total_pools" in stats
        assert "pools" in stats
        assert isinstance(stats["total_pools"], int)
