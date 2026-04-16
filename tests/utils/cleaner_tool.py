"""Test cleaner tool — cleans test directories while preserving expected files."""
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from src.logger import log


class CleanerTool:
    """Cleans test directories, preserving files marked for retention."""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)

    def clean_test_directory(
        self, preserve_cases: List[Dict[str, Any]], dry_run: bool = False
    ) -> Dict[str, Any]:
        """Clean test dir, keeping files from delete_later=false test cases."""
        if not self.base_dir.exists():
            return {"status": "success", "message": "Directory does not exist"}

        mapping = self._load_mapping()

        # Determine which files to preserve
        preserve_keywords = set()
        for case in preserve_cases:
            if not case.get("delete_later", True):
                stock_code = case["stock_code"]
                preserve_keywords.add(stock_code)
                if stock_code in mapping:
                    name = mapping[stock_code].get("name")
                    if name:
                        preserve_keywords.add(name)

        deleted_files = 0
        deleted_dirs = 0
        preserved_files = 0

        for item in self.base_dir.iterdir():
            if item.is_file():
                if self._should_preserve(item, preserve_keywords):
                    preserved_files += 1
                else:
                    if not dry_run:
                        item.unlink()
                    deleted_files += 1
            elif item.is_dir():
                if not any(self._should_preserve(f, preserve_keywords) for f in item.rglob("*")):
                    if not dry_run:
                        shutil.rmtree(item)
                    deleted_dirs += 1

        return {
            "status": "success",
            "deleted_files": deleted_files,
            "deleted_dirs": deleted_dirs,
            "preserved_files": preserved_files,
        }

    def _should_preserve(self, path: Path, keywords: set) -> bool:
        """Check if a file/directory should be preserved."""
        name = path.name
        return any(kw in name for kw in keywords)

    def _load_mapping(self) -> Dict[str, Any]:
        """Load stock mapping for name lookups."""
        candidates = [
            Path("stock_orgid_mapping.json"),
            Path("configs/stock_orgid_mapping.json"),
            Path("src/data/stock_orgid_mapping.json"),
        ]
        for p in candidates:
            if p.exists():
                try:
                    with open(p, encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
        return {}
