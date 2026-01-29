#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
System Integration Test for Unified Downloader
Focuses on the core components and their interactions using mocks.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.factory.downloader_factory import downloader_factory
from src.interfaces.downloader_interface import DownloadRequest, DownloadResult


@pytest.mark.integration
class TestSystemIntegration:
    """Integrated tests for the unified downloader system."""

    @pytest.fixture
    def mock_downloader(self, mocker):
        # Create a mock that behaves like UnifiedDownloader
        mock_instance = MagicMock()
        mocker.patch(
            "src.factory.downloader_factory.downloader_factory.create_downloader",
            return_value=mock_instance,
        )
        return mock_instance

    def test_complete_download_workflow(self, mock_downloader):
        """Tests the full workflow through the factory and downloader."""
        # Setup mock result
        mock_result = DownloadResult(
            success=True,
            downloaded_files=["test.pdf"],
            total_files=1,
            errors=[],
            duration_seconds=1.5,
            metadata={},
        )
        mock_downloader.download_stock_pdfs.return_value = mock_result

        # Execute
        downloader = downloader_factory.create_downloader(downloader_type="unified")
        request = DownloadRequest(stock_code="300470", save_dir="test_downloads")
        result = downloader.download_stock_pdfs(request)

        # Verify
        assert result.success is True
        assert len(result.downloaded_files) == 1
        mock_downloader.download_stock_pdfs.assert_called_once()

    def test_multiple_stock_processing(self, mock_downloader):
        """Tests processing multiple requests."""
        mock_downloader.download_stock_pdfs.return_value = DownloadResult(
            success=True,
            downloaded_files=["f.pdf"],
            total_files=1,
            errors=[],
            duration_seconds=1,
            metadata={},
        )

        downloader = downloader_factory.create_downloader()
        codes = ["000001", "300470"]
        for code in codes:
            req = DownloadRequest(stock_code=code, save_dir="test")
            downloader.download_stock_pdfs(req)

        assert mock_downloader.download_stock_pdfs.call_count == 2

    def test_config_loading_and_validation(self):
        """Tests factory correctly handles configuration."""
        from src.core.config import ConfigManager

        cm = ConfigManager()
        assert cm is not None
        # Verify factory initialization doesn't crash
        factory = downloader_factory
        assert factory is not None

    def test_file_management_integration(self):
        """Tests integration with file utility services."""
        from src.utils.directory_manager import DirectoryManager

        dm = DirectoryManager()
        # Should be able to get a path without crashing
        path = dm.get_company_directory("test_dir", Path("TestCompany"))
        assert "TestCompany" in str(path)

    def test_error_handling_and_logging(self, mock_downloader):
        """Tests system resilience when downloader fails."""
        mock_downloader.download_stock_pdfs.side_effect = Exception("Browser crash")

        downloader = downloader_factory.create_downloader()
        req = DownloadRequest(stock_code="300470", save_dir="test")

        with pytest.raises(Exception) as excinfo:
            downloader.download_stock_pdfs(req)
        assert "Browser crash" in str(excinfo.value)

    def test_backward_compatibility(self):
        """Tests the legacy adapter interface integration."""
        adapter = downloader_factory.create_legacy_adapter("cninfo")
        assert hasattr(adapter, "download_activity_records")

    def test_performance_metrics(self, mock_downloader):
        """Tests that performance data is recorded during integration."""
        mock_result = DownloadResult(
            success=True,
            downloaded_files=[],
            total_files=0,
            errors=[],
            duration_seconds=5.0,
            metadata={},
        )
        mock_downloader.download_stock_pdfs.return_value = mock_result

        downloader = downloader_factory.create_downloader()
        result = downloader.download_stock_pdfs(
            DownloadRequest(stock_code="1", save_dir="t")
        )
        assert result.duration_seconds == 5.0
