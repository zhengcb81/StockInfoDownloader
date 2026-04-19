"""Unit tests for FailedDownloadLogger."""
import json
import tempfile
from pathlib import Path

from src.downloader import FailedDownloadLogger


class TestFailedDownloadLogger:
    def test_record_and_get(self, tmp_path):
        log_file = str(tmp_path / "failed.json")
        logger = FailedDownloadLogger(log_file)
        logger.record("000001", "平安银行", "测试报告", "http://example.com", "timeout")
        logger.flush()
        # After record() + flush(), data is saved to file
        with open(log_file, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["stock_code"] == "000001"
        assert data[0]["error"] == "timeout"

    def test_persist_to_file(self, tmp_path):
        log_file = str(tmp_path / "failed.json")
        logger = FailedDownloadLogger(log_file)
        logger.record("300470", "中密控股", "季报", "http://x.com", "network error")
        logger.flush()

        with open(log_file, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["stock_code"] == "300470"

    def test_append_to_existing(self, tmp_path):
        log_file = str(tmp_path / "failed.json")
        # First session
        logger1 = FailedDownloadLogger(log_file)
        logger1.record("000001", "平安银行", "报告1", "http://a.com", "err1")
        logger1.flush()
        # Second session — loads existing records, appends new one
        logger2 = FailedDownloadLogger(log_file)
        logger2.record("600036", "招商银行", "报告2", "http://b.com", "err2")
        logger2.flush()

        with open(log_file, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 2

    def test_reset_clears_pending(self, tmp_path):
        log_file = str(tmp_path / "failed.json")
        logger = FailedDownloadLogger(log_file)
        logger.record("000001", "银行", "报告", "http://x.com", "err")
        logger.reset()  # Clear without writing
        logger.flush()  # flush should write nothing since reset cleared pending
        assert logger.get_failed() == []
        assert not Path(log_file).exists()

    def test_get_failed_returns_pending(self, tmp_path):
        log_file = str(tmp_path / "failed.json")
        logger = FailedDownloadLogger(log_file)
        logger.record("000001", "银行", "报告", "http://x.com", "err1")
        logger.record("600036", "招商", "公告", "http://y.com", "err2")
        pending = logger.get_failed()
        assert len(pending) == 2
        # get_failed does NOT clear pending
        assert len(logger.get_failed()) == 2

    def test_flush_empty_does_not_create_file(self, tmp_path):
        log_file = str(tmp_path / "empty.json")
        logger = FailedDownloadLogger(log_file)
        logger.flush()
        assert not Path(log_file).exists()