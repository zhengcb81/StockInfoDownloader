#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stock Downloader V2 — Unified Entry Point.

Supports single company, multiple companies, parallel and sequential modes.
Compatible with config_e2e_official.json format.

F4-SID-FAILURES: the ordinary launch establishes its run identity (and a
startup receipt) before argument parsing and any side effect, settles what
each task really returned, and publishes ``feedback-observation/1``
observations through the direct-launch publication interface.  A genuine
task failure is never reported as "All tasks completed" with exit 0.

F4-SID-START-INPUT: the decision *what to run* lives in one place
(``plan_work``).  A list that cannot be read is an entry refusal on record
(run id, stage, native cause chain, nothing dispatched); an empty work list is
a legitimate ``no_tasks`` run, never "all tasks completed"; and only sub-items
that really start are counted as attempted.
"""
import concurrent.futures
from contextvars import copy_context
import sys
import threading
import time
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import load_companies, load_config
from src import constants as C
from src.downloader import StockDownloader
from src.exceptions import ConfigError
from src.feedback_publish import establish_identity, state_root
from src.logger import DiagnosticArgumentParser, diagnostic_file_failed, diagnostic_notice, entry_logging, log, setup_logger
from src.mapping import MappingManager
from src.models import DownloadRequest
from src.progress import ProgressTracker
from src.runtime_steps import capture_steps, checkpoint, exception_types, implementation_version


def get_real_stock_name(stock_code: str) -> str:
    """Get stock name from mapping."""
    try:
        mm = MappingManager()
        return mm.get_stock_name(stock_code) or f"Stock_{stock_code}"
    except Exception:
        log.debug("Stock name lookup failed for %s", stock_code, exc_info=True)
        return f"Stock_{stock_code}"


def _task_key(request: DownloadRequest) -> Dict[str, Any]:
    """The stable business intent of one download request (no local paths)."""
    return {
        "stock_code": request.stock_code,
        "suffix": request.suffix,
        "allowed_keywords": request.allowed_keywords,
        "excluded_keywords": request.excluded_keywords,
        "max_pages": request.max_pages,
        "save_subdir": request.save_subdir,
        "reverse_order": request.reverse_order,
    }


def _open_feedback(identity: tuple[str, str]):
    """Build the run feedback (identity + receipt) before argparse/side effects.

    Feedback is diagnostics: any failure here keeps the business flow alive.
    """
    try:
        from src.feedback_publish import OrdinaryRunFeedback

        return OrdinaryRunFeedback(identity=identity)
    except (OSError, RuntimeError, ValueError):
        log.warning("ordinary feedback unavailable", exc_info=True)
        return None


# ── input sources: the one place that decides what a launch runs ──────────

SETTLEMENT_KEYS = ("attempted", "succeeded", "failed", "skipped")


def _new_settlement() -> Dict[str, int]:
    """One business tally for the whole launch, kept by the runner.

    ``attempted`` counts the sub-items that really started (one company or
    one test case each); a refused or empty launch leaves every key at zero.
    """
    return {key: 0 for key in SETTLEMENT_KEYS}


# run_multi drives sub-items from a thread pool; keep the shared tally exact
# under parallel work (the F4-SID-FAILURES card already required this lock).
_SETTLEMENT_LOCK = threading.Lock()


def _bump(settlement: Dict[str, int], key: str, amount: int = 1) -> None:
    with _SETTLEMENT_LOCK:
        settlement[key] += amount


@dataclass
class WorkPlan:
    """What one launch was asked to run, and where the ask came from."""

    source: str  # cli-stock | companies-file | test-cases | config-companies | config-stock | none
    stock_code: Optional[str] = None
    companies: Optional[List[Dict[str, Any]]] = None
    test_cases: Optional[List[Dict[str, Any]]] = None
    # Company-list runs resume through the progress tracker under this name.
    progress_name: Optional[str] = None
    reason: str = ""  # source == "none": why nothing was asked


def _specified_items(config: Dict[str, Any], key: str) -> Optional[List[Any]]:
    """The list a caller actually specified, or None for absent/empty."""
    value = config.get(key)
    if isinstance(value, list) and value:
        return value
    return None


def plan_work(
    cli_stock_code: Optional[str],
    companies_path: Optional[str],
    config: Dict[str, Any],
) -> WorkPlan:
    """Decide the input source of one launch, in the documented priority.

        CLI stock_code > --companies file > config.test_cases
        > config.companies > config.stock_code > nothing to run

    A source counts as specified only when it carries at least one item.  The
    empty ``companies``/``test_cases`` lists the config loader injects by
    default -- and an explicitly empty list, indistinguishable after the merge
    -- therefore never shadow a non-empty lower-priority source.

    Only an explicit ``--companies`` path is read here.  An unreadable list
    raises ``ConfigError`` with its native cause on the chain; the caller
    refuses the launch.  An explicit list without entries, or a launch that
    names no item at all, is an empty work list (``source="none"``): that is
    legitimate, never a refusal.
    """
    if cli_stock_code:
        return WorkPlan("cli-stock", stock_code=cli_stock_code)
    if companies_path:
        companies = load_companies(companies_path)
        if not companies:
            name = Path(companies_path).name or companies_path
            return WorkPlan("none", reason=f"companies list {name} has no entries")
        return WorkPlan(
            "companies-file",
            companies=companies,
            progress_name=Path(companies_path).name or companies_path,
        )
    test_cases = _specified_items(config, "test_cases")
    if test_cases is not None:
        return WorkPlan("test-cases", test_cases=test_cases)
    companies = _specified_items(config, "companies")
    if companies is not None:
        return WorkPlan("config-companies", companies=companies, progress_name="config.json")
    if config.get("stock_code"):
        return WorkPlan("config-stock", stock_code=config["stock_code"])
    return WorkPlan(
        "none", reason="no stock code, companies list, test cases or config companies"
    )


class UnifiedRunner:
    """Manages execution of download tasks.

    Every sub-item that starts is counted in ``self.settlement`` exactly once
    (``attempted`` at start, then ``succeeded``/``failed`` at its end), so the
    business exit and the published settlement read the same tally.
    """

    def __init__(self, config: Dict[str, Any], progress: Optional[ProgressTracker] = None,
                 feedback=None, settlement: Optional[Dict[str, int]] = None):
        self.config = config
        self.save_dir = config["save_dir"]
        self.progress = progress
        self.feedback = feedback
        self.settlement = settlement if settlement is not None else _new_settlement()

    def _steps(self, step_id: Optional[str]):
        writer = getattr(self.feedback, "checkpoint", None)
        return capture_steps(partial(writer, step_id) if step_id and callable(writer) else None)

    def run_single(self, stock_code: str, company_name: Optional[str] = None) -> bool:
        """Run download for a single stock code."""
        name = company_name
        pages = self.config.get("pages", [])

        _bump(self.settlement, "attempted")
        downloader = None
        success = True
        try:
            for page in pages:
                log.info(f"Downloading {page.get('name', page.get('suffix', ''))} for {stock_code}")
                request = DownloadRequest(
                    stock_code=stock_code,
                    stock_name=name,
                    suffix=page.get("suffix", "research"),
                    allowed_keywords=page.get("allowed_keywords"),
                    excluded_keywords=page.get("excluded_keywords"),
                    max_pages=page.get("max_pages", 5),
                    save_dir=page.get("save_dir", self.save_dir),
                    save_subdir=page.get("save_subdir"),
                    reverse_order=page.get("reverse_order", False),
                )
                step_id = None
                if self.feedback is not None:
                    step_id = self.feedback.task_started(
                        stock_code=stock_code, task_key=_task_key(request)
                    )
                try:
                    with self._steps(step_id):
                        if not name:
                            checkpoint("stock-name", "resolving", stock_code=stock_code)
                            name = get_real_stock_name(stock_code)
                            checkpoint("stock-name", "resolved", stock_code=stock_code)
                        request.stock_name = name
                        if downloader is None:
                            downloader = StockDownloader(self.config)
                        result = downloader.download(request)
                except Exception as e:
                    # The outer handler logs "Task failed" once; here only the
                    # per-task terminal observation is recorded.
                    if self.feedback is not None and step_id is not None:
                        self.feedback.task_finished(
                            step_id=step_id,
                            stock_code=stock_code,
                            success=False,
                            stage="download-engine",
                            error_code=type(e).__name__,
                            cause_chain=exception_types(e),
                            cause_types=exception_types(e),
                        )
                    raise
                page_label = page.get("name", page.get("suffix"))
                if not result.success:
                    log.warning(f"Failed: {page_label} for {stock_code}")
                    for issue in result.verification.issues:
                        log.warning(f"  [{issue.code}] {issue.message}")
                    success = False
                    if self.feedback is not None and step_id is not None:
                        self.feedback.task_finished(
                            step_id=step_id,
                            stock_code=stock_code,
                            success=False,
                            stage="download-result",
                            error_code=result.error_code or "download_failed",
                            cause_chain=[
                                result.error_code or "download_failed",
                                "retryable" if result.retryable else "terminal",
                            ],
                        )
                else:
                    if self.feedback is not None and step_id is not None:
                        self.feedback.task_finished(
                            step_id=step_id,
                            stock_code=stock_code,
                            success=True,
                            stage="download-result",
                        )
                    log.info(
                        f"[{page_label}] {len(result.downloaded_files)} "
                        f"file(s) downloaded and verified OK"
                    )
        except Exception as e:
            log.error("Task failed for %s", stock_code, exc_info=True)
            success = False
        finally:
            if downloader is not None:
                downloader.cleanup()
        _bump(self.settlement, "succeeded" if success else "failed")
        return success

    def run_test_cases(self, test_cases: List[Dict[str, Any]]) -> bool:
        """Run a list of test cases (stock_code + suffix combos)."""
        overall_success = True
        for i, tc in enumerate(test_cases):
            stock_code = tc["stock_code"]
            suffix = tc.get("suffix", "research")
            log.info(
                f"[Test case {i+1}/{len(test_cases)}] "
                f"Downloading {stock_code} - {suffix}"
            )

            _bump(self.settlement, "attempted")
            case_success = False
            downloader = None
            request = DownloadRequest(
                stock_code=stock_code,
                suffix=suffix,
                allowed_keywords=tc.get("allowed_keywords"),
                excluded_keywords=tc.get("excluded_keywords"),
                max_pages=tc.get("max_pages", 5),
                save_subdir=tc.get("save_subdir"),
                reverse_order=tc.get("reverse_order", False),
            )
            step_id = None
            if self.feedback is not None:
                step_id = self.feedback.task_started(
                    stock_code=stock_code, task_key=_task_key(request)
                )
            try:
                with self._steps(step_id):
                    checkpoint("stock-name", "resolving", stock_code=stock_code)
                    request.stock_name = get_real_stock_name(stock_code)
                    checkpoint("stock-name", "resolved", stock_code=stock_code)
                    downloader = StockDownloader(self.config)
                    result = downloader.download(request)
                if not result.success:
                    log.warning(f"Test case {i+1} failed: {stock_code}/{suffix}")
                    overall_success = False
                    if self.feedback is not None and step_id is not None:
                        self.feedback.task_finished(
                            step_id=step_id,
                            stock_code=stock_code,
                            success=False,
                            stage="download-result",
                            error_code=result.error_code or "download_failed",
                            cause_chain=[
                                result.error_code or "download_failed",
                                "retryable" if result.retryable else "terminal",
                            ],
                        )
                else:
                    case_success = True
                    if self.feedback is not None and step_id is not None:
                        self.feedback.task_finished(
                            step_id=step_id,
                            stock_code=stock_code,
                            success=True,
                            stage="download-result",
                        )
                    log.info(f"Test case {i+1} completed: {len(result.downloaded_files)} file(s)")
            except Exception as e:
                log.error("Test case %s failed: %s/%s", i + 1, stock_code, suffix, exc_info=True)
                overall_success = False
                if self.feedback is not None and step_id is not None:
                    self.feedback.task_finished(
                        step_id=step_id,
                        stock_code=stock_code,
                        success=False,
                        stage="download-engine",
                        error_code=type(e).__name__,
                        cause_chain=exception_types(e),
                        cause_types=exception_types(e),
                    )
            finally:
                if downloader is not None:
                    downloader.cleanup()
            _bump(self.settlement, "succeeded" if case_success else "failed")
        return overall_success

    def run_multi(
        self, companies: List[Dict[str, Any]], parallel: bool = False, workers: int = 3
    ) -> Dict[str, int]:
        """Run downloads for multiple companies and settle the real results.

        Returns the runner's shared settlement tally (``attempted`` plus the
        ``succeeded``/``failed``/``skipped`` counts).
        """
        settlement = self.settlement
        if not companies:
            log.error("No companies provided")
            return settlement

        # Filter out already-completed companies when progress tracking is active
        if self.progress:
            all_codes = [c["stock_code"] for c in companies]
            pending_codes = set(self.progress.get_pending(all_codes))
            skipped = len(companies) - len(pending_codes)
            if skipped:
                log.info(f"Skipping {skipped} already completed")
            _bump(settlement, "skipped", skipped)
            companies = [c for c in companies if c["stock_code"] in pending_codes]
            if not companies:
                log.info("All companies already completed")
                return settlement

        if parallel and len(companies) > 1:
            log.info(f"Parallel download with {workers} workers")
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(
                        copy_context().run, self.run_single, c["stock_code"], c.get("company_name")
                    ): c
                    for c in companies
                }
                for future in concurrent.futures.as_completed(futures):
                    c = futures[future]
                    try:
                        # run_single has already tallied this sub-item's end.
                        success = future.result()
                        if self.progress:
                            if success:
                                self.progress.mark_completed(c["stock_code"])
                            else:
                                self.progress.mark_failed(c["stock_code"])
                    except Exception:
                        # run_single started the sub-item but could not tally
                        # its end (e.g. cleanup raised): it still failed.
                        _bump(settlement, "failed")
                        log.error("Parallel task for %s failed", c["stock_code"], exc_info=True)
                        if self.progress:
                            self.progress.mark_failed(c["stock_code"])
        else:
            log.info("Sequential download")
            total = len(companies)
            for i, c in enumerate(companies, 1):
                code = c["stock_code"]
                name = c.get("company_name", get_real_stock_name(code))
                success = self.run_single(code, name)
                if self.progress:
                    if success:
                        self.progress.mark_completed(code)
                        log.info(f"[{i}/{total}] completed {code} {name}")
                    else:
                        self.progress.mark_failed(code)
                        log.warning(f"[{i}/{total}] failed {code} {name}")
                if c != companies[-1]:
                    time.sleep(C.INTER_COMPANY_DELAY)
        return settlement


def _refuse(feedback, *, stage: str, exc: Optional[BaseException] = None) -> None:
    """Record an entry refusal: stage, native cause chain, nothing dispatched."""
    if feedback is None:
        return
    chain = exception_types(exc) if exc is not None else None
    feedback.run_refused(
        stage=stage,
        exit_code=1,
        error_code=type(exc).__name__ if exc is not None else None,
        cause_chain=chain,
        cause_types=chain,
    )


def main():
    identity = establish_identity()
    with entry_logging(
        "ordinary", identity, implementation_version(), state_root(),
        console=True, notice_on_parser_failure=False,
    ) as available:
        feedback = _open_feedback(identity)
        try:
            return _main(feedback)
        except Exception as exc:
            log.error("Ordinary launch failed", exc_info=True)
            if feedback is not None:
                feedback.checkpoint("ordinary-entry", {
                    "stage": "execution", "executed_state": "failed", "sent": "unknown",
                    "cause_types": exception_types(exc),
                })
                feedback.receipt.finish({"result": "failed", "exit_code": 1})
            raise SystemExit(1) from exc
        finally:
            if (not available or diagnostic_file_failed()) and (
                feedback is None or feedback.write_failures
            ):
                diagnostic_notice(identity)


def _main(feedback):
    parser = DiagnosticArgumentParser(description="Stock Downloader V2")
    parser.add_argument("stock_code", nargs="?", help="Stock code to download")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--companies", default=None, help="Path to companies TXT file")
    parser.add_argument("--parallel", action="store_true", help="Enable parallel mode")
    parser.add_argument("--workers", type=int, default=3, help="Parallel workers")
    parser.add_argument("--clean", action="store_true", help="Delete progress file and start fresh")
    try:
        args = parser.parse_args()
    except SystemExit as failure:
        if feedback is not None:
            if failure.code:
                feedback.run_refused(stage="arguments", exit_code=failure.code)
            else:
                feedback.run_finished(exit_code=0, settlement=_new_settlement())
        raise

    # Handle --clean flag
    if args.clean:
        ProgressTracker.clean()

    # Load config
    try:
        config = load_config(args.config)
    except Exception as e:
        # Typed input refusals keep their cause chain in the owner receipt.
        log.error("Failed to load config (%s)", type(e).__name__, exc_info=True)
        _refuse(feedback, stage="config", exc=e)
        sys.exit(1)

    log_cfg = config.get("logging") if isinstance(config.get("logging"), dict) else {}
    configured_log_file = log_cfg.get("log_file", "") if log_cfg.get("log_to_file", True) else ""
    try:
        if configured_log_file:
            setup_logger(level=str(log_cfg.get("level", "INFO")), log_file=str(configured_log_file))
    except OSError as exc:
        log.warning(
            "File logging unavailable (%s), continuing with console logging",
            type(exc).__name__, exc_info=True,
        )
        if feedback is not None:
            feedback.file_log_unavailable(cause_types=exception_types(exc))

    # Decide what this launch runs (the one input-source decision point).
    settlement = _new_settlement()
    try:
        plan = plan_work(args.stock_code, args.companies, config)
    except ConfigError as e:
        # An unreadable explicit list refuses the launch before any dispatch;
        # the run id, the stage and the native cause chain stay on record.
        log.error("Failed to read companies list (%s)", type(e).__name__, exc_info=True)
        _refuse(feedback, stage="companies", exc=e)
        sys.exit(1)

    runner = UnifiedRunner(config, feedback=feedback, settlement=settlement)
    if plan.source in ("companies-file", "config-companies"):
        progress = ProgressTracker()
        progress.init_run(plan.progress_name, len(plan.companies))
        log.info(progress.summary())
        runner = UnifiedRunner(config, progress=progress, feedback=feedback, settlement=settlement)
        runner.run_multi(plan.companies, parallel=args.parallel, workers=args.workers)
    elif plan.source in ("cli-stock", "config-stock"):
        runner.run_single(plan.stock_code)
    elif plan.source == "test-cases":
        runner.run_test_cases(plan.test_cases)
    # plan.source == "none": an empty work list starts nothing, by design.

    exit_code = 1 if settlement["failed"] else 0
    if feedback is not None:
        feedback.run_finished(exit_code=exit_code, settlement=settlement)
    if exit_code:
        summary = (
            f"Tasks settled: {settlement['succeeded']} succeeded, "
            f"{settlement['failed']} failed"
        )
        if settlement["skipped"]:
            summary += f", {settlement['skipped']} skipped"
        log.warning(summary)
        sys.exit(exit_code)
    if settlement["attempted"] == 0:
        # Nothing started: report exactly that, never "all tasks completed".
        if settlement["skipped"]:
            log.info(
                f"No tasks to run: all {settlement['skipped']} companies already completed"
            )
        else:
            log.info(f"No tasks to run: {plan.reason}")
    else:
        log.info("All tasks completed")


if __name__ == "__main__":
    main()
