# -*- coding: utf-8 -*-
"""Progress tracker — persists per-company download state to a JSON file."""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .logger import log


class ProgressTracker:
    """Tracks per-company download progress in a JSON file.

    Each ``mark_*`` call writes to disk immediately so progress survives
    crashes.
    """

    def __init__(self, log_file: str = "logs/progress.json"):
        self.log_file = Path(log_file)
        self.data: Dict = self._load()

    # ── persistence ───────────────────────────────────────────────────

    def _load(self) -> Dict:
        """Load existing progress file or create a fresh structure."""
        if self.log_file.exists():
            try:
                raw = self.log_file.read_text(encoding="utf-8")
                data = json.loads(raw)
                # Validate expected keys
                if isinstance(data, dict) and "completed" in data and "failed" in data:
                    return data
                log.warning("Progress file has unexpected format, starting fresh")
            except (json.JSONDecodeError, OSError) as exc:
                log.warning(f"Cannot read progress file, starting fresh: {exc}")
        return self._fresh()

    def _fresh(self) -> Dict:
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        return {
            "started_at": now,
            "last_updated": now,
            "companies_file": "",
            "total": 0,
            "completed": [],
            "failed": [],
        }

    def _save(self) -> None:
        """Write current state to disk."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.data["last_updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        tmp = self.log_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.log_file)

    # ── public API ────────────────────────────────────────────────────

    def init_run(self, companies_file: str, total: int) -> None:
        """Set metadata for the current run (only on a fresh tracker)."""
        if not self.data["companies_file"]:
            self.data["companies_file"] = companies_file
        self.data["total"] = total
        self._save()

    def is_completed(self, stock_code: str) -> bool:
        """Return True if *stock_code* is already in the completed list."""
        return stock_code in self.data["completed"]

    def mark_completed(self, stock_code: str) -> None:
        """Mark *stock_code* as successfully completed."""
        if stock_code not in self.data["completed"]:
            self.data["completed"].append(stock_code)
        # Remove from failed if it was previously failed (retry succeeded)
        if stock_code in self.data["failed"]:
            self.data["failed"].remove(stock_code)
        self._save()

    def mark_failed(self, stock_code: str) -> None:
        """Mark *stock_code* as failed (will be retried on next run)."""
        if stock_code not in self.data["failed"]:
            self.data["failed"].append(stock_code)
        self._save()

    def get_pending(self, all_codes: List[str]) -> List[str]:
        """Return codes not yet completed (failed codes are retried)."""
        completed_set = set(self.data["completed"])
        return [code for code in all_codes if code not in completed_set]

    def summary(self) -> str:
        """Return a human-readable progress summary string."""
        total = self.data["total"]
        done = len(self.data["completed"])
        failed = len(self.data["failed"])
        pending = total - done
        return (
            f"Progress: {done}/{total} completed"
            f"{f', {failed} failed' if failed else ''}"
            f", {pending} pending"
        )

    @staticmethod
    def clean(log_file: str = "logs/progress.json") -> None:
        """Delete the progress file to start fresh."""
        p = Path(log_file)
        if p.exists():
            p.unlink()
            log.info("Progress file deleted")
