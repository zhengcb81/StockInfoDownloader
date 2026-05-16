#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stock Downloader V2 — Unified Entry Point.

Supports single company, multiple companies, parallel and sequential modes.
Compatible with config_e2e_official.json format.
"""
import argparse
import concurrent.futures
import json
import os
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


class UnifiedRunner:
    """Manages execution of download tasks."""

    def __init__(self, config: Dict[str, Any], progress: Optional[ProgressTracker] = None):
        self.config = config
        self.save_dir = config["save_dir"]
        self.progress = progress

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
                result = downloader.download(request)
                if not result.success:
                    log.warning(f"Failed: {page.get('name', page.get('suffix'))} for {stock_code}")
                    success = False
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
            try:
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
                result = downloader.download(request)
                if not result.success:
                    log.warning(f"Test case {i+1} failed: {stock_code}/{suffix}")
                    overall_success = False
                else:
                    log.info(f"Test case {i+1} completed: {len(result.downloaded_files)} file(s)")
            except Exception as e:
                log.error(f"Test case {i+1} failed: {stock_code}/{suffix}: {e}")
                overall_success = False
            finally:
                downloader.cleanup()
        return overall_success

    def run_multi(
        self, companies: List[Dict[str, Any]], parallel: bool = False, workers: int = 3
    ) -> None:
        """Run downloads for multiple companies."""
        if not companies:
            log.error("No companies provided")
            return

        # Filter out already-completed companies when progress tracking is active
        if self.progress:
            all_codes = [c["stock_code"] for c in companies]
            pending_codes = set(self.progress.get_pending(all_codes))
            skipped = len(companies) - len(pending_codes)
            if skipped:
                log.info(f"Skipping {skipped} already completed")
            companies = [c for c in companies if c["stock_code"] in pending_codes]
            if not companies:
                log.info("All companies already completed")
                return

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
                        if self.progress:
                            if success:
                                self.progress.mark_completed(c["stock_code"])
                            else:
                                self.progress.mark_failed(c["stock_code"])
                    except Exception as e:
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
                if self.progress:
                    if success:
                        self.progress.mark_completed(code)
                        log.info(f"[{i}/{total}] completed {code} {name}")
                    else:
                        self.progress.mark_failed(code)
                        log.warning(f"[{i}/{total}] failed {code} {name}")
                if c != companies[-1]:
                    time.sleep(C.INTER_COMPANY_DELAY)


def main():
    parser = argparse.ArgumentParser(description="Stock Downloader V2")
    parser.add_argument("stock_code", nargs="?", help="Stock code to download")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--companies", default=None, help="Path to companies TXT file")
    parser.add_argument("--parallel", action="store_true", help="Enable parallel mode")
    parser.add_argument("--workers", type=int, default=3, help="Parallel workers")
    parser.add_argument("--clean", action="store_true", help="Delete progress file and start fresh")
    args = parser.parse_args()

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
        sys.exit(1)

    # Create progress tracker for multi-company runs
    progress: Optional[ProgressTracker] = None
    companies_file_name: Optional[str] = None

    if args.companies:
        companies_file_name = Path(args.companies).name
    runner = UnifiedRunner(config)

    # Priority: CLI stock_code > --companies file > test_cases > companies > config stock_code
    if args.stock_code:
        runner.run_single(args.stock_code)
    elif args.companies:
        company_list = load_companies(args.companies)
        progress = ProgressTracker()
        progress.init_run(companies_file_name or args.companies, len(company_list))
        log.info(progress.summary())
        runner = UnifiedRunner(config, progress=progress)
        runner.run_multi(company_list, parallel=args.parallel, workers=args.workers)
    elif "test_cases" in config:
        runner.run_test_cases(config["test_cases"])
    elif "companies" in config:
        company_list = config["companies"]
        progress = ProgressTracker()
        progress.init_run("config.json", len(company_list))
        log.info(progress.summary())
        runner = UnifiedRunner(config, progress=progress)
        runner.run_multi(company_list, parallel=args.parallel, workers=args.workers)
    elif "stock_code" in config:
        runner.run_single(config["stock_code"])
    else:
        log.error(
            "No stock code provided. Usage: python main.py <stock_code> or provide config.json"
        )
        sys.exit(1)

    log.info("All tasks completed")


if __name__ == "__main__":
    main()
