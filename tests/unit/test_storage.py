"""Unit tests for storage module."""
import json
import tempfile

import pytest

from src.exceptions import MappingError
from src.storage import JsonStorage


class TestJsonStorage:
    def test_load_nonexistent_returns_empty(self):
        s = JsonStorage("/nonexistent/file.json")
        assert s.load() == {}

    def test_save_and_load(self):
        f = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        f.close()
        s = JsonStorage(f.name)
        assert s.save({"key": "value"}) is True
        data = s.load()
        assert data == {"key": "value"}

    def test_load_corrupted_raises_error(self):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        f.write("{invalid json")
        f.close()
        s = JsonStorage(f.name)
        with pytest.raises(MappingError):
            s.load()
