"""MB-SID provider dependency direction — API → domain ← adapter, one way.

The provider used to import ``_report_metadata`` *upwards* from
``company_wiki_adapter`` (twice, lazily inside filtering methods), so the
"pure" announcement reader still needed the adapter module — and through it
the downloader/browser layer — to filter a page.

These probes run in a fresh interpreter that refuses those imports at the
finder level.  Production code contains no such guard.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKTREE = Path(__file__).resolve().parents[2]
FIXTURE = WORKTREE / "tests" / "fixtures" / "cninfo" / "byd_fy2024_announcement.json"

BLOCKED = (
    "src.company_wiki_adapter",
    "src.company_wiki_adapter_cli",
    "src.browser",
    "src.downloader",
    "src.orgid",
    "playwright",
)

_PROBE_PREAMBLE = f'''
import json
import sys
from pathlib import Path

BLOCKED = {BLOCKED!r}


class _Blocker:
    """Refuse the provider's upper layers for this interpreter."""

    def find_spec(self, fullname, path=None, target=None):
        for blocked in BLOCKED:
            if fullname == blocked or fullname.startswith(blocked + "."):
                raise ImportError("provider domain import refused: " + fullname)
        return None


sys.meta_path.insert(0, _Blocker())
'''


def _run_probe(script: str, *args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-B", "-c", _PROBE_PREAMBLE + script, *args],
        cwd=str(WORKTREE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


# ---------------------------------------------------------------------------
# pure metadata domain
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("示例公司2024年年度报告", ("annual_report", 2024, "annual_report", "FY", False)),
        (
            "示例公司2024年半年度报告",
            ("semi_annual_report", 2024, "interim_report", "H1", False),
        ),
        (
            "示例公司2024年第一季度报告",
            ("quarterly_report", 2024, "quarterly_report", "Q1", False),
        ),
        (
            "示例公司2024年第三季度报告",
            ("quarterly_report", 2024, "quarterly_report", "Q3", False),
        ),
        (
            "示例公司2024年年度报告（修订版）",
            ("annual_report", 2024, "annual_report", "FY", True),
        ),
        ("示例公司2024年年度报告摘要", ("annual_report", 2024, "annual_report", "FY", False)),
        ("示例公司临时公告", ("other", None, "other", "UNKNOWN", False)),
        ("没有年份的年度报告", ("annual_report", None, "annual_report", "FY", False)),
    ],
)
def test_pure_metadata_module_classifies_report_titles(title, expected):
    from src.cninfo_report_metadata import report_metadata

    assert report_metadata(title) == expected


def test_api_and_adapter_share_the_exact_same_function():
    from src import cninfo_report_metadata, company_wiki_adapter

    assert (
        company_wiki_adapter._report_metadata
        is cninfo_report_metadata.report_metadata
    )


# ---------------------------------------------------------------------------
# the announcement reader works with the upper layers refused
# ---------------------------------------------------------------------------


def test_announcement_filtering_runs_without_the_adapter_or_browser_layers():
    result = _run_probe(
        '''
import urllib.request
from src.cninfo_api import CninfoAnnouncementClient

fixture = Path(sys.argv[1]).read_bytes()


class _Body:
    def __init__(self, body):
        self.body = body
        self.offset = 0
        self.status = 200
        self.headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        }

    def read(self, size=-1):
        chunk = (
            self.body[self.offset:]
            if size < 0
            else self.body[self.offset:self.offset + size]
        )
        self.offset += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


urllib.request.urlopen = lambda *a, **k: _Body(fixture)

client = CninfoAnnouncementClient()
records, state = client.discover_announcements(
    stock_code="002594",
    org_id="gshk0001211",
    document_kind="annual_report",
    fiscal_year=2024,
    max_pages=1,
)
print(json.dumps({
    "ids": [record.announcement_id for record in records],
    "state": state.value,
    "leaked": [name for name in BLOCKED if name in sys.modules],
}))
''',
        str(FIXTURE),
    )

    assert result["state"] == "ready"
    assert result["ids"], "the fixture must still yield the 2024 annual reports"
    assert result["leaked"] == []


def test_pure_metadata_module_imports_with_the_upper_layers_refused():
    result = _run_probe(
        '''
from src.cninfo_report_metadata import report_metadata

print(json.dumps({
    "kind": report_metadata("示例公司2024年年度报告")[0],
    "leaked": [name for name in BLOCKED if name in sys.modules],
}))
'''
    )

    assert result == {"kind": "annual_report", "leaked": []}


# ---------------------------------------------------------------------------
# the adapter may still re-export the helper for historical callers
# ---------------------------------------------------------------------------


def test_adapter_keeps_the_legacy_helper_name_available():
    from src.company_wiki_adapter import _report_metadata

    assert _report_metadata("示例公司2024年年度报告")[0] == "annual_report"
