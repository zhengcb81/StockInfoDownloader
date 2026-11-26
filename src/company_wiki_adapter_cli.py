"""JSON CLI for isolated company-wiki CNINFO discovery and staged fetch."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout, suppress
from dataclasses import asdict
from functools import partial
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
from .feedback_publish import RunReceipt, command_sink, state_root
from .logger import (
    diagnostic_file_failed, legacy_cleanup_console, log, machine_logging, setup_config_logging, setup_logger,
)
from .runtime_steps import capture_steps


SCHEMA_VERSION = "1.0"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stockinfo-company-wiki-adapter")
    parser.add_argument("action", choices=("discover", "fetch"))
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--staging-dir", type=Path)
    return parser


def _payload(raw: str) -> dict[str, Any]:
    value = json.loads(raw)
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
        security_id=value.get("security_id"),
    )


def _discovery_request(value: dict[str, Any]) -> AdapterDiscoveryRequest:
    """Validate the CWP request **before** any provider/browser is constructed.

    ``mode``/``as_of_date``/``fiscal_period``/``form_type`` are optional wire
    fields added by G4-SID-LATEST.  A missing or ``null`` ``mode`` keeps the
    historical exact semantics; ``latest_as_of`` additionally requires a real
    ISO ``as_of_date`` and may leave ``fiscal_year`` null.  Unknown modes and
    malformed dates fail here, so the CLI never starts a provider for a request
    it cannot honour.
    """
    security_id = value.get("security_id")
    if not isinstance(security_id, str) or not security_id.strip():
        raise ValueError("security_id is required for CN discovery")
    mode = value.get("mode")
    mode = "exact" if mode is None else mode
    fiscal_year = value.get("fiscal_year")
    if mode == "exact" and (
        isinstance(fiscal_year, bool) or not isinstance(fiscal_year, int)
    ):
        # Historical message kept for legacy exact callers.
        raise ValueError("fiscal_year is required for CN discovery")
    # Optional provider-local hint.  company-wiki never sends it; when it is
    # present the adapter skips the downloader's org-id resolution path.
    return AdapterDiscoveryRequest(
        stock_code=security_id,
        stock_name=value["entity"],
        document_kind=value["document_kind"],
        fiscal_year=fiscal_year,
        org_id=value.get("org_id"),
        suffix="periodicReports",
        max_pages=5,
        mode=mode,
        as_of_date=value.get("as_of_date"),
        fiscal_period=value.get("fiscal_period"),
        form_type=value.get("form_type"),
    )


def _build_adapter(config_path: str | None) -> StockInfoCompanyWikiAdapter:
    """Build the pure-API provider runtime.

    Direct callers supplying a path still get config validation. The CLI
    passes None because it already loaded that config for its own diagnostics. No
    ``StockDownloader`` is constructed: that would create the failed-download
    log directory and wire the browser-backed mapping in, neither of which the
    company-wiki discover/fetch runtime needs.
    """
    if config_path is not None:
        load_config(config_path)
    return StockInfoCompanyWikiAdapter(None)


def _cleanup(adapter: StockInfoCompanyWikiAdapter) -> None:
    """Release the legacy downloader when this adapter still carries one.

    A downloader-less adapter (the pure-API runtime, or a test double) must not
    turn into an ``AttributeError`` that masks the original outcome.
    """
    downloader = getattr(adapter, "downloader", None)
    if downloader is not None:
        with legacy_cleanup_console():
            downloader.cleanup()


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

# Verification-stage AdapterError codes (post-fetch local checks).
_VERIFICATION_CODES = {"staging_escape", "content_too_small", "pdf_magic_invalid"}


def _cause_types(exc: BaseException) -> list[str]:
    """Sanitized exception type chain: stable names only, no message text."""
    chain: list[str] = []
    current: BaseException | None = exc
    for _ in range(6):
        if current is None:
            break
        name = type(current).__name__
        if name not in chain:
            chain.append(name)
        current = current.__cause__ or current.__context__
    return chain


def _resolve_stage(exc: BaseException, tracked: str, action: str) -> str:
    """Map the failing phase to one stable stage token.

    The tracked token already covers the CLI's own phases (payload, request,
    config, budget).  Inside the adapter phase the exception itself decides:
    provider-reported codes are transport/identity, local fetch errors are
    staging, post-fetch checks are verification.  Distinct failure natures
    keep distinct stages even when the outer code stays upstream_unavailable.
    """
    if tracked not in ("discover", "fetch"):
        return tracked
    if isinstance(exc, AcquisitionBudgetExceeded):
        return "budget"
    code = getattr(exc, "code", None)
    if isinstance(code, str) and code:
        if code in _VERIFICATION_CODES:
            return "verification"
        if code == "org_id_unresolved":
            return "identity"
        if code == "candidate_missing_transport":
            return "request"
        return "transport"
    if isinstance(exc, OSError):
        return "staging" if action == "fetch" else "transport"
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return "request"
    return "transport"


def _sent_state(stage: str, *, prior_phase: str) -> str:
    """Whether anything actually went out for this failure.

    Only a refusal before any provider interaction is known-not-sent.  A raw
    ``OSError`` inside ``fetch`` can be a pre-send staging setup failure *or*
    a post-response local write failure (part file, replace, stat), so the
    staging stage can never claim known-not-sent — it stays unknown.  A failed
    transport attempt may or may not have reached the provider; post-fetch
    checks mean a real response arrived.
    """
    if prior_phase in ("payload", "request", "config"):
        return "not_sent"
    if stage == "verification":
        return "sent"
    return "unknown"


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
    # Typed adapter/transport errors carry their stable identity; prefer it
    # over message sniffing.  ``None`` keeps the historical classification.
    typed_code = getattr(exc, "code", None)
    if typed_code is None:
        typed_code = getattr(exc, "error_code", None)
    typed_retryable = getattr(exc, "retryable", None)
    retryable = (
        typed_retryable
        if isinstance(typed_retryable, bool)
        else exc_type not in _NON_RETRYABLE_TYPES
    )
    error: dict[str, Any] = {
        "code": (
            typed_code
            if isinstance(typed_code, str) and typed_code
            else (
                "budget_exceeded"
                if isinstance(exc, AcquisitionBudgetExceeded)
                else "upstream_unavailable"
            )
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


def _configure_command_log(config: dict[str, Any] | None) -> bool:
    """Open the configured file or the existing SID-owned diagnostic location."""
    failure_type = None
    if config is not None:
        try:
            setup_config_logging(config, console=False)
            return True
        except (OSError, RuntimeError, ValueError) as exc:
            failure_type = type(exc).__name__
    try:
        setup_logger(log_file=str(state_root() / "logs" / "adapter.log"), console=False)
    except (OSError, RuntimeError, ValueError):
        return False
    if failure_type is not None:
        log.warning("adapter_log_setup_failed exception_type=%s", failure_type)
    return True


def _unavailable_notice(run: RunReceipt, logging_available: bool, sink) -> None:
    if ((not logging_available or diagnostic_file_failed()) and not run.available
            and (sink is None or sink.write_failures)):
        run_id, attempt_id = run.identity
        with suppress(OSError, ValueError):
            sys.stderr.write(f"SID diagnostics unavailable run_id={run_id} attempt_id={attempt_id}\n")


def main(argv: Sequence[str] | None = None) -> int:
    with machine_logging():
        return _main(argv)


def _main(argv: Sequence[str] | None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    try:
        args = _parser().parse_args(argv)
    except SystemExit as failure:
        if failure.code:
            run = RunReceipt(entry="adapter", version=ADAPTER_VERSION)
            logging_available = _configure_command_log(None)
            sink = None
            try:
                sink = command_sink(ADAPTER_VERSION, identity=run.identity)
                action = sink.action(step_id="adapter-arguments", check_id="adapter-request",
                                     expected="parsed")
                action.finish("invalid_arguments", disposition="expected",
                              refusal_code="invalid_arguments",
                              details={"action": "adapter-arguments", "stage": "arguments", "sent": "not_sent"})
                log.warning("adapter_arguments_refused run_id=%s exit_code=%s", sink.run_id, failure.code)
            except (OSError, ValueError, TypeError):
                pass
            run.checkpoint("adapter-entry", {"stage": "arguments", "executed_state": "refused", "sent": "not_sent"})
            run.finish({"result": "not_started", "exit_code": failure.code})
            _unavailable_notice(run, logging_available, sink)
        raise
    run = RunReceipt(entry="adapter", version=ADAPTER_VERSION)
    run.checkpoint("adapter-entry", {"stage": "config", "executed_state": "loading", "sent": "not_sent"})
    config_failure = None
    try:
        config = load_config(args.config)
    except Exception as exc:
        config = None
        config_failure = exc
    logging_available = _configure_command_log(config)
    # Explicit sidecars keep their format; direct execution uses owner delivery.
    sink = None
    feedback = None
    fb = None

    def _begin_feedback(input_value: dict[str, Any] | str) -> None:
        nonlocal sink, feedback, fb
        try:
            from . import feedback_observation as fb

            configured_sink = command_sink(ADAPTER_VERSION, identity=run.identity)
            check_id, expected = (
                (fb.CHECK_STAGED_FETCH, "staged") if args.action == "fetch"
                else (fb.CHECK_CANDIDATE_IDENTITY, "verified")
            )
            action = configured_sink.action(
                step_id=fb.request_step_id(args.action, input_value),
                check_id=check_id,
                expected=expected,
            )
            action.begin()
        except (ImportError, OSError, ValueError, RecursionError) as exc:
            log.warning("feedback_setup_failed exception_type=%s", type(exc).__name__)
        else:
            sink, feedback = configured_sink, action

    def _emit_budget(actual: str, disposition: str) -> None:
        if fb is None or sink is None or feedback is None or budget is None or not sink.enabled:
            return
        sink.emit(
            fb.make_observation(
                run_id=sink.run_id,
                attempt_id=sink.attempt_id,
                step_id=feedback.step_id,
                check_id=fb.CHECK_ACQUISITION_BUDGET,
                expected="within_budget",
                actual=actual,
                disposition=disposition,
                version=ADAPTER_VERSION,
            )
        )

    adapter: StockInfoCompanyWikiAdapter | None = None
    budget: ProviderAcquisitionBudget | None = None
    failure: BaseException | None = None
    result: dict[str, Any] | None = None
    # The failing phase, tracked as the request moves through the CLI.  A
    # refusal records which stage rejected it; the payload stage is the
    # default because nothing else has started yet.
    stage = "payload"
    try:
        run.checkpoint("adapter-entry", {"stage": stage, "executed_state": "awaiting_input", "sent": "not_sent"})
        raw_input = sys.stdin.read()
        try:
            value = _payload(raw_input)
        except ValueError:
            _begin_feedback(raw_input)
            raise
        _begin_feedback(value)
        step_id = feedback.step_id if feedback is not None else "adapter-entry"
        run.checkpoint(step_id, {"stage": stage, "executed_state": "parsed", "sent": "not_sent"})
        if "acquisition_budget" in value:
            stage = "budget"
            budget = ProviderAcquisitionBudget.from_payload(value["acquisition_budget"])
        with redirect_stdout(sys.stderr):
            request: AdapterDiscoveryRequest | None = None
            if args.action == "discover":
                # Request shape is validated first: a malformed request must
                # never construct the provider, its browser, or its network.
                stage = "request"
                request = _discovery_request(value)
            stage = "config"
            if config_failure is not None:
                raise config_failure
            adapter = _build_adapter(None)
            stage = args.action
            if args.action == "discover":
                assert request is not None
                run.checkpoint(step_id, {"stage": stage, "executed_state": "dispatching",
                                         "security_id": request.stock_code, "mode": request.mode, "sent": "unknown"})
                with capture_steps(partial(run.checkpoint, step_id)):
                    candidates = (
                        adapter.discover(request)
                        if budget is None
                        else adapter.discover(request, acquisition_budget=budget)
                    )
                run.checkpoint(step_id, {
                    "stage": stage, "executed_state": "observed", "candidate_count": len(candidates),
                    "budget_usage": budget.usage() if budget is not None else None,
                })
                published = [item.to_dict() for item in candidates]
                if feedback is not None:
                    security_id = request.stock_code
                    deviations = [
                        (index, verdict)
                        for index, payload in enumerate(published)
                        if (verdict := fb.classify_candidate_identity(payload, security_id))[
                            "disposition"
                        ] == "deviation"
                    ]
                    details: dict[str, Any] = {
                        "action": (
                            "discover_exact"
                            if request.mode == "exact"
                            else "discover_latest"
                        ),
                        "mode": request.mode,
                        "security_id": security_id,
                        "announcement_ids": [
                            item.provider_document_id for item in candidates
                        ],
                        "budget_usage": budget.usage() if budget is not None else None,
                        "source_result": "ok" if candidates else "no_candidates",
                        "retried": False,
                        "reused": False,
                    }
                    if not deviations:
                        first = candidates[0].provider_document_id if candidates else None
                        feedback.finish(
                            "verified" if candidates else "no_candidates",
                            disposition="expected",
                            evidence_ref=fb.cninfo_announcement_ref(first),
                            details=details,
                        )
                    else:
                        index, verdict = deviations[0]
                        details["error_code"] = verdict["actual"]
                        proof = None
                        # One observation covers this discover step. A single
                        # candidate proof cannot close additional deviations.
                        if (
                            len(deviations) == 1
                            and verdict["issue_key"] == fb.ISSUE_VERIFIED_ID_MISSING
                            and sink.path is not None
                        ):
                            try:
                                from .feedback_candidate_capture import capture_missing_identity

                                proof = capture_missing_identity(
                                    sink.path,
                                    {
                                        "owner": fb.OWNER,
                                        "origin_owner": fb.OWNER,
                                        "run_id": sink.run_id,
                                        "attempt_id": sink.attempt_id,
                                        "step_id": feedback.step_id,
                                        "check_id": feedback.check_id,
                                        "version": sink.version,
                                    },
                                    security_id,
                                    published[index],
                                    asdict(candidates[index]),
                                )
                            except (ImportError, OSError, TypeError, ValueError, RecursionError) as exc:
                                log.debug("candidate proof unavailable: %s", type(exc).__name__)
                        feedback.finish(
                            verdict["actual"],
                            disposition="deviation",
                            issue_key=verdict["issue_key"],
                            evidence_ref=proof,
                            details=details,
                        )
                result_payload: dict[str, Any] = {"candidates": published}
                if budget is not None:
                    result_payload["acquisition_usage"] = budget.usage()
                    _emit_budget("within_budget", "expected")
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
                candidate = _candidate(decoded)
                run.checkpoint(step_id, {"stage": stage, "executed_state": "dispatching",
                                         "provider_document_id": candidate.provider_document_id, "sent": "unknown"})
                with capture_steps(partial(run.checkpoint, step_id)):
                    receipt = (
                        adapter.fetch(candidate, args.staging_dir)
                        if budget is None
                        else adapter.fetch(candidate, args.staging_dir, acquisition_budget=budget)
                    )
                run.checkpoint(step_id, {
                    "stage": "staging", "executed_state": "confirmed",
                    "provider_document_id": receipt.provider_document_id,
                    "budget_usage": budget.usage() if budget is not None else None,
                })
                if feedback is not None:
                    document_id = receipt.provider_document_id
                    feedback.finish(
                        "staged",
                        disposition="expected",
                        evidence_ref=fb.cninfo_announcement_ref(document_id),
                        details={
                            "action": "fetch",
                            "security_id": decoded.get("security_id"),
                            "provider_document_id": document_id,
                            "budget_usage": budget.usage() if budget is not None else None,
                            "source_result": "staged",
                            "retried": False,
                            "reused": False,
                        },
                    )
                result_payload = {"receipt": receipt.to_dict()}
                if budget is not None:
                    result_payload["acquisition_usage"] = budget.usage()
                    _emit_budget("within_budget", "expected")
                result = _response(**result_payload)
    except Exception as exc:
        failure = exc
        failure_stage = _resolve_stage(exc, stage, args.action)
        sent = _sent_state(failure_stage, prior_phase=stage)
        if feedback is None:
            _begin_feedback("adapter-entry")
        run.checkpoint(feedback.step_id if feedback is not None else "adapter-entry", {
            "stage": failure_stage, "executed_state": "failed", "sent": sent, "cause_types": _cause_types(exc),
            "budget_usage": budget.usage() if budget is not None else None,
        })
        log.warning(
            "adapter_failure run_id=%s step_id=%s action=%s phase=%s sent=%s",
            run.identity[0],
            feedback.step_id if feedback is not None else "unbound",
            args.action,
            failure_stage,
            sent,
            exc_info=True,
        )
        if feedback is not None and not feedback.finished:
            code = getattr(exc, "code", None) or getattr(exc, "error_code", None)
            if not isinstance(code, str) or not code or not fb.is_safe_ref(code):
                code = (
                    "budget_exceeded"
                    if isinstance(exc, AcquisitionBudgetExceeded)
                    else type(exc).__name__
                )
            # Same outer code family, but the details distinguish the real
            # nature: failing stage, whether anything went out, and the
            # sanitized exception type chain (F4: 不把性质不同的失败合并).
            justified_refusal = sent == "not_sent" and failure_stage in {"payload", "request"}
            expected = justified_refusal or isinstance(exc, AcquisitionBudgetExceeded)
            feedback.finish(
                code,
                disposition="expected" if expected else "deviation",
                refusal_code="invalid_request" if justified_refusal else "budget_exceeded"
                if isinstance(exc, AcquisitionBudgetExceeded) else None,
                details={
                    "action": args.action,
                    "code_site": "company_wiki_adapter_cli.py:failure-handler",
                    "error_code": code,
                    "retryable": getattr(exc, "retryable", None),
                    "stage": failure_stage,
                    "sent": sent,
                    # Stable cause chain (FB-SID 33): typed code -> outcome
                    # class.  No message text / path / exception repr leaks.
                    "cause_chain": [
                        code,
                        "retryable" if getattr(exc, "retryable", None) else "terminal",
                    ],
                    "cause_types": _cause_types(exc),
                    "budget_usage": budget.usage() if budget is not None else None,
                },
            )
            _emit_budget(code, "expected")
    finally:
        # An interrupt before a terminal state must stay unknown, and cleanup
        # must not turn that into a success report.
        if feedback is not None and not feedback.finished:
            feedback.finish("unknown", disposition="unknown")
        # Cleanup can log; it must happen *before* the protocol document so the
        # documented "last stderr line is the JSON" contract keeps holding.  A
        # cleanup failure must not swallow the original outcome.
        if adapter is not None:
            try:
                with redirect_stdout(sys.stderr):
                    _cleanup(adapter)
            except Exception:  # pragma: no cover - defensive
                log.warning("adapter cleanup failed", exc_info=True)
    if failure is not None:
        run.finish({"result": "failed", "exit_code": 1})
        _unavailable_notice(run, logging_available, sink)
        return _emit_failure(failure, budget)
    if result is None:  # pragma: no cover - defensive
        run.finish({"result": "failed", "exit_code": 1})
        _unavailable_notice(run, logging_available, sink)
        return _emit_failure(RuntimeError("provider produced no result"), budget)
    run.finish({"result": "completed", "exit_code": 0})
    _unavailable_notice(run, logging_available, sink)
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
