"""S1-02 regression tests: file logging activation and pagination error escalation."""

from __future__ import annotations

import logging

import pytest

from src import logger as logger_module
from src.browser import BrowserError, PlaywrightBrowser


def test_setup_logger_activates_file_handler_after_default_import(tmp_path):
    log_path = tmp_path / "logs" / "downloader.log"
    name = "stock_downloader_s1_test"
    try:
        # Simulate default import-time console-only setup followed by config-driven file setup.
        lg = logger_module.setup_logger(name=name, level="INFO", log_file="", console=True)
        lg = logger_module.setup_logger(name=name, level="DEBUG", log_file=str(log_path), console=True)
        lg.info("s1-file-log-probe")
        for h in lg.handlers:
            h.flush()

        assert log_path.is_file(), "Rotating file log must be created even after initial console setup"
        content = log_path.read_text(encoding="utf-8")
        assert "s1-file-log-probe" in content
    finally:
        lg = logging.getLogger(name)
        for h in list(lg.handlers):
            lg.removeHandler(h)
            h.close()


def test_get_current_page_info_raises_and_logs_on_unexpected_browser_error(caplog):
    class _BrokenPage:
        def evaluate(self, script: str):
            raise RuntimeError("Target page, context or browser has been closed")

    browser = PlaywrightBrowser.__new__(PlaywrightBrowser)
    browser._page = _BrokenPage()

    with caplog.at_level(logging.ERROR, logger="stock_downloader"):
        with pytest.raises(BrowserError, match="Failed to read pagination info"):
            browser.get_current_page_info()

    assert any(
        "pagination" in rec.getMessage().lower() and rec.exc_info is not None
        for rec in caplog.records
    )
