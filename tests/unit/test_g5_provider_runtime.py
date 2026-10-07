"""G5-SID-RUNTIME — pure-API provider runtime, org-id paths, shared budget (RED→GREEN).

Five clusters, all offline:

1. runtime purity — importing/constructing the provider must never pull
   ``playwright``, ``src.browser``, ``src.downloader`` or ``src.orgid``, and
   the literal CLI must discover/fetch without a downloader;
2. org-id paths — explicit request ``org_id`` → read-only local cache →
   official bounded identity lookup, in that order, never taking the first
   record for a wrong security / ambiguous / malformed payload;
3. one shared budget — identity, pagination and fetch all charge the same
   ``ProviderAcquisitionBudget`` instance, with no second ledger and no
   deadline reset;
4. honest failures — identity is never reported as "covered but empty", and a
   transport failure keeps its explicit code/retryability plus measured usage;
5. compatibility — legacy positional ``downloader`` constructor, pure filter
   helper equivalence, and a CLI ``finally`` that tolerates a downloader-less
   adapter without masking the original outcome.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
from contextlib import contextmanager
from pathlib import Path
import shutil
import sys
import time
from typing import Any
from urllib.error import URLError
from urllib.parse import parse_qs

import pytest

WORKTREE = Path(__file__).resolve().parents[2]
TEST_ROOT = WORKTREE / ".planning" / "test-tmp" / "g5-runtime"
SEC = "600000"
ORG = "gshk0001211"
NAME = "示例公司"
_OTHER_SEC = "000001"
_OTHER_ORG = "gshk0000001"

_BLOCKED_MODULES = ("playwright", "src.browser", "src.downloader", "src.orgid")
_PROVIDER_MODULES = ("src.company_wiki_adapter_cli", "src.company_wiki_adapter")


# ---------------------------------------------------------------------------
# card-owned test root
# ---------------------------------------------------------------------------


@contextmanager
def _owned_root(label: str):
    """One scratch directory under ``<worktree>/.planning/test-tmp/g5-runtime``."""
    TEST_ROOT.parent.mkdir(parents=True, exist_ok=True)
    TEST_ROOT.mkdir(parents=True, exist_ok=True)
    path = TEST_ROOT / f"{os.getpid()}-{label}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        _leave_owned_root(path)
        shutil.rmtree(path, ignore_errors=True)
        for candidate in (TEST_ROOT, TEST_ROOT.parent):
            try:
                candidate.rmdir()
            except OSError:
                pass


def _leave_owned_root(path: Path) -> None:
    """Windows cannot delete the process working directory."""
    try:
        resolved = path.resolve()
        if Path.cwd().resolve() == resolved or resolved in Path.cwd().resolve().parents:
            os.chdir(WORKTREE)
    except OSError:
        return


# ---------------------------------------------------------------------------
# import guard
# ---------------------------------------------------------------------------


class _BlockedImport:
    def find_spec(self, fullname, path=None, target=None):
        for blocked in _BLOCKED_MODULES:
            if fullname == blocked or fullname.startswith(blocked + "."):
                raise ImportError(f"provider runtime import refused: {fullname}")
        return None


@contextmanager
def _browserless_runtime():
    """Re-import the provider modules while browser-side imports are refused."""
    import src as pkg

    watched = (*_PROVIDER_MODULES, *_BLOCKED_MODULES)
    attrs = {
        name.rsplit(".", 1)[1]: getattr(pkg, name.rsplit(".", 1)[1], None)
        for name in _PROVIDER_MODULES
    }
    saved = {name: sys.modules.pop(name) for name in watched if name in sys.modules}
    finder = _BlockedImport()
    sys.meta_path.insert(0, finder)
    try:
        yield
    finally:
        sys.meta_path.remove(finder)
        for name in watched:
            sys.modules.pop(name, None)
        for key, value in attrs.items():
            if value is None:
                if hasattr(pkg, key):
                    delattr(pkg, key)
            else:
                setattr(pkg, key, value)
        for name, module in saved.items():
            sys.modules[name] = module


# ---------------------------------------------------------------------------
# HTTP doubles
# ---------------------------------------------------------------------------


class _JsonBody:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.offset = 0
        self.status = 200
        self.headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        }
        self.read_sizes: list[int] = []
        self.unbounded_reads = 0

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            self.unbounded_reads += 1
            chunk = self.body[self.offset :]
        else:
            chunk = self.body[self.offset : self.offset + size]
        self.read_sizes.append(size)
        self.offset += len(chunk)
        return chunk

    def __enter__(self) -> "_JsonBody":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


class _PdfBody:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.offset = 0
        self.status = 200
        self.headers = {"Content-Type": "application/pdf"}

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            chunk = self.body[self.offset :]
        else:
            chunk = self.body[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk

    def __enter__(self) -> "_PdfBody":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def _identity_payload(*, sec_code: str = SEC, org_id: str = ORG, pad: int = 0) -> bytes:
    record = {
        "announcementId": "900000001",
        "announcementTime": 1742832000000,
        "announcementTitle": f"{NAME}2024年年度报告",
        "secCode": sec_code,
        "secName": NAME,
        "orgId": org_id,
        "adjunctType": "PDF",
        "adjunctUrl": "finalpage/2025-03-24/900000001.PDF",
    }
    payload = {
        "totalRecordNum": 1,
        "totalpages": 1,
        "hasMore": False,
        "announcements": [record],
        "padding": "x" * pad,
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _ambiguous_identity_payload() -> bytes:
    def record(announcement_id: str, org_id: str) -> dict:
        return {
            "announcementId": announcement_id,
            "announcementTime": 1742832000000,
            "announcementTitle": f"{NAME}2024年年度报告",
            "secCode": SEC,
            "secName": NAME,
            "orgId": org_id,
            "adjunctType": "PDF",
            "adjunctUrl": f"finalpage/2025-03-24/{announcement_id}.PDF",
        }

    return json.dumps(
        {
            "totalRecordNum": 2,
            "totalpages": 1,
            "hasMore": False,
            "announcements": [
                record("900000001", ORG),
                record("900000002", _OTHER_ORG),
            ],
        },
        ensure_ascii=False,
    ).encode("utf-8")


def _announcement_payload() -> bytes:
    payload = {
        "totalRecordNum": 1,
        "totalpages": 1,
        "hasMore": False,
        "announcements": [
            {
                "announcementId": "900001001",
                "announcementTime": 1742832000000,
                "announcementTitle": f"{NAME}2024年年度报告",
                "secCode": SEC,
                "secName": NAME,
                "orgId": ORG,
                "adjunctType": "PDF",
                "adjunctUrl": "finalpage/2025-03-24/900001001.PDF",
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _is_identity(request: object) -> bool:
    data = getattr(request, "data", None)
    if not data:
        return False
    params = parse_qs(data.decode("utf-8"), keep_blank_values=True)
    return "searchkey" in params


class _Transport:
    """Queued ``urllib.request.urlopen`` replacement that records every call."""

    def __init__(self, *items: bytes | Exception) -> None:
        self._queue: list[bytes | Exception] = list(items)
        self.requests: list[object] = []
        self.bodies: list[_JsonBody] = []

    @property
    def identity_calls(self) -> int:
        return sum(1 for request in self.requests if _is_identity(request))

    @property
    def announcement_calls(self) -> int:
        return sum(1 for request in self.requests if not _is_identity(request))

    @property
    def unbounded_reads(self) -> int:
        return sum(body.unbounded_reads for body in self.bodies)

    def __call__(self, request, *args, **kwargs):
        self.requests.append(request)
        if not self._queue:
            raise AssertionError(f"unexpected HTTP request: {request!r}")
        item = self._queue.pop(0)
        if isinstance(item, Exception):
            raise item
        body = _JsonBody(item)
        self.bodies.append(body)
        return body


def _budget(*, byte_limit: int, seconds: float = 30.0):
    from src.acquisition_budget import ProviderAcquisitionBudget

    return ProviderAcquisitionBudget(
        max_response_bytes=byte_limit,
        timeout_seconds=seconds,
        max_cost_usd="0",
    )


def _request(**overrides):
    from src.company_wiki_adapter import AdapterDiscoveryRequest

    base: dict[str, Any] = dict(
        stock_code=SEC,
        stock_name=NAME,
        document_kind="annual_report",
        fiscal_year=2024,
        suffix="periodicReports",
    )
    base.update(overrides)
    return AdapterDiscoveryRequest(**base)


def _candidate():
    from src.company_wiki_adapter import DisclosureCandidate

    return DisclosureCandidate(
        candidate_id="cninfo:900001001",
        provider="cninfo",
        provider_document_id="900001001",
        identity_method="announcement_id",
        market="CN",
        entity=SEC,
        title=f"{NAME}2024年年度报告",
        source_url=(
            "https://www.cninfo.com.cn/new/disclosure/detail?announcementId=900001001"
        ),
        document_kind="annual_report",
        form_type="annual_report",
        filing_date="2025-03-24",
        fiscal_year=2024,
        fiscal_period="FY",
        language="zh-CN",
        amended=False,
        transport_url="https://static.cninfo.com.cn/finalpage/2025-03-24/900001001.PDF",
    )


class _ExplodingResolver:
    def resolve_org_id(self, stock_code, *, budget=None):
        raise AssertionError(f"identity resolver must not run here: {stock_code}")


def _write_config(root: Path) -> Path:
    config = {
        "save_dir": str(root / "downloads"),
        "headless": True,
        "max_retries": 1,
        "timeout_seconds": 30,
        "browser": {"strategy": "playwright", "headless": True},
        "download": {"max_pages": 1, "download_delay": 0.0},
        "logging": {
            "level": "WARNING",
            "log_to_file": False,
            "log_file": str(root / "logs" / "downloader.log"),
        },
        "pages": [],
        "companies": [],
        "test_cases": [],
    }
    path = root / "config.json"
    path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return path


def _invoke(monkeypatch, module, argv, payload):
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.setattr(module.sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(module.sys, "stdout", stdout)
    monkeypatch.setattr(module.sys, "stderr", stderr)
    code = module.main(list(argv))
    return code, stdout.getvalue(), stderr.getvalue()


def _payload(**overrides):
    value = {
        "entity": NAME,
        "market": "CN",
        "security_id": SEC,
        "document_kind": "annual_report",
        "fiscal_year": 2024,
        "acquisition_budget": {
            "schema_version": "1.0",
            "max_response_bytes": 4096,
            "timeout_seconds": 30,
            "max_cost_usd": "0",
        },
    }
    value.update(overrides)
    return value


# ---------------------------------------------------------------------------
# 1. runtime purity
# ---------------------------------------------------------------------------


def test_provider_modules_import_without_browser_or_downloader():
    with _browserless_runtime():
        adapter_module = __import__("src.company_wiki_adapter", fromlist=["*"])
        cli_module = __import__("src.company_wiki_adapter_cli", fromlist=["*"])
        for name in _BLOCKED_MODULES:
            assert name not in sys.modules, f"{name} leaked into the provider runtime"

    assert adapter_module.StockInfoCompanyWikiAdapter is not None
    assert cli_module.main is not None


def test_build_adapter_is_pure_api_and_writes_no_failure_log(monkeypatch):
    with _owned_root("build-adapter") as root:
        config = _write_config(root)
        monkeypatch.chdir(root)
        with _browserless_runtime():
            module = __import__("src.company_wiki_adapter_cli", fromlist=["*"])
            adapter = module._build_adapter(str(config))

        assert adapter.downloader is None
        assert not (root / "logs").exists()
        assert not (root / "logs" / "failed_downloads.json").exists()


def test_literal_cli_discovers_without_org_id_while_browser_imports_are_blocked(
    monkeypatch,
):
    identity = _identity_payload()
    announcement = _announcement_payload()
    transport = _Transport(identity, announcement)

    with _owned_root("literal-cli") as root:
        config = _write_config(root)
        monkeypatch.chdir(root)
        monkeypatch.setattr("urllib.request.urlopen", transport)
        with _browserless_runtime():
            module = __import__("src.company_wiki_adapter_cli", fromlist=["*"])
            code, stdout, stderr = _invoke(
                monkeypatch, module, ["discover", "--config", str(config)], _payload()
            )

        assert code == 0, stderr
        response = json.loads(stdout)
        assert response["status"] == "ok"
        assert [c["provider_document_id"] for c in response["candidates"]] == [
            "900001001"
        ]
        assert transport.identity_calls == 1
        assert transport.announcement_calls == 1
        assert response["acquisition_usage"]["response_bytes"] == len(identity) + len(
            announcement
        )
        assert not (root / "logs").exists()
        assert not (WORKTREE / "src" / "stock_orgid_mapping.json").exists()


def test_cli_fetch_runs_on_a_downloader_less_adapter(monkeypatch):
    from src import company_wiki_adapter_cli as cli
    from src.company_wiki_adapter import StockInfoCompanyWikiAdapter
    from src.cninfo_api import CninfoAnnouncementClient

    pdf = b"%PDF-" + b"g5-cli-fetch-" * 32
    candidate = _candidate().to_dict()
    with _owned_root("cli-fetch") as root:
        config = _write_config(root)
        staging = root / "staging"
        monkeypatch.chdir(root)
        monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: _PdfBody(pdf))
        monkeypatch.setattr(
            cli,
            "_build_adapter",
            lambda _config: StockInfoCompanyWikiAdapter(
                None,
                cninfo_client=CninfoAnnouncementClient(),
                identity_resolver=_ExplodingResolver(),
            ),
        )
        code, stdout, stderr = _invoke(
            monkeypatch,
            cli,
            ["fetch", "--staging-dir", str(staging), "--config", str(config)],
            {
                **candidate,
                "adapter_payload_json": json.dumps(candidate, ensure_ascii=False),
            },
        )

        assert code == 0, stderr
        receipt = json.loads(stdout)["receipt"]
        assert receipt["byte_size"] == len(pdf)
        assert receipt["content_sha256"] == hashlib.sha256(pdf).hexdigest()
        assert list(staging.glob("*.part")) == []
        assert not (root / "logs").exists()


# ---------------------------------------------------------------------------
# 2. org-id paths
# ---------------------------------------------------------------------------


def test_explicit_request_org_id_skips_cache_and_identity_http(monkeypatch):
    from src.company_wiki_adapter import StockInfoCompanyWikiAdapter
    from src.cninfo_api import CninfoAnnouncementClient

    transport = _Transport(_announcement_payload())
    monkeypatch.setattr("urllib.request.urlopen", transport)
    adapter = StockInfoCompanyWikiAdapter(
        None, cninfo_client=CninfoAnnouncementClient()
    )

    candidates = adapter.discover(_request(org_id=ORG))

    assert [c.provider_document_id for c in candidates] == ["900001001"]
    assert transport.identity_calls == 0
    assert transport.announcement_calls == 1


def test_local_cache_resolves_org_id_without_any_http(monkeypatch):
    from src.company_wiki_adapter import StockInfoCompanyWikiAdapter
    from src.cninfo_api import CninfoAnnouncementClient

    transport = _Transport(_announcement_payload())
    monkeypatch.setattr("urllib.request.urlopen", transport)
    with _owned_root("cache-hit") as root:
        cache_path = root / "stock_orgid_mapping.json"
        cache_path.write_text(
            json.dumps({SEC: {"orgId": ORG, "name": NAME}}, ensure_ascii=False),
            encoding="utf-8",
        )
        before = cache_path.read_bytes()
        stat_before = cache_path.stat()
        monkeypatch.chdir(root)

        adapter = StockInfoCompanyWikiAdapter(
            None, cninfo_client=CninfoAnnouncementClient()
        )
        candidates = adapter.discover(_request())

        assert [c.provider_document_id for c in candidates] == ["900001001"]
        assert transport.identity_calls == 0
        assert transport.announcement_calls == 1
        assert cache_path.read_bytes() == before
        assert cache_path.stat().st_mtime_ns == stat_before.st_mtime_ns
        assert not (WORKTREE / "src" / "stock_orgid_mapping.json").exists()


def test_cache_lookup_rejects_entries_without_a_usable_org_id():
    from src.cninfo_identity import LocalOrgIdCache

    with _owned_root("cache-schema") as root:
        cache_path = root / "stock_orgid_mapping.json"
        cache_path.write_text(
            json.dumps(
                {
                    SEC: {"name": NAME},
                    "000002": {"orgId": "   "},
                    "000003": "not-a-dict",
                    "000004": {"org_id": "gshk0000004"},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        cache = LocalOrgIdCache(mapping_file=cache_path)

        assert cache.get_org_id(SEC) is None
        assert cache.get_org_id("000002") is None
        assert cache.get_org_id("000003") is None
        assert cache.get_org_id("000004") == "gshk0000004"
        assert cache.get_org_id("999999") is None


def test_default_cache_candidates_follow_the_legacy_order(monkeypatch):
    from src.cninfo_identity import LocalOrgIdCache, candidate_paths

    with _owned_root("cache-order") as root:
        monkeypatch.chdir(root)
        paths = candidate_paths(None)
        assert len(paths) == 3
        assert paths[0].name == "stock_orgid_mapping.json"
        assert paths[0].parent == WORKTREE / "src"
        assert paths[1] == Path("stock_orgid_mapping.json")
        assert paths[2] == Path("configs") / "stock_orgid_mapping.json"
        assert not paths[0].exists()
        assert LocalOrgIdCache().get_org_id(SEC) is None
        assert not (WORKTREE / "src" / "stock_orgid_mapping.json").exists()


def test_official_identity_and_announcements_share_one_budget(monkeypatch):
    from src.company_wiki_adapter import StockInfoCompanyWikiAdapter
    from src.cninfo_api import CninfoAnnouncementClient

    identity = _identity_payload()
    announcement = _announcement_payload()
    transport = _Transport(identity, announcement)
    monkeypatch.setattr("urllib.request.urlopen", transport)
    budget = _budget(byte_limit=len(identity) + len(announcement))
    adapter = StockInfoCompanyWikiAdapter(
        None, cninfo_client=CninfoAnnouncementClient()
    )

    candidates = adapter.discover(_request(), acquisition_budget=budget)

    assert [c.provider_document_id for c in candidates] == ["900001001"]
    assert transport.identity_calls == 1
    assert transport.announcement_calls == 1
    assert budget.response_bytes_used == len(identity) + len(announcement)
    assert budget.usage() == {
        "schema_version": "1.0",
        "response_bytes": len(identity) + len(announcement),
        "cost_usd": "0",
    }
    assert transport.unbounded_reads == 0
    assert all(size > 0 for body in transport.bodies for size in body.read_sizes)


def test_identity_timeout_is_capped_by_remaining_budget_seconds(monkeypatch):
    from src.cninfo_api import CninfoAnnouncementClient

    seen: dict[str, float] = {}

    def capture(request, *args, **kwargs):
        seen["timeout"] = float(kwargs["timeout"])
        return _JsonBody(_identity_payload())

    monkeypatch.setattr("urllib.request.urlopen", capture)
    budget = _budget(byte_limit=4096, seconds=3.0)

    CninfoAnnouncementClient(timeout_seconds=20.0).resolve_org_id(SEC, budget=budget)

    assert 0 < seen["timeout"] <= 3.0


def test_identity_budget_exhaustion_sends_zero_announcement_requests(monkeypatch):
    from src.acquisition_budget import AcquisitionBudgetExceeded
    from src.company_wiki_adapter import StockInfoCompanyWikiAdapter
    from src.cninfo_api import CninfoAnnouncementClient

    identity = _identity_payload()
    transport = _Transport(identity, _announcement_payload())
    monkeypatch.setattr("urllib.request.urlopen", transport)
    budget = _budget(byte_limit=len(identity))
    adapter = StockInfoCompanyWikiAdapter(
        None, cninfo_client=CninfoAnnouncementClient()
    )

    with pytest.raises(AcquisitionBudgetExceeded):
        adapter.discover(_request(), acquisition_budget=budget)

    assert budget.response_bytes_used == len(identity)
    assert transport.identity_calls == 1
    assert transport.announcement_calls == 0


def test_expired_deadline_stops_before_any_identity_request(monkeypatch):
    from src.acquisition_budget import AcquisitionBudgetExceeded
    from src.company_wiki_adapter import StockInfoCompanyWikiAdapter
    from src.cninfo_api import CninfoAnnouncementClient

    transport = _Transport(_identity_payload(), _announcement_payload())
    monkeypatch.setattr("urllib.request.urlopen", transport)
    budget = _budget(byte_limit=4096, seconds=0.001)
    time.sleep(0.01)
    adapter = StockInfoCompanyWikiAdapter(
        None, cninfo_client=CninfoAnnouncementClient()
    )

    with pytest.raises(AcquisitionBudgetExceeded):
        adapter.discover(_request(), acquisition_budget=budget)

    assert transport.requests == []
    assert budget.response_bytes_used == 0


def test_wrong_security_identity_is_a_failure_and_sends_no_announcement(monkeypatch):
    from src.company_wiki_adapter import AdapterError, StockInfoCompanyWikiAdapter
    from src.cninfo_api import CninfoAnnouncementClient

    transport = _Transport(_identity_payload(sec_code=_OTHER_SEC))
    monkeypatch.setattr("urllib.request.urlopen", transport)
    adapter = StockInfoCompanyWikiAdapter(
        None, cninfo_client=CninfoAnnouncementClient()
    )

    with pytest.raises(AdapterError) as caught:
        adapter.discover(_request())

    assert caught.value.code == "org_id_unresolved"
    assert caught.value.retryable is False
    assert "org_id" in str(caught.value)
    assert transport.identity_calls == 1
    assert transport.announcement_calls == 0


def test_ambiguous_identity_never_takes_the_first_org_id(monkeypatch):
    from src.company_wiki_adapter import AdapterError, StockInfoCompanyWikiAdapter
    from src.cninfo_api import CninfoAnnouncementClient

    transport = _Transport(_ambiguous_identity_payload())
    monkeypatch.setattr("urllib.request.urlopen", transport)
    adapter = StockInfoCompanyWikiAdapter(
        None, cninfo_client=CninfoAnnouncementClient()
    )

    with pytest.raises(AdapterError) as caught:
        adapter.discover(_request())

    assert caught.value.code == "org_id_unresolved"
    assert transport.announcement_calls == 0


def test_malformed_identity_schema_is_reported_as_schema_drift(monkeypatch):
    from src.company_wiki_adapter import AdapterError, StockInfoCompanyWikiAdapter
    from src.cninfo_api import CninfoAnnouncementClient

    broken = json.dumps(
        {"totalpages": 1, "hasMore": False, "announcements": [{"secCode": SEC}]}
    ).encode("utf-8")
    transport = _Transport(broken)
    monkeypatch.setattr("urllib.request.urlopen", transport)
    adapter = StockInfoCompanyWikiAdapter(
        None, cninfo_client=CninfoAnnouncementClient()
    )

    with pytest.raises(AdapterError) as caught:
        adapter.discover(_request())

    assert caught.value.code == "schema_drift"
    assert caught.value.retryable is False
    assert transport.announcement_calls == 0


def test_identity_transport_failure_keeps_code_retryable_and_measured_usage(
    monkeypatch,
):
    from src.company_wiki_adapter import AdapterError, StockInfoCompanyWikiAdapter
    from src.cninfo_api import CninfoAnnouncementClient

    identity = _identity_payload(pad=64)
    transport = _Transport(identity, URLError("connection refused"))
    monkeypatch.setattr("urllib.request.urlopen", transport)
    budget = _budget(byte_limit=len(identity) + 4096)
    adapter = StockInfoCompanyWikiAdapter(
        None, cninfo_client=CninfoAnnouncementClient()
    )

    with pytest.raises(AdapterError) as caught:
        adapter.discover(_request(), acquisition_budget=budget)

    assert caught.value.code == "upstream_unavailable"
    assert caught.value.retryable is True
    assert budget.response_bytes_used == len(identity)
    assert transport.identity_calls == 1
    assert transport.announcement_calls == 1


def test_cli_reports_identity_transport_failure_with_measured_usage(monkeypatch):
    from src import company_wiki_adapter_cli as cli
    from src.company_wiki_adapter import StockInfoCompanyWikiAdapter
    from src.cninfo_api import CninfoAnnouncementClient

    identity = _identity_payload(pad=64)
    transport = _Transport(identity, URLError("connection refused"))
    monkeypatch.setattr("urllib.request.urlopen", transport)
    with _owned_root("cli-identity-error") as root:
        config = _write_config(root)
        monkeypatch.chdir(root)
        monkeypatch.setattr(
            cli,
            "_build_adapter",
            lambda _config: StockInfoCompanyWikiAdapter(
                None, cninfo_client=CninfoAnnouncementClient()
            ),
        )
        code, stdout, stderr = _invoke(
            monkeypatch,
            cli,
            ["discover", "--config", str(config)],
            _payload(
                acquisition_budget={
                    "schema_version": "1.0",
                    "max_response_bytes": len(identity) + 4096,
                    "timeout_seconds": 30,
                    "max_cost_usd": "0",
                }
            ),
        )

    assert code == 1
    assert stdout == ""
    error = json.loads(stderr)["error"]
    assert error["code"] == "upstream_unavailable"
    assert error["retryable"] is True
    assert error["acquisition_usage"]["response_bytes"] == len(identity)


def test_cli_reports_identity_failure_as_identity_error_not_empty_discovery(
    monkeypatch,
):
    from src import company_wiki_adapter_cli as cli
    from src.company_wiki_adapter import StockInfoCompanyWikiAdapter
    from src.cninfo_api import CninfoAnnouncementClient

    transport = _Transport(_identity_payload(sec_code=_OTHER_SEC))
    monkeypatch.setattr("urllib.request.urlopen", transport)
    with _owned_root("cli-identity-failure") as root:
        config = _write_config(root)
        monkeypatch.chdir(root)
        monkeypatch.setattr(
            cli,
            "_build_adapter",
            lambda _config: StockInfoCompanyWikiAdapter(
                None, cninfo_client=CninfoAnnouncementClient()
            ),
        )
        code, stdout, stderr = _invoke(
            monkeypatch, cli, ["discover", "--config", str(config)], _payload()
        )

    assert code == 1
    assert stdout == ""
    error = json.loads(stderr)["error"]
    assert error["code"] == "org_id_unresolved"
    assert error["retryable"] is False
    assert error["type"] == "AdapterError"
    assert transport.announcement_calls == 0
    assert not (root / "logs").exists()


# ---------------------------------------------------------------------------
# 5. compatibility
# ---------------------------------------------------------------------------


def test_legacy_positional_downloader_constructor_is_still_accepted():
    from src.company_wiki_adapter import StockInfoCompanyWikiAdapter
    from src.cninfo_api import CninfoAnnouncementClient

    class _LegacyDownloader:
        class _Mapping:
            @staticmethod
            def get_org_id(stock_code: str):
                raise AssertionError("bounded runtime must not use legacy mapping")

        mapping = _Mapping()

        @staticmethod
        def cleanup():
            return None

    downloader = _LegacyDownloader()
    adapter = StockInfoCompanyWikiAdapter(
        downloader, cninfo_client=CninfoAnnouncementClient()
    )

    assert adapter.downloader is downloader
    assert adapter.name == "stockinfo-cninfo"
    assert adapter.version == "1.3.0"


def test_disclosure_matching_helpers_equal_the_downloader_helpers():
    from src.disclosure_matching import _matches_excluded, _matches_keywords
    from src.downloader import (
        _matches_excluded as legacy_excluded,
        _matches_keywords as legacy_keywords,
    )

    cases = [
        ("", None),
        ("", []),
        ("比亚迪2024年年度报告", ["摘要"]),
        ("比亚迪 2024 年 年度报告 摘要", ["摘要"]),
        ("比亚迪2024年年度报告摘要", ["摘 要"]),
        ("示例公司公告20250725", ["公告20250725"]),
        ("示例公司公告2025-07-25", ["公告20250725"]),
        ("示例公司2024年年度报告", ["半年度报告"]),
        ("Quarterly Report", ["quarterly"]),
        ("季度报告", []),
        (None, None),
        ("文本", None),
    ]
    for text, keywords in cases:
        assert _matches_excluded(text, keywords) == legacy_excluded(text, keywords)
        assert _matches_keywords(text, keywords) == legacy_keywords(text, keywords)


def test_cli_tolerates_an_adapter_without_a_downloader(monkeypatch):
    from src import company_wiki_adapter_cli as cli

    class _PureAdapter:
        name = "stockinfo-cninfo"
        version = "1.3.0"

        def discover(self, request, *, acquisition_budget=None):
            return ()

    with _owned_root("cli-cleanup") as root:
        config = _write_config(root)
        monkeypatch.chdir(root)
        monkeypatch.setattr(cli, "_build_adapter", lambda _config: _PureAdapter())
        code, stdout, stderr = _invoke(
            monkeypatch, cli, ["discover", "--config", str(config)], _payload()
        )

    assert code == 0, stderr
    assert json.loads(stdout)["status"] == "ok"


def test_cli_failure_is_not_masked_by_a_missing_downloader(monkeypatch):
    from src import company_wiki_adapter_cli as cli

    class _BrokenAdapter:
        name = "stockinfo-cninfo"
        version = "1.3.0"

        def discover(self, request, *, acquisition_budget=None):
            raise ValueError("contract violation")

    with _owned_root("cli-failure") as root:
        config = _write_config(root)
        monkeypatch.chdir(root)
        monkeypatch.setattr(cli, "_build_adapter", lambda _config: _BrokenAdapter())
        code, stdout, stderr = _invoke(
            monkeypatch, cli, ["discover", "--config", str(config)], _payload()
        )

    assert code == 1
    assert stdout == ""
    error = json.loads(stderr)["error"]
    assert error["type"] == "ValueError"
    assert error["retryable"] is False


def test_fetch_is_pure_and_never_touches_identity_or_downloader(monkeypatch):
    from src.company_wiki_adapter import StockInfoCompanyWikiAdapter
    from src.cninfo_api import CninfoAnnouncementClient

    pdf = b"%PDF-" + b"g5-pure-fetch-" * 32
    with _owned_root("fetch-identity-free") as root:
        staging = root / "staging"
        monkeypatch.chdir(root)
        monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: _PdfBody(pdf))
        adapter = StockInfoCompanyWikiAdapter(
            None,
            cninfo_client=CninfoAnnouncementClient(),
            identity_resolver=_ExplodingResolver(),
        )

        receipt = adapter.fetch(
            _candidate(),
            staging,
            acquisition_budget=_budget(byte_limit=len(pdf) + 16),
        )

        assert receipt.byte_size == len(pdf)
        assert receipt.content_sha256 == hashlib.sha256(pdf).hexdigest()
        assert adapter.downloader is None
        assert list(staging.glob("*.part")) == []
        assert not (root / "logs").exists()
        assert not (WORKTREE / "src" / "stock_orgid_mapping.json").exists()
