#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Cleanup Tool Module
Provides intelligent test directory cleanup functionality
"""

import os
import shutil
import json
import time
from pathlib import Path
from typing import Dict, List, Any

def get_test_directory_status(test_dir: str) -> Dict[str, Any]:
    """Get test directory status (including root files)"""
    test_path = Path(test_dir)

    if not test_path.exists():
        return {
            "exists": False,
            "total_files": 0,
            "total_dirs": 0,
            "companies": [],
            "root_files": []
        }

    companies = []
    total_files = 0
    root_files = []

    # First check PDF files in root directory
    for file_path in test_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() == '.pdf':
            root_files.append({
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "path": str(file_path)
            })
            total_files += 1

    # Then check company subdirectories
    for company_dir in test_path.iterdir():
        if company_dir.is_dir():
            company_files = []
            for file_path in company_dir.iterdir():
                if file_path.is_file():
                    company_files.append({
                        "name": file_path.name,
                        "size": file_path.stat().st_size,
                        "path": str(file_path)
                    })
                    total_files += 1

            companies.append({
                "name": company_dir.name,
                "files": company_files,
                "file_count": len(company_files)
            })

    return {
        "exists": True,
        "total_files": total_files,
        "total_dirs": len(companies),
        "companies": companies,
        "root_files": root_files,
        "root_file_count": len(root_files)
    }

def clean_test_files(test_dir: str, preserve_cases: List[Dict[str, Any]] = None, dry_run: bool = False) -> Dict[str, Any]:
    """
    Clean test files (including root files cleanup)

    Args:
        test_dir: Test directory path
        preserve_cases: List of test cases to preserve
        dry_run: Whether to only preview without executing

    Returns:
        Cleanup result statistics
    """
    import traceback
    print(f"\n[DEBUG] clean_test_files called")
    print(f"[DEBUG]   test_dir: {test_dir}")
    print(f"[DEBUG]   preserve_cases: {preserve_cases}")
    print(f"[DEBUG]   dry_run: {dry_run}")
    if preserve_cases is None:
        print(f"[DEBUG]   preserve_cases is None, using empty list")
        preserve_cases = []
    else:
        print(f"[DEBUG]   preserve_cases length: {len(preserve_cases)}")
    print(f"[DEBUG]   Call stack: {''.join(traceback.format_stack()[-5:])}")

    test_path = Path(test_dir)
    cleaned_files = 0
    cleaned_dirs = 0
    cleaned_root_files = 0
    preserved_files = 0
    preserved_dirs = 0
    preserved_root_files = 0

    if not test_path.exists():
        return {
            "cleaned_files": 0,
            "cleaned_dirs": 0,
            "cleaned_root_files": 0,
            "preserved_files": 0,
            "preserved_dirs": 0,
            "preserved_root_files": 0,
            "dry_run": dry_run
        }

    # Get company names and stock codes to preserve
    preserve_companies = set()
    preserve_stock_codes = set()
    if preserve_cases is not None and len(preserve_cases) > 0:
        # Only build preservation list when preserve_cases is not empty
        for case in preserve_cases:
            stock_code = case.get("stock_code")
            if stock_code:
                preserve_stock_codes.add(stock_code)
                # Get real company name
                try:
                    from get_stock_name import get_stock_name
                    company_name = get_stock_name(stock_code)
                    if company_name and not company_name.startswith('错误') and not company_name.startswith('网络'):
                        preserve_companies.add(company_name)
                except:
                    preserve_companies.add(f"Stock{stock_code}")

    # 1. Clean PDF files in root directory
    for file_path in test_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() == '.pdf':
            # Check if filename contains stock code to preserve
            should_preserve_root = False
            for stock_code in preserve_stock_codes:
                if stock_code in file_path.name:
                    should_preserve_root = True
                    break

            if should_preserve_root:
                print(f"[DEBUG] Preserving root file: {file_path.name}")
                preserved_root_files += 1
                continue

            # Clean root file
            print(f"[DEBUG] Deleting root file: {file_path.name}")
            if not dry_run:
                try:
                    file_path.unlink()
                    cleaned_root_files += 1
                except Exception as e:
                    print(f"Failed to delete root file {file_path}: {e}")
            else:
                cleaned_root_files += 1

    # 2. Clean company subdirectories
    for company_dir in test_path.iterdir():
        if company_dir.is_dir():
            company_name = company_dir.name

            # Check if preservation is needed
            should_preserve = company_name in preserve_companies
            print(f"[DEBUG] Checking directory: {company_name}, preserve_companies={preserve_companies}, should_preserve={should_preserve}")

            if should_preserve:
                print(f"[DEBUG] Preserving directory: {company_name}")
                preserved_dirs += 1
                # Count preserved files
                file_count = sum(1 for _ in company_dir.iterdir() if _.is_file())
                preserved_files += file_count
                continue

            # Clean directory
            if not should_preserve:
                print(f"[DEBUG] Will delete directory: {company_name}")
            if not dry_run:
                try:
                    # Check file lock
                    lock_file = company_dir / ".lock"
                    if lock_file.exists():
                        print(f"Warning: Directory {company_dir} has lock file, skipping cleanup")
                        continue  # Skip cleanup for this directory

                    # Count files first
                    file_count = sum(1 for _ in company_dir.iterdir() if _.is_file())
                    cleaned_files += file_count

                    # Delete directory, support retry
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            shutil.rmtree(company_dir)
                            cleaned_dirs += 1
                            break  # Exit loop on success
                        except Exception as e:
                            if attempt < max_retries - 1:
                                time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                            else:
                                raise  # Re-raise exception on last failure
                except Exception as e:
                    print(f"Failed to clean directory {company_dir}: {e}")
            else:
                # Only count in dry run
                file_count = sum(1 for _ in company_dir.iterdir() if _.is_file())
                cleaned_files += file_count
                cleaned_dirs += 1

    return {
        "cleaned_files": cleaned_files,
        "cleaned_dirs": cleaned_dirs,
        "cleaned_root_files": cleaned_root_files,
        "preserved_files": preserved_files,
        "preserved_dirs": preserved_dirs,
        "preserved_root_files": preserved_root_files,
        "dry_run": dry_run
    }

def main():
    """Command line entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Test Cleanup Tool')
    parser.add_argument('--test-dir', default='end2end_test/test_results', help='Test directory path')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, do not execute')
    parser.add_argument('--preserve-config', help='Config file path containing test cases to preserve')
    parser.add_argument('--status', action='store_true', help='Only show directory status')

    args = parser.parse_args()

    if args.status:
        # Show directory status
        status = get_test_directory_status(args.test_dir)
        print(f"Directory Status: {args.test_dir}")
        print(f"Exists: {status['exists']}")
        print(f"Company Dirs: {status['total_dirs']}")
        print(f"Total Files: {status['total_files']}")
        print(f"Root Files: {status.get('root_file_count', 0)}")

        if status.get('root_files'):
            print(f"\nRoot Files:")
            for file in status['root_files']:
                print(f"  - {file['name']} ({file['size']} bytes)")

        if status['companies']:
            print(f"\nCompany Directories:")
            for company in status['companies']:
                print(f"  - {company['name']}: {company['file_count']} files")
        return

    # Load test cases to preserve
    preserve_cases = []
    if args.preserve_config and os.path.exists(args.preserve_config):
        try:
            with open(args.preserve_config, 'r', encoding='utf-8') as f:
                config = json.load(f)
                preserve_cases = config.get('test_cases', [])
                # Only preserve cases with delete_later=False
                preserve_cases = [case for case in preserve_cases if not case.get('delete_later', True)]
        except Exception as e:
            print(f"Failed to load config file: {e}")

    # Execute cleanup
    result = clean_test_files(args.test_dir, preserve_cases, args.dry_run)

    print(f"Cleanup Result:")
    print(f"  Cleaned Company Files: {result['cleaned_files']}")
    print(f"  Cleaned Company Dirs: {result['cleaned_dirs']}")
    print(f"  Cleaned Root Files: {result['cleaned_root_files']}")
    print(f"  Preserved Company Files: {result['preserved_files']}")
    print(f"  Preserved Company Dirs: {result['preserved_dirs']}")
    print(f"  Preserved Root Files: {result['preserved_root_files']}")
    print(f"  Dry Run: {result['dry_run']}")

if __name__ == "__main__":
    main()
