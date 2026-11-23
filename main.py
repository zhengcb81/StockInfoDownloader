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
"""
import argparse
import concurrent.futures
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_companies, load_config
from src import constants as C
from src.downloader import StockDownloader
from src.logger import log, setup_logger
from src.mapping import MappingManager
from src.models import DownloadRequest
from src.progress import ProgressTracker


def get_real_stock_name(stock_code: str) -> str:
    """Get stock name from mapping."""
    try:
        mm = MappingManager()
        return mm.get_stock_name(stock_code) or f"Stock_{stock_code}"
    except Exception as e:
        log.debug(f"Stock name lookup failed for {stock_code}: {e}")
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


def _exception_cause_chain(exc: BaseException) -> List[str]:
    """Stable cause chain: exception type names only, no message text."""
    chain: List[str] = []
    current: Optional[BaseException] = exc
    for _ in range(6):
        if current is None:
            break
        name = type(current).__name__
        if name not in chain:
            chain.append(name)
        current = current.__cause__ or current.__context__
    return chain


def _open_feedback():
    """Build the run feedback (identity + receipt) before argparse/side effects.

    Feedback is diagnostics: any failure here keeps the business flow alive.
    """
    try:
        from src.feedback_publish import OrdinaryRunFeedback

        return OrdinaryRunFeedback()
    except Exception as e:  # pragma: no cover - defensive, never fatal
        log.debug(f"ordinary feedback disabled: {type(e).__name__}: {e}")
        return None


class UnifiedRunner:
    """Manages execution of download tasks."""

    def __init__(self, config: Dict[str, Any], progress: Optional[ProgressTracker] = None,
                 feedback=None):
        self.config = config
        self.save_dir = config["save_dir"]
        self.progress = progress
        self.feedback = feedback

    def run_single(self, stock_code: str, company_name: Optional[str] = None) -> bool:
        """Run download for a single stock code."""
        name = company_name or get_real_stock_name(stock_code)
        pages = self.config.get("pages", [])

        downloader = StockDownloader(self.config)
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
                            cause_chain=_exception_cause_chain(e),
                            cause_types=_exception_cause_chain(e),
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
            log.error(f"Task failed for {stock_code}: {e}")
            success = False
        finally:
            downloader.cleanup()
        return success

    def run_test_cases(self, test_cases: List[Dict[str, Any]]) -> bool:
        """Run a list of test cases (stock_code + suffix combos)."""
        overall_success = True
        for i, tc in enumerate(test_cases):
            stock_code = tc["stock_code"]
            stock_name = get_real_stock_name(stock_code)
            suffix = tc.get("suffix", "research")
            log.info(
                f"[Test case {i+1}/{len(test_cases)}] "
                f"Downloading {stock_code} ({stock_name}) - {suffix}"
            )

            downloader = StockDownloader(self.config)
            request = DownloadRequest(
                stock_code=stock_code,
                stock_name=stock_name,
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
                    if self.feedback is not None and step_id is not None:
                        self.feedback.task_finished(
                            step_id=step_id,
                            stock_code=stock_code,
                            success=True,
                            stage="download-result",
                        )
                    log.info(f"Test case {i+1} completed: {len(result.downloaded_files)} file(s)")
            except Exception as e:
                log.error(f"Test case {i+1} failed: {stock_code}/{suffix}: {e}")
                overall_success = False
                if self.feedback is not None and step_id is not None:
                    self.feedback.task_finished(
                        step_id=step_id,
                        stock_code=stock_code,
                        success=False,
                        stage="download-engine",
                        error_code=type(e).__name__,
                        cause_chain=_exception_cause_chain(e),
                        cause_types=_exception_cause_chain(e),
                    )
            finally:
                downloader.cleanup()
        return overall_success

    def run_multi(
        self, companies: List[Dict[str, Any]], parallel: bool = False, workers: int = 3
    ) -> Dict[str, int]:
        """Run downloads for multiple companies and settle the real results."""
        settlement = {"succeeded": 0, "failed": 0, "skipped": 0}
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
            if self.feedback is not None:
                self.feedback.mark_skipped(skipped)
            settlement["skipped"] = skipped
            companies = [c for c in companies if c["stock_code"] in pending_codes]
            if not companies:
                log.info("All companies already completed")
                return settlement

        if parallel and len(companies) > 1:
            log.info(f"Parallel download with {workers} workers")
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(
                        self.run_single, c["stock_code"], c.get("company_name")
                    ): c
                    for c in companies
                }
                for future in concurrent.futures.as_completed(futures):
                    c = futures[future]
                    try:
                        success = future.result()
                        if success:
                            settlement["succeeded"] += 1
                        else:
                            settlement["failed"] += 1
                        if self.progress:
                            if success:
                                self.progress.mark_completed(c["stock_code"])
                            else:
                                self.progress.mark_failed(c["stock_code"])
                    except Exception as e:
                        settlement["failed"] += 1
                        log.error(f"Parallel task for {c['stock_code']} failed: {e}")
                        if self.progress:
                            self.progress.mark_failed(c["stock_code"])
        else:
            log.info("Sequential download")
            total = len(companies)
            for i, c in enumerate(companies, 1):
                code = c["stock_code"]
                name = c.get("company_name", get_real_stock_name(code))
                success = self.run_single(code, name)
                if success:
                    settlement["succeeded"] += 1
                else:
                    settlement["failed"] += 1
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


def _fold_settlement(result: Any, settlement: Dict[str, int]) -> Dict[str, int]:
    """Fold a branch's business outcome into the run settlement counters."""
    if isinstance(result, dict):
        for key in ("succeeded", "failed", "skipped"):
            settlement[key] = int(result.get(key, 0) or 0)
    elif isinstance(result, bool):
        settlement["succeeded" if result else "failed"] += 1
    return settlement


def main():
    # Run identity and startup receipt come before argument parsing and any
    # side effect, so even a refusal or a hard kill leaves a recoverable mark.
    feedback = _open_feedback()
    parser = argparse.ArgumentParser(description="Stock Downloader V2")
    parser.add_argument("stock_code", nargs="?", help="Stock code to download")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--companies", default=None, help="Path to companies TXT file")
    parser.add_argument("--parallel", action="store_true", help="Enable parallel mode")
    parser.add_argument("--workers", type=int, default=3, help="Parallel workers")
    parser.add_argument("--clean", action="store_true", help="Delete progress file and start fresh")
    try:
        args = parser.parse_args()
    except SystemExit as failure:
        if feedback is not None and failure.code:
            feedback.run_refused(stage="arguments", exit_code=failure.code)
        raise

    # Setup logging
    setup_logger()

    # Handle --clean flag
    if args.clean:
        ProgressTracker.clean()

    # Load config
    try:
        config = load_config(args.config)
    except Exception as e:
        log.error(f"Failed to load config: {e}")
        if feedback is not None:
            feedback.run_refused(stage="config", exit_code=1)
        sys.exit(1)

    # Create progress tracker for multi-company runs
    progress: Optional[ProgressTracker] = None
    companies_file_name: Optional[str] = None

    if args.companies:
        companies_file_name = Path(args.companies).name
    runner = UnifiedRunner(config, feedback=feedback)

    # Priority: CLI stock_code > --companies file > test_cases > companies > config stock_code
    settlement: Dict[str, int] = {"succeeded": 0, "failed": 0, "skipped": 0}
    if args.stock_code:
        settlement = _fold_settlement(runner.run_single(args.stock_code), settlement)
    elif args.companies:
        company_list = load_companies(args.companies)
        progress = ProgressTracker()
        progress.init_run(companies_file_name or args.companies, len(company_list))
        log.info(progress.summary())
        runner = UnifiedRunner(config, progress=progress, feedback=feedback)
        settlement = _fold_settlement(
            runner.run_multi(company_list, parallel=args.parallel, workers=args.workers),
            settlement,
        )
    elif "test_cases" in config:
        settlement = _fold_settlement(runner.run_test_cases(config["test_cases"]), settlement)
    elif "companies" in config:
        company_list = config["companies"]
        progress = ProgressTracker()
        progress.init_run("config.json", len(company_list))
        log.info(progress.summary())
        runner = UnifiedRunner(config, progress=progress, feedback=feedback)
        settlement = _fold_settlement(
            runner.run_multi(company_list, parallel=args.parallel, workers=args.workers),
            settlement,
        )
    elif "stock_code" in config:
        settlement = _fold_settlement(runner.run_single(config["stock_code"]), settlement)
    else:
        log.error(
            "No stock code provided. Usage: python main.py <stock_code> or provide config.json"
        )
        if feedback is not None:
            feedback.run_refused(stage="usage", exit_code=1)
        sys.exit(1)

    exit_code = 1 if settlement["failed"] else 0
    if feedback is not None:
        feedback.run_finished(exit_code=exit_code)
    if exit_code:
        summary = (
            f"Tasks settled: {settlement['succeeded']} succeeded, "
            f"{settlement['failed']} failed"
        )
        if settlement["skipped"]:
            summary += f", {settlement['skipped']} skipped"
        log.warning(summary)
        sys.exit(exit_code)
    log.info("All tasks completed")


if __name__ == "__main__":
    main()
