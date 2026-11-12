"""CW-2.27E / Phase 4 Gate 4.1 — Capture BYD 002594 FY2024 announcement fixture.

MB-SID A0 reception note (2026-11-11)
-------------------------------------
This file is kept as the **only recorded origin** of the two tracked fixtures in
``tests/fixtures/cninfo/``.  It is not a runtime dependency, not a production
entry point, and not a company-specific collector to extend:

* the stock code, org id and date window below are the historical capture
  parameters, not a business dictionary;
* do not run it as part of any build, test or automation — the fixtures are
  already checked in and the contract tests read them offline;
* do not generalise it into "download arbitrary companies" without a separate
  product decision.

Original description follows.

Read-only API discovery probe. Does NOT download PDF. Captures the official
announcement API JSON response for BYD 002594 (gshk0001211), strip cookies/
tokens/session/headers, extract minimal schema fields needed by Phase 5
``src/cninfo_api.py`` RED tests:

  - request endpoint + non-secret params
  - response schema: total, announcements array, pagination
  - for each announcement: announcementId, announcementTime, title,
    adjunctUrl (PDF path), announcement_id (also exposed), secCode/secName

Outputs two parts:
  1) byd_fy2024_announcement.json — captured + desensitized real response
  2) synthetic_empty_from_real_schema.json — clearly labelled total=0
     synthetic fixture derived from real schema; never claims to come from a
     real empty company.

Run only when explicitly authorized and after Gate 4.0 passes two consecutive
preflight probes. This script lives under tests/ and only writes fixtures to
tests/fixtures/cninfo/.
"""

from __future__ import annotations

import copy
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINT = "https://www.cninfo.com.cn/new/hisAnnouncement/query"

# Non-secret form params for BYD 002594 FY2024 annual report discovery.
FORM_PARAMS = {
    "pageNum": "1",
    "pageSize": "30",
    "column": "szse",
    "tabName": "fulltext",
    "stock": "002594,gshk0001211",
    "seDate": "2024-01-01~2025-12-31",
    "category": "category_ndbg_szsh",
    "isHLtitle": "true",
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

OUT_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "cninfo"


def _capture_response() -> dict:
    """Send POST and return parsed JSON dict; raise on non-2xx or non-JSON."""
    data = urllib.parse.urlencode(FORM_PARAMS).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        method="POST",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": "https://www.cninfo.com.cn/new/disclosure/stock?stockCode=002594",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            status = response.status
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"announcement_api HTTP {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"announcement_api network: {exc}") from exc
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    if status != 200:
        raise RuntimeError(f"announcement_api returned {status}")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"announcement_api response not valid JSON ({content_type}, first 200 chars: {body[:200]!r})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"announcement_api response root is {type(payload).__name__}, not object"
        )
    print(
        f"capture byd_fy2024: HTTP {status} {content_type} "
        f"{len(body)} bytes {elapsed_ms}ms; payload keys={list(payload.keys())}"
    )
    return payload


_SECRET_FIELDS = (
    "cookie",
    "set-cookie",
    "session",
    "token",
    "csrf",
    "xsrf",
    "authorization",
    "x-csrf-token",
    "x-xsrf-token",
)


def _secret_scan(obj, path=""):
    """Recursively scan for secret-like keys; raise if any found."""
    issues: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            k = str(key).lower()
            if any(s in k for s in _SECRET_FIELDS):
                issues.append(f"{path}.{key}")
            else:
                issues.extend(_secret_scan(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            issues.extend(_secret_scan(value, f"{path}[{index}]"))
    return issues


def _desensitize(payload: dict) -> dict:
    """Keep only minimal schema fields needed by Phase 5 RED tests.

    Why partial: announcement API returns ~20 keys per record. Phase 5 only
    needs a few identity + transport-related fields. Stripping the rest both
    minimises fixture size and removes any spot where accidental tracking
    header / id could leak.
    """
    keep_root_keys = ("total", "announcements", "totalAnnouncement", "totalRecordNum")
    keep_announcement_keys = (
        "announcementId",
        "announcementTime",
        "announcementTitle",
        "announcementTypeName",
        "adjunctUrl",
        "adjunctSize",
        "adjunctType",
        "secCode",
        "secName",
        "orgId",
    )
    out: dict = {}
    for k in keep_root_keys:
        if k in payload:
            out[k] = payload[k]
    if isinstance(payload.get("announcements"), list):
        out["announcements"] = []
        for record in payload["announcements"]:
            if not isinstance(record, dict):
                continue
            minimal = {k: record.get(k) for k in keep_announcement_keys if k in record}
            out["announcements"].append(minimal)
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[1/4] capturing BYD 002594 FY2024 announcement API response (no PDF)")
    raw = _capture_response()

    print("[2/4] secret-scan raw response")
    issues = _secret_scan(raw)
    if issues:
        print(f"FAIL: secret-like fields found: {issues}")
        return 2
    print(f"  pass: 0 secret-like fields across {len(issues)} scanned paths")

    print("[3/4] desensitising and writing byd_fy2024_announcement.json")
    minimal = _desensitize(raw)
    minimal["__provenance__"] = {
        "source": "https://www.cninfo.com.cn/new/hisAnnouncement/query (POST)",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "request_params": dict(FORM_PARAMS),
        "redaction": "Only schema fields required by Phase 5 cninfo_api RED tests are kept; cookies/headers not part of JSON response.",
        "real": True,
        "secret_scan": "0 issues",
    }
    real_out = OUT_DIR / "byd_fy2024_announcement.json"
    real_out.write_text(
        json.dumps(minimal, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"  wrote: {real_out} ({real_out.stat().st_size} bytes)")

    print("[4/4] writing synthetic_empty_from_real_schema.json")
    synthetic = {
        "__provenance__": {
            "source": "synthetic; schema shape derived from byd_fy2024_announcement.json",
            "synthetic": True,
            "label": "synthetic_empty_from_real_schema",
            "notes": "total=0 simulation; NOT a real empty-company endpoint response.",
            "secret_scan": "0 issues",
        },
        "total": 0,
        "totalAnnouncement": 0,
        "totalRecordNum": 0,
        "announcements": [],
    }
    synth_out = OUT_DIR / "synthetic_empty_from_real_schema.json"
    synth_out.write_text(
        json.dumps(synthetic, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"  wrote: {synth_out} ({synth_out.stat().st_size} bytes)")

    print()
    print("summary:")
    print(f"  announcements captured: {len(minimal.get('announcements', []))}")
    for ann in minimal.get("announcements", []):
        title = ann.get("announcementTitle", "")
        aid = ann.get("announcementId", "")
        atime = ann.get("announcementTime", "")
        adj = ann.get("adjunctUrl", "")
        print(f"  - id={aid} time={atime} title={title!r} adjunct={adj!r}")
    print()
    print("PASS: capture complete, no PDF downloaded, secret-scan 0 findings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
