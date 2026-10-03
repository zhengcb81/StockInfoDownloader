"""CLI contract tests for bounded provider usage and early validation."""

from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


class _Adapter:
    def __init__(self, action):
        self.downloader = SimpleNamespace(cleanup=lambda: None)
        self._action = action

    def discover(self, request, *, acquisition_budget):
        return self._action(acquisition_budget)


def _invoke(monkeypatch, module, payload, *, adapter=None, argv=("discover",)):
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.setattr(module.sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(module.sys, "stdout", stdout)
    monkeypatch.setattr(module.sys, "stderr", stderr)
    if adapter is not None:
        monkeypatch.setattr(module, "_build_adapter", lambda _config: adapter)
    code = module.main(list(argv))
    return code, stdout.getvalue(), stderr.getvalue()


def _payload(budget=None):
    value = {
        "entity": "示例公司",
        "security_id": "600000",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
    }
    if budget is not None:
        value["acquisition_budget"] = budget
    return value


def test_cli_budgeted_success_emits_measured_usage(monkeypatch):
    from src import company_wiki_adapter_cli as cli

    def discover(budget):
        budget.consume_response_bytes(17)
        return ()

    code, stdout, stderr = _invoke(
        monkeypatch,
        cli,
        _payload(
            {
                "schema_version": "1.0",
                "max_response_bytes": 100,
                "timeout_seconds": 5.0,
                "max_cost_usd": "0",
            }
        ),
        adapter=_Adapter(discover),
    )

    assert code == 0
    assert stderr == ""
    assert json.loads(stdout)["acquisition_usage"] == {
        "schema_version": "1.0",
        "response_bytes": 17,
        "cost_usd": "0",
    }


def test_cli_budgeted_failure_preserves_partial_usage_and_is_not_retryable(
    monkeypatch,
):
    from src.acquisition_budget import AcquisitionBudgetExceeded
    from src import company_wiki_adapter_cli as cli

    def discover(budget):
        budget.consume_response_bytes(9)
        raise AcquisitionBudgetExceeded("response too large")

    code, stdout, stderr = _invoke(
        monkeypatch,
        cli,
        _payload(
            {
                "schema_version": "1.0",
                "max_response_bytes": 100,
                "timeout_seconds": 5.0,
                "max_cost_usd": "0",
            }
        ),
        adapter=_Adapter(discover),
    )

    assert code == 1
    assert stdout == ""
    error = json.loads(stderr)["error"]
    assert error["code"] == "budget_exceeded"
    assert error["retryable"] is False
    assert error["acquisition_usage"]["response_bytes"] == 9


def test_cli_rejects_malformed_budget_before_creating_provider(monkeypatch):
    from src import company_wiki_adapter_cli as cli

    monkeypatch.setattr(
        cli, "_build_adapter", lambda _config: pytest.fail("must not build")
    )
    code, stdout, stderr = _invoke(
        monkeypatch,
        cli,
        _payload(
            {
                "schema_version": "1.0",
                "max_response_bytes": True,
                "timeout_seconds": 5.0,
                "max_cost_usd": "0",
            }
        ),
    )

    assert code == 1
    assert stdout == ""
    assert json.loads(stderr)["error"]["type"] == "ValueError"


class _Response:
    def __init__(self, body: bytes, content_type: str) -> None:
        self.body = body
        self.offset = 0
        self.status = 200
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
        }

    def read(self, size: int = -1) -> bytes:
        assert size >= 0
        chunk = self.body[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _real_adapter():
    from src.company_wiki_adapter import StockInfoCompanyWikiAdapter

    class _Mapping:
        def get_org_id(self, _stock_code):
            return "gshk0001211"

    class _Downloader:
        mapping = _Mapping()

        @staticmethod
        def cleanup():
            return None

    return StockInfoCompanyWikiAdapter(_Downloader())


def test_cli_budgeted_real_discovery_path_reports_http_body_bytes(
    monkeypatch,
):
    from src import company_wiki_adapter_cli as cli

    body = b'{"totalRecordNum":0,"announcements":[],"totalpages":1}'
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: _Response(body, "application/json"),
    )
    code, stdout, stderr = _invoke(
        monkeypatch,
        cli,
        _payload(
            {
                "schema_version": "1.0",
                "max_response_bytes": 1000,
                "timeout_seconds": 5.0,
                "max_cost_usd": "0",
            }
        ),
        adapter=_real_adapter(),
    )

    assert code == 0
    assert stderr == ""
    response = json.loads(stdout)
    assert response["candidates"] == []
    assert response["acquisition_usage"]["response_bytes"] == len(body)
    assert response["acquisition_usage"]["cost_usd"] == "0"


def test_cli_budgeted_real_pdf_path_reports_receipt_bytes(monkeypatch, tmp_path: Path):
    from src import constants as C
    from src import company_wiki_adapter_cli as cli
    from src.company_wiki_adapter import DisclosureCandidate

    body = b"%PDF-" + b"x" * (C.MIN_FILE_SIZE + 100)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: _Response(body, "application/pdf"),
    )
    candidate = DisclosureCandidate(
        candidate_id="cninfo:1222881496",
        provider="cninfo",
        provider_document_id="1222881496",
        identity_method="announcement_id",
        market="CN",
        entity="002594",
        title="2024年年度报告",
        source_url=(
            "https://www.cninfo.com.cn/new/disclosure/detail?"
            "stockCode=002594&announcementId=1222881496"
        ),
        document_kind="annual_report",
        form_type="annual_report",
        filing_date="2025-03-24",
        fiscal_year=2024,
        fiscal_period="FY",
        language="zh-CN",
        amended=False,
        transport_url="https://static.cninfo.com.cn/report.PDF",
    ).to_dict()
    payload = {
        **candidate,
        "adapter_payload_json": json.dumps(candidate, ensure_ascii=False),
        "acquisition_budget": {
            "schema_version": "1.0",
            "max_response_bytes": len(body) + 100,
            "timeout_seconds": 5.0,
            "max_cost_usd": "0",
        },
    }

    code, stdout, stderr = _invoke(
        monkeypatch,
        cli,
        payload,
        adapter=_real_adapter(),
        argv=("fetch", "--staging-dir", str(tmp_path / "stage")),
    )

    assert code == 0
    assert stderr == ""
    response = json.loads(stdout)
    assert response["receipt"]["byte_size"] == len(body)
    assert response["acquisition_usage"]["response_bytes"] == len(body)
