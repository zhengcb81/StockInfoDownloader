"""G4-SID-LATEST — as-of latest discovery contract (RED → GREEN).

Five RED clusters, all offline:

1. request interpretation — ``mode`` / ``as_of_date`` / ``fiscal_period`` /
   ``form_type`` on ``AdapterDiscoveryRequest`` and validation *before* the
   provider is constructed;
2. date window — one ``seDate`` of ``as_of.year-2-01-01 ~ as_of`` for latest,
   unchanged ``{fy}-01-01~{fy+1}-12-31`` for exact;
3. metadata filtering — cutoff, security, kind, period, title-derived year,
   year hint that must not filter, distinct ids, conflicting duplicate ids;
4. bounded completeness — raw-total-driven pagination, ``discovery_incomplete``
   when the 5-page cap cannot prove coverage, ``bounded_discovery_empty`` when
   a fully covered window has no valid candidate, one shared budget;
5. typed errors — ``AdapterError.code`` / ``.retryable`` reach the CLI JSON.

HTTP is replaced only at ``urllib.request.urlopen``; the real
``CninfoAnnouncementClient`` parses the responses.
"""

from __future__ import annotations

import datetime as _dt
import io
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote

import pytest

from src.cninfo_api import CninfoAnnouncement, CninfoAnnouncementClient, CninfoApiError
from src.transport_states import LoadState

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "g4_latest"
SEC = "600000"
ORG = "gshk0001211"
NAME = "示例公司"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _fixture(label: str) -> Any:
    return json.loads((_FIXTURES / f"{label}.json").read_text(encoding="utf-8"))


def _announce(
    *,
    announcement_id: str,
    title: str,
    ms: int,
    sec_code: str = SEC,
    org_id: str = ORG,
    adjunct_url: str | None = None,
) -> CninfoAnnouncement:
    dt = _dt.datetime.fromtimestamp(ms / 1000.0, tz=_dt.timezone(_dt.timedelta(hours=8)))
    filing_date = dt.date().isoformat()
    if adjunct_url is None:
        adjunct_url = f"finalpage/{filing_date}/{announcement_id}.PDF"
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
        sec_name=NAME,
        org_id=org_id,
        announcement_time_ms=ms,
        adjunct_type="PDF",
        adjunct_url=adjunct_url,
        transport_url=f"https://static.cninfo.com.cn/{adjunct_url.lstrip('/')}",
        detail_url=detail_url,
    )


class _Response:
    def __init__(self, body: bytes, content_type: str = "application/json") -> None:
        self.body = body
        self.offset = 0
        self.status = 200
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
        }
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        if size < 0:
            chunk = self.body[self.offset :]
        else:
            chunk = self.body[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


class _PageTransport:
    """Replaces only the lowest HTTP transport with fixture-backed responses."""

    def __init__(self, *, label: str | None = None, pages: dict | None = None) -> None:
        resolved: Any = pages
        if resolved is None:
            assert label is not None, "label or pages is required"
            resolved = _fixture(label)["pages"]
        self.pages = {str(key): value for key, value in resolved.items()}
        self.requests: list[dict[str, list[str]]] = []
        self.responses: list[_Response] = []

    def __call__(self, request, *args, **kwargs) -> _Response:
        params = parse_qs((request.data or b"").decode("utf-8"), keep_blank_values=True)
        self.requests.append(params)
        page_num = params.get("pageNum", ["1"])[0]
        if page_num not in self.pages:
            raise AssertionError(
                f"provider requested page {page_num} outside fixture pages "
                f"{sorted(self.pages)}"
            )
        response = _Response(json.dumps(self.pages[page_num]).encode("utf-8"))
        self.responses.append(response)
        return response

    @property
    def body_bytes(self) -> int:
        return sum(len(response.body) for response in self.responses)


class _FakeClient:
    """Stands in for ``CninfoAnnouncementClient`` at the adapter seam only."""

    def __init__(self, records=(), *, raise_exc: Exception | None = None) -> None:
        self.records = list(records)
        self.raise_exc = raise_exc
        self.calls: list[dict] = []

    def discover_announcements(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_exc is not None:
            raise self.raise_exc
        return list(self.records), LoadState.READY


class _StubDownloader:
    class _Mapping:
        def get_org_id(self, _stock_code):
            return None

        def get_stock_name(self, stock_code):
            return f"Stock_{stock_code}"

    def __init__(self) -> None:
        self.mapping = _StubDownloader._Mapping()


def _adapter(client) -> Any:
    from src.company_wiki_adapter import StockInfoCompanyWikiAdapter

    return StockInfoCompanyWikiAdapter(_StubDownloader(), cninfo_client=client)


def _request(**overrides):
    from src.company_wiki_adapter import AdapterDiscoveryRequest

    base: dict[str, Any] = dict(
        stock_code=SEC,
        stock_name=NAME,
        document_kind="annual_report",
        fiscal_year=None,
        org_id=ORG,
        suffix="periodicReports",
        mode="latest_as_of",
        as_of_date="2026-06-01",
    )
    base.update(overrides)
    return AdapterDiscoveryRequest(**base)


def _budget(byte_limit: int, seconds: float = 10.0):
    from src.acquisition_budget import ProviderAcquisitionBudget

    return ProviderAcquisitionBudget(
        max_response_bytes=byte_limit,
        timeout_seconds=seconds,
        max_cost_usd="0",
    )


def _cli_invoke(monkeypatch, payload, *, argv=("discover",)):
    import src.company_wiki_adapter_cli as cli

    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.setattr(cli.sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(cli.sys, "stdout", stdout)
    monkeypatch.setattr(cli.sys, "stderr", stderr)
    code = cli.main(list(argv))
    return code, stdout.getvalue(), stderr.getvalue()


def _latest_payload(**overrides):
    value = {
        "entity": NAME,
        "market": "CN",
        "security_id": SEC,
        "document_kind": "annual_report",
        "mode": "latest_as_of",
        "fiscal_year": None,
        "fiscal_period": None,
        "form_type": None,
        "as_of_date": "2026-06-01",
        "acquisition_budget": {
            "schema_version": "1.0",
            "max_response_bytes": 1048576,
            "timeout_seconds": 20,
            "max_cost_usd": "0",
        },
    }
    value.update(overrides)
    return value


# ---------------------------------------------------------------------------
# 1. request interpretation
# ---------------------------------------------------------------------------


def test_latest_request_accepts_null_fiscal_year():
    request = _request()
    assert request.mode == "latest_as_of"
    assert request.fiscal_year is None
    assert request.as_of_date == "2026-06-01"


def test_latest_request_keeps_positional_exact_shape():
    from src.company_wiki_adapter import AdapterDiscoveryRequest

    request = AdapterDiscoveryRequest("600000", NAME, "annual_report", 2024)
    assert request.mode == "exact"
    assert request.fiscal_year == 2024


def test_legacy_request_without_mode_is_exact():
    from src.company_wiki_adapter import AdapterDiscoveryRequest

    request = AdapterDiscoveryRequest(
        stock_code=SEC,
        stock_name=NAME,
        document_kind="annual_report",
        fiscal_year=2025,
        mode=None,
    )
    assert request.mode == "exact"


def test_exact_mode_still_rejects_non_integer_fiscal_year():
    from src.company_wiki_adapter import AdapterDiscoveryRequest

    with pytest.raises(TypeError):
        AdapterDiscoveryRequest(
            stock_code=SEC,
            stock_name=NAME,
            document_kind="annual_report",
            fiscal_year=True,
        )


def test_exact_mode_still_requires_fiscal_year():
    from src.company_wiki_adapter import AdapterDiscoveryRequest

    with pytest.raises((TypeError, ValueError)):
        AdapterDiscoveryRequest(
            stock_code=SEC,
            stock_name=NAME,
            document_kind="annual_report",
            fiscal_year=None,
        )


def test_unknown_mode_is_rejected_never_silently_exact():
    from src.company_wiki_adapter import AdapterDiscoveryRequest

    with pytest.raises(ValueError, match="mode"):
        AdapterDiscoveryRequest(
            stock_code=SEC,
            stock_name=NAME,
            document_kind="annual_report",
            fiscal_year=2025,
            mode="approximate",
        )


def test_latest_requires_as_of_date():
    with pytest.raises(ValueError, match="as_of_date"):
        _request(as_of_date=None)


def test_latest_rejects_non_iso_as_of_date():
    for bad in ("2026/06/01", "20260601", "not-a-date", ""):
        with pytest.raises(ValueError, match="as_of_date"):
            _request(as_of_date=bad)


def test_latest_rejects_unsupported_document_kind():
    with pytest.raises(ValueError, match="document_kind"):
        _request(document_kind="earnings_transcript")


def test_latest_accepts_supported_document_kinds():
    for kind, period in (
        ("annual_report", "FY"),
        ("semi_annual_report", "H1"),
        ("quarterly_report", "Q3"),
    ):
        request = _request(document_kind=kind, fiscal_period=period)
        assert request.document_kind == kind


def test_period_hint_is_normalized_for_comparison():
    assert (
        _request(document_kind="quarterly_report", fiscal_period="q3").fiscal_period
        == "Q3"
    )
    assert _request(form_type="Annual_Report").form_type == "annual_report"


def test_cli_rejects_bad_latest_request_before_building_provider(monkeypatch):
    import src.company_wiki_adapter_cli as cli

    monkeypatch.setattr(
        cli, "_build_adapter", lambda _config: pytest.fail("provider must not be built")
    )
    code, stdout, stderr = _cli_invoke(
        monkeypatch,
        {
            "entity": NAME,
            "security_id": SEC,
            "document_kind": "annual_report",
            "mode": "latest_as_of",
            "fiscal_year": None,
            "as_of_date": None,
        },
    )
    assert code == 1
    assert stdout == ""
    error = json.loads(stderr)["error"]
    assert error["retryable"] is False
    assert "as_of_date" in error["message"]


def test_cli_rejects_unknown_mode_before_building_provider(monkeypatch):
    import src.company_wiki_adapter_cli as cli

    monkeypatch.setattr(
        cli, "_build_adapter", lambda _config: pytest.fail("provider must not be built")
    )
    code, _stdout, stderr = _cli_invoke(
        monkeypatch,
        {
            "entity": NAME,
            "security_id": SEC,
            "document_kind": "annual_report",
            "mode": "whatever",
            "fiscal_year": 2025,
            "as_of_date": "2026-06-01",
        },
    )
    assert code == 1
    assert json.loads(stderr)["error"]["retryable"] is False


def test_cli_rejects_exact_request_without_integer_year_before_provider(monkeypatch):
    import src.company_wiki_adapter_cli as cli

    monkeypatch.setattr(
        cli, "_build_adapter", lambda _config: pytest.fail("provider must not be built")
    )
    code, _stdout, stderr = _cli_invoke(
        monkeypatch,
        {"entity": NAME, "security_id": SEC, "document_kind": "annual_report"},
    )
    assert code == 1
    assert json.loads(stderr)["error"]["type"] in ("ValueError", "TypeError")


def test_cli_latest_null_year_reaches_adapter_with_latest_request(monkeypatch):
    import src.company_wiki_adapter_cli as cli

    seen = {}

    class _Capture:
        name = "stockinfo-cninfo"
        version = "1.3.0"

        def __init__(self):
            from types import SimpleNamespace

            self.downloader = SimpleNamespace(cleanup=lambda: None)

        def discover(self, request, *, acquisition_budget=None):
            seen["request"] = request
            return ()

    monkeypatch.setattr(cli, "_build_adapter", lambda _config: _Capture())
    code, stdout, stderr = _cli_invoke(monkeypatch, _latest_payload())
    assert code == 0, stderr
    request = seen["request"]
    assert request.mode == "latest_as_of"
    assert request.fiscal_year is None
    assert request.as_of_date == "2026-06-01"
    assert json.loads(stdout)["acquisition_usage"]["schema_version"] == "1.0"


# ---------------------------------------------------------------------------
# 2. date window
# ---------------------------------------------------------------------------


def test_latest_window_covers_three_natural_years_ending_at_as_of(monkeypatch):
    transport = _PageTransport(label="annual_cutover")
    monkeypatch.setattr("urllib.request.urlopen", transport)

    records, state = CninfoAnnouncementClient().discover_announcements(
        stock_code=SEC,
        org_id=ORG,
        document_kind="annual_report",
        fiscal_year=None,
        max_pages=5,
        as_of_date="2026-06-01",
    )

    assert transport.requests[0]["seDate"] == ["2024-01-01~2026-06-01"]
    assert transport.requests[0]["stock"] == [f"{SEC},{ORG}"]
    assert state == LoadState.READY
    assert len(records) == 2


def test_latest_window_tracks_as_of_date_rather_than_local_today(monkeypatch):
    transport = _PageTransport(label="annual_cutover")
    monkeypatch.setattr("urllib.request.urlopen", transport)
    CninfoAnnouncementClient().discover_announcements(
        stock_code=SEC,
        org_id=ORG,
        document_kind="annual_report",
        fiscal_year=None,
        max_pages=1,
        as_of_date="2021-05-09",
    )
    assert transport.requests[0]["seDate"] == ["2019-01-01~2021-05-09"]


def test_exact_window_is_unchanged(monkeypatch):
    transport = _PageTransport(label="exact_legacy_year")
    monkeypatch.setattr("urllib.request.urlopen", transport)

    records, _state = CninfoAnnouncementClient().discover_announcements(
        stock_code=SEC,
        org_id=ORG,
        document_kind="annual_report",
        fiscal_year=2024,
        max_pages=5,
    )

    assert transport.requests[0]["seDate"] == ["2024-01-01~2025-12-31"]
    assert [record.announcement_id for record in records] == ["900006001"]


def test_request_body_for_exact_still_matches_captured_params():
    import urllib.parse

    from src.cninfo_api import CninfoAnnouncementClient

    fixture = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "cninfo"
            / "byd_fy2024_announcement.json"
        ).read_text(encoding="utf-8")
    )
    body = CninfoAnnouncementClient()._build_request_body(
        stock_code="002594",
        org_id="gshk0001211",
        document_kind="annual_report",
        fiscal_year=2024,
        page_num=1,
        page_size=30,
    )
    decoded = {
        key: value[0]
        for key, value in urllib.parse.parse_qs(
            body.decode("utf-8"), keep_blank_values=True
        ).items()
    }
    for key, expected in fixture["__provenance__"]["request_params"].items():
        assert decoded.get(key) == expected


# ---------------------------------------------------------------------------
# 3. metadata filtering (adapter seam)
# ---------------------------------------------------------------------------


def test_latest_drops_announcement_published_after_cutoff():
    client = _FakeClient(
        records=[
            _announce(
                announcement_id="900001001",
                title="示例公司2024年年度报告",
                ms=1742472000000,
            ),
            _announce(
                announcement_id="900001002",
                title="示例公司2025年年度报告",
                ms=1774440000000,
            ),
        ]
    )
    candidates = _adapter(client).discover(_request(as_of_date="2026-02-01"))
    assert [c.provider_document_id for c in candidates] == ["900001001"]
    assert candidates[0].fiscal_year == 2024


def test_latest_year_hint_does_not_filter_older_visible_year():
    client = _FakeClient(
        records=[
            _announce(
                announcement_id="900001001",
                title="示例公司2024年年度报告",
                ms=1742472000000,
            )
        ]
    )
    candidates = _adapter(client).discover(
        _request(as_of_date="2026-02-01", fiscal_year=2025)
    )
    assert [c.fiscal_year for c in candidates] == [2024]


def test_latest_year_comes_from_title_not_from_as_of_or_request():
    client = _FakeClient(
        records=[
            _announce(
                announcement_id="900001001",
                title="示例公司2024年年度报告",
                ms=1742472000000,
            )
        ]
    )
    candidates = _adapter(client).discover(
        _request(as_of_date="2026-06-01", fiscal_year=2026)
    )
    assert [c.fiscal_year for c in candidates] == [2024]
    assert candidates[0].fiscal_year != 2026


def test_latest_keeps_both_visible_semi_annual_reports():
    client = _FakeClient(
        records=[
            _announce(
                announcement_id="900002001",
                title="示例公司2025年半年度报告",
                ms=1756382400000,
            ),
            _announce(
                announcement_id="900002002",
                title="示例公司2026年半年度报告",
                ms=1788091200000,
            ),
        ]
    )
    candidates = _adapter(client).discover(
        _request(document_kind="semi_annual_report", as_of_date="2026-09-01")
    )
    assert sorted(c.fiscal_year for c in candidates) == [2025, 2026]
    assert {c.fiscal_period for c in candidates} == {"H1"}
    assert {c.document_kind for c in candidates} == {"semi_annual_report"}


def test_latest_quarterly_keeps_visible_q3_and_q1_without_fabricating_q2():
    client = _FakeClient(
        records=[
            _announce(
                announcement_id="900003001",
                title="示例公司2025年第三季度报告",
                ms=1761825600000,
            ),
            _announce(
                announcement_id="900003002",
                title="示例公司2026年第一季度报告",
                ms=1777118400000,
            ),
            _announce(
                announcement_id="900003003",
                title="示例公司2026年第三季度报告",
                ms=1793188800000,
            ),
        ]
    )
    candidates = _adapter(client).discover(
        _request(document_kind="quarterly_report", as_of_date="2026-06-01")
    )
    assert sorted((c.fiscal_year, c.fiscal_period) for c in candidates) == [
        (2025, "Q3"),
        (2026, "Q1"),
    ]
    assert "Q2" not in {c.fiscal_period for c in candidates}


def test_latest_honours_explicit_period_hint():
    client = _FakeClient(
        records=[
            _announce(
                announcement_id="900003001",
                title="示例公司2025年第三季度报告",
                ms=1761825600000,
            ),
            _announce(
                announcement_id="900003002",
                title="示例公司2026年第一季度报告",
                ms=1777118400000,
            ),
        ]
    )
    candidates = _adapter(client).discover(
        _request(
            document_kind="quarterly_report",
            as_of_date="2026-06-01",
            fiscal_period="Q1",
        )
    )
    assert [c.fiscal_period for c in candidates] == ["Q1"]


def test_latest_drops_mismatched_security():
    from src.company_wiki_adapter import AdapterError

    client = _FakeClient(
        records=[
            _announce(
                announcement_id="900009001",
                title="示例公司2024年年度报告",
                ms=1742472000000,
                sec_code="000001",
            )
        ]
    )
    with pytest.raises(AdapterError) as exc_info:
        _adapter(client).discover(_request())
    assert exc_info.value.code == "bounded_discovery_empty"


def test_latest_drops_record_without_transport_target():
    from src.company_wiki_adapter import AdapterError

    client = _FakeClient(
        records=[
            _announce(
                announcement_id="900009002",
                title="示例公司2024年年度报告",
                ms=1742472000000,
                adjunct_url="",
            )
        ]
    )
    with pytest.raises(AdapterError) as exc_info:
        _adapter(client).discover(_request())
    assert exc_info.value.code == "bounded_discovery_empty"


def test_latest_drops_empty_title_record():
    from src.company_wiki_adapter import AdapterError

    client = _FakeClient(
        records=[_announce(announcement_id="900009003", title="   ", ms=1742472000000)]
    )
    with pytest.raises(AdapterError) as exc_info:
        _adapter(client).discover(_request())
    assert exc_info.value.code == "bounded_discovery_empty"


def test_latest_keeps_distinct_announcement_ids_for_same_period():
    client = _FakeClient(
        records=[
            _announce(
                announcement_id="900001001",
                title="示例公司2024年年度报告",
                ms=1742472000000,
            ),
            _announce(
                announcement_id="900001999",
                title="示例公司2024年年度报告（修订版）",
                ms=1745668800000,
            ),
        ]
    )
    candidates = _adapter(client).discover(_request())
    assert [c.provider_document_id for c in candidates] == ["900001001", "900001999"]
    assert candidates[1].amended is True


def test_conflicting_duplicate_announcement_id_fails_instead_of_overwriting():
    client = _FakeClient(
        records=[
            _announce(
                announcement_id="900001001",
                title="示例公司2024年年度报告",
                ms=1742472000000,
            ),
            _announce(
                announcement_id="900001001",
                title="示例公司2024年年度报告（修订版）",
                ms=1745668800000,
            ),
        ]
    )
    from src.company_wiki_adapter import AdapterError

    with pytest.raises(AdapterError, match="900001001"):
        _adapter(client).discover(_request())


def test_identical_duplicate_announcement_id_is_deduplicated():
    record = _announce(
        announcement_id="900001001",
        title="示例公司2024年年度报告",
        ms=1742472000000,
    )
    client = _FakeClient(records=[record, record])
    candidates = _adapter(client).discover(_request())
    assert [c.provider_document_id for c in candidates] == ["900001001"]


def test_latest_cutoff_uses_china_filing_date_at_day_boundary():
    kept = _announce(
        announcement_id="900009010",
        title="示例公司2024年年度报告",
        ms=1780329599000,  # China 2026-06-01T23:59:59+08:00
    )
    dropped = _announce(
        announcement_id="900009011",
        title="示例公司2024年年度报告（补充）",
        ms=1780329600000,  # China 2026-06-02T00:00:00+08:00
    )
    client = _FakeClient(records=[kept, dropped])
    candidates = _adapter(client).discover(_request(as_of_date="2026-06-01"))
    assert [c.provider_document_id for c in candidates] == ["900009010"]


def test_announcement_time_uses_china_disclosure_date():
    client = CninfoAnnouncementClient()
    raw = {
        "announcementId": "900009012",
        "announcementTime": 1780273800000,  # 2026-06-01T00:30:00Z
        "announcementTitle": "示例公司2024年年度报告",
        "adjunctUrl": "finalpage/2026-06-01/900009012.PDF",
    }
    assert client._parse_announcement(raw, stock_code=SEC).filing_date == "2026-06-01"


def test_exact_mode_keeps_year_filter_and_returns_empty_list_for_other_year():
    client = _FakeClient(
        records=[
            _announce(
                announcement_id="900001001",
                title="示例公司2024年年度报告",
                ms=1742472000000,
            )
        ]
    )
    from src.company_wiki_adapter import AdapterDiscoveryRequest

    request = AdapterDiscoveryRequest(
        stock_code=SEC,
        stock_name=NAME,
        org_id=ORG,
        document_kind="annual_report",
        fiscal_year=2025,
    )
    assert _adapter(client).discover(request) == ()


def test_exact_mode_still_excludes_summary_companion():
    client = _FakeClient(
        records=[
            _announce(
                announcement_id="900001001",
                title="示例公司2024年年度报告",
                ms=1742472000000,
            ),
            _announce(
                announcement_id="900001002",
                title="示例公司2024年年度报告摘要",
                ms=1742472000000,
            ),
        ]
    )
    from src.company_wiki_adapter import AdapterDiscoveryRequest

    request = AdapterDiscoveryRequest(
        stock_code=SEC,
        stock_name=NAME,
        org_id=ORG,
        document_kind="annual_report",
        fiscal_year=2024,
    )
    candidates = _adapter(client).discover(request)
    assert [c.provider_document_id for c in candidates] == ["900001001"]


# ---------------------------------------------------------------------------
# 4. bounded completeness (real client + fixture transport)
# ---------------------------------------------------------------------------


def test_latest_keeps_full_text_that_only_appears_on_a_later_page(monkeypatch):
    transport = _PageTransport(label="paged_summary_first")
    monkeypatch.setattr("urllib.request.urlopen", transport)

    records, _state = CninfoAnnouncementClient().discover_announcements(
        stock_code=SEC,
        org_id=ORG,
        document_kind="annual_report",
        fiscal_year=None,
        max_pages=5,
        as_of_date="2026-06-01",
    )

    assert len(transport.requests) == 2, "must keep paging after a filtered-empty page"
    ids = sorted(record.announcement_id for record in records)
    assert ids == ["900004001", "900004002"]


def test_adapter_returns_only_full_text_after_summary_exclusion(monkeypatch):
    transport = _PageTransport(label="paged_summary_first")
    monkeypatch.setattr("urllib.request.urlopen", transport)

    candidates = _adapter(CninfoAnnouncementClient()).discover(
        _request(as_of_date="2026-06-01", max_pages=5)
    )
    assert [c.provider_document_id for c in candidates] == ["900004002"]
    assert "摘要" not in candidates[0].title


def test_page_budget_exhaustion_is_not_reported_as_complete(monkeypatch):
    transport = _PageTransport(label="over_five_pages")
    monkeypatch.setattr("urllib.request.urlopen", transport)
    budget = _budget(1048576)

    with pytest.raises(CninfoApiError) as exc_info:
        CninfoAnnouncementClient().discover_announcements(
            stock_code=SEC,
            org_id=ORG,
            document_kind="annual_report",
            fiscal_year=None,
            max_pages=5,
            as_of_date="2026-06-01",
            budget=budget,
        )

    assert exc_info.value.error_code == "discovery_incomplete"
    assert exc_info.value.retryable is False
    assert len(transport.requests) == 5
    assert budget.response_bytes_used == transport.body_bytes > 0


def test_complete_window_without_valid_candidate_raises_bounded_discovery_empty(
    monkeypatch,
):
    transport = _PageTransport(label="all_future")
    monkeypatch.setattr("urllib.request.urlopen", transport)

    from src.company_wiki_adapter import AdapterError

    with pytest.raises(AdapterError, match="bounded_discovery_empty") as exc_info:
        _adapter(CninfoAnnouncementClient()).discover(_request(as_of_date="2026-06-01"))

    assert exc_info.value.code == "bounded_discovery_empty"
    assert exc_info.value.retryable is False
    assert "2024-01-01" in str(exc_info.value)
    assert "2026-06-01" in str(exc_info.value)


def test_one_budget_is_shared_by_every_page_of_one_discovery(monkeypatch):
    transport = _PageTransport(label="paged_summary_first")
    monkeypatch.setattr("urllib.request.urlopen", transport)
    budget = _budget(1048576)

    _adapter(CninfoAnnouncementClient()).discover(
        _request(as_of_date="2026-06-01", max_pages=5),
        acquisition_budget=budget,
    )

    assert len(transport.requests) == 2
    assert budget.response_bytes_used == transport.body_bytes
    assert budget.usage() == {
        "schema_version": "1.0",
        "response_bytes": transport.body_bytes,
        "cost_usd": "0",
    }


def test_shared_budget_stops_before_the_next_page_request(monkeypatch):
    transport = _PageTransport(label="paged_summary_first")
    monkeypatch.setattr("urllib.request.urlopen", transport)
    budget = _budget(len(json.dumps(transport.pages["1"]).encode("utf-8")))

    from src.acquisition_budget import AcquisitionBudgetExceeded

    with pytest.raises(AcquisitionBudgetExceeded):
        _adapter(CninfoAnnouncementClient()).discover(
            _request(as_of_date="2026-06-01", max_pages=5),
            acquisition_budget=budget,
        )

    assert len(transport.requests) == 1


def test_bounded_read_never_requests_unbounded_chunks(monkeypatch):
    transport = _PageTransport(label="annual_cutover")
    monkeypatch.setattr("urllib.request.urlopen", transport)
    budget = _budget(1048576)

    CninfoAnnouncementClient().discover_announcements(
        stock_code=SEC,
        org_id=ORG,
        document_kind="annual_report",
        fiscal_year=None,
        max_pages=5,
        as_of_date="2026-06-01",
        budget=budget,
    )

    assert all(
        size > 0 for response in transport.responses for size in response.read_sizes
    )


# ---------------------------------------------------------------------------
# 5. typed errors reach the CLI JSON
# ---------------------------------------------------------------------------


def test_adapter_error_carries_typed_code_and_retryable():
    from src.company_wiki_adapter import AdapterError

    client = _FakeClient(
        raise_exc=CninfoApiError(
            "coverage cannot be proven",
            error_code="discovery_incomplete",
            retryable=False,
        )
    )
    with pytest.raises(AdapterError) as exc_info:
        _adapter(client).discover(_request())
    assert exc_info.value.code == "discovery_incomplete"
    assert exc_info.value.retryable is False


def test_cli_reports_discovery_incomplete_without_stdout_json(monkeypatch):
    import src.company_wiki_adapter_cli as cli
    from src.company_wiki_adapter import AdapterError

    class _Broken:
        def __init__(self):
            from types import SimpleNamespace

            self.downloader = SimpleNamespace(cleanup=lambda: None)

        def discover(self, request, *, acquisition_budget=None):
            if acquisition_budget is not None:
                acquisition_budget.consume_response_bytes(11)
            raise AdapterError(
                "cninfo_api_discover failed: discovery_incomplete: covered 5 < total 6",
                code="discovery_incomplete",
                retryable=False,
            )

    monkeypatch.setattr(cli, "_build_adapter", lambda _config: _Broken())
    code, stdout, stderr = _cli_invoke(monkeypatch, _latest_payload())

    assert code == 1
    assert stdout == ""
    payload = json.loads(stderr)
    assert payload["schema_version"] == "1.0"
    assert payload["status"] == "failed"
    assert payload["adapter"]["version"] == "1.3.0"
    assert payload["error"]["code"] == "discovery_incomplete"
    assert payload["error"]["retryable"] is False
    assert payload["error"]["acquisition_usage"]["response_bytes"] == 11


def test_adapter_version_is_1_3_0():
    from src.company_wiki_adapter import ADAPTER_NAME, ADAPTER_VERSION

    assert ADAPTER_NAME == "stockinfo-cninfo"
    assert ADAPTER_VERSION == "1.3.0"


@pytest.mark.parametrize(
    "contradiction", ("short_final_page", "more_after_zero", "more_after_final")
)
def test_latest_rejects_conflicting_page_completion_facts(monkeypatch, contradiction):
    page = _fixture("annual_cutover")["pages"]["1"]
    if contradiction == "short_final_page":
        page["totalRecordNum"] = 3
    elif contradiction == "more_after_zero":
        page["totalRecordNum"] = 0
        page["announcements"] = []
        page.pop("totalpages")
        page["hasMore"] = True
    else:
        page["hasMore"] = True
    transport = _PageTransport(pages={"1": page})
    monkeypatch.setattr("urllib.request.urlopen", transport)
    with pytest.raises(CninfoApiError) as caught:
        CninfoAnnouncementClient().discover_announcements(
            stock_code=SEC,
            org_id=ORG,
            document_kind="annual_report",
            as_of_date="2026-02-01",
            fiscal_year=None,
        )
    assert caught.value.error_code == "discovery_incomplete"
    assert caught.value.retryable is False
    assert len(transport.requests) == 1
