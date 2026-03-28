#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UnifiedDownloader Core Unit Tests
Tests the core logic of UnifiedDownloader with full mocking of external dependencies.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.interfaces.downloader_interface import DownloadRequest
from src.services.unified_downloader import UnifiedDownloader


class TestUnifiedDownloaderCore:

    @pytest.fixture
    def mock_factory(self):
        with patch("src.web.browser_strategy.BrowserStrategyFactory") as mock:
            yield mock

    @pytest.fixture
    def mock_mapping(self):
        with patch("src.data.mapping.MappingManager") as mock:
            instance = mock.return_value
            instance.get_org_id.return_value = "9900000000"
            instance.get_stock_name.return_value = "TestCompany"
            yield instance

    @pytest.fixture
    def downloader(self, mock_factory, mock_mapping):
        # Initialize with a dummy config
        config = {
            "browser_strategy": "mock_strategy",
            "save_dir": "/tmp/test_downloads",
            "headless": True,
        }
        downloader = UnifiedDownloader(config=config)
        # Manually attach a mock strategy instance for verification
        downloader.browser_strategy = MagicMock()
        return downloader

    def test_initialization(self, mock_factory):
        """Test proper initialization and strategy creation"""
        config = {"browser_strategy": "playwright", "save_dir": "/tmp"}
        downloader = UnifiedDownloader(config=config)

        assert downloader.config["browser_strategy"] == "playwright"
        mock_factory.create_strategy.assert_called_once()
        downloader.browser_strategy.initialize.assert_called_once()

    def test_download_stock_pdfs_request_object(self, downloader):
        """Test downloading using a DownloadRequest object"""
        # Setup mocks
        downloader.browser_strategy.navigate.return_value = True
        downloader._get_links_safe = MagicMock(
            return_value=[("Test Report 2025", "/detail/123")]
        )
        downloader._matches = MagicMock(return_value=True)
        downloader.browser_strategy.download_file.return_value = True

        # Mock file existence check to simulate successful download
        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.stat"
        ) as mock_stat:
            mock_stat.return_value.st_size = 1024  # > 100 bytes

            request = DownloadRequest(
                stock_code="000001",
                stock_name="TestBank",
                max_pages=1,
                save_dir="/tmp/test_downloads",
            )

            result = downloader.download_stock_pdfs(request)

            assert result.success is True
            assert len(result.downloaded_files) == 1
            downloader.browser_strategy.navigate.assert_called()

    def test_retry_logic_success_after_failure(self, downloader):
        """Test that the downloader retries upon failure"""
        # First attempt fails, second succeeds
        downloader._download_internal = MagicMock(
            side_effect=[
                MagicMock(success=False, errors=["Timeout"]),
                MagicMock(success=True, downloaded_files=["file.pdf"]),
            ]
        )

        request = DownloadRequest(stock_code="000001")
        result = downloader._download_with_retry(request)

        assert result.success is True
        assert downloader._download_internal.call_count == 2

    def test_retry_logic_max_retries_exceeded(self, downloader):
        """Test that the downloader gives up after max retries"""
        # All attempts fail
        fail_result = MagicMock(success=False, errors=["Timeout"])
        downloader._download_internal = MagicMock(return_value=fail_result)

        request = DownloadRequest(stock_code="000001")
        downloader.config["retry_count"] = 2

        result = downloader._download_with_retry(request)

        assert result.success is False
        # Initial try + 2 retries = 3 calls
        assert downloader._download_internal.call_count == 3

    def test_perform_download_pagination(self, downloader):
        """Test pagination logic"""
        # Mock navigation
        downloader.browser_strategy.navigate.return_value = True

        # Mock links for 2 pages
        # The first call is consumed by the 'Wait for page load' loop in _perform_download
        links_p1 = [("Report P1", "/p1")]
        links_p2 = [("Report P2", "/p2")]

        downloader._get_links_safe = MagicMock(
            side_effect=[
                links_p1,  # Wait loop call 1 (Success, breaks loop)
                links_p1,  # Page 1 processing
                links_p2,  # Page 2 processing
                [],  # Page 3/End
            ]
        )

        downloader.browser_strategy.go_to_next_page.side_effect = [True, False]
        downloader.browser_strategy.download_file.return_value = True
        downloader._matches = MagicMock(return_value=True)

        # We need exists to be False during the check, and True during the verification after download
        with patch("pathlib.Path.exists") as mock_exists, patch(
            "pathlib.Path.stat"
        ) as mock_stat:
            mock_exists.side_effect = [
                False,
                True,
                False,
                True,
            ]  # Page 1: Check, Verify; Page 2: Check, Verify
            mock_stat.return_value.st_size = 1024

            request = DownloadRequest(
                stock_code="000001",
                org_id="999",
                max_pages=2,
                save_dir="/tmp/test_downloads",
                stock_name="TestCompany",
            )

            # Inject org_id to avoid mapping call in _perform_download
            files = downloader._perform_download(request)

            assert len(files) == 2
            assert downloader.browser_strategy.go_to_next_page.call_count >= 1

    def test_keyword_filtering(self, downloader):
        """Test that files are filtered by keywords"""
        # Setup links: one matching, one not matching
        links = [("Annual Report 2025", "/link1"), ("Daily News", "/link2")]
        downloader.browser_strategy.navigate.return_value = True
        # First call for wait loop, second for page 1 processing
        downloader._get_links_safe = MagicMock(side_effect=[links, links])

        # Real _matches logic logic is used, so we don't mock it
        # But we need to ensure perform_download uses the real one?
        # _perform_download calls self._matches.
        # By default in this fixture `downloader` is a real instance with mocked strategies.
        # So `_matches` is the real method.

        with patch("pathlib.Path.exists") as mock_exists, patch(
            "pathlib.Path.stat"
        ) as mock_stat:
            # Only one file (Annual Report) will reach the verification check
            mock_exists.side_effect = [False, True]
            mock_stat.return_value.st_size = 1024
            downloader.browser_strategy.download_file.return_value = True

            request = DownloadRequest(
                stock_code="000001",
                stock_name="TestCompany",
                org_id="999",
                allowed_keywords=["Annual Report"],
                max_pages=1,
                save_dir="/tmp/test_downloads",
            )

            files = downloader._perform_download(request)

            # Should only download the Annual Report
            assert len(files) == 1
            assert "Annual Report" in files[0]
            # Verify download was called only for the matching link
            downloader.browser_strategy.download_file.assert_called_once()
            args, _ = downloader.browser_strategy.download_file.call_args
            assert "/link1" in args[0]

    def test_cleanup(self, downloader):
        """Test resource cleanup"""
        downloader.cleanup()
        downloader.browser_strategy.close.assert_called_once()

    def test_status_reporting(self, downloader):
        """Test status reporting"""
        status = downloader.get_status()
        assert status.is_running is False
        assert status.downloaded_count == 0

    def test_legacy_call_compatibility(self, downloader):
        """Test backward compatibility with legacy call style - returns DownloadResult"""
        mock_result = MagicMock()
        mock_result.downloaded_files = ["f1.pdf"]
        mock_result.success = True
        downloader._download_with_retry = MagicMock(return_value=mock_result)

        # Call with string stock_code - now returns DownloadResult
        res = downloader.download_stock_pdfs("000001", stock_name="Bank")

        assert res.downloaded_files == ["f1.pdf"]
        assert res.success is True
        # Verify request object was constructed correctly
        call_args = downloader._download_with_retry.call_args[0][0]
        assert isinstance(call_args, DownloadRequest)
        assert call_args.stock_code == "000001"
        assert call_args.stock_name == "Bank"
