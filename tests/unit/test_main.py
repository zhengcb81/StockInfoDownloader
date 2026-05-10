"""Unit tests for main() CLI integration."""
import sys
from unittest.mock import MagicMock, patch

import pytest

from src.exceptions import ConfigError


class TestMainCLI:
    """Test main() argument parsing and execution priority."""

    def _mock_config(self):
        return {
            "save_dir": "/tmp/test",
            "headless": True,
            "max_retries": 1,
            "pages": [{"name": "Research", "suffix": "research", "max_pages": 1}],
        }

    def test_companies_flag_calls_run_multi(self, tmp_path):
        """--companies flag should call run_multi with loaded list."""
        companies_file = tmp_path / "companies.txt"
        companies_file.write_text("300470 中密控股\n300750\n", encoding="utf-8")

        mock_config = self._mock_config()

        with (
            patch("main.load_config", return_value=mock_config),
            patch("main.setup_logger"),
            patch("main.UnifiedRunner") as MockRunner,
        ):
            mock_runner = MagicMock()
            MockRunner.return_value = mock_runner

            with patch.object(sys, "argv", ["main.py", "--companies", str(companies_file)]):
                from main import main
                main()

            mock_runner.run_multi.assert_called_once()
            args, kwargs = mock_runner.run_multi.call_args
            companies = args[0]
            assert len(companies) == 2
            assert companies[0] == {"stock_code": "300470", "company_name": "中密控股"}
            assert companies[1] == {"stock_code": "300750"}
            assert kwargs.get("parallel") is False
            assert kwargs.get("workers") == 3

    def test_cli_stock_code_wins_over_companies(self, tmp_path):
        """When both stock_code and --companies are provided, stock_code wins."""
        companies_file = tmp_path / "companies.txt"
        companies_file.write_text("300470 中密控股\n", encoding="utf-8")

        mock_config = self._mock_config()

        with (
            patch("main.load_config", return_value=mock_config),
            patch("main.setup_logger"),
            patch("main.UnifiedRunner") as MockRunner,
        ):
            mock_runner = MagicMock()
            MockRunner.return_value = mock_runner

            with patch.object(sys, "argv", ["main.py", "000001", "--companies", str(companies_file)]):
                from main import main
                main()

            mock_runner.run_single.assert_called_once_with("000001")
            mock_runner.run_multi.assert_not_called()

    def test_companies_wins_over_config_test_cases(self, tmp_path):
        """--companies should take priority over config test_cases."""
        companies_file = tmp_path / "companies.txt"
        companies_file.write_text("300470 中密控股\n", encoding="utf-8")

        mock_config = self._mock_config()
        mock_config["test_cases"] = [{"stock_code": "999999", "suffix": "research"}]

        with (
            patch("main.load_config", return_value=mock_config),
            patch("main.setup_logger"),
            patch("main.UnifiedRunner") as MockRunner,
        ):
            mock_runner = MagicMock()
            MockRunner.return_value = mock_runner

            with patch.object(sys, "argv", ["main.py", "--companies", str(companies_file)]):
                from main import main
                main()

            mock_runner.run_multi.assert_called_once()
            mock_runner.run_test_cases.assert_not_called()

    def test_missing_companies_file_exits_with_error(self, tmp_path):
        """--companies with nonexistent file should exit with error."""
        missing_file = tmp_path / "nonexistent.txt"

        mock_config = self._mock_config()

        with (
            patch("main.load_config", return_value=mock_config),
            patch("main.setup_logger"),
        ):
            with patch.object(sys, "argv", ["main.py", "--companies", str(missing_file)]):
                from main import main
                with pytest.raises(ConfigError, match="Companies file not found"):
                    main()
