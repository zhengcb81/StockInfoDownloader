#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
StockInfoDevKit CLI
Unified entry point for debugging, validation, and mapping management.
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tools.stock_tools import StockDebugTool, StockMappingTool, StockValidationTool
from src.tools.tool_interface import tool_manager

# Register tools
tool_manager.register_tool("mapping", StockMappingTool)
tool_manager.register_tool("validation", StockValidationTool)
tool_manager.register_tool("debug", StockDebugTool)


def main():
    parser = argparse.ArgumentParser(
        description="StockInfoDevKit CLI - Unified Developer Tools"
    )
    subparsers = parser.add_subparsers(dest="tool", help="Tool to use")

    # Mapping Tool
    mapping_parser = subparsers.add_parser(
        "mapping", help="Manage stock code to OrgID mapping"
    )
    mapping_parser.add_argument(
        "action", choices=["get", "update", "list"], help="Action to perform"
    )
    mapping_parser.add_argument("--stock-code", help="Stock code")
    mapping_parser.add_argument(
        "--headless", action="store_true", default=True, help="Run in headless mode"
    )

    # Validation Tool
    validation_parser = subparsers.add_parser(
        "validation", help="Validate OrgIDs and cache consistency"
    )
    validation_parser.add_argument("--stock-code", help="Stock code to validate")
    validation_parser.add_argument(
        "--all", action="store_true", help="Validate all cached entries"
    )

    # Debug Tool
    debug_parser = subparsers.add_parser("debug", help="Debug system state and flow")
    debug_parser.add_argument(
        "--category",
        choices=["flow", "structure"],
        default="flow",
        help="Debug category",
    )

    args = parser.parse_args()

    if not args.tool:
        parser.print_help()
        return

    # Execute tool
    kwargs = vars(args)
    tool_name = kwargs.pop("tool")

    # Handle specific tool argument renaming if needed
    if tool_name == "validation" and kwargs.get("all"):
        kwargs["validate_all"] = kwargs.pop("all")

    result = tool_manager.execute_tool(tool_name, **kwargs)

    # Output result
    if result.get("success"):
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
