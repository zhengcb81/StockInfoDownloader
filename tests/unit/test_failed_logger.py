"""Unit tests for FailedDownloadLogger."""
import json
import tempfile

from src.downloader import FailedDownloadLogger


class TestFailedDownloadLogger:
    def test_record_and_get(self, tmp_path):
        log_file = str(tmp_path / "failed.json")
        logger = FailedDownloadLogger(log_file)
        logger.record("000001", "平安银行", "测试报告", "http://example.com", "timeout")
        # After record(), data is saved to file
        with open(log_file) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["stock_code"] == "000001"
        assert data[0]["error"] == "timeout"

    def test_persist_to_file(self, tmp_path):
        log_file = str(tmp_path / "failed.json")
        logger = FailedDownloadLogger(log_file)
        logger.record("300470", "中密控股", "季报", "http://x.com", "network error")

        with open(log_file) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["stock_code"] == "300470"

    def test_append_to_existing(self, tmp_path):
        log_file = str(tmp_path / "failed.json")
        # First session
        logger1 = FailedDownloadLogger(log_file)
        logger1.record("000001", "平安银行", "报告1", "http://a.com", "err1")
        # Second session
        logger2 = FailedDownloadLogger(log_file)
        logger2.record("600036", "招商银行", "报告2", "http://b.com", "err2")

        with open(log_file) as f:
            data = json.load(f)
        assert len(data) == 2
