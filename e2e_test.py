#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
End-to-End Test Final Version
Strictly implements all features required by testing requirements.
Tests full functionality of both new and old downloaders.
"""

# Set event loop policy before importing any other modules
import sys
import asyncio
if sys.platform == 'win32':
    # Set console encoding to UTF-8 to prevent mojibake
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

    # Playwright on Windows needs ProactorEventLoop, but sync_playwright handles it automatically
    # To avoid event loop conflicts, ensure a clean event loop for each test
    try:
        # Try to get and close existing event loop (if it exists and is not running)
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                # If loop exists but is not running, close it
                loop.close()
        except RuntimeError:
            # No event loop, this is normal
            pass
        except:
            # Other errors, ignore
            pass

        # Create new event loop and set as current
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
    except Exception as e:
        print(f"Error setting event loop policy: {e}")

def get_real_stock_name(stock_code):
    """Get real stock name, do not hardcode"""
    try:
        from get_stock_name import get_stock_name
        stock_name = get_stock_name(stock_code)
        if not stock_name or stock_name.startswith('错误') or stock_name.startswith('网络'):
            log(f"Warning: Failed to get stock name, using fallback: {stock_name}")
            return f"股票{stock_code}"
        return stock_name
    except Exception as e:
        log(f"Error: Exception while getting stock name: {e}")
        return f"股票{stock_code}"

import sys
import locale
import os
import json
import time
import shutil
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime

# Import test report generator
sys.path.insert(0, str(Path(__file__).parent))
# from tests.unit.test_report_generator import TestReportGenerator  # Temporarily commented out to avoid import errors

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def log(message):
    """Simple log output, handling encoding issues"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{timestamp}] {message}")
    except UnicodeEncodeError:
        # If encoding fails (e.g. printing special symbols in GBK terminal), try replacement
        try:
            print(f"[{timestamp}] {message.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)}")
        except:
            # Last resort: print ASCII only
            print(f"[{timestamp}] {message.encode('ascii', errors='replace').decode('ascii')}")

def calculate_file_hash(file_path):
    """Calculate file MD5"""
    if not os.path.exists(file_path):
        return ""
    
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def compare_files(file1, file2, max_retries=3):
    """Compare if two files are identical, with retry support"""
    for attempt in range(max_retries):
        try:
            if not os.path.exists(file1) or not os.path.exists(file2):
                time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                continue

            # Compare size
            if os.path.getsize(file1) != os.path.getsize(file2):
                return False

            # Compare MD5
            return calculate_file_hash(file1) == calculate_file_hash(file2)
        except (PermissionError, OSError) as e:
            if attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))
            else:
                log(f"File comparison failed {file1} vs {file2}: {e}")
                return False
    return False

def test_skip_logic(test_case, config, downloader_type="new"):
    """Test file skipping logic (when delete_later=False)"""
    if test_case.get("delete_later", True):
        return None  # Skip this test
        
    stock_code = test_case["stock_code"]
    log(f"\nTesting skip logic ({downloader_type} downloader): {stock_code}")
    
    # Let the downloader handle directory structure, test program only checks final save location
    # Copy expected files to download root directory, let downloader organize into subdirectories
    save_dir = Path(config["save_dir"])
    expected_dir = Path(config["expected_result_dir"])
    
    # Find actual company directories in expected result directory (do not hardcode company name)
    expected_base_dir = Path(config["expected_result_dir"])
    expected_company_dirs = [d for d in expected_base_dir.iterdir() if d.is_dir()] if expected_base_dir.exists() else []
    
    if not expected_company_dirs:
        log(f"Warning: No company directories found in expected result directory")
        return None
    
    # Fix: Only copy files corresponding to current test stock code, not all files
    save_dir = Path(config["save_dir"])
    files_copied = 0
    
    # Get stock code and company name for current test case
    current_stock_code = test_case["stock_code"]
    current_company_name = None
    
    # Find expected company directory for current test case
    target_expected_dir = None
    for expected_company_dir in expected_company_dirs:
        dir_name = expected_company_dir.name
        
        # Get mapping from stock code to company name from config
        # Check if files in this directory contain current test case stock code
        for expected_file in expected_company_dir.glob("*.pdf"):
            if current_stock_code in expected_file.name:
                target_expected_dir = expected_company_dir
                current_company_name = dir_name
                break
        if target_expected_dir:
            break
    
    if not target_expected_dir:
        log(f"Warning: Expected result directory for stock code {current_stock_code} not found")
        return None
    
    # Get standard company name
    try:
        from get_stock_name import get_stock_name
        standard_name = get_stock_name(current_stock_code)
        if standard_name and not standard_name.startswith('错误'):
            current_company_name = standard_name
    except Exception:
        pass  # Use directory name
    
    # Create corresponding company directory
    target_company_dir = save_dir / current_company_name
    target_company_dir.mkdir(parents=True, exist_ok=True)
    
    # Only copy files for current test case
    for expected_file in target_expected_dir.glob("*.pdf"):
        target_file = target_company_dir / expected_file.name
        if not target_file.exists():
            shutil.copy2(expected_file, target_file)
            log(f"Copying file to test skip logic: {expected_file.name} -> {current_company_name}")
            files_copied += 1
    
    if files_copied == 0:
        log("No files copied for skip test")
        return None
    
    # Record existing files in entire save_dir (let downloader organize)
    existing_files = list(save_dir.rglob("*.pdf")) if save_dir.exists() else []
    
    # Run downloader (should skip existing files)
    if downloader_type == "old":
        result = run_test_with_old_downloader(test_case, config)
    else:
        result = run_test_with_new_downloader(test_case, config)
    
    # Verify file count in entire save_dir (let downloader decide file location)
    if save_dir.exists():
        new_files = list(save_dir.rglob("*.pdf"))
        if len(new_files) == len(existing_files):
            log("Skip logic test passed: File count did not increase")
            result["skip_test_passed"] = True
        else:
            log("Skip logic test failed: File count increased")
            result["skip_test_passed"] = False
    
    return result

def run_test_with_old_downloader(test_case, config):
    """Run test with old downloader"""
    stock_code = test_case["stock_code"]
    log(f"\nTesting with old downloader: {stock_code}")
    
    # Let downloader handle directory structure, test program does not interfere
    suffix = test_case.get("suffix", "research")
    allowed_keywords = test_case.get("allowed_keywords")
    delete_later = test_case.get("delete_later", True)
    max_pages = test_case.get("max_pages", 5)
    timeout = test_case.get("timeout_seconds", 180)
    
    # Let downloader handle directory structure, test program does not interfere
    
    start_time = time.time()
    success = False
    error_msg = ""
    downloaded_files = []
    duration = 0
    
    try:
        # Use unified downloader factory to create old downloader (backward compatible)
        from src.factory.downloader_factory import downloader_factory

        # Create downloader (guaranteed compatible via adapter)
        downloader = downloader_factory.create_legacy_adapter(
            'cninfo',
            save_dir=config["save_dir"]
        )
        
        # Get Org ID
        org_id = downloader.get_org_id(stock_code)
        if not org_id:
            error_msg = "Failed to get Org ID"
        else:
            # Parse keywords
            keywords = allowed_keywords
            
            # Execute download
            success = downloader.download_activity_records(
                stock_code=stock_code,
                org_id=org_id,
                headless=config.get("headless", True),
                max_retries=config.get("max_retries", 3),
                suffix=suffix,
                allowed_keywords=keywords,
                max_pages=max_pages
            )
            
            if not success:
                error_msg = "Download failed"
        
        duration = time.time() - start_time
        
        # Check downloaded files (let downloader decide file location)
        save_dir = Path(config["save_dir"])
        downloaded_files = list(save_dir.rglob("*.pdf")) if save_dir.exists() else []
        
        # Verify result
        if success:
            # Check timeout
            if duration > timeout:
                error_msg = f"Download too slow: {duration:.1f}s"
                success = False
            else:
                log(f"Download successful, took {duration:.1f}s, found {len(downloaded_files)} files")
                
                # Compare with expected result (strict file directory structure verification)
                # Let downloader handle directory structure, test program only verifies result
                if success:
                    # Find actual company directories in expected result directory
                    expected_base_dir = Path(config["expected_result_dir"])
                    if expected_base_dir.exists():
                        expected_company_dirs = [d for d in expected_base_dir.iterdir() if d.is_dir()]
                        
                        if not expected_company_dirs:
                            success = False
                            error_msg = "No company directories found in expected result directory"
                        else:
                            # Strict verification: Check if each expected file is in the correct company directory
                            all_matched = True
                            matched_files = 0
                            total_expected_files = 0
                            
                            for expected_company_dir in expected_company_dirs:
                                expected_files = list(expected_company_dir.glob("*.pdf"))
                                total_expected_files += len(expected_files)
                                
                                for expected_file in expected_files:
                                    file_matched = False
                                    
                                    # Find file with same name in same company directory in downloaded files
                                    for downloaded_file in downloaded_files:
                                        if (downloaded_file.name == expected_file.name and 
                                            downloaded_file.parent.name == expected_company_dir.name and
                                            compare_files(downloaded_file, expected_file)):
                                            log(f"File match: {expected_company_dir.name}/{expected_file.name}")
                                            matched_files += 1
                                            file_matched = True
                                            break
                                    
                                    if not file_matched:
                                        log(f"File mismatch: {expected_company_dir.name}/{expected_file.name}")
                                        all_matched = False
                            
                            # Check for extra downloaded files
                            if len(downloaded_files) > matched_files:
                                log(f"Warning: Found {len(downloaded_files) - matched_files} extra downloaded files")
                                for downloaded_file in downloaded_files:
                                    # Check if this file is expected
                                    is_expected = False
                                    for expected_company_dir in expected_company_dirs:
                                        for expected_file in expected_company_dir.glob("*.pdf"):
                                            if downloaded_file.name == expected_file.name:
                                                is_expected = True
                                                break
                                        if is_expected:
                                            break
                                    
                                    if not is_expected:
                                        log(f"Extra file: {downloaded_file.parent.name}/{downloaded_file.name}")
                                        all_matched = False
                            
                            # Check for missing expected files
                            if matched_files < total_expected_files:
                                error_msg = f"Missing {total_expected_files - matched_files} expected files"
                                all_matched = False
                            
                            if all_matched and matched_files > 0:
                                log(f"All files matched successfully: {matched_files}/{total_expected_files}")
                            else:
                                success = False
                                error_msg = f"File match failed: {matched_files}/{total_expected_files}"
                    else:
                        success = False
                        error_msg = "Expected result directory does not exist"
                
                # Verify if directory structure meets requirements (files should be in company subdirectories, not root)
                if success and not delete_later:
                    root_pdf_files = [f for f in save_dir.glob("*.pdf")]
                    if root_pdf_files:
                        log(f"Warning: Found files in root directory: {[f.name for f in root_pdf_files]}")
                        # This itself is not a failure, but should be logged as warning
        else:
            error_msg = error_msg or "No files downloaded"
            success = False
            
    except Exception as e:
        error_msg = f"Test exception: {str(e)}"
        success = False
    
    # Note: Cleanup logic moved to main function end for unified processing
    log(f"Test finished, waiting for unified cleanup (delete_later={delete_later})")
    
    # Output result
    log(f"Result: {'Success' if success else 'Failed'}")
    if error_msg:
        log(f"Error: {error_msg}")
    
    # Get real stock name
    stock_name = get_real_stock_name(stock_code)
    
    return {
        "downloader": "old",
        "stock_code": stock_code,
        "stock_name": stock_name,
        "success": success,
        "error": error_msg,
        "duration": duration,
        "downloaded_files": len(downloaded_files)
    }

def run_test_with_new_downloader(test_case, config, browser_strategy="playwright"):
    """Run test with new downloader"""
    stock_code = test_case["stock_code"]
    log(f"\nTesting with new downloader: {stock_code} (Strategy: {browser_strategy})")
    
    # Let downloader handle directory structure, test program does not interfere
    allowed_keywords = test_case.get("allowed_keywords")
    delete_later = test_case.get("delete_later", True)
    max_pages = test_case.get("max_pages", 5)
    timeout = test_case.get("timeout_seconds", 180)
    suffix = test_case.get("suffix", "research")
    
    start_time = time.time()
    success = False
    error_msg = ""
    downloaded_files = []
    duration = 0
    
    try:
        # Create temporary config directory
        temp_config_dir = Path(config["save_dir"]) / "temp_config"
        temp_config_dir.mkdir(exist_ok=True)
        
        # Create temporary mapping file - use actual mapping data instead of hardcoded
        temp_mapping_file = temp_config_dir / "temp_mapping.json"
        
        # Copy relevant stock mapping data from main mapping file
        from src.data.mapping import MappingManager
        main_mapping = MappingManager("stock_orgid_mapping.json")
        
        test_mapping = {}
        # Only include stock code for current test case
        test_stock_code = test_case["stock_code"]
        org_id = main_mapping.get_org_id(test_stock_code)
        stock_name = main_mapping.get_stock_name(test_stock_code) or f"测试公司{test_stock_code}"
        
        if org_id:
            test_mapping[test_stock_code] = {"orgId": org_id, "name": stock_name}
        else:
            # If orgId not found, use a valid test orgId
            test_mapping[test_stock_code] = {"orgId": "9900056250", "name": stock_name}
        
        with open(temp_mapping_file, 'w', encoding='utf-8') as f:
            json.dump(test_mapping, f, ensure_ascii=False, indent=2)
        
        # Create temporary config file
        temp_config_file = temp_config_dir / "temp_config.json"
        temp_config_data = {
            "browser": {
                "strategy": browser_strategy,
                "headless": True
            },
            "download": {
                "max_retries": config.get("max_retries", 3),
                "max_downloads_per_session": 5,
                "human_behavior_delay": 3
            },
            "webdriver": {
                "window_size": "1920,1080",
                "user_agents": [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ]
            },
            "timeout": {
                "page_load": 15,
                "element_wait": 3
            }
        }
        with open(temp_config_file, 'w', encoding='utf-8') as f:
            json.dump(temp_config_data, f, ensure_ascii=False, indent=2)
        
        # Use unified downloader factory API (backward compatible)
        from src.factory.downloader_factory import downloader_factory
        from src.interfaces.downloader_interface import DownloadRequest

        # Create downloader instance, use specified browser strategy (guaranteed compatible via adapter)
        downloader = downloader_factory.create_legacy_adapter(
            'download_service_v2',
            save_dir=config["save_dir"],
            mapping_file=str(temp_mapping_file),
            browser_strategy=browser_strategy
        )

        # Get stock name
        stock_name = get_real_stock_name(stock_code)

        # Create DownloadRequest object (Critical Fix)
        request = DownloadRequest(
            stock_code=stock_code,
            stock_name=stock_name,
            suffix=suffix,
            allowed_keywords=allowed_keywords,
            max_pages=max_pages,
            delete_later=delete_later,
            timeout_seconds=timeout,
            save_dir=config["save_dir"]
        )

        # Execute download - Adapter needs separate arguments, not DownloadRequest object
        # Note: We forcibly pass delete_later=False here because we need to preserve files for final directory comparison.
        # Cleanup will be performed uniformly by e2e_test.py after comparison, based on test_case config.
        download_records = downloader.download_stock_pdfs(
            stock_code=request.stock_code,
            stock_name=request.stock_name,
            suffix=request.suffix,
            allowed_keywords=request.allowed_keywords,
            max_pages=request.max_pages,
            timeout_seconds=request.timeout_seconds,
            save_dir=request.save_dir,
            delete_later=False  # Forcibly do not delete, wait for test script unified cleanup
        )

        # Diagnostic info: Print return value type
        print(f"[DEBUG] download_stock_pdfs() return type: {type(download_records)}")
        print(f"[DEBUG] download_stock_pdfs() return value: {download_records}")

        duration = time.time() - start_time

        # Check return value type, handle compatibility issues
        if hasattr(download_records, 'downloaded_files'):
            # If DownloadResult object
            actual_files = download_records.downloaded_files
            success = len(actual_files) > 0
        elif isinstance(download_records, dict) and 'downloaded_files' in download_records:
            # If dictionary format
            actual_files = download_records['downloaded_files']
            success = len(actual_files) > 0
        elif isinstance(download_records, list):
            # If list format
            actual_files = download_records
            success = len(actual_files) > 0
        else:
            # Unknown type, assume old list format
            actual_files = download_records
            success = len(actual_files) > 0
        if success:
            log(f"Download successful, obtained {len(actual_files)} files")
        else:
            error_msg = "No files downloaded"
            log(error_msg)
        
        # Check downloaded files (use actual file list returned by downloader)
        save_dir = Path(config["save_dir"])

        # Use actual_files instead of searching again, as downloader might have different save logic
        if success and actual_files:
            # Verify if files really exist
            existing_files = [f for f in actual_files if Path(f).exists()]
            downloaded_files = existing_files  # Update downloaded_files variable
            log(f"Found {len(existing_files)} actual downloaded files")

            # Verify result
            # Check timeout
            if duration > timeout:
                error_msg = f"Download too slow: {duration:.1f}s"
                success = False
            else:
                # Check if files are in company directory (if not deleted)
                if not delete_later:
                    # Find actual company directories (created by downloader)
                    company_dirs = [d for d in save_dir.iterdir() if d.is_dir() and d.name != '.tmp']

                    if not company_dirs:
                        # Check if files are in root directory (compatible with old version)
                        root_files = [f for f in save_dir.glob("*.pdf")]
                        if root_files:
                            log(f"Warning: No company directory found, but found {len(root_files)} files in root")
                        else:
                            if len(existing_files) == 0:
                                error_msg = "Downloader did not create any company directory and no files found"
                            else:
                                log(f"Info: Downloader reported {len(existing_files)} files downloaded, but corresponding directory structure not found")
                    else:
                        # Check if files are in company subdirectory
                        company_files = []
                        for company_dir in company_dirs:
                            company_files.extend([f for f in company_dir.glob("*.pdf")])

                        if not company_files:
                            root_files = [f for f in save_dir.glob("*.pdf")]
                            if root_files:
                                log(f"Warning: Company directory empty, but found {len(root_files)} files in root")
                            else:
                                if len(existing_files) == 0:
                                    error_msg = "No PDF files found in company subdirectory"
                                else:
                                    log(f"Info: Downloader reported {len(existing_files)} files downloaded, but company directory empty")
                        else:
                            log(f"Found {len(company_files)} files in company directory: {[f.parent.name for f in company_files]}")
        else:
            # If no actual files, but success is True, it means actual_files is empty
            if success and not actual_files:
                error_msg = "Downloader reported success but returned no file paths"
                success = False

        # Fix: Do not overwrite previous success logic
        # success = not error_msg  # This line would overwrite all previous success checks, which is wrong
        
        # Clean up temporary config directory
        try:
            shutil.rmtree(temp_config_dir)
        except Exception as e:
            log(f"Failed to clean up temporary config directory: {e}")

    except Exception as e:
        error_msg = f"Test exception: {str(e)}"
        success = False
        duration = time.time() - start_time

        # Ensure temporary config directory is cleaned up
        try:
            if 'temp_config_dir' in locals():
                shutil.rmtree(temp_config_dir)
        except Exception:
            pass

    # Clean up downloader resources (especially browser instances)
    try:
        if 'downloader' in locals() and hasattr(downloader, 'cleanup'):
            downloader.cleanup()
            log(f"Downloader resources cleaned up")
    except Exception as e:
        log(f"Failed to clean up downloader resources: {e}")

    # Read debug markers (before cleanup)
    debug_markers = []
    debug_summary = {}
    try:
        if 'downloader' in locals():
            # Try to get debug markers
            if hasattr(downloader, 'get_debug_markers'):
                debug_markers = downloader.get_debug_markers()
                log(f"Got {len(debug_markers)} debug markers")

            if hasattr(downloader, 'get_debug_summary'):
                debug_summary = downloader.get_debug_summary()
                log(f"Debug marker summary: Success={debug_summary.get('successful', 0)}, Failed={debug_summary.get('failed', 0)}")

                # Output statistics for each step
                if 'steps' in debug_summary:
                    for step_name, step_stats in debug_summary['steps'].items():
                        log(f"  - {step_name}: {step_stats['successful']}/{step_stats['total']} successful")
    except Exception as e:
        log(f"Failed to read debug markers: {e}")

    # Ensure all temporary files are cleaned up (including possibly residual temp directories)
    try:
        save_path = Path(save_dir)
        # Clean up temporary config directory
        temp_config_path = save_path / "temp_config"
        if temp_config_path.exists():
            shutil.rmtree(temp_config_path, ignore_errors=True)

        # Clean up potentially residual Playwright temporary directories
        for item in save_path.iterdir():
            if item.is_dir() and (item.name.startswith('playwright_user_') or
                                (len(item.name) == 36 and '-' in item.name)):  # UUID format
                try:
                    shutil.rmtree(item, ignore_errors=True)
                    log(f"Cleaned up residual temporary directory: {item.name}")
                except:
                    pass
    except Exception as e:
        log(f"Failed to clean up residual temporary files: {e}")

    log(f"Test finished (delete_later={delete_later})")

    # Output result
    log(f"Result: {'Success' if success else 'Failed'}")
    if error_msg:
        log(f"Error: {error_msg}")
    log(f"Duration: {duration:.1f}s")

    # Get real stock name
    stock_name = get_real_stock_name(stock_code)

    # Output detailed debug info
    log(f"Debug Info:")
    log(f"  - Stock Code: {stock_code}")
    log(f"  - Stock Name: {stock_name}")
    log(f"  - Browser Strategy: {browser_strategy}")
    log(f"  - Download Success: {success}")
    log(f"  - Downloaded Files: {len(downloaded_files)}")
    log(f"  - Error Message: {error_msg}")
    log(f"  - Duration: {duration:.1f}s")
    log(f"  - Debug Markers: {len(debug_markers)}")

    return {
        "downloader": "new",
        "browser_strategy": browser_strategy,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "success": success,
        "error": error_msg,
        "duration": duration,
        "downloaded_files": len(downloaded_files),
        "debug_markers": debug_markers,
        "debug_summary": debug_summary
    }

def compare_directories(actual_dir, expected_dir):
    """Compare if two directories structure and content are identical (100% strict mode, no filtering)"""
    actual_path = Path(actual_dir)
    expected_path = Path(expected_dir)

    if not actual_path.exists() or not expected_path.exists():
        return False, "Directory does not exist"

    # Create file locks to prevent cleanup
    lock_files = []
    try:
        # Lock all company directories in actual directory
        companies_to_lock = [d.name for d in actual_path.iterdir() if d.is_dir()]

        log(f"Starting strict file comparison, locking {len(companies_to_lock)} company directories to prevent cleanup...")
        for company_name in companies_to_lock:
            company_dir = actual_path / company_name
            if company_dir.exists():
                lock_file = company_dir / ".lock"
                try:
                    lock_file.touch(exist_ok=True)
                    lock_files.append(lock_file)
                except Exception as e:
                    log(f"Warning: Failed to create lock file for directory {company_dir}: {e}")

        # Compare directory structure (100% strict, no filtering)
        actual_dirs = sorted([p.relative_to(actual_path) for p in actual_path.rglob('*') if p.is_dir()])
        expected_dirs = sorted([p.relative_to(expected_path) for p in expected_path.rglob('*') if p.is_dir()])

        if actual_dirs != expected_dirs:
            return False, f"Directory structure mismatch:\n  Actual: {actual_dirs}\n  Expected: {expected_dirs}"

        # Compare files (100% strict, no filtering)
        actual_files = sorted([p.relative_to(actual_path) for p in actual_path.rglob('*.pdf')])
        expected_files = sorted([p.relative_to(expected_path) for p in expected_path.rglob('*.pdf')])

        if actual_files != expected_files:
            return False, f"File list mismatch:\n  Actual: {actual_files}\n  Expected: {expected_files}"

        # Compare file content
        for file_path in expected_files:
            actual_file = actual_path / file_path
            expected_file = expected_path / file_path

            if not compare_files(actual_file, expected_file):
                return False, f"File content mismatch: {file_path}"

        return True, "All files and directories matched exactly"
    finally:
        # Cleanup lock files
        log(f"File comparison finished, cleaning {len(lock_files)} lock files...")
        for lock_file in lock_files:
            try:
                if lock_file.exists():
                    lock_file.unlink()
            except Exception as e:
                log(f"Warning: Failed to delete lock file {lock_file}: {e}")

def main():
    """Main function"""
    log("Starting End-to-End Test (Final Version)")
    log("Strictly implementing requirements from test instructions")

    # Load config (only supports config_end2end_test.json)
    import argparse
    import json
    parser = argparse.ArgumentParser(description='End-to-End Test')
    parser.add_argument('--test-old-downloader', action='store_true', help='Test old downloader')
    parser.add_argument('--browser-strategy', choices=['selenium', 'playwright', 'both'],
                       default='playwright', help='Browser strategy mode (default: playwright)')
    args = parser.parse_args()
    
    # Always use config_end2end_test.json config file
    config_file = 'config_end2end_test.json'
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        log(f"Failed to load config: {e}")
        return 1
    
    log(f"Using config: {config_file}")
    log(f"Save directory: {config['save_dir']}")
    log(f"Expected result directory: {config['expected_result_dir']}")
    log(f"Browser strategy: {args.browser_strategy}")
    
    # Create necessary directories
    save_dir = Path(config["save_dir"])
    Path("logs").mkdir(exist_ok=True)

    # Get test case list (for smart cleanup)
    test_cases = config.get("test_cases", [])

    # === Critical Change: Force reset test directory ===
    # Pain point solution: Ensure absolutely clean environment before each test, remove all residual files from previous tests (including .crdownload etc.)
    log("Initializing test environment...")
    try:
        if save_dir.exists():
            log(f"Cleaning old test directory: {save_dir}")
            # Use shutil.rmtree to thoroughly delete directory and all contents
            shutil.rmtree(save_dir)
            # Wait briefly for filesystem to release lock (Windows specific)
            time.sleep(0.5)
        
        # Recreate clean empty directory
        save_dir.mkdir(parents=True, exist_ok=True)
        log(f"Created brand new test result directory: {save_dir}")
    except Exception as e:
        log(f"Critical Error: Failed to reset test directory: {e}")
        # If unable to clean directory, test cannot proceed, must error exit
        return 1
    
    # Verify test setup
    log("\nVerifying test setup...")
    expected_dir = Path(config["expected_result_dir"])
    if not expected_dir.exists():
        log(f"Warning: Expected result directory does not exist: {expected_dir}")
    else:
        company_dirs = [d for d in expected_dir.iterdir() if d.is_dir()]
        log(f"Found {len(company_dirs)} expected result company directories")
        
        # Check total expected files
        expected_files = list(expected_dir.rglob('*.pdf'))
        log(f"Total expected files: {len(expected_files)}")
        for file in expected_files:
            log(f"  - {file.relative_to(expected_dir)}")
    
    # Run all test cases
    all_results = []
    max_test_retries = 1  # Max retries per test case
    companies_to_compare = []  # To store company names involved in tests

    for i, test_case in enumerate(test_cases, 1):
        log(f"\n{'='*80}")
        log(f"Test Case {i}/{len(test_cases)}: {test_case['stock_code']}")
        log(f"Type: {test_case.get('suffix', 'research')}")
        log(f"delete_later: {test_case.get('delete_later', True)}")
        log(f"max_pages: {test_case.get('max_pages', 5)}")
        log(f"{'='*80}")
        
        # Test new downloader (with retry mechanism) - Select strategy based on command line args
        if args.browser_strategy == 'both':
            strategies_to_test = ["playwright", "selenium"]
        else:
            strategies_to_test = [args.browser_strategy]
        
        for strategy in strategies_to_test:
            new_result = None
            for retry in range(max_test_retries + 1):
                try:
                    log(f"Testing new downloader ({strategy})... (Attempt {retry + 1}/{max_test_retries + 1})")
                    new_result = run_test_with_new_downloader(test_case, config, strategy)
                    
                    # If download successful (regardless of file match), break retry loop
                    if new_result.get("downloaded_files", 0) > 0:
                        log(f"Download successful, obtained {new_result['downloaded_files']} files")
                        break
                    else:
                        log(f"Download failed, error: {new_result.get('error', 'Unknown error')}")
                        if retry < max_test_retries:
                            log(f"Waiting {10 + retry * 5} seconds before retry...")
                            time.sleep(10 + retry * 5)
                        else:
                            log(f"New downloader ({strategy}) test reached max retries")
                except Exception as e:
                    log(f"New downloader ({strategy}) test exception: {e}")
                    if retry < max_test_retries:
                        log(f"Waiting {10 + retry * 5} seconds before retry...")
                        time.sleep(10 + retry * 5)
                    else:
                        log(f"New downloader ({strategy}) test reached max retries")
                        new_result = {
                            "downloader": "new",
                            "browser_strategy": strategy,
                            "stock_code": test_case["stock_code"],
                            "stock_name": get_real_stock_name(test_case['stock_code']),
                            "success": False,
                            "error": f"Test exception: {str(e)}",
                            "duration": 0,
                            "downloaded_files": 0
                        }
            
            if new_result:
                all_results.append(new_result)
            
            # DEBUG CHECK
            debug_file = Path(config["save_dir"]) / "中密控股" / "中密控股：2025年一季度报告.pdf"
            log(f"DEBUG: After {strategy}, file exists: {debug_file.exists()}")

        # Test old downloader (if enabled)
        if args.test_old_downloader:
            log(f"\n{'='*80}")
            log(f"Testing old downloader: {test_case['stock_code']}")
            log(f"{'='*80}")
            try:
                old_result = run_test_with_old_downloader(test_case, config)
                all_results.append(old_result)
                log(f"Old downloader test finished: {old_result.get('success', False)}")
                time.sleep(2)  # Interval after old downloader test
            except Exception as e:
                log(f"Old downloader test exception: {e}")
                old_result = {
                    "downloader": "old",
                    "stock_code": test_case["stock_code"],
                    "success": False,
                    "error": f"Old downloader test exception: {e}",
                    "duration": 0,
                    "downloaded_files": 0
                }
                all_results.append(old_result)

        # Strategy interval (if testing multiple strategies)
        if len(strategies_to_test) > 1:
            time.sleep(5)  # 5 seconds interval between strategies
        else:
            time.sleep(2)  # 2 seconds interval for single strategy
    
    # Execute final directory comparison
    log(f"\n{'='*80}")
    log("Final Directory Comparison")
    log(f"{'='*80}")

    save_dir = Path(config["save_dir"])
    expected_dir = Path(config["expected_result_dir"])

    # Check total downloaded files
    downloaded_files = list(save_dir.rglob('*.pdf'))
    log(f"Total downloaded files: {len(downloaded_files)}")
    for file in downloaded_files:
        log(f"  - {file.relative_to(save_dir)}")

    # Execute directory comparison (100% strict mode, no filtering)
    log(f"Starting 100% strict directory comparison...")
    comparison_success, comparison_message = compare_directories(save_dir, expected_dir)

    log(f"Directory comparison result: {'Success' if comparison_success else 'Failed'}")
    log(f"Comparison details: {comparison_message}")

    # Verify directory structure (strict mode) - Verify before final cleanup
    log(f"\nDirectory Structure Verification (Strict Mode):")
    from src.utils.directory_manager import DirectoryManager
    directory_manager = DirectoryManager()

    # Get expected company list (only include companies involved in tests)
    expected_companies = companies_to_compare if companies_to_compare else []
    if not expected_companies and expected_dir.exists():
        # If company names not obtained, fallback to all directories
        expected_companies = [d.name for d in expected_dir.iterdir() if d.is_dir()]
    log(f"Verifying directory structure, expected companies: {expected_companies}")

    structure_valid, structure_issues = directory_manager.validate_directory_structure(
        save_dir, expected_companies
    )

    log(f"Directory structure verification: {'Passed' if structure_valid else 'Failed'}")
    if not structure_valid:
        for issue in structure_issues:
            log(f"  - {issue}")

    # After directory verification, perform final cleanup (only delete files that need deletion)
    log("\nExecuting final cleanup...")
    try:
        from tools.debug.test_helper_cleaner import clean_test_files
        preserve_cases = [case for case in test_cases if not case.get("delete_later", True)]
        clean_result = clean_test_files(config["save_dir"], preserve_cases)
        log(f"Cleanup finished:")
        log(f"  - Cleaned temp files: {clean_result.get('cleaned_temp_files', 0)}")
        log(f"  - Cleaned temp dirs: {clean_result.get('cleaned_temp_dirs', 0)}")
        log(f"  - Cleaned company files: {clean_result['cleaned_files']}")
        log(f"  - Cleaned company dirs: {clean_result['cleaned_dirs']}")
        log(f"  - Preserved files: {clean_result['preserved_files']}")
        log(f"  - Preserved dirs: {clean_result['preserved_dirs']}")
    except Exception as e:
        log(f"Cleanup failed: {e}")

    # Generate report
    total_tests = len(all_results)
    successful_downloads = sum(1 for r in all_results if r.get("downloaded_files", 0) > 0)

    # Update overall test result - Must match directory structure and file content 100% exactly
    # comparison_success already contains strict directory and file match check
    overall_success = comparison_success
    
    log(f"\nTest Summary:")
    log(f"Total Test Cases: {total_tests}")
    log(f"Successful Downloads: {successful_downloads}")
    log(f"Success Rate: {successful_downloads/total_tests*100:.1f}%")
    log(f"Directory Comparison: {'Passed' if comparison_success else 'Failed'}")
    log(f"Directory Structure: {'Passed' if structure_valid else 'Failed'}")
    log(f"Overall Test: {'Passed' if overall_success else 'Failed'}")
    
    # Output detailed results
    log(f"\nDetailed Results:")
    for result in all_results:
        status = "Success" if result.get("downloaded_files", 0) > 0 else "Failed"
        strategy = result.get("browser_strategy", "unknown")
        log(f"  - {result['stock_code']} [{strategy}]: {status} ({result.get('downloaded_files', 0)} files, {result.get('duration', 0):.1f}s)")
    
    # Compare browser strategy performance
    log(f"\nBrowser Strategy Performance Comparison:")
    strategy_results = {}
    for result in all_results:
        strategy = result.get("browser_strategy", "selenium")
        if strategy not in strategy_results:
            strategy_results[strategy] = {
                "total_tests": 0,
                "successful_tests": 0,
                "total_duration": 0,
                "total_files": 0,
                "total_errors": 0,
                "error_messages": []
            }
        
        strategy_results[strategy]["total_tests"] += 1
        if result.get("downloaded_files", 0) > 0:
            strategy_results[strategy]["successful_tests"] += 1
            strategy_results[strategy]["total_files"] += result.get("downloaded_files", 0)
        else:
            strategy_results[strategy]["total_errors"] += 1
            if result.get("error"):
                strategy_results[strategy]["error_messages"].append(result["error"])
        strategy_results[strategy]["total_duration"] += result.get("duration", 0)
    
    for strategy, stats in strategy_results.items():
        success_rate = (stats["successful_tests"] / stats["total_tests"] * 100) if stats["total_tests"] > 0 else 0
        avg_duration = stats["total_duration"] / stats["total_tests"] if stats["total_tests"] > 0 else 0
        avg_files = stats["total_files"] / stats["successful_tests"] if stats["successful_tests"] > 0 else 0
        error_rate = (stats["total_errors"] / stats["total_tests"] * 100) if stats["total_tests"] > 0 else 0
        
        log(f"  - {strategy.upper()}:")
        log(f"     Success Rate: {success_rate:.1f}% ({stats['successful_tests']}/{stats['total_tests']})")
        log(f"     Failure Rate: {error_rate:.1f}% ({stats['total_errors']}/{stats['total_tests']})")
        log(f"     Avg Duration: {avg_duration:.1f}s")
        log(f"     Avg Files: {avg_files:.1f} / successful test")
        
        # Show common error messages
        if stats["error_messages"]:
            from collections import Counter
            error_counter = Counter(stats["error_messages"])
            log(f"     Common Errors:")
            for error_msg, count in error_counter.most_common(3):
                log(f"        - {count} times: {error_msg}")

    # Generate test report
    log("\nGenerating test report...")
    try:
        import json
        from datetime import datetime

        report_data = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "test_type": "e2e",
                "description": "End-to-End Test Report",
                "config_file": config_file
            },
            "test_cases": test_cases,
            "results": strategy_results,
            "summary": {
                "overall_success": overall_success,
                "total_tests": sum(stats["total_tests"] for stats in strategy_results.values()),
                "successful_tests": sum(stats["successful_tests"] for stats in strategy_results.values()),
                "total_errors": sum(stats["total_errors"] for stats in strategy_results.values()),
                "total_duration": sum(stats["total_duration"] for stats in strategy_results.values()),
                "total_files": sum(stats["total_files"] for stats in strategy_results.values())
            }
        }

        report_file = "e2e_test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        log(f"Test report saved to: {report_file}")

    except Exception as e:
        log(f"Failed to generate test report: {e}")

    return 0 if overall_success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
