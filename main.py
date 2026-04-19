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

from src.config import load_config
from src import constants as C
from src.downloader import StockDownloader
from src.logger import log, setup_logger
from src.mapping import MappingManager
from src.models import DownloadRequest


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

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.save_dir = config["save_dir"]

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
                    max_pages=page.get("max_pages", 5),
                    save_dir=page.get("save_dir", self.save_dir),
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
                    max_pages=tc.get("max_pages", 5),
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
                        future.result()
                    except Exception as e:
                        log.error(f"Parallel task for {c['stock_code']} failed: {e}")
        else:
            log.info("Sequential download")
            for c in companies:
                self.run_single(c["stock_code"], c.get("company_name"))
                if c != companies[-1]:
                    time.sleep(C.INTER_COMPANY_DELAY)


def main():
    parser = argparse.ArgumentParser(description="Stock Downloader V2")
    parser.add_argument("stock_code", nargs="?", help="Stock code to download")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--parallel", action="store_true", help="Enable parallel mode")
    parser.add_argument("--workers", type=int, default=3, help="Parallel workers")
    args = parser.parse_args()

    # Setup logging
    setup_logger()

    # Load config
    try:
        config = load_config(args.config)
    except Exception as e:
        log.error(f"Failed to load config: {e}")
        sys.exit(1)

    runner = UnifiedRunner(config)

    # Priority: CLI stock_code > test_cases > companies > config stock_code
    if args.stock_code:
        runner.run_single(args.stock_code)
    elif "test_cases" in config:
        runner.run_test_cases(config["test_cases"])
    elif "companies" in config:
        runner.run_multi(config["companies"], parallel=args.parallel, workers=args.workers)
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
