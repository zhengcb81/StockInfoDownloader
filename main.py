#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stock Information Downloader - Unified Entry Point
Supports single company, multiple companies, parallel and sequential modes.
"""

import argparse
import concurrent.futures
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import ConfigManager
from src.core.logger import get_logger
from src.core.performance_monitor import log_performance_stats
from src.data.mapping import MappingManager
from src.factory.downloader_factory import downloader_factory

# Set console encoding to UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_real_stock_name(stock_code, mapping_file="configs/stock_orgid_mapping.json"):
    """Get stock name from mapping"""
    mapping_manager = MappingManager(mapping_file)
    return mapping_manager.get_stock_name(stock_code) or f"Stock_{stock_code}"


class UnifiedRunner:
    """Manager for executing download tasks"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("UnifiedRunner")
        self.save_dir = config.get("save_dir", "downloads")
        self.strategy = config.get("browser", {}).get("strategy", "playwright")

    def _prepare_task(
        self, stock_code: str, company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare configuration for a single stock download task"""
        name = company_name or get_real_stock_name(stock_code)
        return {
            "stock_code": stock_code,
            "stock_name": name,
            "save_dir": self.save_dir,
            "max_retries": self.config.get("max_retries", 3),
            "pages": self.config.get(
                "pages",
                [
                    {"name": "Research", "suffix": "research", "max_pages": 5},
                    {
                        "name": "Periodic Reports",
                        "suffix": "periodicReports",
                        "max_pages": 5,
                    },
                ],
            ),
        }

    def run_single(self, stock_code: str, company_name: Optional[str] = None) -> bool:
        """Run download for a single stock code"""
        task = self._prepare_task(stock_code, company_name)
        self.logger.info(
            f"Starting task for {task['stock_code']} ({task['stock_name']})"
        )

        # Create the modern unified downloader
        downloader = downloader_factory.create_downloader(
            downloader_type="unified",
            browser_strategy=self.strategy,
            save_dir=self.save_dir,
        )

        success = True
        try:
            for page in task["pages"]:
                self.logger.info(f"Downloading {page['name']} for {stock_code}")
                # UnifiedDownloader.download_activity_records is the best compat entry point
                res = downloader.download_activity_records(
                    stock_code=stock_code,
                    suffix=page.get("suffix", "research"),
                    allowed_keywords=page.get("allowed_keywords"),
                    max_pages=page.get("max_pages", 5),
                    headless=True,
                )
                if not res:
                    self.logger.warning(
                        f"Failed to download {page['name']} for {stock_code}"
                    )
                    success = False
        except Exception as e:
            self.logger.error(f"Task failed for {stock_code}: {e}")
            success = False
        finally:
            downloader.cleanup()

        return success

    def run_multi(
        self, companies: List[Dict[str, Any]], parallel: bool = False, workers: int = 3
    ):
        """Run downloads for multiple companies"""
        if not companies:
            self.logger.error("No companies provided for download")
            return

        if parallel and len(companies) > 1:
            self.logger.info(f"Starting parallel download with {workers} workers")
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
                        self.logger.error(
                            f"Parallel task for {c['stock_code']} failed: {e}"
                        )
        else:
            self.logger.info("Starting sequential download")
            for c in companies:
                self.run_single(c["stock_code"], c.get("company_name"))
                if c != companies[-1]:
                    time.sleep(2)  # Anti-crawler delay


def main():
    parser = argparse.ArgumentParser(
        description="Stock Information Downloader (Unified)"
    )
    parser.add_argument(
        "stock_code",
        nargs="?",
        help="Stock code to download (optional if provided in config)",
    )
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument(
        "--parallel", action="store_true", help="Enable parallel downloading"
    )
    parser.add_argument(
        "--workers", type=int, default=3, help="Number of parallel workers"
    )
    args = parser.parse_args()

    logger = get_logger("main")

    # Load Config
    config_manager = ConfigManager()
    config = {}
    if os.path.exists(args.config):
        try:
            config = config_manager.load_config(args.config)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")

    runner = UnifiedRunner(config)

    # Priority 1: Command line stock code
    if args.stock_code:
        runner.run_single(args.stock_code)
    # Priority 2: List of companies in config
    elif "companies" in config:
        runner.run_multi(
            config["companies"], parallel=args.parallel, workers=args.workers
        )
    # Priority 3: Single stock_code in config
    elif "stock_code" in config:
        runner.run_single(config["stock_code"])
    else:
        logger.error(
            "No stock code or companies provided. Usage: python main.py <stock_code> or provide config.json"
        )
        sys.exit(1)

    logger.info("All tasks completed")
    log_performance_stats()


if __name__ == "__main__":
    main()
