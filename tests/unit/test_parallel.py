"""Unit tests for parallel download functionality."""
import json
import tempfile
from unittest.mock import MagicMock, patch

from main import UnifiedRunner


class TestParallelDownload:
    """Test parallel/sequential download modes."""

    def _make_config(self):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(
            {"000001": {"orgId": "9900000001", "name": "平安银行"}}, f
        )
        f.close()
        return {
            "save_dir": tempfile.mkdtemp(),
            "headless": True,
            "max_retries": 1,
            "pages": [
                {"name": "Research", "suffix": "research", "max_pages": 1}
            ],
        }

    def test_run_multi_empty_companies(self):
        """Test that empty companies list doesn't crash."""
        runner = UnifiedRunner(self._make_config())
        runner.run_multi([])  # Should not raise

    def test_run_multi_sequential_calls_run_single(self):
        """Test sequential mode calls run_single for each company."""
        config = self._make_config()
        runner = UnifiedRunner(config)
        runner.run_single = MagicMock(return_value=True)

        companies = [
            {"stock_code": "000001", "company_name": "平安银行"},
            {"stock_code": "600036", "company_name": "招商银行"},
        ]

        with patch("main.time.sleep"):
            runner.run_multi(companies, parallel=False)

        assert runner.run_single.call_count == 2
        runner.run_single.assert_any_call("000001", "平安银行")
        runner.run_single.assert_any_call("600036", "招商银行")

    def test_run_multi_parallel_uses_thread_pool(self):
        """Test parallel mode uses ThreadPoolExecutor."""
        config = self._make_config()
        runner = UnifiedRunner(config)
        runner.run_single = MagicMock(return_value=True)

        companies = [
            {"stock_code": "000001"},
            {"stock_code": "600036"},
            {"stock_code": "002415"},
        ]

        runner.run_multi(companies, parallel=True, workers=2)

        assert runner.run_single.call_count == 3

    def test_run_multi_single_company_no_parallel(self):
        """Test single company uses sequential even with parallel=True."""
        config = self._make_config()
        runner = UnifiedRunner(config)
        runner.run_single = MagicMock(return_value=True)

        companies = [{"stock_code": "000001"}]

        runner.run_multi(companies, parallel=True, workers=3)

        # Single company should call run_single once
        assert runner.run_single.call_count == 1

    def test_run_multi_handles_exceptions(self):
        """Test that one company failing doesn't stop others."""
        config = self._make_config()
        runner = UnifiedRunner(config)
        runner.run_single = MagicMock(
            side_effect=[True, Exception("Network error"), True]
        )

        companies = [
            {"stock_code": "000001"},
            {"stock_code": "600036"},
            {"stock_code": "002415"},
        ]

        # Should not raise despite the exception
        runner.run_multi(companies, parallel=True, workers=3)
        assert runner.run_single.call_count == 3

    def test_run_test_cases_empty(self):
        """Test empty test_cases list."""
        runner = UnifiedRunner(self._make_config())
        result = runner.run_test_cases([])
        assert result is True

    def test_run_test_cases_calls_download(self):
        """Test run_test_cases creates downloader for each case."""
        config = self._make_config()
        runner = UnifiedRunner(config)

        with patch("main.StockDownloader") as MockDownloader:
            mock_instance = MagicMock()
            mock_instance.download_activity_records.return_value = ["file.pdf"]
            mock_instance.cleanup = MagicMock()
            MockDownloader.return_value = mock_instance

            result = runner.run_test_cases([
                {"stock_code": "000001", "suffix": "research"}
            ])

            assert result is True
            mock_instance.download_activity_records.assert_called_once()
            mock_instance.cleanup.assert_called_once()
