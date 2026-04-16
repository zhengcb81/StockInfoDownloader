"""Test configuration — EnvironmentManager and test constants."""
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List


TEST_STOCK_CODES = ["000001", "000002", "002415", "600036", "600519"]

TEST_ORG_IDS = {
    "000001": "9900000001",
    "000002": "9900000002",
    "002415": "9900012688",
    "600036": "9900010036",
    "600519": "9900010519",
}


class EnvironmentManager:
    """Manages temp dirs/files for tests."""

    def __init__(self):
        self.temp_dirs: List[str] = []
        self.temp_files: List[str] = []

    def create_temp_dir(self, prefix: str = "test_") -> str:
        d = tempfile.mkdtemp(prefix=prefix)
        self.temp_dirs.append(d)
        return d

    def create_temp_file(self, suffix: str = ".tmp", content: str = "") -> str:
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        if content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        self.temp_files.append(path)
        return path

    def cleanup(self):
        for f in self.temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass
        for d in self.temp_dirs:
            try:
                if os.path.exists(d):
                    shutil.rmtree(d)
            except Exception:
                pass
        self.temp_dirs.clear()
        self.temp_files.clear()


def create_test_config(stock_code: str = "000001", save_dir: str = None) -> Dict[str, Any]:
    if save_dir is None:
        save_dir = tempfile.mkdtemp(prefix="test_downloads_")
    return {
        "stock_code": stock_code,
        "save_dir": save_dir,
        "headless": True,
        "max_retries": 2,
    }


def create_test_mapping() -> Dict[str, Any]:
    return {
        code: {"orgId": org_id, "name": f"Test{code}"}
        for code, org_id in TEST_ORG_IDS.items()
    }
