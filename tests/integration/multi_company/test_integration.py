#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration Test for Multi-Company Downloader (Refactored)
Tests the workflow through the legacy parallel runner.
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.interfaces.downloader_interface import DownloadResult

# Legacy import now handled by conftest.py path injection
try:
    from main_parallel import MultiCompanyDownloader
except ImportError:
    MultiCompanyDownloader = None

@pytest.mark.integration
class TestMultiCompanyIntegration:
    """Integrated tests for multi-company downloading logic."""

    def test_end_to_end_workflow_mocked(self, mocker):
        """Tests the end-to-end workflow using mocked downloader factory."""
        if MultiCompanyDownloader is None:
            pytest.skip("main_parallel module not found")

        # Setup test configuration
        test_config = {
            "companies": [
                {
                    "stock_code": "300470",
                    "company_name": "中密控股",
                    "enabled": True
                }
            ],
            "parallel_download": {
                "enabled": False,
                "max_workers": 1
            }
        }

        # Mock dependencies
        mocker.patch('src.data.mapping.MappingManager.get_org_id', return_value='9900012345')
        
        # Patch the factory inside main_parallel
        mock_factory = mocker.patch('src.factory.downloader_factory.downloader_factory.create_downloader')
        mock_adapter = MagicMock()
        
        # The modern runner returns boolean for download_activity_records
        mock_adapter.download_activity_records.return_value = True
        mock_factory.return_value = mock_adapter

        # Create and execute
        downloader = MultiCompanyDownloader(test_config)
        results = downloader.download_all_companies()

        # Verify
        assert len(results) == 1
        assert results[0]['success'] is True
        assert results[0]['stock_code'] == '300470'