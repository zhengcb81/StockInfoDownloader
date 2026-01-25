#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modern Test Verification Suite
Runs only the highest quality, refactored tests to ensure system integrity.
"""

import sys
import subprocess
from pathlib import Path

def run_pytest(description, files):
    print(f"\n>>> Running {description} (via pytest)...")
    cmd = [sys.executable, "-m", "pytest", "-v"] + files
    result = subprocess.run(cmd)
    return result.returncode == 0

def run_script(description, script_path, args=None):
    print(f"\n>>> Running {description} (direct script)...")
    cmd = [sys.executable, script_path] + (args or [])
    result = subprocess.run(cmd)
    return result.returncode == 0

def main():
    print("=" * 60)
    print("STOCK INFO DOWNLOADER - FINAL QUALITY VERIFICATION")
    print("=" * 60)
    
    # 1. Modern Unit Tests
    unit_success = run_pytest("Modern Unit Tests", [
        "tests/unit/test_orgid_utils.py", 
        "tests/unit/test_cninfo_downloader.py", 
        "tests/unit/test_mapping.py", 
        "tests/unit/test_config.py"
    ])
    
    # 2. Integration Tests
    integration_success = run_pytest("Multi-Company Integration", ["tests/integration/multi_company/test_integration.py"])
    
    # 3. Official E2E Test
    e2e_success = run_script("Official End-to-End Test", "tests/e2e/official_e2e_test.py")
    
    print("\n" + "=" * 60)
    if all([unit_success, integration_success, e2e_success]):
        print("FINAL RESULT: ALL MODERN TESTS PASSED!")
        sys.exit(0)
    else:
        print("FINAL RESULT: SOME MODERN TESTS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()