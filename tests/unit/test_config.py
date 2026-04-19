"""Unit tests for config module."""
import json
import tempfile

import pytest

from src.config import load_config, _default_config
from src.exceptions import ConfigError


class TestLoadConfig:
    def test_load_valid_config(self, tmp_path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"save_dir": "/tmp/test", "max_retries": 5}))
        config = load_config(str(cfg_file))
        assert config["save_dir"] == "/tmp/test"
        assert config["max_retries"] == 5

    def test_missing_config_returns_defaults(self):
        config = load_config("/nonexistent/config.json")
        assert "save_dir" in config
        assert "max_retries" in config
        assert config["max_retries"] == 3

    def test_invalid_json_raises_error(self, tmp_path):
        cfg_file = tmp_path / "bad.json"
        cfg_file.write_text("{invalid json}")
        with pytest.raises(ConfigError):
            load_config(str(cfg_file))

    def test_defaults_merge_with_user_config(self, tmp_path):
        cfg_file = tmp_path / "partial.json"
        cfg_file.write_text(json.dumps({"save_dir": "/custom/path"}))
        config = load_config(str(cfg_file))
        assert config["save_dir"] == "/custom/path"
        # Defaults should still be present
        assert "browser" in config
        assert "anti_crawler" in config
