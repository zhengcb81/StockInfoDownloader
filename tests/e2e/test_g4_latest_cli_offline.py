"""G4-SID-LATEST — real ``-m src.company_wiki_adapter_cli`` offline E2E.

Only two seams are replaced:

* ``urllib.request.urlopen`` — injected by ``g4_bootstrap/sitecustomize.py``
  when this directory's bootstrap is first on the child's ``PYTHONPATH``, and
  only to rewrite cninfo hosts onto a loopback ``ThreadingHTTPServer``;
* ``git archive`` of the committed company-wiki ``5930a644...`` package, which
  is exported read-only into this card's temp root so the *real*
  ``JsonCommandAdapter.discover_bounded`` can consume the 1.3.0 response.

Everything else — request validation, ``CninfoAnnouncementClient``,
``StockInfoCompanyWikiAdapter``, JSON serialization, budget accounting — is the
production code path.  All scratch lives under a unique ``si4l-*`` temp root.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

import pytest

WORKTREE = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "g4_latest"
BOOTSTRAP = WORKTREE / "docs" / "implementation" / "g4-sid-latest" / "g4_bootstrap"
CWP_REPO = Path("C:/Users/郑曾波/Projects/company-wiki")
CWP_COMMIT = "5930a644453ed46494c2c83c5ecfb97767fa9492"
ORG = "gshk0001211"
SEC = "600000"
NAME = "示例公司"

_PDF = b"%PDF-1.7\n" + b"g4-latest-offline-fetch-" * 16
_PDF_SHA256 = hashlib.sha256(_PDF).hexdigest()

_BUDGET = {
    "schema_version": "1.0",
    "max_response_bytes": 1_048_576,
    "timeout_seconds": 30,
    "max_cost_usd": "0",
}


# ---------------------------------------------------------------------------
# loopback HTTP transport
# ---------------------------------------------------------------------------


class _Server:
    """Fixture-backed loopback stand-in for the cninfo announcement endpoint."""

    def __init__(self) -> None:
        self.pages: dict[str, dict] = {}
        self.posts: list[dict[str, str]] = []
        self.gets: list[str] = []
        self.sent_bytes = 0
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def _handler(self):
        state = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args) -> None:
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
                state.posts.append(params)
                payload = state.pages.get(params.get("pageNum", "1"))
                if payload is None:
                    self._send(404, b'{"error":"no such page"}', "application/json")
                    return
                self._send(
                    200,
                    json.dumps(payload).encode("utf-8"),
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

    def use(self, label: str) -> None:
        self.pages = _pages(label)

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
# card-owned temp root
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def card_root():
    root = Path(tempfile.mkdtemp(prefix="si4l-")).resolve()
    logs_in_worktree = WORKTREE / "logs"
    logs_existed = logs_in_worktree.exists()
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)
        if not logs_existed and logs_in_worktree.exists():
            try:
                if not any(logs_in_worktree.iterdir()):
                    logs_in_worktree.rmdir()
            except OSError:
                pass


def _safe_rmtree(path: Path) -> None:
    resolved = str(path.resolve())
    if "si4l-" not in resolved:
        raise AssertionError(f"refusing to delete non-card path: {resolved}")
    shutil.rmtree(path, ignore_errors=True)


def _pages(label: str) -> dict[str, dict]:
    payload = json.loads((FIXTURES / f"{label}.json").read_text(encoding="utf-8"))
    return {str(key): value for key, value in payload["pages"].items()}


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
    env["G4_LOOPBACK"] = base_url
    env["PYTHONUTF8"] = "1"
    # Keep interpreter caches out of this worktree: only the sources this card
    # owns should ever appear on disk here.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _payload(**overrides):
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
        "org_id": ORG,
        "acquisition_budget": dict(_BUDGET),
    }
    value.update(overrides)
    return value


def _run_cli(
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


# ---------------------------------------------------------------------------
# discover: latest lanes
# ---------------------------------------------------------------------------


def test_offline_cli_latest_annual_falls_back_to_the_previous_year(card_root, loopback):
    loopback.use("annual_cutover")
    config = _write_config(card_root)
    proc = _run_cli(
        card_root,
        config,
        _payload(as_of_date="2026-02-01", fiscal_year=2025),
        base_url=loopback.base,
    )

    assert proc.returncode == 0, proc.stderr
    response = _one_json(proc.stdout)
    assert response["schema_version"] == "1.0"
    assert response["status"] == "ok"
    assert response["adapter"] == {"name": "stockinfo-cninfo", "version": "1.3.0"}
    candidates = response["candidates"]
    assert [c["fiscal_year"] for c in candidates] == [2024]
    assert candidates[0]["fiscal_period"] == "FY"
    assert candidates[0]["filing_date"] == "2025-03-20"
    assert candidates[0]["provider_document_id"] == "900001001"
    assert response["acquisition_usage"]["cost_usd"] == "0"
    assert response["acquisition_usage"]["response_bytes"] == loopback.sent_bytes > 0
    assert loopback.posts[0]["seDate"] == "2024-01-01~2026-02-01"


def test_offline_cli_latest_keeps_both_visible_half_year_reports(card_root, loopback):
    loopback.use("semi_annual_visible")
    config = _write_config(card_root)
    proc = _run_cli(
        card_root,
        config,
        _payload(document_kind="semi_annual_report", as_of_date="2026-09-01"),
        base_url=loopback.base,
    )

    assert proc.returncode == 0, proc.stderr
    candidates = _one_json(proc.stdout)["candidates"]
    assert sorted((c["fiscal_year"], c["fiscal_period"]) for c in candidates) == [
        (2025, "H1"),
        (2026, "H1"),
    ]
    assert {c["document_kind"] for c in candidates} == {"semi_annual_report"}


def test_offline_cli_latest_quarterly_excludes_future_and_never_fabricates_q2(
    card_root, loopback
):
    loopback.use("quarterly_cutover")
    config = _write_config(card_root)
    proc = _run_cli(
        card_root,
        config,
        _payload(document_kind="quarterly_report", as_of_date="2026-06-01"),
        base_url=loopback.base,
    )

    assert proc.returncode == 0, proc.stderr
    candidates = _one_json(proc.stdout)["candidates"]
    assert sorted((c["fiscal_year"], c["fiscal_period"]) for c in candidates) == [
        (2025, "Q3"),
        (2026, "Q1"),
    ]
    assert "Q2" not in {c["fiscal_period"] for c in candidates}
    assert "900003003" not in {c["provider_document_id"] for c in candidates}


def test_offline_cli_keeps_full_text_that_only_appears_on_a_later_page(
    card_root, loopback
):
    loopback.use("paged_summary_first")
    config = _write_config(card_root)
    proc = _run_cli(
        card_root,
        config,
        _payload(as_of_date="2026-06-01"),
        base_url=loopback.base,
    )

    assert proc.returncode == 0, proc.stderr
    candidates = _one_json(proc.stdout)["candidates"]
    assert [c["provider_document_id"] for c in candidates] == ["900004002"]
    assert "摘要" not in candidates[0]["title"]
    assert len(loopback.posts) == 2, "pagination must continue past page 1"
    assert loopback.posts[1]["pageNum"] == "2"


def test_offline_cli_reports_discovery_incomplete_when_five_pages_run_out(
    card_root, loopback
):
    loopback.use("over_five_pages")
    config = _write_config(card_root)
    proc = _run_cli(
        card_root,
        config,
        _payload(as_of_date="2026-06-01"),
        base_url=loopback.base,
    )

    assert proc.returncode != 0
    assert proc.stdout == ""
    payload = _error(proc.stderr)
    assert payload["schema_version"] == "1.0"
    assert payload["status"] == "failed"
    assert payload["error"]["code"] == "discovery_incomplete"
    assert payload["error"]["retryable"] is False
    assert (
        payload["error"]["acquisition_usage"]["response_bytes"] == loopback.sent_bytes
    )
    assert payload["error"]["acquisition_usage"]["cost_usd"] == "0"
    assert len(loopback.posts) == 5


def test_offline_cli_reports_bounded_discovery_empty_for_a_covered_window(
    card_root, loopback
):
    loopback.use("all_future")
    config = _write_config(card_root)
    proc = _run_cli(
        card_root,
        config,
        _payload(as_of_date="2026-06-01"),
        base_url=loopback.base,
    )

    assert proc.returncode != 0
    assert proc.stdout == ""
    payload = _error(proc.stderr)
    assert payload["error"]["code"] == "bounded_discovery_empty"
    assert payload["error"]["retryable"] is False
    assert "2024-01-01" in payload["error"]["message"]
    assert "2026-06-01" in payload["error"]["message"]


def test_offline_cli_exact_year_request_is_preserved(card_root, loopback):
    loopback.use("exact_legacy_year")
    config = _write_config(card_root)
    payload = _payload()
    payload.pop("mode")
    payload.pop("as_of_date")
    payload["fiscal_year"] = 2024
    proc = _run_cli(card_root, config, payload, base_url=loopback.base)

    assert proc.returncode == 0, proc.stderr
    candidates = _one_json(proc.stdout)["candidates"]
    assert [c["fiscal_year"] for c in candidates] == [2024]
    assert loopback.posts[0]["seDate"] == "2024-01-01~2025-12-31"


def test_offline_cli_stops_at_the_shared_response_byte_budget(card_root, loopback):
    loopback.use("exact_legacy_year")
    config = _write_config(card_root)
    payload = _payload()
    payload.pop("mode")
    payload.pop("as_of_date")
    payload["fiscal_year"] = 2024
    payload["acquisition_budget"] = {
        "schema_version": "1.0",
        "max_response_bytes": 8,
        "timeout_seconds": 30,
        "max_cost_usd": "0",
    }
    proc = _run_cli(card_root, config, payload, base_url=loopback.base)

    assert proc.returncode != 0
    assert proc.stdout == ""
    error = _error(proc.stderr)["error"]
    assert error["code"] == "budget_exceeded"
    assert error["retryable"] is False
    assert error["acquisition_usage"]["response_bytes"] <= 8


def test_offline_literal_m_entry_rejects_bad_request_before_any_http(
    card_root, loopback
):
    """The card's literal command line, with no request the provider can serve."""
    config = _write_config(card_root)
    proc = _run_cli(
        card_root,
        config,
        _payload(as_of_date=None),
        base_url=loopback.base,
    )

    assert proc.returncode != 0
    assert proc.stdout == ""
    error = _error(proc.stderr)["error"]
    assert error["retryable"] is False
    assert "as_of_date" in error["message"]
    assert loopback.posts == [], "a malformed request must not reach the network"


def test_offline_literal_m_entry_rejects_unknown_mode(card_root, loopback):
    config = _write_config(card_root)
    proc = _run_cli(
        card_root,
        config,
        _payload(mode="approximate"),
        base_url=loopback.base,
    )

    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "mode" in _error(proc.stderr)["error"]["message"]
    assert loopback.posts == []


# ---------------------------------------------------------------------------
# fetch: loopback synthetic PDF to this card's staging
# ---------------------------------------------------------------------------


def _discover_candidate(card_root, config, loopback) -> dict:
    loopback.use("exact_legacy_year")
    payload = _payload()
    payload.pop("mode")
    payload.pop("as_of_date")
    payload["fiscal_year"] = 2024
    proc = _run_cli(card_root, config, payload, base_url=loopback.base)
    assert proc.returncode == 0, proc.stderr
    candidates = _one_json(proc.stdout)["candidates"]
    assert len(candidates) == 1
    return candidates[0]


def test_offline_fetch_stages_loopback_pdf_with_real_sha_and_size(card_root, loopback):
    config = _write_config(card_root)
    candidate = _discover_candidate(card_root, config, loopback)
    staging = card_root / "staging-fetch"
    loopback.gets.clear()

    proc = _run_cli(
        card_root,
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
    assert staged.read_bytes().startswith(b"%PDF-")
    assert receipt["byte_size"] == len(_PDF)
    assert receipt["content_sha256"] == _PDF_SHA256
    assert receipt["adapter_name"] == "stockinfo-cninfo"
    assert receipt["adapter_version"] == "1.3.0"
    assert list(staging.glob("*.part")) == []
    assert loopback.gets and loopback.gets[0].startswith("/finalpage/")
    _safe_rmtree(staging)


def test_offline_fetch_over_budget_removes_partial_files(card_root, loopback):
    config = _write_config(card_root)
    candidate = _discover_candidate(card_root, config, loopback)
    staging = card_root / "staging-oversize"

    proc = _run_cli(
        card_root,
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
    _safe_rmtree(staging)


# ---------------------------------------------------------------------------
# company-wiki 5930a644 consumption of the 1.3.0 response
# ---------------------------------------------------------------------------


@contextmanager
def _chdir(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _export_cwp_package(dest: Path) -> None:
    archive = subprocess.run(
        [
            "git",
            "-C",
            str(CWP_REPO),
            "archive",
            "--format=tar",
            CWP_COMMIT,
            "src/company_wiki",
        ],
        stdout=subprocess.PIPE,
        check=True,
    )
    extract = dest / "_x"
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as bundle:
        bundle.extractall(extract, filter="data")
    shutil.move(str(extract / "src" / "company_wiki"), str(dest / "company_wiki"))
    shutil.rmtree(extract, ignore_errors=True)


def _cwp_child_env(base_url: str) -> dict[str, str]:
    env = dict(os.environ)
    python_path = [str(BOOTSTRAP), str(WORKTREE)]
    if env.get("PYTHONPATH"):
        python_path.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(python_path)
    env["G4_LOOPBACK"] = base_url
    env["PYTHONUTF8"] = "1"
    # Keep interpreter caches out of this worktree: only the sources this card
    # owns should ever appear on disk here.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _seed_org_mapping(root: Path) -> Path:
    """Give the provider a local org-id cache so nothing reaches the network.

    company-wiki's ``SourceRequest`` has no ``org_id`` field, so the CLI falls
    back to ``StockDownloader.mapping``.  Without a local cache that path would
    issue a live cninfo lookup; seeding the cache keeps the run at zero
    external requests while leaving the production lookup code untouched.
    """
    path = root / "stock_orgid_mapping.json"
    path.write_text(
        json.dumps(
            {
                SEC: {
                    "orgId": ORG,
                    "name": NAME,
                    "source": "g4-offline-fixture",
                    "confidence": 1.0,
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


@pytest.mark.skipif(not CWP_REPO.exists(), reason="company-wiki repo not available")
def test_cwp_discover_bounded_consumes_the_1_3_0_response(card_root, loopback):
    loopback.use("annual_cutover")
    config = _write_config(card_root)
    seeded_mapping = _seed_org_mapping(card_root)
    export_root = card_root / "cwp-export"
    export_root.mkdir(parents=True, exist_ok=True)
    _export_cwp_package(export_root)

    sys.path.insert(0, str(export_root))
    saved_env = {
        key: os.environ.get(key) for key in ("PYTHONPATH", "G4_LOOPBACK", "PYTHONUTF8")
    }
    try:
        with _chdir(card_root):
            from company_wiki.source_catalog.adapter_process import (
                AdapterProcessError,
                JsonCommandAdapter,
            )
            from company_wiki.source_catalog.download_budget import AcquisitionBudget
            from company_wiki.source_catalog.resolver import SourceRequest

            adapter = JsonCommandAdapter(
                name="stockinfo-cninfo",
                version="1.3.0",
                command=[
                    sys.executable,
                    "-m",
                    "src.company_wiki_adapter_cli",
                    "--config",
                    str(config),
                ],
                project_root=card_root,
                timeout_seconds=120,
                supports_acquisition_budget=True,
            )
            request = SourceRequest(
                entity=NAME,
                market="CN",
                security_id=SEC,
                document_kind="annual_report",
                fiscal_year=None,
                fiscal_period=None,
                form_type=None,
                as_of_date="2026-02-01",
                mode="latest_as_of",
                provider="cninfo",
            )
            budget = AcquisitionBudget.from_limits(
                max_response_bytes=1_048_576,
                max_seconds=60,
                max_cost_usd="0",
            )
            os.environ.update(_cwp_child_env(loopback.base))

            candidates = adapter.discover_bounded(request, budget)

            assert len(candidates) == 1
            candidate = candidates[0]
            assert candidate.candidate_id == "cninfo:900001001"
            assert candidate.provider_document_id == "900001001"
            assert candidate.entity == NAME
            assert candidate.fiscal_year == 2024
            assert candidate.fiscal_period == "FY"
            assert candidate.form_type == "annual_report"
            assert candidate.filing_date == "2025-03-20"
            assert candidate.document_kind == "annual_report"
            assert budget.response_bytes_used == loopback.sent_bytes > 0
            assert budget.cost_usd_used == 0

            payload = json.loads(candidate.adapter_payload_json)
            assert payload["fiscal_year"] == 2024
            assert payload["fiscal_period"] == "FY"
            assert payload["filing_date"] == "2025-03-20"
            assert payload["transport_url"].startswith("https://static.cninfo.com.cn/")

            # A route that still advertises 1.2.0 must be rejected, which is
            # why main_wiring.md requires the production route bump.
            stale = JsonCommandAdapter(
                name="stockinfo-cninfo",
                version="1.2.0",
                command=adapter.command,
                project_root=card_root,
                timeout_seconds=120,
                supports_acquisition_budget=True,
            )
            with pytest.raises(AdapterProcessError, match="identity/version mismatch"):
                stale.discover_bounded(request, budget)
    finally:
        seeded_mapping.unlink(missing_ok=True)
        for key, value in saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        while str(export_root) in sys.path:
            sys.path.remove(str(export_root))
