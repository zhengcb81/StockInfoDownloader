"""Unit tests for downloader module."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.downloader import StockDownloader, _matches_keywords, _matches_excluded
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

    def test_pure_date_keyword(self):
        # Pure 8-digit date as keyword matches if date appears in text
        assert _matches_keywords("公司报告20250725", ["20250725"]) is True
        assert _matches_keywords("公司报告20250725", ["20250724"]) is False

    def test_empty_keyword(self):
        # Empty keyword in list is skipped (normalised to empty string)
        assert _matches_keywords("报告", ["", "报告"]) is True

    def test_special_characters(self):
        assert _matches_keywords("报告(2025)", ["报告(2025)"]) is True
        assert _matches_keywords("报告(2025)", ["报告2025"]) is False

    def test_keyword_longer_than_text(self):
        assert _matches_keywords("报告", ["这是一段很长的关键词"]) is False

    def test_multiple_keywords_one_matches(self):
        # Multiple keywords; first two don't match, third does
        assert _matches_keywords("研究报告", ["公告", "快讯", "研究"]) is True


class TestMatchesExcluded:
    def test_no_keywords_not_excluded(self):
        assert _matches_excluded("anything", None) is False
        assert _matches_excluded("anything", []) is False

    def test_exact_match_excluded(self):
        assert _matches_excluded("2024年年度报告摘要", ["摘要"]) is True

    def test_no_match_not_excluded(self):
        assert _matches_excluded("2024年年度报告", ["摘要"]) is False

    def test_case_insensitive(self):
        assert _matches_excluded("Test Summary", ["summary"]) is True

    def test_multiple_keywords_one_matches(self):
        assert _matches_excluded("公告摘要", ["目录", "摘要"]) is True


class TestDownloadRequestExcludedKeywords:
    def test_default_is_none(self):
        req = DownloadRequest(stock_code="000001")
        assert req.excluded_keywords is None

    def test_set_excluded_keywords(self):
        req = DownloadRequest(stock_code="000001", excluded_keywords=["摘要", "目录"])
        assert req.excluded_keywords == ["摘要", "目录"]


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


class TestDownloadPathConstruction:
    """Test that _download_single_link constructs correct paths with save_subdir."""

    def _make_config(self, save_dir=None):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump({"300470": {"orgId": "9900023856", "name": "中密控股"}}, f)
        f.close()
        return {
            "save_dir": save_dir or tempfile.mkdtemp(),
            "max_retries": 1,
            "headless": True,
            "skip_browser_init": True,
            "files": {"mapping_file": f.name},
        }

    def test_path_without_save_subdir(self, tmp_path):
        """Without save_subdir, files go to save_dir/company_name/file.pdf."""
        config = self._make_config(save_dir=str(tmp_path))
        d = StockDownloader(config)
        d._browser = MagicMock()
        d._browser.download_file.return_value = False  # skip actual download

        request = DownloadRequest(
            stock_code="300470",
            stock_name="百傲化学",
        )
        result = d._download_single_link(request, "test_report", "http://example.com/file")

        # Verify the failed_logger was called (download_file returns False)
        assert len(d._failed_logger._pending) == 1

    def test_path_with_save_subdir(self, tmp_path):
        """With save_subdir, files go to save_dir/company_name/save_subdir/file.pdf."""
        config = self._make_config(save_dir=str(tmp_path))
        d = StockDownloader(config)
        d._browser = MagicMock()

        # Create a real file so the skip-existing check triggers
        subdir = tmp_path / "百傲化学" / "raw" / "prospectus"
        subdir.mkdir(parents=True, exist_ok=True)
        existing_file = subdir / "test_report.pdf"
        existing_file.write_bytes(b"x" * 1024)  # > MIN_FILE_SIZE

        request = DownloadRequest(
            stock_code="300470",
            stock_name="百傲化学",
            save_subdir="raw/prospectus",
        )
        result = d._download_single_link(request, "test_report", "http://example.com/file")

        assert result is not None
        assert "raw" in result
        assert "prospectus" in result

    def test_path_with_nested_save_subdir(self, tmp_path):
        """Nested save_subdir like 'raw/prospectus' creates intermediate dirs."""
        config = self._make_config(save_dir=str(tmp_path))
        d = StockDownloader(config)
        d._browser = MagicMock()

        # Create file at the nested path
        subdir = tmp_path / "百傲化学" / "raw" / "financial_reports"
        subdir.mkdir(parents=True, exist_ok=True)
        existing_file = subdir / "annual_report.pdf"
        existing_file.write_bytes(b"x" * 2048)

        request = DownloadRequest(
            stock_code="300470",
            stock_name="百傲化学",
            save_subdir="raw/financial_reports",
        )
        result = d._download_single_link(request, "annual_report", "http://example.com/file")

        assert result is not None
        assert Path(result).parent.name == "financial_reports"

