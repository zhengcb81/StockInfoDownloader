"""Minimal logging configuration with rotating file support."""
import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path

_DEFAULT_MAX_BYTES = 10 * 1024 * 1024
_DEFAULT_BACKUP_COUNT = 5


def setup_logger(
    name: str = "stock_downloader",
    level: str = "INFO",
    log_file: str = "",
    console: bool = True,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    backup_count: int = _DEFAULT_BACKUP_COUNT,
) -> logging.Logger:
    """Configure (or reconfigure) and return a logger instance."""
    logger = logging.getLogger(name)
    numeric_level = getattr(logging, str(level).upper(), logging.INFO)
    logger.setLevel(numeric_level)
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if console and not any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in logger.handlers
    ):
        ch = logging.StreamHandler(sys.stderr)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    if log_file:
        target = Path(log_file).resolve()
        has_target_file = any(
            isinstance(h, logging.FileHandler)
            and Path(getattr(h, "baseFilename", "")).resolve() == target
            for h in logger.handlers
        )
        if not has_target_file:
            target.parent.mkdir(parents=True, exist_ok=True)
            fh = RotatingFileHandler(
                str(target),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            fh.setFormatter(fmt)
            logger.addHandler(fh)

    return logger


# Default logger
log = setup_logger()
