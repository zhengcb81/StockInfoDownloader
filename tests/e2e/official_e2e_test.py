#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Official End-to-End Test (Refactored)
Reserves the "e2e" term for this specific verification suite.
Strictly implements all features required by the project specifications.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Path management
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
sys.path.insert(0, str(project_root))


def log(message):
    """Simple log output, handling encoding issues"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{timestamp}] {message}")
    except UnicodeEncodeError:
        try:
            print(
                f"[{timestamp}] {message.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)}"
            )
        except Exception:
            print(
                f"[{timestamp}] {message.encode('ascii', errors='replace').decode('ascii')}"
            )


def get_real_stock_name(stock_code):
    """Get real stock name from mapping."""
    try:
        from src.data.mapping import MappingManager

        mapping_manager = MappingManager()
        return mapping_manager.get_stock_name(stock_code) or f"股票{stock_code}"
    except Exception as e:
        log(f"Error getting stock name: {e}")
        return f"股票{stock_code}"


def calculate_file_hash(file_path):
    """Calculate file MD5"""
    if not os.path.exists(file_path):
        return ""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compare_files(file1, file2):
    """Compare if two files are identical."""
    if not os.path.exists(file1) or not os.path.exists(file2):
        return False
    if os.path.getsize(file1) != os.path.getsize(file2):
        return False
    return calculate_file_hash(file1) == calculate_file_hash(file2)


def run_test_with_new_downloader(test_case, config, browser_strategy="playwright"):
    """Run test with the unified downloader directly."""
    stock_code = test_case["stock_code"]
    log(f"\nTesting Official E2E: {stock_code} ({browser_strategy})")

    from src.services.unified_downloader import UnifiedDownloader
    from src.interfaces.downloader_interface import DownloadRequest

    try:
        # Create UnifiedDownloader directly
        downloader_config = {
            "save_dir": config["save_dir"],
            "browser_strategy": browser_strategy,
        }
        downloader = UnifiedDownloader(downloader_config)

        stock_name = get_real_stock_name(stock_code)

        # Create DownloadRequest
        request = DownloadRequest(
            stock_code=stock_code,
            stock_name=stock_name,
            suffix=test_case.get("suffix", "research"),
            allowed_keywords=test_case.get("allowed_keywords"),
            max_pages=test_case.get("max_pages", 5),
            timeout_seconds=test_case.get("timeout_seconds", 180),
            save_dir=config["save_dir"],
            reverse_order=test_case.get("reverse_order", False),
        )

        # Execute download
        result = downloader.download_stock_pdfs(request)

        # Handle result from UnifiedDownloader
        success = False
        downloaded_count = 0
        skipped_files = []
        pages_traversed = 0

        if hasattr(result, "success"):
            success = result.success
            if hasattr(result, "downloaded_files"):
                downloaded_count = len(result.downloaded_files)
            # 获取行为验证字段
            if hasattr(result, "skipped_files"):
                skipped_files = result.skipped_files
            if hasattr(result, "pages_traversed"):
                pages_traversed = result.pages_traversed
        elif isinstance(result, dict):
            success = result.get("success", False)
            downloaded_files = result.get("downloaded_files", [])
            downloaded_count = len(downloaded_files) if downloaded_files else 0
            skipped_files = result.get("skipped_files", [])
            pages_traversed = result.get("pages_traversed", 0)

        # 记录行为验证信息
        if skipped_files:
            log(f"  Skipped files: {len(skipped_files)}")
        if pages_traversed > 0:
            log(f"  Pages traversed: {pages_traversed}")

        return {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "success": success,
            "downloaded_files": downloaded_count,
            "duration": 0,  # Simplified
            # 行为验证字段
            "skipped_files": len(skipped_files),
            "pages_traversed": pages_traversed,
        }
    finally:
        if "downloader" in locals():
            downloader.cleanup()


def compare_directories(actual_dir, expected_dir):
    """
    Strictly compare actual downloaded files with expected results.
    Rules:
    1. Every actual PDF must exist in expected directory with matching name.
    2. Every expected PDF must exist in actual directory.
    3. No extra PDF files allowed in root or subdirectories.
    """
    actual_path = Path(actual_dir)
    expected_path = Path(expected_dir)

    if not actual_path.exists():
        return False, f"Actual directory does not exist: {actual_dir}"
    if not expected_path.exists():
        return False, f"Expected directory does not exist: {expected_dir}"

    # Get all PDF files recursively
    actual_files = {f.relative_to(actual_path): f for f in actual_path.rglob("*.pdf")}
    expected_files = {
        f.relative_to(expected_path): f for f in expected_path.rglob("*.pdf")
    }

    # Get all subdirectories
    actual_subdirs = {d.name for d in actual_path.iterdir() if d.is_dir()}
    expected_subdirs = {d.name for d in expected_path.iterdir() if d.is_dir()}

    actual_rel_paths = set(actual_files.keys())
    expected_rel_paths = set(expected_files.keys())

    extra_files = actual_rel_paths - expected_rel_paths
    missing_files = expected_rel_paths - actual_rel_paths
    extra_dirs = actual_subdirs - expected_subdirs

    if extra_files:
        log(f"  Extra files found: {[str(f) for f in extra_files]}")
    if missing_files:
        log(f"  Missing files: {[str(f) for f in missing_files]}")
    if extra_dirs:
        log(f"  Extra directories found: {list(extra_dirs)}")

    if extra_files or missing_files or extra_dirs:
        error_msg = []
        if extra_files:
            error_msg.append(f"{len(extra_files)} extra file(s)")
        if missing_files:
            error_msg.append(f"{len(missing_files)} missing file(s)")
        if extra_dirs:
            error_msg.append(f"{len(extra_dirs)} extra directory(ies)")
        return False, "Mismatch: " + " and ".join(error_msg)

    return (
        True,
        f"Perfect match: all {len(actual_rel_paths)} file(s) and directory structures are correct",
    )


def check_and_restore_expected_results(config):
    """
    Check if expected_results directory has been modified and restore if necessary.
    Returns True if directory is clean or was successfully restored.
    """
    expected_dir = Path(
        config.get("expected_result_dir", "end2end_test/expected_results")
    )
    test_cases = config.get("test_cases", [])

    if not expected_dir.exists():
        log(f"Error: Expected results directory does not exist: {expected_dir}")
        return False

    # Simple local mapping to avoid external dependencies
    def get_company_name_from_stock_code(stock_code):
        mapping = {"301611": "珂玛科技", "300470": "中密控股"}
        return mapping.get(stock_code, f"股票{stock_code}")

    # Get expected company names from stock codes
    expected_companies = set()
    expected_files = {}  # company -> set of keywords to match

    for test_case in test_cases:
        stock_code = test_case.get("stock_code")
        if not stock_code:
            continue

        # Get company name from stock code
        company_name = get_company_name_from_stock_code(stock_code)
        expected_companies.add(company_name)

        # Get allowed keywords for file matching
        allowed_keywords = test_case.get("allowed_keywords") or []
        if company_name not in expected_files:
            expected_files[company_name] = []
        expected_files[company_name].extend(allowed_keywords)

    log(f"Checking expected_results directory integrity...")
    log(f"Expected companies: {list(expected_companies)}")

    # Check for extra directories
    all_items = list(expected_dir.iterdir())
    extra_dirs = []
    for item in all_items:
        if item.is_dir() and item.name not in expected_companies:
            extra_dirs.append(item)

    # Check for missing directories
    missing_dirs = []
    for company in expected_companies:
        company_dir = expected_dir / company
        if not company_dir.exists():
            missing_dirs.append(company)

    # Check for extra files in company directories
    extra_files = []
    for company, keywords in expected_files.items():
        company_dir = expected_dir / company
        if not company_dir.exists():
            continue

        # Get all PDF files in company directory
        pdf_files = list(company_dir.glob("*.pdf"))
        for pdf_file in pdf_files:
            # Check if file name contains any of the expected keywords
            matched = False
            for keyword in keywords:
                if keyword in pdf_file.name:
                    matched = True
                    break

            if not matched:
                extra_files.append(pdf_file)

    issues_found = False

    if extra_dirs:
        log(f"Found {len(extra_dirs)} extra directories:")
        for d in extra_dirs:
            log(f"  - {d.name}")
        issues_found = True

    if missing_dirs:
        log(f"Found {len(missing_dirs)} missing directories:")
        for d in missing_dirs:
            log(f"  - {d}")
        issues_found = True

    if extra_files:
        log(f"Found {len(extra_files)} extra files:")
        for f in extra_files:
            log(f"  - {f.relative_to(expected_dir)}")
        issues_found = True

    # Restore if issues found
    if issues_found:
        log("Restoring expected_results directory to clean state...")

        # Remove extra directories
        for dir_path in extra_dirs:
            try:
                shutil.rmtree(dir_path)
                log(f"  Removed extra directory: {dir_path.name}")
            except Exception as e:
                log(f"  Failed to remove directory {dir_path.name}: {e}")

        # Remove extra files
        for file_path in extra_files:
            try:
                file_path.unlink()
                log(f"  Removed extra file: {file_path.relative_to(expected_dir)}")
            except Exception as e:
                log(f"  Failed to remove file {file_path.name}: {e}")

        # Note: Missing directories cannot be automatically restored
        # as they require the actual expected PDF files
        if missing_dirs:
            log(f"Warning: Missing expected directories: {missing_dirs}")
            log(f"  These directories cannot be automatically restored.")
            log(f"  Please ensure expected PDF files exist for these companies.")
            return False

        log("Expected_results directory restored successfully.")
        return True
    else:
        log("Expected_results directory is clean.")
        return True


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Official End-to-End Test")
    parser.add_argument(
        "--browser-strategy",
        choices=["selenium", "playwright", "both"],
        default="playwright",
        help="Browser strategy to use (default: playwright)",
    )
    args = parser.parse_args()

    browser_strategy = args.browser_strategy
    log(f"Starting Official End-to-End Test (browser strategy: {browser_strategy})")

    config_file = "config_e2e_official.json"
    if not os.path.exists(config_file):
        # Fallback to the one in root if not found (though it should be there)
        config_file = "config_e2e_official.json"

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        log(f"Failed to load config: {e}")
        return 1

    # Check and restore expected_results directory before running tests
    if not check_and_restore_expected_results(config):
        log("Warning: Expected_results directory may not be in correct state.")
        log("Tests may fail due to missing expected files.")

    save_dir = Path(config["save_dir"])

    # Use CleanerTool to prepare directory (preserving specific files)
    from tests.utils.cleaner_tool import CleanerTool

    log(f"Preparing test directory: {save_dir}")
    if save_dir.exists():
        cleaner = CleanerTool(str(save_dir))
        cleaner.clean_test_directory(config.get("test_cases", []))
    else:
        save_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for test_case in config.get("test_cases", []):
        res = run_test_with_new_downloader(test_case, config, browser_strategy)
        results.append(res)

    # Final Verification
    comp_ok, msg = compare_directories(
        config["save_dir"], config["expected_result_dir"]
    )
    log(f"Verification: {msg}")

    # Generate official report
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_success": comp_ok,
        "results": results,
    }
    with open("e2e_official_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return 0 if comp_ok else 1


if __name__ == "__main__":
    sys.exit(main())
