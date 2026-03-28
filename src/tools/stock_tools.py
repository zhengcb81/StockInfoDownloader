#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stock Information Tools
Concrete implementations of mapping, validation and debug tools.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


from src.data.mapping import MappingManager

from .tool_interface import BaseTool, DebugTool, ValidationTool


class StockMappingTool(BaseTool):
    """
    Tool for managing stock code to OrgID mapping.
    Consolidates logic from orgid_crawler.py and get_stock_name.py.
    """

    def __init__(self, config_manager=None):
        super().__init__(config_manager)
        self.mapping_file = self.config_manager.get("cache_management", {}).get(
            "mapping_file", "stock_orgid_mapping.json"
        )
        self.mapping_manager = MappingManager(self.mapping_file)

    def execute(
        self, action: str = "get", stock_code: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        if action == "get":
            if not stock_code:
                return {
                    "success": False,
                    "error": "stock_code is required for 'get' action",
                }
            org_id = self.mapping_manager.get_org_id(stock_code)
            name = self.mapping_manager.get_stock_name(stock_code)
            return {
                "success": True,
                "stock_code": stock_code,
                "org_id": org_id,
                "name": name,
            }

        elif action == "update":
            if not stock_code:
                return {
                    "success": False,
                    "error": "stock_code is required for 'update' action",
                }
            # Logic for updating mapping (crawler)
            return self._run_crawler(stock_code, **kwargs)

        elif action == "list":
            return {
                "success": True,
                "count": len(self.mapping_manager.mapping_data),
                "mapping": self.mapping_manager.mapping_data,
            }

        return {"success": False, "error": f"Unknown action: {action}"}

    def _run_crawler(self, stock_code: str, headless: bool = True) -> Dict[str, Any]:
        """Runs the crawler logic to find OrgID for a stock code."""
        # For now, we delegate to the existing crawler logic or implement a simplified version
        # To avoid massive code duplication here, we could import and use OrgIdCrawler
        # but the goal is to consolidate.
        from orgid_crawler import OrgIdCrawler

        crawler = OrgIdCrawler(output_file=self.mapping_file, headless=headless)
        org_id = crawler.get_org_id(stock_code)
        if org_id:
            name = (
                self.mapping_manager.get_stock_name(stock_code) or f"Stock_{stock_code}"
            )
            self.mapping_manager.add_mapping(stock_code, org_id, name)
            return {
                "success": True,
                "stock_code": stock_code,
                "org_id": org_id,
                "name": name,
            }
        return {"success": False, "error": f"Failed to crawl OrgID for {stock_code}"}


class StockValidationTool(ValidationTool):
    """
    Tool for validating OrgIDs and cache consistency.
    Consolidates logic from validate_org_id.py and validate_all_cached.py.
    """

    def execute(
        self, stock_code: Optional[str] = None, validate_all: bool = False, **kwargs
    ) -> Dict[str, Any]:
        if validate_all:
            return self._validate_all(**kwargs)
        if stock_code:
            return self.validate_page_content(stock_code, **kwargs)
        return {"success": False, "error": "stock_code or validate_all is required"}

    def _perform_validation(
        self, stock_code: str, org_id: str, **kwargs
    ) -> Dict[str, Any]:
        from validate_org_id import validate_org_id_url

        is_valid = validate_org_id_url(stock_code, org_id)
        return {
            "success": True,
            "stock_code": stock_code,
            "org_id": org_id,
            "is_valid": is_valid,
        }

    def _validate_all(self, **kwargs) -> Dict[str, Any]:
        mapping_file = self.config_manager.get("cache_management", {}).get(
            "mapping_file", "stock_orgid_mapping.json"
        )
        with open(mapping_file, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        results = {}
        for code, info in mapping.items():
            org_id = info.get("orgId")
            if org_id:
                res = self._perform_validation(code, org_id)
                results[code] = res.get("is_valid", False)

        return {
            "success": True,
            "results": results,
            "total": len(mapping),
            "valid_count": sum(1 for v in results.values() if v),
        }


class StockDebugTool(DebugTool):
    """
    Tool for debugging system state and flow.
    Consolidates logic from debug_stock_name_flow.py and debug_directory_structure.py.
    """

    def execute(self, category: str = "flow", **kwargs) -> Dict[str, Any]:
        if category == "flow":
            # Implementation from debug_stock_name_flow.py
            return self._debug_flow(**kwargs)
        elif category == "structure":
            # Implementation from debug_directory_structure.py
            return self._debug_structure(**kwargs)
        return {"success": False, "error": f"Unknown category: {category}"}

    def _perform_debug(self, **kwargs) -> Dict[str, Any]:
        return self.execute(**kwargs)

    def _debug_flow(self, **kwargs) -> Dict[str, Any]:
        # Simplified flow analysis
        from src.data.mapping import MappingManager

        mapping_file = self.config_manager.get("cache_management", {}).get(
            "mapping_file", "stock_orgid_mapping.json"
        )
        mm = MappingManager(mapping_file)

        sample_codes = ["301611", "300470", "000001"]
        flow_results = {}
        for code in sample_codes:
            flow_results[code] = {
                "name": mm.get_stock_name(code),
                "org_id": mm.get_org_id(code),
            }

        return {"success": True, "flow_results": flow_results}

    def _debug_structure(self, **kwargs) -> Dict[str, Any]:
        root = Path(".")
        structure = {
            "root_files": [f.name for f in root.iterdir() if f.is_file()],
            "src_dirs": (
                [d.name for d in (root / "src").iterdir() if d.is_dir()]
                if (root / "src").exists()
                else []
            ),
        }
        return {"success": True, "structure": structure}
