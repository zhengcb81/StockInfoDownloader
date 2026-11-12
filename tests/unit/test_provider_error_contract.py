"""MB-SID provider error contract — stable code / retryability / usage.

All cases run through the *public* adapter CLI (``python -m
src.company_wiki_adapter_cli fetch``) with a local HTTP double, so the
assertion covers the whole transport → adapter → CLI chain rather than a single
helper.

The historical behaviour folded every transport failure into
``upstream_unavailable`` with ``retryable=true``: the adapter re-raised a bare
``AdapterError`` and the CLI fell back to its default classification.  A caller
therefore retried permanent failures (wrong host, HTML challenge page, empty
body) and could not distinguish them from a real network outage.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

WORKTREE = Path(__file__).resolve().parents[2]

CANDIDATE = {
    "candidate_id": "cninfo:900001001",
    "provider": "cninfo",
    "provider_document_id": "900001001",
    "identity_method": "announcement_id",
    "market": "CN",
    "entity": "600000",
    "title": "示例公司2024年年度报告",
    "source_url": (
        "https://www.cninfo.com.cn/new/disclosure/detail?announcementId=900001001"
    ),
    "document_kind": "annual_report",
    "form_type": "annual_report",
    "filing_date": "2025-03-24",
    "fiscal_year": 2024,
    "fiscal_period": "FY",
    "language": "zh-CN",
    "amended": False,
    "transport_url": "https://static.cninfo.com.cn/finalpage/2025-03-24/900001001.PDF",
}


class _Body:
    """Minimal ``urlopen`` result with a controlled body and content type."""

    def __init__(self, body: bytes, content_type: str = "application/pdf") -> None:
        self._body = body
        self._offset = 0
        self.status = 200
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
        }

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            chunk = self._body[self._offset :]
        else:
            chunk = self._body[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk

    def __enter__(self) -> "_Body":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def _config(root: Path) -> Path:
    config = {
        "save_dir": str(root / "downloads"),
        "headless": True,
        "max_retries": 1,
        "timeout_seconds": 30,
        "browser": {"strategy": "playwright", "headless": True},
        "download": {"max_pages": 1, "download_delay": 0.0},
        "logging": {"level": "WARNING", "log_to_file": False},
        "pages": [],
        "companies": [],
        "test_cases": [],
    }
    path = root / "config.json"
    path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return path


def _payload(**candidate_overrides) -> dict:
    candidate = {**CANDIDATE, **candidate_overrides}
    return {
        **candidate,
        "adapter_payload_json": json.dumps(candidate, ensure_ascii=False),
        "acquisition_budget": {
            "schema_version": "1.0",
            "max_response_bytes": 8192,
            "timeout_seconds": 30,
            "max_cost_usd": "0",
        },
    }


def _run_fetch(monkeypatch, tmp_path: Path, payload: dict):
    """Invoke the literal CLI entry point; return (code, stdout, stderr)."""
    from src import company_wiki_adapter_cli as cli

    staging = tmp_path / "staging"
    config = _config(tmp_path)
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(cli.sys, "stdout", stdout)
    monkeypatch.setattr(cli.sys, "stderr", stderr)
    code = cli.main(
        ["fetch", "--staging-dir", str(staging), "--config", str(config)]
    )
    return code, stdout.getvalue(), stderr.getvalue(), staging


def _error(stderr: str) -> dict:
    # Diagnostics may precede the document; the contract is that the failure
    # JSON is the last line on stderr.
    payload = json.loads(stderr.strip().splitlines()[-1])
    assert payload["schema_version"] == "1.0"
    assert payload["status"] == "failed"
    return payload["error"]


# ---------------------------------------------------------------------------
# permanent transport failures must not be advertised as retryable
# ---------------------------------------------------------------------------


def test_host_outside_the_allowlist_is_non_retryable(monkeypatch, tmp_path):
    payload = _payload(transport_url="https://evil.example.com/doc.pdf")

    code, stdout, stderr, staging = _run_fetch(monkeypatch, tmp_path, payload)

    assert code == 1
    assert stdout == ""
    error = _error(stderr)
    assert error["code"] == "transport_url_host_not_allowed"
    assert error["retryable"] is False
    assert list(staging.glob("*.part")) == []


def test_non_pdf_body_is_non_retryable(monkeypatch, tmp_path):
    body = b"<html><body>challenge</body></html>" + b"x" * 512
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _Body(body))

    code, stdout, stderr, staging = _run_fetch(monkeypatch, tmp_path, _payload())

    assert code == 1
    assert stdout == ""
    error = _error(stderr)
    assert error["code"] == "pdf_magic_invalid"
    assert error["retryable"] is False
    assert list(staging.glob("*.part")) == []


def test_too_small_body_is_non_retryable(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **k: _Body(b"x" * 10)
    )

    code, stdout, stderr, staging = _run_fetch(monkeypatch, tmp_path, _payload())

    assert code == 1
    assert stdout == ""
    error = _error(stderr)
    assert error["code"] == "content_too_small"
    assert error["retryable"] is False
    assert list(staging.glob("*.part")) == []


# ---------------------------------------------------------------------------
# a real transport fault keeps its retryable identity
# ---------------------------------------------------------------------------


def test_transport_timeout_is_retryable(monkeypatch, tmp_path):
    def raise_timeout(*_args, **_kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr("urllib.request.urlopen", raise_timeout)

    code, stdout, stderr, staging = _run_fetch(monkeypatch, tmp_path, _payload())

    assert code == 1
    assert stdout == ""
    error = _error(stderr)
    assert error["code"] == "upstream_timeout"
    assert error["retryable"] is True
    assert list(staging.glob("*.part")) == []


# ---------------------------------------------------------------------------
# measured usage survives the failure path; unknown usage is not fabricated
# ---------------------------------------------------------------------------


def test_failure_reports_measured_usage_not_zero_placeholders(monkeypatch, tmp_path):
    body = b"x" * 10
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **k: _Body(body)
    )

    _code, _stdout, stderr, _staging = _run_fetch(
        monkeypatch, tmp_path, _payload()
    )

    error = _error(stderr)
    usage = error["acquisition_usage"]
    assert usage["schema_version"] == "1.0"
    assert usage["response_bytes"] == len(body)
    assert usage["cost_usd"] == "0"


def test_failure_without_a_budget_does_not_invent_usage(monkeypatch, tmp_path):
    payload = _payload()
    payload.pop("acquisition_budget")
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **k: _Body(b"x" * 10)
    )

    _code, _stdout, stderr, _staging = _run_fetch(monkeypatch, tmp_path, payload)

    error = _error(stderr)
    assert error["code"] == "content_too_small"
    assert "acquisition_usage" not in error


# ---------------------------------------------------------------------------
# the typed identity is carried by the adapter, not re-derived from the message
# ---------------------------------------------------------------------------


def test_adapter_preserves_the_upstream_error_identity(monkeypatch, tmp_path):
    from src.company_wiki_adapter import AdapterError, DisclosureCandidate
    from src.cninfo_api import CninfoAnnouncementClient
    from src.company_wiki_adapter import StockInfoCompanyWikiAdapter

    adapter = StockInfoCompanyWikiAdapter(
        None, cninfo_client=CninfoAnnouncementClient()
    )
    # A host outside the allowlist fails before any socket is opened.
    candidate = DisclosureCandidate(
        **{**CANDIDATE, "transport_url": "https://evil.example.com/doc.pdf"}
    )

    with pytest.raises(AdapterError) as caught:
        adapter.fetch(candidate, tmp_path / "staging")

    assert caught.value.code == "transport_url_host_not_allowed"
    assert caught.value.retryable is False
    assert caught.value.__cause__ is not None


def test_adapter_preserves_retryable_transport_identity(monkeypatch, tmp_path):
    from src.company_wiki_adapter import (
        AdapterError,
        DisclosureCandidate,
        StockInfoCompanyWikiAdapter,
    )
    from src.cninfo_api import CninfoAnnouncementClient

    def raise_timeout(*_args, **_kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr("urllib.request.urlopen", raise_timeout)
    adapter = StockInfoCompanyWikiAdapter(
        None, cninfo_client=CninfoAnnouncementClient()
    )
    candidate = DisclosureCandidate(**CANDIDATE)

    with pytest.raises(AdapterError) as caught:
        adapter.fetch(candidate, tmp_path / "staging")

    assert caught.value.code == "upstream_timeout"
    assert caught.value.retryable is True


def test_failure_document_is_the_last_stderr_line_even_after_cleanup_logs(
    monkeypatch, tmp_path
):
    """Cleanup runs before the failure document is written."""
    from src import company_wiki_adapter_cli as cli

    class _LoggingDownloader:
        @staticmethod
        def cleanup():
            cli.log.warning("cleanup diagnostic")

    class _BrokenAdapter:
        name = "stockinfo-cninfo"
        version = "1.3.0"
        downloader = _LoggingDownloader()

        @staticmethod
        def fetch(*_args, **_kwargs):
            raise ValueError("boom")

    staging = tmp_path / "staging"
    config = _config(tmp_path)
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.sys, "stdin", io.StringIO(json.dumps(_payload())))
    monkeypatch.setattr(cli.sys, "stdout", stdout)
    monkeypatch.setattr(cli.sys, "stderr", stderr)
    monkeypatch.setattr(cli, "_build_adapter", lambda _config: _BrokenAdapter())

    code = cli.main(["fetch", "--staging-dir", str(staging), "--config", str(config)])

    assert code == 1
    assert stdout.getvalue() == ""
    lines = stderr.getvalue().strip().splitlines()
    assert "cleanup diagnostic" in stderr.getvalue()
    assert json.loads(lines[-1])["error"]["type"] == "ValueError"


def test_failure_document_is_the_last_stderr_line_even_after_cleanup_logs(
    monkeypatch, tmp_path
):
    """Cleanup runs before the failure document is written."""
    from src import company_wiki_adapter_cli as cli

    class _LoggingDownloader:
        @staticmethod
        def cleanup():
            cli.log.warning("cleanup diagnostic")

    class _BrokenAdapter:
        name = "stockinfo-cninfo"
        version = "1.3.0"
        downloader = _LoggingDownloader()

        @staticmethod
        def fetch(*_args, **_kwargs):
            raise ValueError("boom")

    staging = tmp_path / "staging"
    config = _config(tmp_path)
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.sys, "stdin", io.StringIO(json.dumps(_payload())))
    monkeypatch.setattr(cli.sys, "stdout", stdout)
    monkeypatch.setattr(cli.sys, "stderr", stderr)
    monkeypatch.setattr(cli, "_build_adapter", lambda _config: _BrokenAdapter())

    code = cli.main(["fetch", "--staging-dir", str(staging), "--config", str(config)])

    assert code == 1
    assert stdout.getvalue() == ""
    lines = stderr.getvalue().strip().splitlines()
    assert "cleanup diagnostic" in stderr.getvalue()
    assert json.loads(lines[-1])["error"]["type"] == "ValueError"
