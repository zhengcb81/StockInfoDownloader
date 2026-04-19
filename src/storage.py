"""Simple JSON file storage."""
import json
from pathlib import Path
from typing import Any, Dict, Optional, cast

from .exceptions import MappingError
from .logger import log


class JsonStorage:
    """Read/write JSON files with error handling."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def load(self) -> Dict[str, Any]:
        """Load data from JSON file.

        Raises:
            MappingError: if the file exists but cannot be parsed as valid JSON.
            FileNotFoundError: if the file does not exist.
        """
        if not self.file_path.exists():
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return cast(Dict[str, Any], json.load(f))
        except json.JSONDecodeError as e:
            raise MappingError(f"Corrupted JSON file {self.file_path}: {e}") from e
        except Exception as e:
            log.error(f"Failed to load JSON {self.file_path}: {e}")
            raise MappingError(f"Failed to load JSON {self.file_path}: {e}") from e

    def save(self, data: Dict[str, Any]) -> bool:
        """Save data to JSON file."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            log.error(f"Failed to save JSON {self.file_path}: {e}")
            return False
