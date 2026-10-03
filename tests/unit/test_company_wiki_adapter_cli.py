"""JSON-only CLI contract for the company-wiki StockInfo bridge."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace


class _FakeAdapter:
    name = "stockinfo-cninfo"
    version = "1.0.0"

    def __init__(self):
        self.downloader = SimpleNamespace(cleanup=lambda: None)

    def discover(self, request):
        from src.company_wiki_adapter import DisclosureCandidate

        assert request.stock_code == "600000"
        return (
            DisclosureCandidate(
                candidate_id="cninfo:1",
                provider="cninfo",
                provider_document_id="1",
                identity_method="announcement_id",
                market="CN",
                entity=request.stock_code,
                title="示例公司2025年年度报告",
                source_url="https://example.invalid/report.pdf",
                document_kind="annual_report",
                form_type="annual_report",
                filing_date="2026-03-20",
                fiscal_year=2025,
                fiscal_period="FY",
                language="zh-CN",
                amended=False,
            ),
        )

    def fetch(self, candidate, staging_dir):
        from src.company_wiki_adapter import StagedDownloadReceipt

        path = staging_dir / "report.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        body = b"%PDF-1.7\ncli bytes"
        path.write_bytes(body)
        return StagedDownloadReceipt(
            candidate_id=candidate.candidate_id,
            provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            source_url=candidate.source_url,
            staged_path=str(path),
            content_sha256=hashlib.sha256(body).hexdigest(),
            byte_size=len(body),
            mime_type="application/pdf",
            retrieved_at="2026-07-18T12:00:00Z",
            http_status=200,
            adapter_name=self.name,
            adapter_version=self.version,
        )


def _invoke(monkeypatch, module, argv, payload):
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.setattr(module.sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(module.sys, "stdout", stdout)
    monkeypatch.setattr(module.sys, "stderr", stderr)
    code = module.main(argv)
    return code, json.loads(stdout.getvalue()), stderr.getvalue()


def test_cli_discover_and_fetch_emit_one_json_value(monkeypatch, tmp_path: Path):
    import src.company_wiki_adapter_cli as module

    monkeypatch.setattr(module, "_build_adapter", lambda _: _FakeAdapter())
    request = {
        "entity": "示例公司",
        "security_id": "600000",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
    }
    code, discovered, _ = _invoke(monkeypatch, module, ["discover"], request)
    candidate = discovered["candidates"][0]
    fetch_payload = {
        **candidate,
        "adapter_payload_json": json.dumps(candidate, ensure_ascii=False),
    }
    fetch_code, fetched, _ = _invoke(
        monkeypatch,
        module,
        ["fetch", "--staging-dir", str(tmp_path / "staging")],
        fetch_payload,
    )

    assert code == 0
    assert discovered["status"] == "ok"
    assert fetch_code == 0
    assert fetched["receipt"]["adapter_name"] == "stockinfo-cninfo"
    assert Path(fetched["receipt"]["staged_path"]).is_file()
