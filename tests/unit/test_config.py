"""Unit tests for config module."""
import json
import tempfile

import pytest

from src.config import load_companies, load_config, _default_config
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


class TestLoadCompanies:
    def test_basic_parsing(self, tmp_path):
        f = tmp_path / "companies.txt"
        f.write_text("300470 中密控股\n300750\n301611 珂玛科技\n", encoding="utf-8")
        companies = load_companies(str(f))
        assert len(companies) == 3
        assert companies[0] == {"stock_code": "300470", "company_name": "中密控股"}
        assert companies[1] == {"stock_code": "300750"}
        assert companies[2] == {"stock_code": "301611", "company_name": "珂玛科技"}

    def test_comments_and_blanks_skipped(self, tmp_path):
        f = tmp_path / "companies.txt"
        f.write_text("# comment\n\n  \n300470 中密控股\n# another comment\n", encoding="utf-8")
        companies = load_companies(str(f))
        assert len(companies) == 1
        assert companies[0]["stock_code"] == "300470"

    def test_empty_file(self, tmp_path):
        f = tmp_path / "companies.txt"
        f.write_text("", encoding="utf-8")
        companies = load_companies(str(f))
        assert companies == []

    def test_file_not_found(self):
        with pytest.raises(ConfigError, match="Companies file not found"):
            load_companies("/nonexistent/companies.txt")

    def test_trailing_whitespace_stripped(self, tmp_path):
        """Trailing whitespace on company name should be stripped."""
        f = tmp_path / "companies.txt"
        f.write_text("300470 中密控股  \n", encoding="utf-8")
        companies = load_companies(str(f))
        assert len(companies) == 1
        assert companies[0]["company_name"] == "中密控股"

    def test_tab_separator(self, tmp_path):
        """Tab separator between code and name should work."""
        f = tmp_path / "companies.txt"
        f.write_text("300470\t中密控股\n", encoding="utf-8")
        companies = load_companies(str(f))
        assert len(companies) == 1
        assert companies[0] == {"stock_code": "300470", "company_name": "中密控股"}

    def test_windows_line_endings(self, tmp_path):
        """Windows \\r\\n line endings should parse correctly."""
        f = tmp_path / "companies.txt"
        f.write_bytes(b"300470 \xe4\xb8\xad\xe5\xaf\x86\xe6\x8e\xa7\xe8\x82\xa1\r\n300750\r\n")
        companies = load_companies(str(f))
        assert len(companies) == 2
        assert companies[0] == {"stock_code": "300470", "company_name": "中密控股"}
        assert companies[1] == {"stock_code": "300750"}

    def test_file_with_only_comments(self, tmp_path):
        """File containing only comments should return empty list."""
        f = tmp_path / "companies.txt"
        f.write_text("# comment 1\n# comment 2\n", encoding="utf-8")
        companies = load_companies(str(f))
        assert companies == []
