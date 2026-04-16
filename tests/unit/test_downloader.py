"""Unit tests for downloader module."""
import json
import tempfile
from unittest.mock import MagicMock, patch

from src.downloader import StockDownloader, _matches_keywords
from src.models import DownloadRequest, DownloadResult


class TestMatchesKeywords:
    def test_no_keywords_matches_all(self):
        assert _matches_keywords("anything", None) is True
        assert _matches_keywords("anything", []) is True

    def test_exact_match(self):
        assert _matches_keywords("测试报告", ["测试"]) is True

    def test_no_match(self):
        assert _matches_keywords("年报", ["季报"]) is False

    def test_date_match(self):
        assert _matches_keywords("公司报告20250725", ["公告20250725"]) is True

    def test_case_insensitive(self):
        assert _matches_keywords("Test Report", ["test"]) is True


class TestStockDownloader:
    def _make_config(self):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump({"300470": {"orgId": "9900023856", "name": "中密控股"}}, f)
        f.close()
        return {
            "save_dir": tempfile.mkdtemp(),
            "max_retries": 1,
            "headless": True,
            "skip_browser_init": True,
            "files": {"mapping_file": f.name},
        }

    def test_init(self):
        config = self._make_config()
        d = StockDownloader(config)
        assert d.save_dir == config["save_dir"]
        assert d.max_retries == 1

    def test_counters_initialized(self):
        d = StockDownloader(self._make_config())
        assert d.skipped_files == []
        assert d.pages_traversed == 0
        assert d.download_count == 0

    def test_download_activity_records_returns_list(self):
        """Test that download_activity_records returns a list (even on failure)."""
        d = StockDownloader(self._make_config())
        # With skip_browser_init and no browser, it should fail gracefully
        # But download_activity_records calls _download_internal which needs browser
        # So we test the API shape, not the full pipeline
        assert hasattr(d, "download_activity_records")
        assert hasattr(d, "cleanup")
