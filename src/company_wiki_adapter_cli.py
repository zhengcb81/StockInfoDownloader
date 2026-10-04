"""JSON CLI for isolated company-wiki CNINFO discovery and staged fetch."""

from __future__ import annotations

import argparse
import logging
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from .acquisition_budget import (
    AcquisitionBudgetExceeded,
    ProviderAcquisitionBudget,
)
from .company_wiki_adapter import (
    ADAPTER_NAME,
    ADAPTER_VERSION,
    AdapterDiscoveryRequest,
    DisclosureCandidate,
    StockInfoCompanyWikiAdapter,
)
from .config import load_config
from .downloader import StockDownloader
from .logger import log


SCHEMA_VERSION = "1.0"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stockinfo-company-wiki-adapter")
    parser.add_argument("action", choices=("discover", "fetch"))
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--staging-dir", type=Path)
    return parser


def _payload() -> dict[str, Any]:
    value = json.loads(sys.stdin.read())
    if not isinstance(value, dict):
        raise ValueError("stdin payload must be a JSON object")
    return value


def _candidate(value: dict[str, Any]) -> DisclosureCandidate:
    return DisclosureCandidate(
        candidate_id=value["candidate_id"],
        provider=value["provider"],
        provider_document_id=value["provider_document_id"],
        identity_method=value["identity_method"],
        market=value["market"],
        entity=value["entity"],
        title=value["title"],
        source_url=value["source_url"],
        document_kind=value["document_kind"],
        form_type=value["form_type"],
        filing_date=value["filing_date"],
        fiscal_year=value["fiscal_year"],
        fiscal_period=value["fiscal_period"],
        language=value["language"],
        amended=value["amended"],
        transport_url=value.get("transport_url", ""),
    )


def _build_adapter(config_path: str) -> StockInfoCompanyWikiAdapter:
    return StockInfoCompanyWikiAdapter(StockDownloader(load_config(config_path)))


def _response(**payload: Any) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "adapter": {"name": ADAPTER_NAME, "version": ADAPTER_VERSION},
        **payload,
    }


# Stable error codes shared with company-wiki ``AdapterProcessError``.
# Wraps the downloader via StockInfoCompanyWikiAdapter, so any non-Value
# exception defaults to retryable upstream_unavailable. ValueError /
# TypeError / KeyError are contract-level and never auto-retryable.
_NON_RETRYABLE_TYPES = (
    "ValueError",
    "TypeError",
    "KeyError",
    "AcquisitionBudgetExceeded",
)


def _emit_failure(
    exc: BaseException,
    budget: ProviderAcquisitionBudget | None = None,
) -> int:
    """Emit the structured 1.0 failure JSON on stderr and return nonzero exit.

    The shape intentionally mirrors the success response schema for
    schema_version / status / adapter fields; ``error`` carries a stable
    ``code`` + ``retryable`` so the company-wiki side can degrade safely
    when parsing legacy/unknown stderr.
    """
    exc_type = type(exc).__name__
    retryable = exc_type not in _NON_RETRYABLE_TYPES
    error: dict[str, Any] = {
        "code": (
            "budget_exceeded"
            if isinstance(exc, AcquisitionBudgetExceeded)
            else "upstream_unavailable"
        ),
        "type": exc_type,
        "message": str(exc),
        "retryable": retryable,
    }
    if budget is not None:
        error["acquisition_usage"] = budget.usage()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "failed",
        "adapter": {"name": ADAPTER_NAME, "version": ADAPTER_VERSION},
        "error": error,
    }
    sys.stderr.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return 1


def _redirect_console_logs_to_stderr() -> None:
    """Keep the JSON-lines stdout channel free of logger diagnostics."""
    for handler in log.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.FileHandler
        ):
            handler.setStream(sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = _parser().parse_args(argv)
    _redirect_console_logs_to_stderr()
    adapter: StockInfoCompanyWikiAdapter | None = None
    budget: ProviderAcquisitionBudget | None = None
    try:
        value = _payload()
        if "acquisition_budget" in value:
            budget = ProviderAcquisitionBudget.from_payload(
                value["acquisition_budget"]
            )
        with redirect_stdout(sys.stderr):
            adapter = _build_adapter(args.config)
            if args.action == "discover":
                security_id = value.get("security_id")
                fiscal_year = value.get("fiscal_year")
                if not isinstance(security_id, str) or not security_id.strip():
                    raise ValueError("security_id is required for CN discovery")
                if isinstance(fiscal_year, bool) or not isinstance(fiscal_year, int):
                    raise ValueError("fiscal_year is required for CN discovery")
                request = AdapterDiscoveryRequest(
                    stock_code=security_id,
                    stock_name=value["entity"],
                    document_kind=value["document_kind"],
                    fiscal_year=fiscal_year,
                    suffix="periodicReports",
                    max_pages=5,
                )
                candidates = (
                    adapter.discover(request)
                    if budget is None
                    else adapter.discover(request, acquisition_budget=budget)
                )
                result_payload: dict[str, Any] = {
                    "candidates": [item.to_dict() for item in candidates]
                }
                if budget is not None:
                    result_payload["acquisition_usage"] = budget.usage()
                result = _response(**result_payload)
            else:
                if args.staging_dir is None:
                    raise ValueError("--staging-dir is required for fetch")
                raw = value.get("adapter_payload_json")
                if not isinstance(raw, str):
                    raise ValueError("adapter_payload_json is required for fetch")
                decoded = json.loads(raw)
                if not isinstance(decoded, dict):
                    raise ValueError("adapter_payload_json must contain an object")
                receipt = (
                    adapter.fetch(_candidate(decoded), args.staging_dir)
                    if budget is None
                    else adapter.fetch(
                        _candidate(decoded),
                        args.staging_dir,
                        acquisition_budget=budget,
                    )
                )
                result_payload = {"receipt": receipt.to_dict()}
                if budget is not None:
                    result_payload["acquisition_usage"] = budget.usage()
                result = _response(**result_payload)
    except Exception as exc:
        return _emit_failure(exc, budget)
    finally:
        if adapter is not None:
            with redirect_stdout(sys.stderr):
                adapter.downloader.cleanup()
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
