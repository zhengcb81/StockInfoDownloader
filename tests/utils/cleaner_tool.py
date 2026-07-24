"""Test cleaner tool — cleans test directories while preserving expected files."""
import json
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

        # Decide preservation file by file.  Preserving a company directory as
        # one opaque unit can accidentally retain delete_later=true artifacts
        # that happen to share the same directory.
        files = [path for path in self.base_dir.rglob("*") if path.is_file()]
        for path in files:
            if self._should_preserve(path, preserve_keywords):
                preserved_files += 1
                continue
            if not dry_run:
                path.unlink()
            deleted_files += 1

        # Remove only directories that are empty after file cleanup.  Work
        # deepest-first so nested empty directories are handled deterministically.
        directories = sorted(
            (path for path in self.base_dir.rglob("*") if path.is_dir()),
            key=lambda path: len(path.parts),
            reverse=True,
        )
        for directory in directories:
            is_empty = not any(directory.iterdir())
            if is_empty:
                if not dry_run:
                    directory.rmdir()
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
            Path("src/stock_orgid_mapping.json"),
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
