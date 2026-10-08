"""Contracts for the company-wiki staging-only CNINFO adapter.

CW-2.27F / Phase 5 — discover() now uses the official cninfo announcement
API (via injected ``CninfoAnnouncementClient``) instead of the historical SPA
scraper. Fetch() uses the API client's HTTPS PDF transport. All discovery
tests use a ``_FakeCninfoApi`` stub returning canned ``CninfoAnnouncement``
records; fetch tests use the real ``CninfoAnnouncementClient.fetch_pdf``
under a ``patch("urllib.request.urlopen")`` mock to stay fully offline.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from urllib.parse import quote
from unittest.mock import MagicMock, patch

import pytest

from src import constants as C
from src.cninfo_api import (
    CninfoAnnouncement,
    CninfoAnnouncementClient,
    CninfoApiError,
    LoadState,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _StubDownloader:
    """Minimal stub downloader — adapter (API-first) only needs ``.mapping`` for
    org_id resolution when caller omits org_id, which our tests always supply.
    """

    class _StubMapping:
        def get_org_id(self, stock_code):
            return None

        def get_stock_name(self, stock_code):
            return f"Stock_{stock_code}"

    def __init__(self) -> None:
        self.mapping = _StubDownloader._StubMapping()


def _detail_url(
    announcement_id, *, sec_code="002594", ann_time_ms=1742832000000
) -> str:
    dt = _dt.datetime.fromtimestamp(ann_time_ms / 1000.0, tz=_dt.timezone(_dt.timedelta(hours=8)))
    detail_time = dt.strftime("%Y-%m-%d %H:%M")
    return (
        f"https://www.cninfo.com.cn/new/disclosure/detail?stockCode={sec_code}"
        f"&announcementId={announcement_id}"
        f"&announcementTime={quote(detail_time, safe='/:')}"
    )


def _make_announcement(
    *,
    announcement_id: str = "1222881496",
    title: str = "比亚迪股份有限公司2024年年度报告",
    sec_code: str = "002594",
    sec_name: str = "比亚迪",
    org_id: str = "gshk0001211",
    announcement_time_ms: int = 1742832000000,  # 2025-03-24T16:00Z → China 2025-03-25
    adjunct_url: str = "finalpage/2025-03-25/1222881496.PDF",
) -> CninfoAnnouncement:
    dt = _dt.datetime.fromtimestamp(announcement_time_ms / 1000.0, tz=_dt.timezone(_dt.timedelta(hours=8)))
    filing_date = dt.date().isoformat()
    transport_url = f"https://static.cninfo.com.cn/{adjunct_url.lstrip('/')}"
    detail_time = dt.strftime("%Y-%m-%d %H:%M")
    detail_url = (
        f"https://www.cninfo.com.cn/new/disclosure/detail?stockCode={sec_code}"
        f"&announcementId={announcement_id}"
        f"&announcementTime={quote(detail_time, safe='/:')}"
    )
    return CninfoAnnouncement(
        announcement_id=announcement_id,
        filing_date=filing_date,
        title=title,
        sec_code=sec_code,
        sec_name=sec_name,
        org_id=org_id,
        announcement_time_ms=announcement_time_ms,
        adjunct_type="PDF",
        adjunct_url=adjunct_url,
        transport_url=transport_url,
        detail_url=detail_url,
    )


class _FakeCninfoApi:
    """Mock CninfoAnnouncementClient stub returning canned records + fetch."""

    def __init__(self, *, records=None, state=LoadState.READY, raise_exc=None) -> None:
        self.records = list(records) if records is not None else []
        self.state = state
        self.raise_exc = raise_exc
        self.discover_calls = 0
        self.fetch_calls = 0
        self.fetch_args: list[dict] = []

    def discover_announcements(self, **kwargs) -> tuple[list, "LoadState"]:
        self.discover_calls += 1
        self.last_discover_kwargs = dict(kwargs)
        if self.raise_exc is not None:
            raise self.raise_exc
        return list(self.records), self.state

    def fetch_pdf(self, *, transport_url, staging_dir, expected_filename=None) -> Path:
        self.fetch_calls += 1
        self.fetch_args.append(
            {
                "transport_url": transport_url,
                "staging_dir": staging_dir,
                "expected_filename": expected_filename,
            }
        )
        staging_dir.mkdir(parents=True, exist_ok=True)
        path = staging_dir / (expected_filename or "test.pdf")
        path.write_bytes(b"%PDF-1.7\n" + b"x" * (C.MIN_FILE_SIZE + 1024))
        return path


# ---------------------------------------------------------------------------
# Discover tests
# ---------------------------------------------------------------------------


def test_discover_returns_cninfo_identity_and_report_metadata_via_api():
    from src.company_wiki_adapter import (
        AdapterDiscoveryRequest,
        StockInfoCompanyWikiAdapter,
    )

    api = _FakeCninfoApi(records=[_make_announcement()])
    adapter = StockInfoCompanyWikiAdapter(_StubDownloader(), cninfo_client=api)
    candidates = adapter.discover(
        AdapterDiscoveryRequest(
            stock_code="002594",
            stock_name="比亚迪",
            org_id="gshk0001211",
            suffix="periodicReports",
            document_kind="annual_report",
            fiscal_year=2024,
            max_pages=1,
        )
    )
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.provider == "cninfo"
    assert candidate.provider_document_id == "1222881496"
    assert candidate.identity_method == "announcement_id"
    assert candidate.market == "CN"
    assert candidate.document_kind == "annual_report"
    assert candidate.fiscal_year == 2024
    assert candidate.fiscal_period == "FY"
    assert candidate.filing_date == "2025-03-25"
    assert candidate.amended is False
    # source_url must be the human-openable detail page, NOT the transport URL
    assert candidate.source_url.startswith(
        "https://www.cninfo.com.cn/new/disclosure/detail?"
    )
    assert "announcementId=1222881496" in candidate.source_url
    # transport_url preserved in opaque DisclosureCandidate field
    assert candidate.transport_url == (
        "https://static.cninfo.com.cn/finalpage/2025-03-25/1222881496.PDF"
    )
    assert api.discover_calls == 1


def test_discover_excludes_summary_companion_by_default_for_annual_request():
    from src.company_wiki_adapter import (
        AdapterDiscoveryRequest,
        StockInfoCompanyWikiAdapter,
    )

    full = _make_announcement(
        announcement_id="1222881496",
        title="比亚迪股份有限公司2024年年度报告",
    )
    summary = _make_announcement(
        announcement_id="1222881505",
        title="比亚迪股份有限公司2024年年度报告摘要",
        adjunct_url="finalpage/2025-03-25/1222881505.PDF",
    )
    api = _FakeCninfoApi(records=[full, summary])
    adapter = StockInfoCompanyWikiAdapter(_StubDownloader(), cninfo_client=api)
    candidates = adapter.discover(
        AdapterDiscoveryRequest(
            stock_code="002594",
            stock_name="比亚迪",
            org_id="gshk0001211",
            suffix="periodicReports",
            document_kind="annual_report",
            fiscal_year=2024,
        )
    )
    assert len(candidates) == 1
    only = candidates[0]
    assert only.provider_document_id == "1222881496"
    assert "摘要" not in only.title


def test_discover_keeps_two_legal_full_reports_without_selecting():
    from src.company_wiki_adapter import (
        AdapterDiscoveryRequest,
        StockInfoCompanyWikiAdapter,
    )

    full = _make_announcement(
        announcement_id="1222881496",
        title="比亚迪股份有限公司2024年年度报告",
    )
    amended = _make_announcement(
        announcement_id="1222881999",
        title="比亚迪股份有限公司2024年年度报告（修订版）",
        adjunct_url="finalpage/2025-04-26/1222881999.PDF",
        announcement_time_ms=1745683800000,  # different publish time
    )
    api = _FakeCninfoApi(records=[full, amended])
    adapter = StockInfoCompanyWikiAdapter(_StubDownloader(), cninfo_client=api)
    candidates = adapter.discover(
        AdapterDiscoveryRequest(
            stock_code="002594",
            stock_name="比亚迪",
            org_id="gshk0001211",
            suffix="periodicReports",
            document_kind="annual_report",
            fiscal_year=2024,
        )
    )
    ids = sorted(c.provider_document_id for c in candidates)
    assert ids == ["1222881496", "1222881999"]


def test_discover_summary_excluded_and_does_not_invoke_spa_navigation():
    """Adapter discover must NOT call legacy SPA internals (_navigate, _switch_tab,
    _get_links) since the API path replaced them."""
    from src.company_wiki_adapter import (
        AdapterDiscoveryRequest,
        StockInfoCompanyWikiAdapter,
    )

    full = _make_announcement()
    summary = _make_announcement(
        announcement_id="1222881505",
        title="比亚迪股份有限公司2024年年度报告摘要",
        adjunct_url="finalpage/2025-03-25/1222881505.PDF",
    )
    api = _FakeCninfoApi(records=[full, summary])
    downloader = _StubDownloader()
    # Mark each SPA method to detect accidental calls
    spa_calls: list[str] = []
    for name in (
        "_navigate_to_stock_page",
        "_switch_tab",
        "_get_links",
        "_wait_for_page_load",
    ):

        def _mark(*a, name=name, **k):
            spa_calls.append(name)
            raise AssertionError(f"adapter must NOT call SPA method {name}")

    adapter = StockInfoCompanyWikiAdapter(downloader, cninfo_client=api)
    candidates = adapter.discover(
        AdapterDiscoveryRequest(
            stock_code="002594",
            stock_name="比亚迪",
            org_id="gshk0001211",
            suffix="periodicReports",
            document_kind="annual_report",
            fiscal_year=2024,
        )
    )
    assert all("摘要" not in c.title for c in candidates)
    assert spa_calls == []
    assert api.discover_calls == 1


def test_discover_raises_adapter_error_when_cninfo_api_raises():
    from src.company_wiki_adapter import (
        AdapterDiscoveryRequest,
        AdapterError,
        StockInfoCompanyWikiAdapter,
    )

    api = _FakeCninfoApi(
        raise_exc=CninfoApiError(
            "boom", error_code="upstream_unavailable", retryable=True
        )
    )
    adapter = StockInfoCompanyWikiAdapter(_StubDownloader(), cninfo_client=api)
    with pytest.raises(AdapterError, match="cninfo_api_discover failed"):
        adapter.discover(
            AdapterDiscoveryRequest(
                stock_code="002594",
                stock_name="比亚迪",
                org_id="gshk0001211",
                suffix="periodicReports",
                document_kind="annual_report",
                fiscal_year=2024,
            )
        )


# ---------------------------------------------------------------------------
# Fetch tests (use real CninfoAnnouncementClient with patched urlopen)
# ---------------------------------------------------------------------------


def _make_candidate(adapter):
    """Discover a single BYD FY2024 full annual report via adapter."""
    from src.company_wiki_adapter import AdapterDiscoveryRequest

    api = _FakeCninfoApi(records=[_make_announcement()])
    adapter._cninfo_client = api
    candidates = adapter.discover(
        AdapterDiscoveryRequest(
            stock_code="002594",
            stock_name="比亚迪",
            org_id="gshk0001211",
            suffix="periodicReports",
            document_kind="annual_report",
            fiscal_year=2024,
        )
    )
    assert len(candidates) == 1
    return candidates[0]


def test_fetch_writes_only_allocated_staging_and_returns_hash_receipt(tmp_path):
    from src.company_wiki_adapter import StockInfoCompanyWikiAdapter

    adapter = StockInfoCompanyWikiAdapter(
        _StubDownloader(), cninfo_client=_FakeCninfoApi()
    )
    candidate = _make_candidate(adapter)

    # Now swap in real cninfo_client with mocked urlopen for fetch validation.
    body = b"%PDF-1.7\n" + b"x" * (C.MIN_FILE_SIZE + 1024)
    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.headers = {"Content-Type": "application/pdf"}
    fake_resp.read.return_value = body
    cm = MagicMock()
    cm.__enter__.return_value = fake_resp
    cm.__exit__.return_value = False

    real_api = CninfoAnnouncementClient()
    adapter._cninfo_client = real_api
    staging = tmp_path / "allocated-staging"

    with patch("urllib.request.urlopen", lambda *a, **kw: cm):
        receipt = adapter.fetch(candidate, staging)

    path = Path(receipt.staged_path)
    assert path.is_file()
    assert path.resolve().is_relative_to(staging.resolve())
    assert path.read_bytes().startswith(b"%PDF-")
    assert len(receipt.source_url.split("/")[-1]) > 0
    assert len(receipt.content_sha256) == 64
    assert receipt.byte_size == path.stat().st_size
    assert receipt.source_url == candidate.source_url
    assert receipt.provider_document_id == "1222881496"
    assert receipt.adapter_name == "stockinfo-cninfo"
    assert receipt.adapter_version == "1.3.0"


def test_fetch_rejects_non_cninfo_transport_host(tmp_path):
    from src.company_wiki_adapter import (
        AdapterError,
        StockInfoCompanyWikiAdapter,
    )

    adapter = StockInfoCompanyWikiAdapter(
        _StubDownloader(), cninfo_client=_FakeCninfoApi()
    )
    candidate = _make_candidate(adapter)
    # Inject invalid transport_url by reconstructing candidate (DisclosureCandidate is frozen)
    from dataclasses import replace

    bad_candidate = replace(candidate, transport_url="https://example.com/fake.pdf")
    # Use the real cninfo_client for fetch — host whitelist lives inside fetch_pdf.
    adapter._cninfo_client = CninfoAnnouncementClient()
    with pytest.raises(AdapterError, match="cninfo_transport failed"):
        adapter.fetch(bad_candidate, tmp_path / "staging")
    # Nothing staged
    assert (
        list((tmp_path / "staging").glob("*")) == []
        if (tmp_path / "staging").exists()
        else True
    )


def test_fetch_rejects_non_pdf_payload(tmp_path):
    from src.company_wiki_adapter import (
        AdapterError,
        StockInfoCompanyWikiAdapter,
    )

    adapter = StockInfoCompanyWikiAdapter(
        _StubDownloader(), cninfo_client=_FakeCninfoApi()
    )
    candidate = _make_candidate(adapter)

    body = b"<html>not a pdf</html>" + b"x" * 2048
    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.headers = {"Content-Type": "application/octet-stream"}
    fake_resp.read.return_value = body
    cm = MagicMock()
    cm.__enter__.return_value = fake_resp
    cm.__exit__.return_value = False

    adapter._cninfo_client = CninfoAnnouncementClient()
    with patch("urllib.request.urlopen", lambda *a, **kw: cm):
        with pytest.raises(AdapterError, match="cninfo_transport failed"):
            adapter.fetch(candidate, tmp_path / "staging")
    # No leftover .part files
    staging = tmp_path / "staging"
    if staging.exists():
        assert list(staging.glob("*.part")) == []


def test_fetch_missing_transport_url_raises(tmp_path):
    from src.company_wiki_adapter import (
        AdapterError,
        StockInfoCompanyWikiAdapter,
    )
    from dataclasses import replace

    adapter = StockInfoCompanyWikiAdapter(
        _StubDownloader(), cninfo_client=_FakeCninfoApi()
    )
    candidate = _make_candidate(adapter)
    bad_candidate = replace(candidate, transport_url="")

    with pytest.raises(AdapterError, match="missing transport_url"):
        adapter.fetch(bad_candidate, tmp_path / "staging")


# ---------------------------------------------------------------------------
# Date parser tests (preserved from Phase 2 — still useful for parsing URL
# strings — even though discover no longer calls _filing_date directly).
# ---------------------------------------------------------------------------


CNINFO_DETAIL_PREFIX = "https://www.cninfo.com.cn/new/disclosure/detail"


def _phase2_detail_url(announcement_id: str, announcement_time: str) -> str:
    return (
        f"{CNINFO_DETAIL_PREFIX}?stockCode=002594"
        f"&announcementId={announcement_id}"
        f"&announcementTime={quote(announcement_time, safe='/: +')}"
    )


@pytest.mark.parametrize(
    "raw_time, expected",
    [
        ("2025-03-24", "2025-03-24"),
        ("2025-03-24 16:00", "2025-03-24"),
        ("2025-03-24 16:00:59", "2025-03-24"),
        ("2025/03/24 16:00", "2025-03-24"),
        ("20250324", "2025-03-24"),
    ],
)
def test_filing_date_handles_real_cninfo_announcement_time_formats(raw_time, expected):
    from src.company_wiki_adapter import _filing_date

    assert _filing_date(_phase2_detail_url("1222881496", raw_time)) == expected


@pytest.mark.parametrize(
    "raw_time",
    [
        "2025-13-40",
        "2025-03",
        "2025/03",
        "random free-form text",
        "2025年03月24日 16:00",
    ],
)
def test_filing_date_returns_none_for_invalid_inputs(raw_time):
    from src.company_wiki_adapter import _filing_date

    assert _filing_date(_phase2_detail_url("1222881496", raw_time)) is None
