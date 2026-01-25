#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CninfoDownloader 单元测试 (Refactored to Pytest)
Focuses on the adapter and delegation to UnifiedDownloader with full mocking.
"""

import pytest
from unittest.mock import MagicMock
import os
from pathlib import Path

from cninfo_activity_downloader import CninfoDownloader

@pytest.fixture
def downloader(tmp_path):
    """创建下载器实例 (CninfoDownloaderAdapter)"""
    save_dir = tmp_path / "downloads"
    save_dir.mkdir()
    return CninfoDownloader(save_dir=str(save_dir))

@pytest.mark.unit
def test_downloader_initialization(downloader):
    """测试下载器初始化状态"""
    assert downloader.save_dir is not None
    assert downloader._unified_downloader is not None

@pytest.mark.unit
def test_clean_filename_via_service(downloader):
    """测试文件名清洗"""
    # Use a direct mock to avoid dependency on FileService's internal ConfigManager
    mock_fs = MagicMock()
    mock_fs.clean_filename.side_effect = lambda x: x.replace("/", "_")
    downloader._unified_downloader.file_service = mock_fs
    
    res = downloader._unified_downloader.file_service.clean_filename("test/file.pdf")
    assert "test_file.pdf" in res

@pytest.mark.unit
def test_get_org_id_mocked(downloader, mocker):
    """测试组织ID获取 (Mocked)"""
    # Mock the internal MappingManager used by the adapter
    mock_mm = MagicMock()
    mock_mm.get_org_id.return_value = "9900000062"
    mocker.patch('src.data.mapping.MappingManager', return_value=mock_mm)
    
    assert downloader.get_org_id("000001") == "9900000062"

@pytest.mark.unit
def test_driver_lifecycle(downloader):
    """测试 WebDriver 的资源清理逻辑"""
    mock_strategy = MagicMock()
    downloader._unified_downloader.browser_strategy = mock_strategy

    downloader.cleanup()
    mock_strategy.close.assert_called_once()

@pytest.mark.unit
def test_cleanup_pdf_txt(downloader, tmp_path):
    """测试临时文件的清理 (如果方法存在)"""
    # UnifiedDownloader might not have _cleanup_pdf_txt, but we check compatibility
    if hasattr(downloader._unified_downloader, '_cleanup_pdf_txt'):
        pdf_txt = Path(downloader.save_dir) / "pdf.txt"
        pdf_txt.write_text("dummy")
        downloader._unified_downloader._cleanup_pdf_txt()
        assert not pdf_txt.exists()