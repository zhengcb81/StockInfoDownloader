#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Debug Tracking System
Provides detailed step-tracking and marking for complex processes like downloading.
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.logger import get_logger

logger = get_logger(__name__)


class DebugStep(Enum):
    ORG_ID_MAPPING = "org_id_mapping"
    URL_GENERATION = "url_generation"
    WEBPAGE_CONNECTION = "webpage_connection"
    PDF_VISIBILITY = "pdf_visibility"
    PAGINATION = "pagination"
    KEYWORD_MATCHING = "keyword_matching"
    DOWNLOAD_PAGE_OPENING = "download_page_opening"
    DOWNLOAD_SUCCESS = "download_success"


class DebugMarker:
    def __init__(
        self, step: DebugStep, success: bool, details: Optional[Dict[str, Any]] = None, error: Optional[str] = None
    ):
        self.step = step
        self.success = success
        self.details = details or {}
        self.error = error
        self.timestamp = datetime.now()
        self.marker_id = f"{step.value}_{int(self.timestamp.timestamp() * 1000)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step.value,
            "step_name": self.step.name,
            "success": self.success,
            "details": self.details,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
            "timestamp_ms": int(self.timestamp.timestamp() * 1000),
            "marker_id": self.marker_id,
        }

    def to_log_string(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        msg = f"[DEBUG_MARKER] {status} {self.step.name} | Details: {json.dumps(self.details, ensure_ascii=False, separators=(',', ':'))}"
        if self.error:
            msg += f" | Error: {self.error}"
        return msg

    def log(self) -> None:
        logger.info(self.to_log_string())


class DebugMarkerManager:
    _instance: Optional["DebugMarkerManager"] = None
    _initialized: bool = False

    def __new__(cls, *args: Any, **kwargs: Any) -> "DebugMarkerManager":
        if not cls._instance:
            cls._instance = super(DebugMarkerManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir: str = "logs/debug_markers") -> None:
        if self._initialized:
            return
        self.markers: List[DebugMarker] = []
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"markers_{self.session_id}.jsonl"
        self._initialized = True

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def add_marker(
        self, step: DebugStep, success: bool, details: Optional[Dict[str, Any]] = None, error: Optional[str] = None
    ) -> DebugMarker:
        marker = DebugMarker(step, success, details, error)
        self.markers.append(marker)
        marker.log()

        # Write to file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(marker.to_dict(), ensure_ascii=False) + "\n")

        return marker

    def get_summary(self) -> Dict[str, Any]:
        total = len(self.markers)
        successful = len([m for m in self.markers if m.success])
        failed = total - successful

        steps_summary: Dict[str, Dict[str, int]] = {}
        for m in self.markers:
            step_val = m.step.value
            if step_val not in steps_summary:
                steps_summary[step_val] = {"total": 0, "success": 0}
            steps_summary[step_val]["total"] += 1
            if m.success:
                steps_summary[step_val]["success"] += 1

        return {
            "total_markers": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "steps": steps_summary,
        }

    def get_markers_for_e2e_test(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self.markers]

    def clear(self) -> None:
        self.markers = []


def get_debug_marker_manager() -> DebugMarkerManager:
    return DebugMarkerManager()
