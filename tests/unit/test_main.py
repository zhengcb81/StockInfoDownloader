"""Unit tests for main() CLI integration."""
import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from src.exceptions import ConfigError


@pytest.fixture(autouse=True)
def _isolated_feedback_root(tmp_path, monkeypatch):
    """Keep ordinary-run feedback inside the test sandbox.

    main() now publishes observations and run receipts by default; without a
    mapped state root those would land in the real user state directory.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RESEARCH_FEEDBACK_OUT", raising=False)
    monkeypatch.delenv("RESEARCH_FEEDBACK_RUN_ID", raising=False)
    monkeypatch.delenv("RESEARCH_FEEDBACK_ATTEMPT_ID", raising=False)
    monkeypatch.delenv("RESEARCH_FEEDBACK_DIR", raising=False)
    monkeypatch.setenv("RESEARCH_FEEDBACK_STATE_ROOT", str(tmp_path / "state"))


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

    def test_missing_companies_file_refuses_the_launch_on_record(self, tmp_path):
        """--companies with a nonexistent file refuses the launch (exit 1).

        F4-SID-START-INPUT: the refusal is recorded through the feedback
        publisher with its stage and native cause chain, and no task runs.
        """
        missing_file = tmp_path / "nonexistent.txt"

        mock_config = self._mock_config()

        with (
            patch("main.load_config", return_value=mock_config),
            patch("main.setup_logger"),
            patch("main.UnifiedRunner") as MockRunner,
        ):
            with patch.object(sys, "argv", ["main.py", "--companies", str(missing_file)]):
                from main import main
                with pytest.raises(SystemExit) as stop:
                    main()

            assert stop.value.code == 1
            MockRunner.return_value.run_multi.assert_not_called()
            MockRunner.return_value.run_single.assert_not_called()

        def rows(pattern):
            return [
                json.loads(line)
                for path in sorted((tmp_path / "state" / "observations").glob(pattern))
                if not path.name.endswith(".details.jsonl") or "details" in pattern
                for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
            ]

        settlement = [r for r in rows("feedback-*.jsonl") if r["check_id"] == "ordinary-run-settlement"]
        assert len(settlement) == 1
        assert settlement[0]["actual"] == "not_started"
        assert settlement[0]["disposition"] == "expected"
        refused = [d for d in rows("feedback-*.details.jsonl") if d.get("stage") == "companies"]
        assert len(refused) == 1
        assert refused[0]["cause_chain"] == ["ConfigError"]
        assert refused[0]["sent"] == "not_sent"
        assert refused[0]["attempted"] == 0


class TestPlanWork:
    """The one input-source decision point, in the documented priority."""

    def _companies_file(self, tmp_path, text="300470 中密控股\n"):
        path = tmp_path / "companies.txt"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_priority_cli_stock_over_list_over_test_cases_over_companies(self, tmp_path):
        from main import plan_work

        config = {
            "test_cases": [{"stock_code": "999999"}],
            "companies": [{"stock_code": "888888"}],
            "stock_code": "777777",
        }
        assert plan_work("000001", self._companies_file(tmp_path), config).source == "cli-stock"
        assert plan_work(None, self._companies_file(tmp_path), config).source == "companies-file"
        assert plan_work(None, None, config).source == "test-cases"

    def test_priority_companies_over_config_stock_code(self, tmp_path):
        from main import plan_work

        config = {"companies": [{"stock_code": "888888"}], "stock_code": "777777"}
        plan = plan_work(None, None, config)
        assert plan.source == "config-companies"
        assert plan.companies == [{"stock_code": "888888"}]
        assert plan.progress_name == "config.json"

    def test_default_empty_keys_never_shadow_real_config(self, tmp_path):
        from main import plan_work

        config = {
            "test_cases": [],  # injected by load_config
            "companies": [{"stock_code": "888888"}],
            "stock_code": "777777",
        }
        assert plan_work(None, None, config).source == "config-companies"
        config = {"test_cases": [], "companies": [], "stock_code": "777777"}
        assert plan_work(None, None, config).stock_code == "777777"

    def test_no_item_anywhere_is_an_empty_work_list_not_a_refusal(self, tmp_path):
        from main import plan_work

        plan = plan_work(None, None, {"test_cases": [], "companies": []})
        assert plan.source == "none"
        assert plan.reason

    def test_comment_only_list_is_an_empty_work_list(self, tmp_path):
        from main import plan_work

        path = self._companies_file(tmp_path, "# nothing here\n\n")
        plan = plan_work(None, path, {"companies": [{"stock_code": "888888"}]})
        assert plan.source == "none"
        assert "no entries" in plan.reason

    def test_missing_list_raises_typed_error_with_no_side_effect(self, tmp_path):
        from main import plan_work

        with pytest.raises(ConfigError, match="Companies file not found"):
            plan_work(None, str(tmp_path / "missing.txt"), {})
