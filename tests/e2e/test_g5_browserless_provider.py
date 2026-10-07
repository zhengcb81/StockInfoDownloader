"""G5-SID-RUNTIME — real ``-m src.company_wiki_adapter_cli`` browserless E2E.

Three seams are replaced, all inside ``tests/fixtures/g5_provider/sitecustomize.py``
which is first on the child's ``PYTHONPATH``:

* ``urllib.request.urlopen`` maps only the official cninfo hosts onto the
  loopback ``ThreadingHTTPServer``;
* ``socket.getaddrinfo`` / ``socket.socket.connect`` refuse every non-loopback
  destination, so ``external_network_requests`` cannot become nonzero silently;
* importing ``playwright`` / ``src.browser`` / ``src.downloader`` /
  ``src.orgid`` raises ``ImportError`` immediately.

Everything else — request validation, cache read, official identity lookup,
pagination, staged PDF transport, budget accounting — is the production code
path of the real command line.  All scratch lives under the card-owned
``<worktree>/.planning/test-tmp/g5-runtime`` root.
"""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import sys
import threading
from urllib.parse import parse_qs

import pytest

WORKTREE = Path(__file__).resolve().parents[2]
TEST_ROOT = WORKTREE / ".planning" / "test-tmp" / "g5-runtime"
BOOTSTRAP = WORKTREE / "tests" / "fixtures" / "g5_provider"
SEC = "600000"
ORG = "gshk0001211"
NAME = "示例公司"
_OTHER_SEC = "000001"

_PDF = b"%PDF-1.7\n" + b"g5-browserless-fetch-" * 32
_PDF_SHA256 = hashlib.sha256(_PDF).hexdigest()

_BUDGET = {
    "schema_version": "1.0",
    "max_response_bytes": 1_048_576,
    "timeout_seconds": 30,
    "max_cost_usd": "0",
}


# ---------------------------------------------------------------------------
# loopback transport
# ---------------------------------------------------------------------------


def _identity_json(*, sec_code: str = SEC, org_id: str = ORG, pad: int = 0) -> bytes:
    payload = {
        "totalRecordNum": 1,
        "totalpages": 1,
        "hasMore": False,
        "announcements": [
            {
                "announcementId": "900000001",
                "announcementTime": 1742832000000,
                "announcementTitle": f"{NAME}2024年年度报告",
                "secCode": sec_code,
                "secName": NAME,
                "orgId": org_id,
                "adjunctType": "PDF",
                "adjunctUrl": "finalpage/2025-03-24/900000001.PDF",
            }
        ],
        "padding": "x" * pad,
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _announcement_page() -> dict:
    return {
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


class _Server:
    """Loopback stand-in for the cninfo identity + announcement endpoints."""

    def __init__(self) -> None:
        self.identity_body = _identity_json()
        self.pages: dict[str, dict] = {"1": _announcement_page()}
        self.posts: list[tuple[str, dict[str, str]]] = []
        self.gets: list[str] = []
        self.sent_bytes = 0
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def _handler(self):
        state = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args, **kwargs) -> None:
                return

            def _send(self, code: int, body: bytes, content_type: str) -> None:
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                state.sent_bytes += len(body)

            def do_POST(self) -> None:  # noqa: N802 - stdlib naming
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length)
                params = {
                    key: values[0]
                    for key, values in parse_qs(raw.decode("utf-8")).items()
                }
                if "searchkey" in params:
                    state.posts.append(("identity", params))
                    self._send(200, state.identity_body, "application/json")
                    return
                state.posts.append(("announcement", params))
                payload = state.pages.get(params.get("pageNum", "1"))
                if payload is None:
                    self._send(404, b'{"error":"no such page"}', "application/json")
                    return
                self._send(
                    200,
                    json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    "application/json;charset=UTF-8",
                )

            def do_GET(self) -> None:  # noqa: N802 - stdlib naming
                state.gets.append(self.path)
                if self.path.startswith("/finalpage/"):
                    self._send(200, state.pdf, "application/pdf")
                    return
                self._send(404, b"not found", "text/plain")

        return Handler

    pdf = _PDF

    @property
    def base(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}"

    @property
    def kinds(self) -> list[str]:
        return [kind for kind, _params in self.posts]

    @property
    def announcement_posts(self) -> list[dict[str, str]]:
        return [params for kind, params in self.posts if kind == "announcement"]

    @property
    def identity_posts(self) -> list[dict[str, str]]:
        return [params for kind, params in self.posts if kind == "identity"]

    @property
    def identity_bytes(self) -> int:
        return len(self.identity_body)

    @property
    def announcement_bytes(self) -> int:
        return len(json.dumps(self.pages["1"], ensure_ascii=False).encode("utf-8"))

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


@pytest.fixture
def loopback():
    server = _Server()
    server.start()
    try:
        yield server
    finally:
        server.stop()


# ---------------------------------------------------------------------------
# card-owned test root
# ---------------------------------------------------------------------------


@contextmanager
def _owned_root(label: str):
    TEST_ROOT.parent.mkdir(parents=True, exist_ok=True)
    TEST_ROOT.mkdir(parents=True, exist_ok=True)
    path = TEST_ROOT / f"{os.getpid()}-e2e-{label}"
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


@pytest.fixture
def owned_root(request):
    label = "".join(ch if ch.isalnum() else "-" for ch in request.node.name)[:60]
    with _owned_root(label) as root:
        yield root


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


def _child_env(base_url: str) -> dict[str, str]:
    env = dict(os.environ)
    python_path = [str(BOOTSTRAP), str(WORKTREE)]
    if env.get("PYTHONPATH"):
        python_path.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(python_path)
    env["G5_LOOPBACK"] = base_url
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _payload(**overrides) -> dict:
    value = {
        "entity": NAME,
        "market": "CN",
        "security_id": SEC,
        "document_kind": "annual_report",
        "fiscal_year": 2024,
        "acquisition_budget": dict(_BUDGET),
    }
    value.update(overrides)
    return value


def _run(
    root: Path,
    config: Path,
    payload: dict,
    *,
    base_url: str,
    action: str = "discover",
    extra_args: tuple[str, ...] = (),
) -> subprocess.CompletedProcess:
    command = [
        sys.executable,
        "-m",
        "src.company_wiki_adapter_cli",
        action,
        *extra_args,
        "--config",
        str(config),
    ]
    return subprocess.run(
        command,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(root),
        env=_child_env(base_url),
        timeout=120,
        check=False,
    )


def _one_json(stdout: str) -> dict:
    assert stdout.strip(), "success stdout must contain one JSON value"
    value = json.loads(stdout)
    assert isinstance(value, dict)
    return value


def _error(stderr: str) -> dict:
    lines = [line for line in stderr.splitlines() if line.strip()]
    assert lines, "failure stderr must carry the structured error JSON"
    return json.loads(lines[-1])


def _seed_cache(root: Path) -> Path:
    path = root / "stock_orgid_mapping.json"
    path.write_text(
        json.dumps({SEC: {"orgId": ORG, "name": NAME}}, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _assert_no_browser_artifacts(root: Path) -> None:
    assert not (root / "logs").exists()
    assert not (root / "logs" / "failed_downloads.json").exists()
    assert not (root / "downloads").exists()
    assert not (root / "configs").exists()
    assert not (WORKTREE / "src" / "stock_orgid_mapping.json").exists()


# ---------------------------------------------------------------------------
# discover: browserless, org-id-less
# ---------------------------------------------------------------------------


def test_literal_cli_discovers_without_org_id_or_browser(owned_root, loopback):
    config = _write_config(owned_root)
    proc = _run(owned_root, config, _payload(), base_url=loopback.base)

    assert proc.returncode == 0, proc.stderr
    response = _one_json(proc.stdout)
    assert response["schema_version"] == "1.0"
    assert response["status"] == "ok"
    assert response["adapter"] == {"name": "stockinfo-cninfo", "version": "1.3.0"}
    assert [c["provider_document_id"] for c in response["candidates"]] == ["900001001"]
    assert loopback.kinds == ["identity", "announcement"]
    assert loopback.identity_posts[0]["stock"] == f"{SEC},"
    assert loopback.announcement_posts[0]["stock"] == f"{SEC},{ORG}"
    expected = loopback.identity_bytes + loopback.announcement_bytes
    assert response["acquisition_usage"]["response_bytes"] == expected
    assert loopback.sent_bytes == expected
    assert response["acquisition_usage"]["cost_usd"] == "0"
    _assert_no_browser_artifacts(owned_root)


def test_local_cache_hit_skips_the_identity_request(owned_root, loopback):
    config = _write_config(owned_root)
    cache = _seed_cache(owned_root)
    before = cache.read_bytes()
    proc = _run(owned_root, config, _payload(), base_url=loopback.base)

    assert proc.returncode == 0, proc.stderr
    assert loopback.kinds == ["announcement"]
    assert (
        _one_json(proc.stdout)["acquisition_usage"]["response_bytes"]
        == loopback.announcement_bytes
    )
    assert cache.read_bytes() == before
    _assert_no_browser_artifacts(owned_root)


def test_explicit_org_id_skips_the_identity_request(owned_root, loopback):
    config = _write_config(owned_root)
    proc = _run(owned_root, config, _payload(org_id=ORG), base_url=loopback.base)

    assert proc.returncode == 0, proc.stderr
    assert loopback.kinds == ["announcement"]
    assert (
        _one_json(proc.stdout)["acquisition_usage"]["response_bytes"]
        == loopback.announcement_bytes
    )
    _assert_no_browser_artifacts(owned_root)


# ---------------------------------------------------------------------------
# discover: budget boundaries
# ---------------------------------------------------------------------------


def test_identity_over_budget_sends_no_announcement_request(owned_root, loopback):
    config = _write_config(owned_root)
    proc = _run(
        owned_root,
        config,
        _payload(
            acquisition_budget={
                "schema_version": "1.0",
                "max_response_bytes": loopback.identity_bytes - 1,
                "timeout_seconds": 30,
                "max_cost_usd": "0",
            }
        ),
        base_url=loopback.base,
    )

    assert proc.returncode != 0
    assert proc.stdout == ""
    error = _error(proc.stderr)["error"]
    assert error["code"] == "budget_exceeded"
    assert error["retryable"] is False
    assert error["acquisition_usage"]["response_bytes"] == 0
    assert loopback.kinds == ["identity"]
    assert loopback.announcement_posts == []


def test_identity_consumes_the_whole_budget_so_announcement_never_starts(
    owned_root, loopback
):
    config = _write_config(owned_root)
    proc = _run(
        owned_root,
        config,
        _payload(
            acquisition_budget={
                "schema_version": "1.0",
                "max_response_bytes": loopback.identity_bytes,
                "timeout_seconds": 30,
                "max_cost_usd": "0",
            }
        ),
        base_url=loopback.base,
    )

    assert proc.returncode != 0
    assert proc.stdout == ""
    error = _error(proc.stderr)["error"]
    assert error["code"] == "budget_exceeded"
    assert error["acquisition_usage"]["response_bytes"] == loopback.identity_bytes
    assert loopback.kinds == ["identity"]
    assert loopback.announcement_posts == []


def test_expired_deadline_makes_no_http_request_at_all(owned_root, loopback):
    config = _write_config(owned_root)
    proc = _run(
        owned_root,
        config,
        _payload(
            acquisition_budget={
                "schema_version": "1.0",
                "max_response_bytes": 4096,
                "timeout_seconds": 0.001,
                "max_cost_usd": "0",
            }
        ),
        base_url=loopback.base,
    )

    assert proc.returncode != 0
    assert proc.stdout == ""
    error = _error(proc.stderr)["error"]
    assert error["code"] == "budget_exceeded"
    assert error["acquisition_usage"]["response_bytes"] == 0
    assert loopback.posts == []


def test_oversized_announcement_page_reports_usage_not_a_candidate(
    owned_root, loopback
):
    config = _write_config(owned_root)
    proc = _run(
        owned_root,
        config,
        _payload(
            acquisition_budget={
                "schema_version": "1.0",
                "max_response_bytes": loopback.identity_bytes
                + loopback.announcement_bytes
                - 1,
                "timeout_seconds": 30,
                "max_cost_usd": "0",
            }
        ),
        base_url=loopback.base,
    )

    assert proc.returncode != 0
    assert proc.stdout == ""
    error = _error(proc.stderr)["error"]
    assert error["code"] == "budget_exceeded"
    assert error["acquisition_usage"]["response_bytes"] == loopback.identity_bytes
    assert loopback.kinds == ["identity", "announcement"]


# ---------------------------------------------------------------------------
# discover: identity failures
# ---------------------------------------------------------------------------


def test_wrong_security_identity_is_an_identity_failure(owned_root, loopback):
    loopback.identity_body = _identity_json(sec_code=_OTHER_SEC)
    config = _write_config(owned_root)
    proc = _run(owned_root, config, _payload(), base_url=loopback.base)

    assert proc.returncode != 0
    assert proc.stdout == ""
    error = _error(proc.stderr)["error"]
    assert error["code"] == "org_id_unresolved"
    assert error["retryable"] is False
    assert error["type"] == "AdapterError"
    assert loopback.kinds == ["identity"]
    assert loopback.announcement_posts == []
    _assert_no_browser_artifacts(owned_root)


def test_ambiguous_identity_never_takes_the_first_org_id(owned_root, loopback):
    payload = json.loads(loopback.identity_body.decode("utf-8"))
    payload["announcements"].append(dict(payload["announcements"][0]))
    payload["announcements"][1]["announcementId"] = "900000002"
    payload["announcements"][1]["orgId"] = "gshk0000001"
    payload["totalRecordNum"] = 2
    loopback.identity_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    config = _write_config(owned_root)
    proc = _run(owned_root, config, _payload(), base_url=loopback.base)

    assert proc.returncode != 0
    assert proc.stdout == ""
    assert _error(proc.stderr)["error"]["code"] == "org_id_unresolved"
    assert loopback.announcement_posts == []


def test_malformed_identity_schema_is_reported_as_schema_drift(owned_root, loopback):
    loopback.identity_body = json.dumps(
        {"totalpages": 1, "hasMore": False, "announcements": [{"secCode": SEC}]}
    ).encode("utf-8")
    config = _write_config(owned_root)
    proc = _run(owned_root, config, _payload(), base_url=loopback.base)

    assert proc.returncode != 0
    assert proc.stdout == ""
    error = _error(proc.stderr)["error"]
    assert error["code"] == "schema_drift"
    assert error["retryable"] is False
    assert loopback.announcement_posts == []


# ---------------------------------------------------------------------------
# fetch: real staged PDF
# ---------------------------------------------------------------------------


def test_fetch_stages_the_synthetic_pdf_with_real_sha_and_size(owned_root, loopback):
    config = _write_config(owned_root)
    discover = _run(owned_root, config, _payload(org_id=ORG), base_url=loopback.base)
    assert discover.returncode == 0, discover.stderr
    candidates = _one_json(discover.stdout)["candidates"]
    assert len(candidates) == 1
    candidate = candidates[0]

    staging = owned_root / "staging"
    loopback.gets.clear()
    proc = _run(
        owned_root,
        config,
        {
            **candidate,
            "adapter_payload_json": json.dumps(candidate, ensure_ascii=False),
            "acquisition_budget": dict(_BUDGET),
        },
        base_url=loopback.base,
        action="fetch",
        extra_args=("--staging-dir", str(staging)),
    )

    assert proc.returncode == 0, proc.stderr
    receipt = _one_json(proc.stdout)["receipt"]
    staged = Path(receipt["staged_path"])
    assert staged.is_file()
    assert staged.resolve().is_relative_to(staging.resolve())
    assert receipt["byte_size"] == len(_PDF)
    assert receipt["content_sha256"] == _PDF_SHA256
    assert receipt["adapter_name"] == "stockinfo-cninfo"
    assert receipt["adapter_version"] == "1.3.0"
    assert list(staging.glob("*.part")) == []
    assert loopback.gets and loopback.gets[0].startswith("/finalpage/")
    _assert_no_browser_artifacts(owned_root)


def test_fetch_over_budget_removes_the_partial_file(owned_root, loopback):
    config = _write_config(owned_root)
    discover = _run(owned_root, config, _payload(org_id=ORG), base_url=loopback.base)
    assert discover.returncode == 0, discover.stderr
    candidate = _one_json(discover.stdout)["candidates"][0]

    staging = owned_root / "staging-oversize"
    proc = _run(
        owned_root,
        config,
        {
            **candidate,
            "adapter_payload_json": json.dumps(candidate, ensure_ascii=False),
            "acquisition_budget": {
                "schema_version": "1.0",
                "max_response_bytes": 16,
                "timeout_seconds": 30,
                "max_cost_usd": "0",
            },
        },
        base_url=loopback.base,
        action="fetch",
        extra_args=("--staging-dir", str(staging)),
    )

    assert proc.returncode != 0
    assert proc.stdout == ""
    assert _error(proc.stderr)["error"]["code"] == "budget_exceeded"
    assert list(staging.glob("*.part")) == []
    assert list(staging.glob("*.pdf")) == []


# ---------------------------------------------------------------------------
# the bootstrap itself
# ---------------------------------------------------------------------------

_GUARD_PROBE = """
import json
import socket
import sys

probe = {}
probe["sitecustomize_active"] = bool(
    getattr(sys.modules.get("sitecustomize"), "_G5_OFFLINE", False)
)
probe["urlopen_guarded"] = bool(
    getattr(
        __import__("urllib.request", fromlist=["urlopen"]).urlopen,
        "_g5_offline_guard",
        False,
    )
)
probe["getaddrinfo_guarded"] = bool(
    getattr(socket.getaddrinfo, "_g5_offline_guard", False)
)
probe["connect_guarded"] = bool(getattr(socket.socket.connect, "_g5_offline_guard", False))
probe["blocked"] = {}
for name in ("playwright", "src.browser", "src.downloader", "src.orgid"):
    try:
        __import__(name)
    except ImportError:
        probe["blocked"][name] = True
    else:
        probe["blocked"][name] = False
try:
    socket.getaddrinfo("192.0.2.1", 80)
except OSError as exc:
    probe["non_loopback_refused"] = str(exc)
else:
    probe["non_loopback_refused"] = None
print(json.dumps(probe))
"""


def test_child_bootstrap_blocks_browser_imports_and_non_loopback_network(
    owned_root,
):
    proc = subprocess.run(
        [sys.executable, "-c", _GUARD_PROBE],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(owned_root),
        env=_child_env("http://127.0.0.1:1"),
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    probe = json.loads(proc.stdout)
    assert probe["sitecustomize_active"] is True
    assert probe["urlopen_guarded"] is True
    assert probe["getaddrinfo_guarded"] is True
    assert probe["connect_guarded"] is True
    assert probe["blocked"] == {
        "playwright": True,
        "src.browser": True,
        "src.downloader": True,
        "src.orgid": True,
    }
    assert (
        probe["non_loopback_refused"]
        and "non-loopback" in probe["non_loopback_refused"]
    )
