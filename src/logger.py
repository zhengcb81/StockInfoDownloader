"""Own the downloader log sinks, rotation and local credential filtering."""

from contextlib import contextmanager
from copy import copy
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path, PureWindowsPath
import re
import sys
from typing import Any, Mapping

from .feedback_files import native_path

_DEFAULT_MAX_BYTES = 10 * 1024 * 1024
_DEFAULT_BACKUP_COUNT = 5
_QUOTED = r"""(?:"(?:\\[^\r\n]|[^"\\\r\n])*"|'(?:\\[^\r\n]|[^'\\\r\n])*')"""
_VALUE = r'''[^\s,;&"'<>]+'''
_TOKEN = rf"(?:{_QUOTED}|{_VALUE})"
_CREDENTIAL = re.compile(
    r"(?i)((?<![a-z0-9_-])(?:[a-z0-9_-]{1,64}[-_])?"
    r"(?:authorization|api[-_]?key|secret|token|password|credential|signature)"
    r"\b[\"']?[ \t]*[:=]\s*)"
    rf"(?:(?:bearer|basic|token)\s+)?{_TOKEN}"
)
_COOKIE = re.compile(rf"""(?i)(\b(?:set-cookie|cookie)\b["']?[ \t]*:[ \t]*)(?:{_QUOTED}|[^\r\n]+)""")
_BEARER = re.compile(rf"(?i)(\bbearer\s+){_TOKEN}")
_URL_QUERY = re.compile(r'''(?i)(https?://[^\s?#"'<>]+)\?[^\s"'<>]+''')
_URL_AUTHORITY = re.compile(r'''(?i)(https?://)[^\s/@?"'<>]+@''')


def _redact(text: str) -> str:
    text = _COOKIE.sub(r"\g<1><redacted>", text)
    text = _CREDENTIAL.sub(r"\g<1><redacted>", text)
    text = _BEARER.sub(r"\g<1><redacted>", text)
    text = _URL_AUTHORITY.sub(r"\g<1><redacted>@", text)
    return _URL_QUERY.sub(r"\g<1>?<redacted>", text)


class _SafeFormatter(logging.Formatter):
    include_exception_text = False

    def format(self, record: logging.LogRecord) -> str:
        owned = copy(record)
        # Another handler may already have cached an unredacted traceback.
        owned.exc_text = None
        return _redact(super().format(owned))

    def formatException(self, exc_info: Any) -> str:
        current = exc_info[1]
        lines = ["Traceback (most recent call last):"] if self.include_exception_text else []
        seen = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            name = type(current).__name__
            lines.append(f"{name}: {current}" if self.include_exception_text else name)
            frame = current.__traceback__
            while frame is not None:
                code = frame.tb_frame.f_code
                lines.append(f"  {PureWindowsPath(code.co_filename).name}:{frame.tb_lineno} {code.co_name}")
                frame = frame.tb_next
            cause = current.__cause__
            current = cause if cause is not None or current.__suppress_context__ else current.__context__
        return "\n".join(lines)


class _HumanFormatter(_SafeFormatter):
    include_exception_text = True


class _ConsoleHandler(logging.StreamHandler):
    pass


class _QuietHandler(logging.NullHandler):
    pass


class _FileHandler(RotatingFileHandler):
    warn_on_error = False
    reported_error = False

    def handleError(self, record: logging.LogRecord) -> None:
        first_failure = not self.reported_error
        self.reported_error = True
        if self.warn_on_error and first_failure and sys.stderr is not None:
            error_type = type(sys.exc_info()[1]).__name__
            try:
                print(f"warning: SID log write unavailable ({error_type})", file=sys.stderr)
            except (OSError, ValueError):
                pass


def diagnostic_file_failed() -> bool:
    """Report an actual failure from the currently attached local file sink."""
    return any(isinstance(handler, _FileHandler) and handler.reported_error for handler in log.handlers)


def _remove_handler(logger: logging.Logger, handler: logging.Handler) -> None:
    logger.removeHandler(handler)
    handler.close()


def setup_logger(
    name: str = "stock_downloader",
    level: str = "INFO",
    log_file: str = "",
    console: bool = True,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    backup_count: int = _DEFAULT_BACKUP_COUNT,
) -> logging.Logger:
    """Reconcile the sinks we own with the current configuration."""
    logger = logging.getLogger(name)
    numeric_level = getattr(logging, str(level).upper(), logging.INFO)
    logger.setLevel(numeric_level if isinstance(numeric_level, int) else logging.INFO)
    logger.propagate = console
    log_format = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    timestamp_format = "%Y-%m-%d %H:%M:%S"
    target = native_path(Path(log_file).absolute()) if log_file else None
    console_handler = None
    file_handler = None
    quiet_handler = None
    for handler in list(logger.handlers):
        if isinstance(handler, _ConsoleHandler):
            if console and handler.stream is sys.stderr:
                console_handler = handler
            else:
                _remove_handler(logger, handler)
        elif isinstance(handler, _FileHandler):
            if (target is not None and Path(handler.baseFilename) == target
                    and handler.maxBytes == max_bytes and handler.backupCount == backup_count):
                file_handler = handler
            else:
                _remove_handler(logger, handler)
        elif isinstance(handler, _QuietHandler):
            if console:
                _remove_handler(logger, handler)
            else:
                quiet_handler = handler

    if console and console_handler is None and sys.stderr is not None:
        console_handler = _ConsoleHandler(sys.stderr)
        console_handler.setFormatter(_HumanFormatter(log_format, datefmt=timestamp_format))
        logger.addHandler(console_handler)
    if not console and quiet_handler is None:
        logger.addHandler(_QuietHandler())
    if target is not None and file_handler is None:
        target.parent.mkdir(parents=True, exist_ok=True)
        file_handler = _FileHandler(
            target, maxBytes=max_bytes, backupCount=backup_count,
            encoding="utf-8", errors="backslashreplace",
        )
        file_handler.setFormatter(_SafeFormatter(log_format, datefmt=timestamp_format))
        logger.addHandler(file_handler)
    if file_handler is not None:
        file_handler.warn_on_error = console
    return logger


def setup_config_logging(config: Mapping[str, Any], *, console: bool = True) -> logging.Logger:
    settings = config.get("logging")
    settings = settings if isinstance(settings, dict) else {}
    target = settings.get("log_file") if settings.get("log_to_file", True) else None
    return setup_logger(
        level=str(settings.get("level", "INFO")),
        log_file=str(target or ""),
        console=console,
    )


log = setup_logger()


@contextmanager
def legacy_cleanup_console():
    """Keep a legacy downloader's cleanup diagnostics before its wire result."""
    if sys.stderr is None or any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
        and handler.stream is sys.stderr
        for handler in log.handlers
    ):
        yield
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_SafeFormatter("%(message)s"))
    log.addHandler(handler)
    try:
        yield
    finally:
        _remove_handler(log, handler)


@contextmanager
def machine_logging():
    """Use local sinks only during one JSON CLI invocation."""
    previous_handlers, level, propagate = log.handlers, log.level, log.propagate
    log.handlers = [logging.NullHandler()]
    log.propagate = False
    # Embedded callers can intentionally attach a diagnostic console. Keep
    # that route on stderr without touching their original stream or copying
    # the downloader's automatic console handler into the machine command.
    if sys.stderr is not None:
        for handler in previous_handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, (logging.FileHandler, _ConsoleHandler),
            ):
                console = logging.StreamHandler(sys.stderr)
                console.setLevel(handler.level)
                console.setFormatter(_SafeFormatter("%(message)s"))
                log.addHandler(console)
    try:
        yield
    finally:
        for handler in list(log.handlers):
            _remove_handler(log, handler)
        log.handlers = previous_handlers
        log.setLevel(level)
        log.propagate = propagate
