#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Debug Marker Tool - Records detailed debug information
"""

import json
import time
import os
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path


def _sanitize_for_json(obj: Any) -> Any:
    """
    Convert object to JSON serializable format

    Args:
        obj: Object to convert

    Returns:
        JSON serializable object
    """
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj

    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(item) for item in obj]

    if isinstance(obj, dict):
        return {str(k): _sanitize_for_json(v) for k, v in obj.items()}

    # For objects that cannot be serialized, return their string representation
    try:
        # Try calling __dict__ or related attributes
        if hasattr(obj, '__dict__'):
            return {
                '__class__': obj.__class__.__name__,
                '__module__': obj.__class__.__module__,
                'repr': repr(obj)[:200]  # Limit length
            }
        return str(obj)[:200]
    except:
        return f"<Unserializable: {obj.__class__.__name__}>"


class DebugMarker:
    """Debug Marker - Records detailed execution steps and status"""

    def __init__(self, marker_type: str):
        """
        Initialize debug marker

        Args:
            marker_type: Marker type (e.g. "pagination", "download", "url_generation")
        """
        self.marker_type = marker_type
        self.steps: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self.marker_id = f"{marker_type}_{int(time.time() * 1000)}"

    def add_step(self, step_id: str, description: str, details: Dict[str, Any] = None):
        """
        Add step record

        Args:
            step_id: Step ID
            description: Step description
            details: Detailed info
        """
        step = {
            "step_id": step_id,
            "description": description,
            "details": details or {},
            "timestamp": time.time(),
            "elapsed_ms": int((time.time() - self.start_time) * 1000)
        }
        self.steps.append(step)

    def save(self, log_dir: str = "logs/debug_markers"):
        """
        Save debug marker to file

        Args:
            log_dir: Log directory
        """
        try:
            # Ensure directory exists
            Path(log_dir).mkdir(parents=True, exist_ok=True)

            # Build complete marker data (use sanitize to handle non-serializable objects)
            marker_data = {
                "marker_id": self.marker_id,
                "marker_type": self.marker_type,
                "start_time": datetime.now().isoformat(),
                "total_elapsed_ms": int((time.time() - self.start_time) * 1000),
                "steps": _sanitize_for_json(self.steps),
                "step_count": len(self.steps)
            }

            # Save to file
            filename = f"markers_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            filepath = Path(log_dir) / filename

            # Append mode (each line is a complete JSON object)
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(marker_data, ensure_ascii=False) + '\n')

        except Exception as e:
            # If save fails, at least print to console
            try:
                sanitized_data = _sanitize_for_json(marker_data) if 'marker_data' in locals() else "data unavailable"
                print(f"[DEBUG_MARKER] Save failed: {e}")
                print(f"[DEBUG_MARKER] Data: {json.dumps(sanitized_data, ensure_ascii=False)}")
            except:
                print(f"[DEBUG_MARKER] Save failed and unable to print data: {e}")

    def __repr__(self):
        return f"DebugMarker(type={self.marker_type}, steps={len(self.steps)})"
