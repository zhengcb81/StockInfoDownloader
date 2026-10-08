"""CW-2.27E / Phase 4 Gate 4.1 — offline fixture loader contract.

Demonstrates that the captured announcement API fixture is sufficient to drive
Phase 5 RED tests offline (without network). This file is NOT the full Phase 5
``test_cninfo_api.py`` — it only proves:

  1. Fixture loads offline as JSON.
  2. Required identity + transport fields are present and typed.
  3. BYD FY2024 fixture contains exactly one full annual report whose
     official China disclosure date is 2025-03-25.
  4. Summary companion is present and can be cleanly excluded by ``摘要`` token.
  5. Synthetic empty fixture is clearly labelled and never claims to come
     from a real empty company.
  6. No ResidentToken / secret-shaped fields are present in either fixture.

Tests intentionally run offline (no HTTP) so they never leverage live network.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "cninfo"
_REAL_FIXTURE = _FIXTURES / "byd_fy2024_announcement.json"
_SYNTHETIC_FIXTURE = _FIXTURES / "synthetic_empty_from_real_schema.json"

_SECRET_TOKENS = (
    "cookie",
    "set-cookie",
    "session",
    "token",
    "csrf",
    "xsrf",
    "authorization",
    "x-csrf-token",
    "x-xsrf-token",
    "api-key",
    "apikey",
)


def _walk_keys(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield f"{prefix}.{k}" if prefix else str(k)
            yield from _walk_keys(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_keys(v, f"{prefix}[{i}]")


def _load_real() -> dict:
    return json.loads(_REAL_FIXTURE.read_text(encoding="utf-8"))


def _load_synthetic() -> dict:
    return json.loads(_SYNTHETIC_FIXTURE.read_text(encoding="utf-8"))


def test_real_fixture_loads_offline_and_is_marked_real():
    payload = _load_real()
    assert payload["__provenance__"]["real"] is True
    assert payload["__provenance__"]["source"].startswith(
        "https://www.cninfo.com.cn/new/hisAnnouncement/query"
    )


def test_real_fixture_announcements_array_present_and_typed():
    payload = _load_real()
    announcements = payload["announcements"]
    assert isinstance(announcements, list)
    assert len(announcements) >= 1
    for ann in announcements:
        assert isinstance(ann.get("announcementId"), str)
        assert isinstance(ann.get("announcementTime"), int)
        assert isinstance(ann.get("announcementTitle"), str)
        assert isinstance(ann.get("adjunctUrl"), str)
        assert isinstance(ann.get("secCode"), str)
        assert isinstance(ann.get("secName"), str)


def test_real_fixture_has_exactly_one_byd_fy2024_full_annual_report():
    payload = _load_real()
    annual_reports = [
        ann
        for ann in payload["announcements"]
        if ann["announcementTitle"] == "2024年年度报告"
    ]
    assert len(annual_reports) == 1
    full = annual_reports[0]
    assert full["announcementId"] == "1222881496"
    assert full["secCode"] == "002594"
    assert full["secName"] == "比亚迪"
    assert full["adjunctUrl"] == "finalpage/2025-03-25/1222881496.PDF"
    assert full["adjunctType"] == "PDF"


def test_real_fixture_fy2024_full_china_disclosure_date_is_2025_03_25():
    """UTC epoch instant converts to the official China disclosure calendar date."""
    payload = _load_real()
    full = next(
        ann
        for ann in payload["announcements"]
        if ann["announcementTitle"] == "2024年年度报告"
    )
    canonical_date = (
        _dt.datetime.fromtimestamp(
            full["announcementTime"] / 1000.0, tz=_dt.timezone(_dt.timedelta(hours=8))
        )
        .date()
        .isoformat()
    )
    assert canonical_date == "2025-03-25"


def test_real_fixture_has_fy2024_summary_companion_excludable_by_token():
    payload = _load_real()
    summaries = [
        ann
        for ann in payload["announcements"]
        if ann["announcementTitle"] == "2024年年度报告摘要"
    ]
    assert len(summaries) == 1
    summary = summaries[0]
    assert "摘要" in summary["announcementTitle"]
    assert summary["announcementId"] == "1222881505"


def test_real_fixture_total_record_num_matches_announcements_length():
    payload = _load_real()
    assert payload["totalRecordNum"] == len(payload["announcements"])


def test_synthetic_empty_fixture_marked_synthetic_and_total_zero():
    payload = _load_synthetic()
    provenance = payload["__provenance__"]
    assert provenance["synthetic"] is True
    assert provenance["label"] == "synthetic_empty_from_real_schema"
    assert payload["total"] == 0
    assert payload["totalRecordNum"] == 0
    assert payload["announcements"] == []


def test_synthetic_empty_fixture_does_not_claim_to_be_from_real_empty_company():
    payload = _load_synthetic()
    notes = payload["__provenance__"]["notes"].lower()
    assert "total=0" in notes
    assert "synthetic" in notes or "not" in notes  # NOT a real empty company


@pytest.mark.parametrize(
    "fixture_name",
    ["byd_fy2024_announcement.json", "synthetic_empty_from_real_schema.json"],
)
def test_no_secret_shaped_keys_in_fixtures(fixture_name):
    """Reject any cookie/token/session/csrf header-like keys in saved fixtures."""
    payload = json.loads((_FIXTURES / fixture_name).read_text(encoding="utf-8"))
    all_keys = list(_walk_keys(payload))
    leaks = [k for k in all_keys if any(token in k.lower() for token in _SECRET_TOKENS)]
    assert leaks == [], (
        f"secret-shaped keys leaked into fixture {fixture_name}: {leaks}"
    )
