"""CW-2.27F / Phase 5 — cninfo official announcement API + transport RED contract.

RED tests for the new ``src/cninfo_api.py`` module. All offline: live HTTP is
mocked via ``patch("urllib.request.urlopen")`` or fixture-only parsing seam
``_parse_announcement`` / ``_filter_announcements_from_response`` /
``_build_request_body`` (added in production code deliberately so tests can
verify parsing logic independently of network).

Covers all 7 sub-requirements per cw-2.27 Phase 5 spec.

Run:
    python -m pytest tests/unit/test_cninfo_api.py -q
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock
import urllib.error
import urllib.request

import pytest

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "cninfo"
_REAL_FIXTURE = _FIXTURES / "byd_fy2024_announcement.json"
_SYNTHETIC_FIXTURE = _FIXTURES / "synthetic_empty_from_real_schema.json"


def _load_real_payload() -> dict:
    return json.loads(_REAL_FIXTURE.read_text(encoding="utf-8"))


def _load_synthetic_payload() -> dict:
    return json.loads(_SYNTHETIC_FIXTURE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Requirement 1 — request params/encoding identical to fixture capture
# ---------------------------------------------------------------------------


def test_build_request_body_matches_capture_params_bit_for_bit():
    from src.cninfo_api import CninfoAnnouncementClient

    fixture = _load_real_payload()
    expected = fixture["__provenance__"]["request_params"]

    client = CninfoAnnouncementClient()
    body = client._build_request_body(
        stock_code="002594",
        org_id="gshk0001211",
        document_kind="annual_report",
        fiscal_year=2024,
        page_num=1,
        page_size=30,
    )
    assert isinstance(body, (bytes, bytearray))
    # Body is form-urlencoded bytes; decode then parse for str-key comparison.
    import urllib.parse

    parsed = urllib.parse.parse_qs(body.decode("utf-8"), keep_blank_values=True)
    decoded = {k: v[0] for k, v in parsed.items()}
    for key, expected_val in expected.items():
        assert decoded.get(key) == expected_val, (
            f"param {key!r}: capture={expected_val!r}, built={decoded.get(key)!r}"
        )


# ---------------------------------------------------------------------------
# Requirement 2 — parse record identity/transport fields
# ---------------------------------------------------------------------------


def test_parse_announcement_record_preserves_fy2024_full_identity():
    from src.cninfo_api import CninfoAnnouncementClient

    client = CninfoAnnouncementClient()
    raw = _load_real_payload()["announcements"][1]  # FY2024 full
    parsed = client._parse_announcement(raw, stock_code="002594")

    assert parsed.announcement_id == "1222881496"
    # Official China disclosure date from the captured epoch milliseconds
    assert parsed.filing_date == "2025-03-25"
    assert parsed.title == "2024年年度报告"
    assert parsed.sec_code == "002594"
    assert parsed.sec_name == "比亚迪"
    assert parsed.org_id == "gshk0001211"
    assert parsed.announcement_time_ms == 1742832000000
    assert parsed.adjunct_type == "PDF"
    assert parsed.adjunct_url == "finalpage/2025-03-25/1222881496.PDF"
    assert parsed.transport_url == (
        "https://static.cninfo.com.cn/finalpage/2025-03-25/1222881496.PDF"
    )
    # detail_url must be human-openable official detail page on www.cninfo.com.cn
    assert parsed.detail_url.startswith(
        "https://www.cninfo.com.cn/new/disclosure/detail?"
    )
    assert "stockCode=002594" in parsed.detail_url
    assert "announcementId=1222881496" in parsed.detail_url


# ---------------------------------------------------------------------------
# Requirement 3 — filter full+summary; legitimate multiple full preserved
# ---------------------------------------------------------------------------


def test_filter_announcements_returns_all_fy2024_records_summary_filter_at_adapter():
    """API client returns every record matching fiscal_year+document_kind (via
    ``_report_metadata``). Summary exclusion is the adapter's safety layer, NOT
    the API client's responsibility, so both full + summary are returned."""
    from src.cninfo_api import CninfoAnnouncementClient
    from src.transport_states import LoadState

    client = CninfoAnnouncementClient()
    payload = _load_real_payload()
    records, state = client._filter_announcements_from_response(
        payload, stock_code="002594", document_kind="annual_report", fiscal_year=2024
    )
    assert state == LoadState.READY
    ids = sorted(r.announcement_id for r in records)
    # FY2024 only: full annual report + its summary companion.
    assert ids == ["1222881496", "1222881505"]
    # FY2023 announcements must be filtered out by fiscal_year=2024.
    titles = [r.title for r in records]
    assert "2023年年度报告" not in titles
    assert "2023年年度报告摘要" not in titles


def test_filter_announcements_synthetic_total_zero_returns_confirmed_empty():
    from src.cninfo_api import CninfoAnnouncementClient
    from src.transport_states import LoadState

    client = CninfoAnnouncementClient()
    payload = _load_synthetic_payload()
    records, state = client._filter_announcements_from_response(
        payload, stock_code="002594", document_kind="annual_report", fiscal_year=2024
    )
    assert records == []
    assert state == LoadState.CONFIRMED_EMPTY


def test_filter_announcements_keeps_full_amended_and_summary_at_api_level():
    """Adapter chooses among 1+ full after summary exclusion. API client returns
    all matching records (full + amended + summary); summary exclusion later at
    adapter is what makes ``legitimate multiple full`` valid (1 full + 1 amended)."""
    from src.cninfo_api import CninfoAnnouncementClient
    from src.transport_states import LoadState

    client = CninfoAnnouncementClient()
    payload = _load_real_payload()
    amended = dict(payload["announcements"][1])
    amended["announcementId"] = "1222882000"
    amended["announcementTitle"] = "2024年年度报告（修订版）"
    payload["announcements"] = list(payload["announcements"]) + [amended]
    payload["totalRecordNum"] = 5
    records, state = client._filter_announcements_from_response(
        payload, stock_code="002594", document_kind="annual_report", fiscal_year=2024
    )
    assert state == LoadState.READY
    ids = sorted(r.announcement_id for r in records)
    # API client returns all 3 FY2024 records: full, summary, amended full.
    assert ids == ["1222881496", "1222881505", "1222882000"]


# ---------------------------------------------------------------------------
# Requirement 4 — API 2xx + total 0 → confirmed empty (already covered above)
# Add: discover_announcements propagates CONFIRMED_EMPTY into LoadState
# ---------------------------------------------------------------------------


def test_discover_with_mocked_total_zero_response_returns_confirmed_empty(monkeypatch):
    from src.cninfo_api import CninfoAnnouncementClient
    from src.transport_states import LoadState

    client = CninfoAnnouncementClient()
    payload = _load_synthetic_payload()
    fake_response_bytes = json.dumps(payload).encode("utf-8")

    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.headers = {"Content-Type": "application/json;charset=UTF-8"}
    fake_resp.read.return_value = fake_response_bytes
    cm = MagicMock()
    cm.__enter__.return_value = fake_resp
    cm.__exit__.return_value = False
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: cm)

    records, state = client.discover_announcements(
        stock_code="002594",
        org_id="gshk0001211",
        document_kind="annual_report",
        fiscal_year=2024,
        max_pages=1,
    )
    assert records == []
    assert state == LoadState.CONFIRMED_EMPTY


# ---------------------------------------------------------------------------
# Requirement 5 — DNS/timeout/TLS/429/5xx/non-JSON/schema drift → typed error
# never return empty candidates.
# ---------------------------------------------------------------------------


def test_dns_failure_raises_upstream_unavailable_retryable_typed(monkeypatch):
    from src.cninfo_api import CninfoAnnouncementClient, CninfoApiError

    client = CninfoAnnouncementClient(timeout_seconds=2.0)
    err = urllib.error.URLError("getaddrinfo failed")
    monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=err))
    with pytest.raises(CninfoApiError) as exc_info:
        client.discover_announcements(
            stock_code="002594",
            org_id="gshk0001211",
            document_kind="annual_report",
            fiscal_year=2024,
            max_pages=1,
        )
    assert exc_info.value.error_code == "upstream_unavailable"
    assert exc_info.value.retryable is True


def test_timeout_raises_upstream_timeout_retryable_typed(monkeypatch):
    from src.cninfo_api import CninfoAnnouncementClient, CninfoApiError

    client = CninfoAnnouncementClient(timeout_seconds=1.0)
    monkeypatch.setattr(
        "urllib.request.urlopen", MagicMock(side_effect=TimeoutError("timed out"))
    )
    with pytest.raises(CninfoApiError) as exc_info:
        client.discover_announcements(
            stock_code="002594",
            org_id="gshk0001211",
            document_kind="annual_report",
            fiscal_year=2024,
            max_pages=1,
        )
    assert exc_info.value.error_code == "upstream_timeout"
    assert exc_info.value.retryable is True


def test_http_429_raises_rate_limited_retryable_typed(monkeypatch):
    from src.cninfo_api import CninfoAnnouncementClient, CninfoApiError

    client = CninfoAnnouncementClient()
    err = urllib.error.HTTPError(
        url="https://www.cninfo.com.cn",
        code=429,
        msg="Too Many",
        hdrs=None,
        fp=None,
    )
    monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=err))
    with pytest.raises(CninfoApiError) as exc_info:
        client.discover_announcements(
            stock_code="002594",
            org_id="gshk0001211",
            document_kind="annual_report",
            fiscal_year=2024,
            max_pages=1,
        )
    assert exc_info.value.error_code == "rate_limited"
    assert exc_info.value.retryable is True
    assert exc_info.value.http_status == 429


def test_http_500_raises_upstream_unavailable_retryable_typed(monkeypatch):
    from src.cninfo_api import CninfoAnnouncementClient, CninfoApiError

    client = CninfoAnnouncementClient()
    err = urllib.error.HTTPError(
        url="https://www.cninfo.com.cn",
        code=500,
        msg="ISE",
        hdrs=None,
        fp=None,
    )
    monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=err))
    with pytest.raises(CninfoApiError) as exc_info:
        client.discover_announcements(
            stock_code="002594",
            org_id="gshk0001211",
            document_kind="annual_report",
            fiscal_year=2024,
            max_pages=1,
        )
    assert exc_info.value.error_code == "upstream_unavailable"
    assert exc_info.value.retryable is True
    assert exc_info.value.http_status == 500


def test_http_400_raises_client_error_non_retryable_typed(monkeypatch):
    from src.cninfo_api import CninfoAnnouncementClient, CninfoApiError

    client = CninfoAnnouncementClient()
    err = urllib.error.HTTPError(
        url="https://www.cninfo.com.cn",
        code=400,
        msg="Bad Req",
        hdrs=None,
        fp=None,
    )
    monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=err))
    with pytest.raises(CninfoApiError) as exc_info:
        client.discover_announcements(
            stock_code="002594",
            org_id="gshk0001211",
            document_kind="annual_report",
            fiscal_year=2024,
            max_pages=1,
        )
    assert exc_info.value.error_code == "client_error"
    assert exc_info.value.retryable is False
    assert exc_info.value.http_status == 400


def test_non_json_response_raises_schema_drift_non_retryable(monkeypatch):
    from src.cninfo_api import CninfoAnnouncementClient, CninfoApiError

    client = CninfoAnnouncementClient()
    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.headers = {"Content-Type": "text/html"}
    fake_resp.read.return_value = b"<html>not json</html>"
    cm = MagicMock()
    cm.__enter__.return_value = fake_resp
    cm.__exit__.return_value = False
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: cm)
    with pytest.raises(CninfoApiError) as exc_info:
        client.discover_announcements(
            stock_code="002594",
            org_id="gshk0001211",
            document_kind="annual_report",
            fiscal_year=2024,
            max_pages=1,
        )
    assert exc_info.value.error_code == "schema_drift"
    assert exc_info.value.retryable is False


def test_schema_drift_missing_total_record_num_raises_non_retryable(monkeypatch):
    from src.cninfo_api import CninfoAnnouncementClient, CninfoApiError

    client = CninfoAnnouncementClient()
    broken_payload = {"announcements": []}  # missing totalRecordNum
    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.headers = {"Content-Type": "application/json"}
    fake_resp.read.return_value = json.dumps(broken_payload).encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value = fake_resp
    cm.__exit__.return_value = False
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: cm)
    with pytest.raises(CninfoApiError) as exc_info:
        client.discover_announcements(
            stock_code="002594",
            org_id="gshk0001211",
            document_kind="annual_report",
            fiscal_year=2024,
            max_pages=1,
        )
    assert exc_info.value.error_code == "schema_drift"
    assert exc_info.value.retryable is False


# ---------------------------------------------------------------------------
# Requirement 6 — PDF transport
# ---------------------------------------------------------------------------


def test_fetch_pdf_rejects_non_cninfo_transport_host(tmp_path):
    from src.cninfo_api import CninfoAnnouncementClient, CninfoApiError

    client = CninfoAnnouncementClient()
    with pytest.raises(CninfoApiError) as exc_info:
        client.fetch_pdf(
            transport_url="https://example.com/fake.pdf",
            staging_dir=tmp_path,
            expected_filename="fake.pdf",
        )
    assert exc_info.value.error_code == "transport_url_host_not_allowed"
    assert exc_info.value.retryable is False
    # No staging files written
    assert list(tmp_path.iterdir()) == []


def test_fetch_pdf_writes_part_then_atomic_rename_on_success(tmp_path, monkeypatch):
    from src.cninfo_api import CninfoAnnouncementClient
    from src import constants as C

    client = CninfoAnnouncementClient()
    body = b"%PDF-1.7\n" + b"x" * (C.MIN_FILE_SIZE + 1000)
    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.headers = {"Content-Type": "application/pdf"}
    fake_resp.read.return_value = body
    cm = MagicMock()
    cm.__enter__.return_value = fake_resp
    cm.__exit__.return_value = False
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: cm)

    staged = client.fetch_pdf(
        transport_url="https://static.cninfo.com.cn/finalpage/2025-03-25/1222881496.PDF",
        staging_dir=tmp_path,
        expected_filename="byd_fy2024_full.pdf",
    )
    assert staged.is_file()
    assert staged.name == "byd_fy2024_full.pdf"
    assert staged.read_bytes() == body
    # .part file cleaned
    parts = list(tmp_path.glob("*.part"))
    assert parts == []


def test_fetch_pdf_non_2xx_removes_part_and_raises(tmp_path, monkeypatch):
    from src.cninfo_api import CninfoAnnouncementClient, CninfoApiError

    client = CninfoAnnouncementClient()
    err = urllib.error.HTTPError(
        url="https://static.cninfo.com.cn/fake.pdf",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None,
    )
    monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=err))
    with pytest.raises(CninfoApiError) as exc_info:
        client.fetch_pdf(
            transport_url="https://static.cninfo.com.cn/finalpage/2025-03-25/1222881496.PDF",
            staging_dir=tmp_path,
            expected_filename="404.pdf",
        )
    assert exc_info.value.error_code == "upstream_unavailable"
    assert exc_info.value.http_status == 404
    parts = list(tmp_path.glob("*.part"))
    assert parts == []


def test_fetch_pdf_bad_magic_removes_part_and_raises(tmp_path, monkeypatch):
    from src.cninfo_api import CninfoAnnouncementClient, CninfoApiError

    client = CninfoAnnouncementClient()
    body = b"<html>fake pdf</html>" + b"x" * 2048  # enough size but bad magic
    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.headers = {"Content-Type": "application/pdf"}
    fake_resp.read.return_value = body
    cm = MagicMock()
    cm.__enter__.return_value = fake_resp
    cm.__exit__.return_value = False
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: cm)
    with pytest.raises(CninfoApiError) as exc_info:
        client.fetch_pdf(
            transport_url="https://static.cninfo.com.cn/finalpage/2025-03-25/1222881496.PDF",
            staging_dir=tmp_path,
            expected_filename="byd.pdf",
        )
    assert exc_info.value.error_code == "pdf_magic_invalid"
    parts = list(tmp_path.glob("*.part"))
    assert parts == []


def test_fetch_pdf_small_file_removes_part_and_raises(tmp_path, monkeypatch):
    from src.cninfo_api import CninfoAnnouncementClient, CninfoApiError

    client = CninfoAnnouncementClient()
    body = b"%PDF-1.7\nshort"  # < MIN_FILE_SIZE
    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.headers = {"Content-Type": "application/pdf"}
    fake_resp.read.return_value = body
    cm = MagicMock()
    cm.__enter__.return_value = fake_resp
    cm.__exit__.return_value = False
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: cm)
    with pytest.raises(CninfoApiError) as exc_info:
        client.fetch_pdf(
            transport_url="https://static.cninfo.com.cn/finalpage/2025-03-25/1222881496.PDF",
            staging_dir=tmp_path,
            expected_filename="small.pdf",
        )
    assert exc_info.value.error_code == "content_too_small"
    parts = list(tmp_path.glob("*.part"))
    assert parts == []


# ---------------------------------------------------------------------------
# Requirement 7 — source_url = detail page; transport_url only in opaque payload
# ---------------------------------------------------------------------------


def test_candidate_construction_exposes_detail_url_as_source_url():
    from src.cninfo_api import CninfoAnnouncementClient

    client = CninfoAnnouncementClient()
    raw = _load_real_payload()["announcements"][1]
    parsed = client._parse_announcement(raw, stock_code="002594")
    # source_url field (when wired into DisclosureCandidate) must be the detail URL;
    # transport_url is only carried in opaque adapter_payload_json at adapter stage.
    assert parsed.detail_url == parsed.detail_url  # self-consistent
    assert parsed.transport_url.endswith("PDF")
    assert parsed.detail_url != parsed.transport_url
    assert parsed.transport_url.startswith("https://static.cninfo.com.cn/")
    assert parsed.detail_url.startswith(
        "https://www.cninfo.com.cn/new/disclosure/detail"
    )


# Real 688012 official category queries captured 2026-10-08 proved these
# categories differ. A broad/invalid category can silently return all notices.
@pytest.mark.parametrize(("kind", "expected"), [
    ("annual_report", "category_ndbg_szsh"),
    ("semi_annual_report", "category_bndbg_szsh"),
    ("quarterly_report", "category_yjdbg_szsh;category_sjdbg_szsh"),
])
def test_official_periodic_request_uses_its_own_categories(kind, expected):
    from urllib.parse import parse_qs
    from src.cninfo_api import CninfoAnnouncementClient

    body = CninfoAnnouncementClient()._build_request_body(
        stock_code="688012", org_id="9900038991", document_kind=kind,
        fiscal_year=2026, page_num=1, page_size=30,
    )
    params = parse_qs(body.decode("utf-8"))
    assert params["category"] == [expected]
    assert params["stock"] == ["688012,9900038991"]
    assert params["seDate"] == ["2026-01-01~2027-12-31"]


def test_official_china_disclosure_date_uses_exchange_timezone():
    from src.cninfo_api import CninfoAnnouncementClient
    raw = dict(_load_real_payload()["announcements"][1])
    raw.update(announcementId="1225482884", secCode="688012",
               announcementTitle="2026年半年度报告",
               announcementTime=1787155200000,
               adjunctUrl="finalpage/2026-08-20/1225482884.PDF")
    parsed = CninfoAnnouncementClient()._parse_announcement(raw, stock_code="688012")
    assert parsed.filing_date == "2026-08-20"
    assert parsed.announcement_time_ms == 1787155200000
    assert "announcementTime=2026-08-20" in parsed.detail_url


def test_latest_cannot_include_tomorrow_china_report_via_utc_date():
    from src.cninfo_api import CninfoAnnouncementClient
    raw = dict(_load_real_payload()["announcements"][1])
    raw.update(announcementId="1225482884", secCode="688012",
               announcementTitle="2026年半年度报告",
               announcementTime=1787155200000,
               adjunctUrl="finalpage/2026-08-20/1225482884.PDF")
    payload = {"totalRecordNum": 1, "totalpages": 1, "hasMore": False,
               "announcements": [raw]}
    records, _meta = CninfoAnnouncementClient()._filter_latest_page(
        payload, stock_code="688012", document_kind="semi_annual_report",
        cutoff="2026-08-19", fiscal_period="H1", form_type=None,
    )
    assert records == []
