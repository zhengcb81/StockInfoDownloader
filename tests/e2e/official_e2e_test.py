#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Official End-to-End Test (Refactored)
Reserves the "e2e" term for this specific verification suite.

This test exercises the full user-facing pipeline by calling main.py via
subprocess with the test config. It only verifies the results afterwards
by comparing downloaded files against expected_results.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Path management
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
sys.path.insert(0, str(project_root))
DEFAULT_CONFIG_PATH = project_root / "config_e2e_official.json"


def sha256_file(path):
    """Return a file's SHA-256 digest without loading it all into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_project_path(path):
    """Resolve a config path relative to the repository root."""
    candidate = Path(path)
    return candidate.resolve() if candidate.is_absolute() else (project_root / candidate).resolve()


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


def compare_directories(actual_dir, expected_dir):
    """
    Strictly compare actual downloaded files with expected results.
    Rules:
    1. Every actual PDF must exist in expected directory with matching name.
    2. Every expected PDF must exist in actual directory.
    3. No extra PDF files allowed in root or subdirectories.
    """
    actual_path = resolve_project_path(actual_dir)
    expected_path = resolve_project_path(expected_dir)

    if not actual_path.exists():
        return False, f"Actual directory does not exist: {actual_dir}"
    if not expected_path.exists():
        return False, f"Expected directory does not exist: {expected_dir}"

    # Get all PDF files recursively
    actual_files = {f.relative_to(actual_path): f for f in actual_path.rglob("*.pdf")}
    expected_files = {
        f.relative_to(expected_path): f for f in expected_path.rglob("*.pdf")
    }

    # Compare the complete recursive directory structure, not only top-level names.
    actual_subdirs = {
        d.relative_to(actual_path)
        for d in actual_path.rglob("*")
        if d.is_dir() and any(d.rglob("*.pdf"))
    }
    expected_subdirs = {
        d.relative_to(expected_path)
        for d in expected_path.rglob("*")
        if d.is_dir() and any(d.rglob("*.pdf"))
    }

    actual_rel_paths = set(actual_files.keys())
    expected_rel_paths = set(expected_files.keys())

    extra_files = actual_rel_paths - expected_rel_paths
    missing_files = expected_rel_paths - actual_rel_paths
    extra_dirs = actual_subdirs - expected_subdirs
    missing_dirs = expected_subdirs - actual_subdirs
    content_mismatches = []

    for relative_path in sorted(actual_rel_paths & expected_rel_paths):
        actual_file = actual_files[relative_path]
        expected_file = expected_files[relative_path]
        if actual_file.stat().st_size != expected_file.stat().st_size:
            content_mismatches.append(relative_path)
            continue
        if sha256_file(actual_file) != sha256_file(expected_file):
            content_mismatches.append(relative_path)

    if extra_files:
        log(f"  Extra files found: {[str(f) for f in extra_files]}")
    if missing_files:
        log(f"  Missing files: {[str(f) for f in missing_files]}")
    if extra_dirs:
        log(f"  Extra directories found: {list(extra_dirs)}")
    if missing_dirs:
        log(f"  Missing directories: {[str(d) for d in missing_dirs]}")
    if content_mismatches:
        log(f"  Content/hash mismatches: {[str(f) for f in content_mismatches]}")

    if extra_files or missing_files or extra_dirs or missing_dirs or content_mismatches:
        error_msg = []
        if extra_files:
            error_msg.append(f"{len(extra_files)} extra file(s)")
        if missing_files:
            error_msg.append(f"{len(missing_files)} missing file(s)")
        if extra_dirs:
            error_msg.append(f"{len(extra_dirs)} extra directory(ies)")
        if missing_dirs:
            error_msg.append(f"{len(missing_dirs)} missing directory(ies)")
        if content_mismatches:
            error_msg.append(f"{len(content_mismatches)} content/hash mismatch(es)")
        return False, "Mismatch: " + " and ".join(error_msg)

    return (
        True,
        f"Perfect match: all {len(actual_rel_paths)} file(s) and directory structures are correct",
    )


def validate_expected_results(config):
    """
    Validate the immutable expected baseline without modifying it.

    Returns ``(is_valid, message)``.  Any extra or missing file is a hard
    failure; the runner never deletes or "repairs" checked-in fixtures.
    """
    expected_dir = resolve_project_path(
        config.get("expected_result_dir", "end2end_test/expected_results")
    )
    test_cases = config.get("test_cases", [])

    if not expected_dir.exists():
        message = f"Expected results directory does not exist: {expected_dir}"
        log(f"Error: {message}")
        return False, message

    # Simple local mapping to avoid external dependencies
    def get_company_name_from_stock_code(stock_code):
        mapping = {"301611": "珂玛科技", "300470": "中密控股", "300750": "宁德时代"}
        return mapping.get(stock_code, f"股票{stock_code}")

    # Get expected company names from stock codes
    expected_companies = set()
    expected_files = {}  # company -> list of keywords to match

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

    # Only company directories are allowed at the root.
    all_items = list(expected_dir.iterdir())
    extra_dirs = [
        item for item in all_items
        if (
            item.is_dir()
            and item.name not in expected_companies
            and any(path.is_file() for path in item.rglob("*"))
        )
    ]
    root_files = [item for item in all_items if item.is_file()]

    # Check for missing directories
    missing_dirs = []
    for company in expected_companies:
        company_dir = expected_dir / company
        if not company_dir.exists():
            missing_dirs.append(company)

    # Each configured keyword must match exactly one PDF; unmatched PDFs are
    # extra fixtures and multiple matches make the baseline ambiguous.
    extra_files = []
    missing_keywords = []
    ambiguous_keywords = []
    for company, keywords in expected_files.items():
        company_dir = expected_dir / company
        if not company_dir.exists():
            continue

        # Canonical fixtures are direct-child PDFs.  Nested or non-PDF files
        # are baseline drift and must not be silently ignored.
        all_company_files = [
            path for path in company_dir.rglob("*") if path.is_file()
        ]
        pdf_files = [
            path
            for path in all_company_files
            if path.parent == company_dir and path.suffix.lower() == ".pdf"
        ]
        matched_files = set()
        for keyword in keywords:
            matches = [pdf_file for pdf_file in pdf_files if keyword in pdf_file.name]
            if not matches:
                missing_keywords.append((company, keyword))
            elif len(matches) > 1:
                ambiguous_keywords.append((company, keyword, matches))
            matched_files.update(matches)

        extra_files.extend(
            path for path in all_company_files if path not in matched_files
        )

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
    if root_files:
        log(f"Found {len(root_files)} unexpected root file(s).")
        issues_found = True
    if missing_keywords:
        for company, keyword in missing_keywords:
            log(f"Missing expected PDF for {company}: {keyword}")
        issues_found = True
    if ambiguous_keywords:
        for company, keyword, matches in ambiguous_keywords:
            log(f"Ambiguous expected PDFs for {company}/{keyword}: {len(matches)}")
        issues_found = True

    if issues_found:
        message = "Expected baseline validation failed; no files were modified."
        log(message)
        return False, message

    message = f"Expected baseline is valid: {len(list(expected_dir.rglob('*.pdf')))} PDF(s)."
    log(message)
    return True, message


def check_and_restore_expected_results(config):
    """Compatibility wrapper; validation is intentionally read-only."""
    valid, _message = validate_expected_results(config)
    return valid


def compute_overall_success(main_py_success, directory_compare_success):
    """The E2E passes only when execution and verification both pass."""
    return bool(main_py_success and directory_compare_success)


def report_path_for_config(config_path):
    """Use separate report files for official and extended suites."""
    stem = Path(config_path).stem
    suite = stem.removeprefix("config_e2e_")
    return project_root / f"e2e_{suite}_report.json"


def run_main_py(config_path, browser_strategy):
    """Run main.py as a subprocess, exactly as a user would."""
    cmd = [
        sys.executable,
        str(project_root / "main.py"),
        "--config", config_path,
    ]
    log(f"Running: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        cwd=str(project_root),
        capture_output=False,  # Let main.py output pass through
        timeout=1200,  # 20 minute timeout for the full suite
    )

    return result.returncode == 0


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Official End-to-End Test")
    parser.add_argument(
        "--browser-strategy",
        choices=["selenium", "playwright", "both"],
        default="playwright",
        help="Browser strategy to use (default: playwright)",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="E2E config path (default: config_e2e_official.json)",
    )
    args = parser.parse_args()

    browser_strategy = args.browser_strategy
    log(f"Starting Official End-to-End Test (browser strategy: {browser_strategy})")

    config_path = resolve_project_path(args.config)
    if not config_path.exists():
        config_file = str(config_path)
        log(f"Config file not found: {config_file}")
        return 1

    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        log(f"Failed to load config: {e}")
        return 1

    # Expected fixtures are immutable.  Refuse to run if their contract drifts.
    expected_valid, expected_message = validate_expected_results(config)
    if not expected_valid:
        log(f"Aborting before main.py: {expected_message}")
        return 1

    save_dir = resolve_project_path(config["save_dir"])

    # Use CleanerTool to prepare directory (preserving specific files)
    from tests.utils.cleaner_tool import CleanerTool

    log(f"Preparing test directory: {save_dir}")
    if save_dir.exists():
        cleaner = CleanerTool(str(save_dir))
        pre_cleanup_summary = cleaner.clean_test_directory(config.get("test_cases", []))
    else:
        save_dir.mkdir(parents=True, exist_ok=True)
        pre_cleanup_summary = {
            "status": "success",
            "deleted_files": 0,
            "deleted_dirs": 0,
            "preserved_files": 0,
        }

    preexisting_pdfs = {
        str(path.relative_to(save_dir)): {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
        for path in save_dir.rglob("*.pdf")
    }

    # Inject browser_strategy into config and write a temporary config file
    # so main.py picks it up. The user's config_e2e_official.json is not modified.
    run_config = dict(config)
    run_config["browser"] = {"strategy": browser_strategy, "headless": True}

    temp_config = None
    success = False
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8",
            dir=str(project_root),
        ) as f:
            json.dump(run_config, f, indent=2, ensure_ascii=False)
            temp_config = f.name

        # Run main.py exactly as a user would
        log("Executing main.py with test config...")
        success = run_main_py(temp_config, browser_strategy)
        log(f"main.py exit status: {'success' if success else 'failed'}")

    finally:
        # Clean up temp config
        if temp_config and os.path.exists(temp_config):
            os.unlink(temp_config)

    # Final Verification: compare downloaded files with expected results
    comp_ok, msg = compare_directories(
        config["save_dir"], config["expected_result_dir"]
    )
    log(f"Verification: {msg}")

    # Post-verification cleanup: delete files for delete_later=true test cases,
    # keep files for delete_later=false test cases
    log("Cleaning up test files (delete_later=true)...")
    cleaner2 = CleanerTool(str(save_dir))
    post_cleanup_summary = cleaner2.clean_test_directory(config.get("test_cases", []))

    retained_pdfs = {
        str(path.relative_to(save_dir)): {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
        for path in save_dir.rglob("*.pdf")
    }
    overall_success = compute_overall_success(success, comp_ok)

    # Generate official report
    report = {
        "timestamp": datetime.now().isoformat(),
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "case_count": len(config.get("test_cases", [])),
        "overall_success": overall_success,
        "browser_strategy": browser_strategy,
        "main_py_success": success,
        "directory_compare_success": comp_ok,
        "directory_compare_message": msg,
        "cleanup_summary": {
            "before_run": pre_cleanup_summary,
            "after_verification": post_cleanup_summary,
        },
        "preexisting_pdfs": preexisting_pdfs,
        "retained_pdfs_after_cleanup": retained_pdfs,
    }
    report_path = report_path_for_config(config_path)
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
