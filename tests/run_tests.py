#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified Test Orchestrator
Uses pytest to run different categories of tests with standardized reporting.
"""

import sys
import argparse
import subprocess
from pathlib import Path

def run_pytest(args):
    """Executes pytest with given arguments."""
    cmd = [sys.executable, "-m", "pytest"] + args
    print(f"Executing: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode

def main():
    parser = argparse.ArgumentParser(description="Unified Test Runner for StockInfoDownloader")
    parser.add_argument(
        'type', 
        choices=['unit', 'integration', 'e2e', 'performance', 'all'],
        default='all',
        nargs='?',
        help='Type of tests to run (default: all)'
    )
    parser.add_argument('--cov', action='store_true', help='Enable coverage reporting')
    parser.add_argument('--html', action='store_true', help='Generate HTML report')
    parser.add_argument('--fast', action='store_true', help='Skip slow tests')
    parser.add_argument('-k', help='Filter tests by expression')

    args = parser.parse_args()
    
    pytest_args = ["-v"]
    
    # Map types to markers
    if args.type != 'all':
        pytest_args.extend(["-m", args.type])
    
    if args.fast:
        if "-m" in pytest_args:
            # Append "and not slow" to existing marker expression
            idx = pytest_args.index("-m") + 1
            pytest_args[idx] = f"({pytest_args[idx]}) and not slow"
        else:
            pytest_args.extend(["-m", "not slow"])

    if args.cov:
        pytest_args.extend(["--cov=src", "--cov-report=term-missing"])
        
    if args.html:
        report_dir = Path("test_reports")
        report_dir.mkdir(exist_ok=True)
        pytest_args.extend([f"--html=test_reports/report_{args.type}.html", "--self-contained-html"])

    if args.k:
        pytest_args.extend(["-k", args.k])

    # If no specific type but not 'all', default paths
    if args.type == 'all':
        pytest_args.append("tests/")
    
    ret_code = run_pytest(pytest_args)
    sys.exit(ret_code)

if __name__ == "__main__":
    main()