"""MB-SID A0 — behaviour contract for the accepted legacy downloader WIP.

Every case here is offline: a fake SPA page, ``tmp_path`` scratch directories
and a fake DNS resolver.  Nothing starts Chromium, resolves a real host or
downloads a real PDF.

The fake page models what the real cninfo page provides — a set of menu items,
exactly one selected, and one link list per tab — so the tests assert the
*observable* tab scope rather than repeating the browser's selectors.

The five clusters correspond to the static gaps recorded in
``review/repo_reconciliation_20261111/acquisition_review.md`` §4.3:

1. ``CONFIRMED_EMPTY`` is request-scoped — a second request on the same
   instance must re-observe instead of inheriting the first empty result.
2. ``save_subdir`` is matched by path *components*, not by replacing
   separators and running a substring test.
3. Link extraction stays inside the active tab pane; an empty or unreachable
   active pane must never fall back to the whole page and download another
   tab's documents.
4. The download owner decides success/failure from a machine-readable
   verification outcome; the CLI does not re-judge a successful result.
5. Console diagnostics go to stderr so the JSON protocol owns stdout.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from src import constants as C
from src.downloader import StockDownloader
from src.models import DownloadRequest

WORKTREE = Path(__file__).resolve().parents[2]
MIN_SIZE = C.MIN_FILE_SIZE


def _within(path, save_subdir, **kwargs):
    """Import the pure scope helper lazily so collection never hides a RED."""
    from src.downloader import _path_is_within_subdir

    return _path_is_within_subdir(path, save_subdir, **kwargs)


# ---------------------------------------------------------------------------
# doubles
# ---------------------------------------------------------------------------


class _Element:
    def __init__(self, text: str, href: str) -> None:
        self.text = text
        self.href = href


class _FakePage:
    """A cninfo-like SPA page: menu items, one selected, links per tab.

    ``select_menu_item`` is the real interaction: it selects the tab whose
    label matches and reports the resulting state.  ``find_active_tab_links``
    returns only the selected tab's links.  A page-wide query still sees every
    tab, which is exactly what the downloader must not rely on.
    """

    TAB_ACTIVE = "active"
    TAB_INACTIVE = "inactive"
    TAB_UNKNOWN = "unknown"
    TAB_MISSING = "missing"

    def __init__(
        self,
        tabs: dict[str, list[tuple[str, str]]],
        *,
        selected: str | None = None,
        total_pages: int = 1,
        select_state: str | None = None,
    ) -> None:
        self.tabs = {label: list(links) for label, links in tabs.items()}
        self.selected = selected or next(iter(self.tabs), None)
        self.total_pages = total_pages
        # Force a specific outcome (e.g. "inactive") to model a page whose
        # click does not actually change the selection.
        self.select_state = select_state
        self.downloaded: list[tuple[str, str]] = []
        self.navigated: list[str] = []
        self.failed_hrefs: set[str] = set()
        self.menu_clicks: list[str] = []

    # ── tab interaction ─────────────────────────────────────────────
    def select_menu_item(self, label: str) -> str:
        self.menu_clicks.append(label)
        if label not in self.tabs:
            return self.TAB_MISSING
        if self.select_state is not None:
            return self.select_state
        self.selected = label
        return self.TAB_ACTIVE

    def find_active_tab_links(self) -> list[tuple[str, str]]:
        if self.selected is None:
            return []
        return [(href, text) for text, href in self.tabs.get(self.selected, [])]

    # ── page-wide access (unscoped navigation only) ─────────────────
    def find_elements(self, _selector: str, by: str | None = None):
        return [
            _Element(text, href)
            for links in self.tabs.values()
            for text, href in links
        ]

    def get_attribute(self, element, name: str):
        return getattr(element, name, None)

    def get_text(self, element) -> str:
        return element.text

    # ── navigation / lifecycle ──────────────────────────────────────
    def navigate(self, url: str) -> bool:
        self.navigated.append(url)
        return True

    def execute_script(self, _script: str):
        return None

    def go_to_next_page(self) -> bool:
        return False

    def get_current_page_info(self) -> dict:
        return {"total_pages": self.total_pages, "current_page": 1}

    def take_screenshot(self, _path: str) -> None:
        return None

    def clear_cookies(self) -> None:
        return None

    def restart(self) -> bool:
        return True

    def close(self) -> None:
        return None

    def download_file(self, href: str, save_path: str) -> bool:
        self.downloaded.append((href, save_path))
        if href in self.failed_hrefs:
            return False
        target = Path(save_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"%PDF-" + b"x" * (MIN_SIZE + 64))
        return True


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """The downloader sleeps between SPA steps; offline tests must not."""
    import src.downloader as downloader_module

    monkeypatch.setattr(downloader_module.time, "sleep", lambda *_args: None)


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path, monkeypatch):
    """``FailedDownloadLogger`` creates ``logs/`` relative to the cwd."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _downloader(tmp_path: Path) -> StockDownloader:
    return StockDownloader(
        {
            "save_dir": str(tmp_path / "downloads"),
            "max_retries": 0,
            "headless": True,
            "skip_browser_init": True,
            "files": {"mapping_file": str(tmp_path / "mapping.json")},
        }
    )


def _request(**overrides) -> DownloadRequest:
    base = dict(
        stock_code="300470",
        stock_name="中密控股",
        org_id="9900023856",
        suffix="periodicReports",
        max_pages=1,
    )
    base.update(overrides)
    return DownloadRequest(**base)


def _write_pdf(path: Path, size: int = MIN_SIZE + 64) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-" + b"y" * size)
    return path


PERIODIC_LINK = ("中密控股：2024年年度报告", "/new/disclosure/detail?id=1")
RESEARCH_LINK = ("中密控股：投资者关系活动记录表", "/new/disclosure/detail?id=7")
PROSPECTUS_LINK = ("中密控股：招股说明书", "/new/disclosure/detail?id=9")


# ---------------------------------------------------------------------------
# 1. request-scoped empty state
# ---------------------------------------------------------------------------


class TestRequestScopedEmptyState:
    def test_upstream_confirmed_empty_is_reported_for_that_request(self, tmp_path):
        page = _FakePage({"定期报告": []})
        downloader = _downloader(tmp_path)
        downloader._browser = page

        result = downloader.download(_request(confirmed_empty=True))

        assert result.success is True
        assert result.total_files == 0
        assert result.load_state == "confirmed_empty"
        assert page.downloaded == []

    def test_second_request_does_not_inherit_the_first_confirmed_empty(self, tmp_path):
        """A different company/period on the same instance must re-observe."""
        page = _FakePage({"定期报告": []})
        downloader = _downloader(tmp_path)
        downloader._browser = page

        first = downloader.download(_request(confirmed_empty=True))
        second = downloader.download(
            _request(stock_code="301611", stock_name="珂玛科技", org_id="ORG2")
        )

        assert first.load_state == "confirmed_empty"
        # The second request carries no upstream confirmation and the page has
        # no links: that is an infrastructure outcome, never a positive empty.
        assert second.load_state != "confirmed_empty"
        assert second.success is False
        assert second.error_code == "upstream_unavailable"
        assert second.retryable is True

    def test_third_request_recovers_content_after_an_empty_request(self, tmp_path):
        page = _FakePage({"定期报告": []})
        downloader = _downloader(tmp_path)
        downloader._browser = page

        downloader.download(_request(confirmed_empty=True))
        page.tabs["定期报告"] = [PERIODIC_LINK]
        result = downloader.download(_request())

        assert result.success is True
        assert result.load_state in (None, "ready")
        assert len(result.downloaded_files) == 1

    def test_confirmed_empty_does_not_suppress_a_page_that_has_documents(
        self, tmp_path
    ):
        """An upstream empty hint never overrides observed official links."""
        page = _FakePage({"定期报告": [PERIODIC_LINK]})
        downloader = _downloader(tmp_path)
        downloader._browser = page

        result = downloader.download(_request(confirmed_empty=True))

        assert result.success is True
        assert len(result.downloaded_files) == 1


# ---------------------------------------------------------------------------
# 2. component directory match
# ---------------------------------------------------------------------------


class TestSaveSubdirComponentMatch:
    def test_posix_path_matches_by_components(self):
        path = PurePosixPath("/data/company/raw/prospectus/report.pdf")
        assert _within(path, "raw/prospectus") is True

    def test_windows_path_matches_case_insensitively(self):
        path = PureWindowsPath(r"C:\Data\Company\RAW\Prospectus\report.pdf")
        assert _within(path, "raw/prospectus") is True

    def test_windows_path_is_case_sensitive_when_asked(self):
        path = PureWindowsPath(r"C:\Data\Company\RAW\Prospectus\report.pdf")
        assert _within(path, "raw/prospectus", case_sensitive=True) is False

    def test_backslash_subdir_input_is_normalised(self):
        path = PureWindowsPath(r"C:\Data\company\raw\prospectus\report.pdf")
        assert _within(path, r"raw\prospectus") is True

    @pytest.mark.parametrize(
        "sibling",
        ["prospectus-extra", "prospectus_old", "my-prospectus"],
    )
    def test_sibling_directory_is_not_the_same_scope(self, sibling):
        path = PurePosixPath(f"/data/company/raw/{sibling}/report.pdf")
        assert _within(path, "raw/prospectus") is False

    def test_partial_component_prefix_does_not_match(self):
        path = PurePosixPath("/data/company/rawX/prospectus/report.pdf")
        assert _within(path, "raw/prospectus") is False

    def test_parent_reference_is_rejected(self):
        with pytest.raises(ValueError):
            _within(PurePosixPath("/data/company/raw/report.pdf"), "raw/../raw")

    def test_absolute_subdir_is_rejected(self):
        with pytest.raises(ValueError):
            _within(
                PurePosixPath("/data/company/raw/prospectus/report.pdf"),
                "/raw/prospectus",
            )

    def test_download_in_the_wrong_sibling_directory_is_not_a_success(self, tmp_path):
        """Behavioural: a file under ``prospectus-extra`` must not verify."""
        stray = _write_pdf(
            tmp_path / "downloads" / "中密控股" / "raw" / "prospectus-extra" / "r.pdf"
        )
        page = _FakePage({"定期报告": []})
        downloader = _downloader(tmp_path)
        downloader._browser = page
        downloader._download_pages = lambda _request: [str(stray)]

        result = downloader.download(_request(suffix=None, save_subdir="raw/prospectus"))

        assert result.success is False
        assert result.verification.ok is False
        assert {issue.code for issue in result.verification.issues} == {
            "unexpected_directory"
        }

    def test_download_in_the_declared_directory_verifies(self, tmp_path):
        good = _write_pdf(
            tmp_path / "downloads" / "中密控股" / "raw" / "prospectus" / "r.pdf"
        )
        page = _FakePage({"定期报告": []})
        downloader = _downloader(tmp_path)
        downloader._browser = page
        downloader._download_pages = lambda _request: [str(good)]

        result = downloader.download(_request(suffix=None, save_subdir="raw/prospectus"))

        assert result.verification.ok is True
        assert result.success is True


# ---------------------------------------------------------------------------
# 3. active tab scope
# ---------------------------------------------------------------------------


class TestActiveTabScope:
    def test_empty_active_tab_never_downloads_another_tab(self, tmp_path):
        page = _FakePage(
            {"定期报告": [], "最新公告": [RESEARCH_LINK, PERIODIC_LINK]},
            selected="最新公告",
        )
        downloader = _downloader(tmp_path)
        downloader._browser = page

        result = downloader.download(_request())

        assert page.downloaded == []
        assert result.downloaded_files == []
        assert result.success is False
        assert result.load_state == "infrastructure_fail"

    def test_empty_active_tab_with_upstream_confirmation_stays_empty(self, tmp_path):
        page = _FakePage(
            {"定期报告": [], "最新公告": [PERIODIC_LINK]}, selected="最新公告"
        )
        downloader = _downloader(tmp_path)
        downloader._browser = page

        result = downloader.download(_request(confirmed_empty=True))

        assert page.downloaded == []
        assert result.success is True
        assert result.load_state == "confirmed_empty"

    def test_only_the_selected_tab_is_downloaded(self, tmp_path):
        page = _FakePage(
            {
                "定期报告": [PERIODIC_LINK],
                "最新公告": [RESEARCH_LINK],
                "研究报告": [PROSPECTUS_LINK],
            },
            selected="最新公告",
        )
        downloader = _downloader(tmp_path)
        downloader._browser = page

        result = downloader.download(_request())

        assert len(page.downloaded) == 1
        assert page.downloaded[0][0].endswith("?id=1")
        assert len(result.downloaded_files) == 1

    def test_unreachable_menu_item_never_falls_back_to_the_page(self, tmp_path):
        """Markup drift must not turn into another tab's documents."""
        page = _FakePage({"最新公告": [RESEARCH_LINK]}, selected="最新公告")
        downloader = _downloader(tmp_path)
        downloader._browser = page

        result = downloader.download(_request())

        assert page.downloaded == []
        assert result.success is False
        assert result.load_state == "infrastructure_fail"

    def test_unknown_suffix_is_a_configuration_error_not_a_wrong_scope(self, tmp_path):
        page = _FakePage({"最新公告": [RESEARCH_LINK]}, selected="最新公告")
        downloader = _downloader(tmp_path)
        downloader._browser = page

        result = downloader.download(_request(suffix="periodicReport"))

        assert page.downloaded == []
        assert result.success is False
        assert any("unsupported tab suffix" in error for error in result.errors)

    def test_click_that_does_not_change_the_selection_is_refused(self, tmp_path):
        """A click landing on the default tab must not read that tab."""
        page = _FakePage(
            {"定期报告": [PERIODIC_LINK], "最新公告": [RESEARCH_LINK]},
            selected="最新公告",
            select_state=_FakePage.TAB_INACTIVE,
        )
        downloader = _downloader(tmp_path)
        downloader._browser = page

        result = downloader.download(_request())

        assert page.downloaded == []
        assert result.success is False
        assert result.load_state == "infrastructure_fail"

    def test_unscoped_navigation_may_still_use_the_whole_page(self, tmp_path):
        page = _FakePage({"最新公告": [RESEARCH_LINK]}, selected="最新公告")
        downloader = _downloader(tmp_path)
        downloader._browser = page

        result = downloader.download(_request(suffix=None))

        assert len(result.downloaded_files) == 1


# ---------------------------------------------------------------------------
# 4. verification outcome consistency
# ---------------------------------------------------------------------------


class TestVerificationOutcome:
    def test_missing_file_fails_the_owner_result(self, tmp_path):
        page = _FakePage({"定期报告": []})
        downloader = _downloader(tmp_path)
        downloader._browser = page
        downloader._download_pages = lambda _request: [
            str(tmp_path / "downloads" / "gone.pdf")
        ]

        result = downloader.download(_request(suffix=None))

        assert result.success is False
        assert result.verification.ok is False
        assert [issue.code for issue in result.verification.issues] == ["file_missing"]
        assert result.error_code == "verification_failed"
        assert result.retryable is False

    def test_zero_files_is_not_a_silent_success(self, tmp_path):
        page = _FakePage({"定期报告": []})
        downloader = _downloader(tmp_path)
        downloader._browser = page
        downloader._download_pages = lambda _request: []

        result = downloader.download(_request(suffix=None))

        assert result.success is False
        assert [issue.code for issue in result.verification.issues] == ["no_files"]

    def test_partial_download_failure_is_not_a_success(self, tmp_path):
        """One failed candidate must not hide behind the successful ones."""
        page = _FakePage({"定期报告": [PERIODIC_LINK, RESEARCH_LINK]})
        page.failed_hrefs = {C.BASE_URL + RESEARCH_LINK[1]}
        downloader = _downloader(tmp_path)
        downloader._browser = page

        result = downloader.download(_request())

        assert len(result.downloaded_files) == 1
        assert result.success is False
        assert result.verification.ok is False
        assert [issue.code for issue in result.verification.issues] == [
            "download_failed"
        ]

    def test_each_retry_attempt_starts_with_no_recorded_failures(self, tmp_path):
        """A failed attempt must not poison the attempt that recovers."""
        page = _FakePage({"定期报告": [PERIODIC_LINK]})
        downloader = _downloader(tmp_path)
        downloader._browser = page
        downloader.max_retries = 2
        from src.models import DownloadResult

        seen: list[int] = []

        def fake_internal(_request):
            seen.append(len(downloader._request_failures))
            if len(seen) < 3:
                downloader._request_failures.append(("candidate", "transient"))
                return DownloadResult(success=False, retryable=True, errors=["x"])
            return DownloadResult(success=True)

        downloader._download_internal = fake_internal
        result = downloader._download_with_retry(_request(), 0.0)

        assert seen == [0, 0, 0]
        assert result.success is True

    def test_verification_is_machine_readable_not_prose(self, tmp_path):
        page = _FakePage({"定期报告": []})
        downloader = _downloader(tmp_path)
        downloader._browser = page
        downloader._download_pages = lambda _request: []

        result = downloader.download(_request(suffix=None))

        issue = result.verification.issues[0]
        assert issue.code == "no_files"
        assert isinstance(issue.message, str) and issue.message

    def test_cli_does_not_rejudge_a_successful_owner_result(self, tmp_path, monkeypatch):
        import main as cli_main
        from src.models import DownloadResult

        class _FakeDownloader:
            def __init__(self, _config):
                pass

            def download(self, _request):
                return DownloadResult(
                    success=True,
                    downloaded_files=["a.pdf"],
                    total_files=1,
                    metadata={"verification_warnings": ["legacy prose only"]},
                )

            def cleanup(self):
                return None

        monkeypatch.setattr(cli_main, "StockDownloader", _FakeDownloader)
        monkeypatch.setattr(cli_main, "get_real_stock_name", lambda _code: "中密控股")
        runner = cli_main.UnifiedRunner(
            {"save_dir": str(tmp_path), "pages": [{"name": "定期报告"}]}
        )

        assert runner.run_single("300470") is True

    def test_cli_reports_a_failed_owner_result(self, tmp_path, monkeypatch):
        import main as cli_main
        from src.models import DownloadResult

        class _FakeDownloader:
            def __init__(self, _config):
                pass

            def download(self, _request):
                return DownloadResult(success=False, errors=["verification_failed"])

            def cleanup(self):
                return None

        monkeypatch.setattr(cli_main, "StockDownloader", _FakeDownloader)
        monkeypatch.setattr(cli_main, "get_real_stock_name", lambda _code: "中密控股")
        runner = cli_main.UnifiedRunner(
            {"save_dir": str(tmp_path), "pages": [{"name": "定期报告"}]}
        )

        assert runner.run_single("300470") is False


# ---------------------------------------------------------------------------
# 5. stdout is the protocol channel
# ---------------------------------------------------------------------------


class TestProtocolStreams:
    def test_console_logger_writes_to_stderr_in_a_fresh_process(self):
        marker = "MB-SID-STDERR-MARKER"
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                f"from src.logger import log; log.info('{marker}')",
            ],
            cwd=str(WORKTREE),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
        )

        assert completed.returncode == 0, completed.stderr
        assert completed.stdout == ""
        assert marker in completed.stderr

    def test_cli_stdout_carries_only_the_protocol_document(self, tmp_path):
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "src.company_wiki_adapter_cli",
                "discover",
                "--config",
                str(tmp_path / "config.json"),
            ],
            cwd=str(WORKTREE),
            input=json.dumps({"entity": "示例公司", "market": "CN"}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
        )

        assert completed.returncode == 1
        assert completed.stdout == ""
        # Diagnostics may precede the document; the documented contract is that
        # the failure JSON is the last line on stderr.
        payload = json.loads(completed.stderr.strip().splitlines()[-1])
        assert payload["status"] == "failed"
        assert payload["error"]["code"] == "upstream_unavailable"
        assert payload["error"]["retryable"] is False


# ---------------------------------------------------------------------------
# 6. browser host resolution (offline DNS doubles)
# ---------------------------------------------------------------------------


class _FakeChromium:
    def __init__(self, record: dict) -> None:
        self._record = record

    def launch(self, *, headless, args):
        self._record["headless"] = headless
        self._record["args"] = list(args)
        return _FakeBrowser(record=self._record)


class _FakeBrowser:
    def __init__(self, *, record: dict) -> None:
        self._record = record

    def new_context(self, **_kwargs):
        self._record["context"] = True
        return _FakeContext()

    def close(self):
        return None


class _FakeContext:
    def add_init_script(self, _script):
        return None

    def new_page(self):
        return object()

    def close(self):
        return None


class _FakePlaywright:
    def __init__(self, record: dict) -> None:
        self.chromium = _FakeChromium(record)

    def start(self):
        return self

    def stop(self):
        return None


class TestBrowserHostResolution:
    def _patch_playwright(self, monkeypatch, record: dict) -> None:
        import src.browser as browser_module

        monkeypatch.setattr(
            browser_module, "sync_playwright", lambda: _FakePlaywright(record)
        )

    def _patch_dns(self, monkeypatch, mapping: dict[str, str | None]) -> None:
        import socket

        def fake_getaddrinfo(host, *_args, **_kwargs):
            resolved = mapping.get(host)
            if resolved is None:
                raise socket.gaierror(f"unresolved: {host}")
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (resolved, 443))]

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    def test_critical_host_failure_aborts_before_launch(self, monkeypatch):
        import src.browser as browser_module

        record: dict = {}
        self._patch_playwright(monkeypatch, record)
        self._patch_dns(
            monkeypatch,
            {"www.cninfo.com.cn": "203.0.113.10", "static.cninfo.com.cn": None},
        )
        browser = browser_module.PlaywrightBrowser(headless=True)

        with pytest.raises(browser_module.BrowserError):
            browser.initialize()

        assert record == {}

    def test_optional_bare_host_failure_still_launches(self, monkeypatch):
        import src.browser as browser_module

        record: dict = {}
        self._patch_playwright(monkeypatch, record)
        self._patch_dns(
            monkeypatch,
            {
                "www.cninfo.com.cn": "203.0.113.10",
                "static.cninfo.com.cn": "203.0.113.11",
                "cninfo.com.cn": None,
            },
        )
        browser = browser_module.PlaywrightBrowser(headless=True)

        assert browser.initialize() is True

        resolver_args = [
            arg for arg in record["args"] if arg.startswith("--host-resolver-rules=")
        ]
        assert len(resolver_args) == 1
        rules = resolver_args[0].split("=", 1)[1]
        mapped_hosts = [rule.split()[1] for rule in rules.split(", ") if rule]
        assert mapped_hosts == ["www.cninfo.com.cn", "static.cninfo.com.cn"]

    def test_resolved_addresses_come_from_dns_not_hardcoded(self, monkeypatch):
        import src.browser as browser_module

        record: dict = {}
        self._patch_playwright(monkeypatch, record)
        self._patch_dns(
            monkeypatch,
            {
                "www.cninfo.com.cn": "198.51.100.7",
                "static.cninfo.com.cn": "198.51.100.8",
                "cninfo.com.cn": "198.51.100.9",
            },
        )
        browser = browser_module.PlaywrightBrowser(headless=True)

        assert browser.initialize() is True

        rules = next(
            arg.split("=", 1)[1]
            for arg in record["args"]
            if arg.startswith("--host-resolver-rules=")
        )
        assert "198.51.100.7" in rules
        assert "198.51.100.8" in rules
        assert "198.51.100.9" in rules
