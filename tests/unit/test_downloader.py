"""Unit tests for downloader module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.downloader import StockDownloader, _matches_keywords, _matches_excluded
from src.models import DownloadRequest


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
        d._download_single_link(request, "test_report", "http://example.com/file")

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
        result = d._download_single_link(
            request, "test_report", "http://example.com/file"
        )

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
        result = d._download_single_link(
            request, "annual_report", "http://example.com/file"
        )

        assert result is not None
        assert Path(result).parent.name == "financial_reports"


class TestVerifyDownloads:
    """Tests for StockDownloader._verify_downloads()."""

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

    def test_no_files_downloaded(self):
        config = self._make_config()
        d = StockDownloader(config)
        request = DownloadRequest(stock_code="300470")
        warnings = d._verify_downloads(request, [])
        assert len(warnings) == 1
        assert "No files were downloaded" in warnings[0]

    def test_file_missing(self):
        config = self._make_config()
        d = StockDownloader(config)
        request = DownloadRequest(stock_code="300470")
        warnings = d._verify_downloads(request, ["/nonexistent/file.pdf"])
        assert any("File missing" in w for w in warnings)

    def test_file_too_small(self, tmp_path):
        config = self._make_config(save_dir=str(tmp_path))
        d = StockDownloader(config)
        small_file = tmp_path / "small.pdf"
        small_file.write_bytes(b"x" * 10)  # well below MIN_FILE_SIZE (100)
        request = DownloadRequest(stock_code="300470")
        warnings = d._verify_downloads(request, [str(small_file)])
        assert any("too small" in w for w in warnings)

    def test_keyword_mismatch(self, tmp_path):
        config = self._make_config(save_dir=str(tmp_path))
        d = StockDownloader(config)
        ok_file = tmp_path / "annual_report_2024.pdf"
        ok_file.write_bytes(b"x" * 1024)
        request = DownloadRequest(
            stock_code="300470",
            allowed_keywords=["季报"],
        )
        warnings = d._verify_downloads(request, [str(ok_file)])
        assert any("does not match any allowed keyword" in w for w in warnings)

    def test_keyword_match_ok(self, tmp_path):
        config = self._make_config(save_dir=str(tmp_path))
        d = StockDownloader(config)
        ok_file = tmp_path / "季报2024.pdf"
        ok_file.write_bytes(b"x" * 1024)
        request = DownloadRequest(
            stock_code="300470",
            allowed_keywords=["季报"],
        )
        warnings = d._verify_downloads(request, [str(ok_file)])
        assert warnings == []

    def test_excluded_keyword_match(self, tmp_path):
        config = self._make_config(save_dir=str(tmp_path))
        d = StockDownloader(config)
        bad_file = tmp_path / "年报摘要.pdf"
        bad_file.write_bytes(b"x" * 1024)
        request = DownloadRequest(
            stock_code="300470",
            excluded_keywords=["摘要"],
        )
        warnings = d._verify_downloads(request, [str(bad_file)])
        assert any("matches excluded keyword" in w for w in warnings)

    def test_wrong_directory(self, tmp_path):
        config = self._make_config(save_dir=str(tmp_path))
        d = StockDownloader(config)
        wrong_dir = tmp_path / "wrong_place"
        wrong_dir.mkdir(parents=True, exist_ok=True)
        f = wrong_dir / "report.pdf"
        f.write_bytes(b"x" * 1024)
        request = DownloadRequest(
            stock_code="300470",
            save_subdir="raw/prospectus",
        )
        warnings = d._verify_downloads(request, [str(f)])
        assert any("unexpected directory" in w for w in warnings)

    def test_correct_directory_ok(self, tmp_path):
        config = self._make_config(save_dir=str(tmp_path))
        d = StockDownloader(config)
        correct_dir = tmp_path / "company" / "raw" / "prospectus"
        correct_dir.mkdir(parents=True, exist_ok=True)
        f = correct_dir / "report.pdf"
        f.write_bytes(b"x" * 1024)
        request = DownloadRequest(
            stock_code="300470",
            save_subdir="raw/prospectus",
        )
        warnings = d._verify_downloads(request, [str(f)])
        assert warnings == []

    def test_all_ok_no_keywords_no_subdir(self, tmp_path):
        config = self._make_config(save_dir=str(tmp_path))
        d = StockDownloader(config)
        f = tmp_path / "report.pdf"
        f.write_bytes(b"x" * 1024)
        request = DownloadRequest(stock_code="300470")
        warnings = d._verify_downloads(request, [str(f)])
        assert warnings == []

    def test_multiple_files_mixed_issues(self, tmp_path):
        config = self._make_config(save_dir=str(tmp_path))
        d = StockDownloader(config)
        # Good file
        good = tmp_path / "季报2024.pdf"
        good.write_bytes(b"x" * 1024)
        # Small file
        small = tmp_path / "年报2024.pdf"
        small.write_bytes(b"x" * 10)
        # Non-existent
        missing = str(tmp_path / "nonexistent.pdf")
        request = DownloadRequest(
            stock_code="300470",
            allowed_keywords=["季报", "年报"],
        )
        warnings = d._verify_downloads(request, [str(good), str(small), missing])
        assert len(warnings) == 2  # small + missing
        assert any("too small" in w for w in warnings)
        assert any("File missing" in w for w in warnings)


# ---------------------------------------------------------------------------
# CW-2.27D / Phase 3 — typed load state, DNS diagnostics, CLI error contract
# RED: 0 DOM links must NOT be folded into success/0; only the official
# announcement API confirming total=0 may be CONFIRMED_EMPTY.
# ---------------------------------------------------------------------------


class TestLoadState:
    """LoadState enum + DownloadResultTypedStatus backbone."""

    def test_load_state_enum_has_exactly_four_members(self):
        from src.transport_states import LoadState

        names = {member.name for member in LoadState}
        assert names == {"READY", "CONFIRMED_EMPTY", "INFRASTRUCTURE_FAIL", "TIMEOUT"}

    def test_load_state_is_hashable_immutable_enum(self):
        from src.transport_states import LoadState

        assert LoadState.READY is LoadState.READY
        assert LoadState.READY != LoadState.INFRASTRUCTURE_FAIL


class TestDownloadInternalTypedFailures:
    """0 DOM links without an observed official 2xx empty response must be
    INFRASTRUCTURE_FAIL, not the historical ``success=True / 0 files`` path."""

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

    def test_repeated_no_links_without_official_empty_is_infrastructure_fail(self):
        from src.downloader import StockDownloader
        from src.transport_states import LoadState

        config = self._make_config()
        d = StockDownloader(config)
        d._browser = MagicMock()
        d._browser.navigate.return_value = True
        # `_switch_tab` polls `querySelectorAll(detail)` count == 0 on all 3 retries.
        d._browser.execute_script.return_value = 0
        d._browser.get_current_page_info.return_value = {"total_pages": 1}

        request = DownloadRequest(
            stock_code="300470",
            stock_name="中密控股",
            suffix="periodicReports",
        )
        # Avoid real `_wait_for_page_load` sleeps / `_get_links` browser polling.
        with patch.object(StockDownloader, "_wait_for_page_load", lambda self: None):
            result = d._download_internal(request)

        assert result.success is False
        assert result.load_state == LoadState.INFRASTRUCTURE_FAIL
        assert result.downloaded_files == []
        assert result.error_code == "upstream_unavailable"
        assert result.retryable is True

    def test_official_confirmed_total_zero_is_success_zero_files(self):
        from src.downloader import StockDownloader
        from src.transport_states import LoadState

        config = self._make_config()
        d = StockDownloader(config)
        d._browser = MagicMock()
        d._browser.navigate.return_value = True
        # Simulate the Phase 5 cninfo_api client already confirming total=0
        # before SPA tab-switch. The seam is the downloader-level
        # `_official_status` field; `_switch_tab` must not override it.
        d._official_status = LoadState.CONFIRMED_EMPTY
        # `_switch_tab` polls `querySelectorAll(detail)` count == 0 on all 3 retries.
        d._browser.execute_script.return_value = 0
        d._browser.get_current_page_info.return_value = {"total_pages": 1}

        request = DownloadRequest(
            stock_code="300470",
            stock_name="中密控股",
            suffix="periodicReports",
        )
        # Avoid real `_wait_for_page_load` sleeps / `_get_links` browser polling.
        with patch.object(StockDownloader, "_wait_for_page_load", lambda self: None):
            result = d._download_internal(request)

        assert result.success is True
        assert result.load_state == LoadState.CONFIRMED_EMPTY
        assert result.downloaded_files == []
        assert result.error_code is None


class TestBrowserStaticHostMapping:
    """Hardcoded fallback IP must be removed; static host mapped separately."""

    def test_no_hardcoded_cninfo_fallback_ip(self):
        src = Path("src/browser.py").read_text(encoding="utf-8")
        assert "148.153.240.73" not in src, (
            "hardcoded fallback IP must be removed; resolve per-host on demand"
        )

    def test_resolves_static_and_www_hosts_separately(self):
        src = Path("src/browser.py").read_text(encoding="utf-8")
        # Critical hosts (www + static) must each be resolved independently —
        # bare ``cninfo.com.cn`` is best-effort and NOT required since the
        # SPA + PDF pipeline never requests that host (Akamai CDN quirk).
        for host in (
            "www.cninfo.com.cn",
            "static.cninfo.com.cn",
        ):
            assert host in src, f"{host} must be resolved per-host (critical)"
        # Hardcoded fallback IP replaced by per-host getaddrinfo loop.
        assert "getaddrinfo(" in src
        # Refuse the historical single-IP aliasing fallback.
        assert "_CNINFO_FALLBACK_IP" not in src
        assert "148.153.240.73" not in src


class TestCliErrorJsonContract:
    """Non-zero exit must emit the structured 1.0 error JSON with adapter 1.2.0."""

    def test_failure_stderr_last_line_is_structured_error_with_adapter_version_1_2_0(
        self, capsys, monkeypatch
    ):
        import io

        import src.company_wiki_adapter_cli as cli

        # Feed a valid discover payload so _payload() passes; _build_adapter is
        # patched to raise a stable RuntimeError so the structured error path
        # is exercised without touching real config / browser / network.
        monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
        original_name = cli.ADAPTER_NAME
        with (
            patch.object(cli, "ADAPTER_VERSION", "1.2.0"),
            patch.object(
                cli,
                "_build_adapter",
                side_effect=RuntimeError("boom"),
            ),
        ):
            argv = ["discover", "--config", "config.json"]
            rc = cli.main(argv)

        assert rc == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        last_line = captured.err.strip().splitlines()[-1]
        payload = json.loads(last_line)
        assert payload["schema_version"] == "1.0"
        assert payload["status"] == "failed"
        assert payload["adapter"] == {"name": original_name, "version": "1.2.0"}
        err = payload["error"]
        assert err["code"] == "upstream_unavailable"
        assert err["type"] == "RuntimeError"
        assert err["message"] == "boom"
        assert err["retryable"] is True
