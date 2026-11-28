"""Own the downloader log sinks, rotation and local credential filtering."""

import argparse
from contextlib import contextmanager
from copy import copy
import logging
import os
from pathlib import Path, PureWindowsPath
import re
import sys
from typing import Any, Mapping

from .feedback_files import exclusive_file, native_path

_DEFAULT_MAX_BYTES = 10 * 1024 * 1024
_DEFAULT_BACKUP_COUNT = 5
_QUOTED = r"""(?:"(?:\\[^\r\n]|[^"\\\r\n])*"|'(?:\\[^\r\n]|[^'\\\r\n])*')"""
_VALUE = r'''[^\s,;&"'<>]+'''
# Whitespace-leading lines remain part of a folded credential value.
# The first unindented line belongs to the surrounding diagnostic.
_FOLDED_CONTINUATIONS = r"(?:[ \t]*\r?\n[ \t]+[^\r\n]*)*"
_TOKEN = rf"(?:{_QUOTED}|{_VALUE}){_FOLDED_CONTINUATIONS}"
_CREDENTIAL = re.compile(
    r"(?i)((?<![a-z0-9_-])(?:[a-z0-9_-]{1,64}[-_])?"
    r"(?:authorization|api[-_]?key|secret|token|password|credential|signature)"
    r"\b[\"']?[ \t]*[:=]\s*)"
    rf"(?:(?:bearer|basic|token)\s+)?{_TOKEN}"
)
_COOKIE = re.compile(rf"""(?i)(\b(?:set-cookie|cookie)\b["']?[ \t]*:[ \t]*)(?:{_QUOTED}|[^\r\n]+)""")
_AUTH_SCHEME = re.compile(rf"(?i)(\b(?:bearer|basic)\s+){_TOKEN}")
_KEY_PREFIX = re.compile(r"(?i)(?<![a-z0-9_])(?:sk-|tvly-|ghp_|AIza)[a-z0-9_-]{8,}")
_URL_QUERY = re.compile(r'''(?i)(https?://[^\s?#"'<>]+)\?[^\s"'<>]+''')
_URL_AUTHORITY = re.compile(r'''(?i)(https?://)[^\s/@?"'<>]+@''')


def redact(text: str) -> str:
    """Remove credential material from diagnostic and human/wire explanations."""
    text = _COOKIE.sub(r"\g<1><redacted>", text)
    text = _CREDENTIAL.sub(r"\g<1><redacted>", text)
    text = _AUTH_SCHEME.sub(r"\g<1><redacted>", text)
    text = _KEY_PREFIX.sub("<redacted>", text)
    text = _URL_AUTHORITY.sub(r"\g<1><redacted>@", text)
    return _URL_QUERY.sub(r"\g<1>?<redacted>", text)


class _SafeFormatter(logging.Formatter):
    def __init__(self, fmt: str | None = None, datefmt: str | None = None, *, identity: str = ""):
        super().__init__(fmt, datefmt)
        self.identity = redact(identity)

    def format(self, record: logging.LogRecord) -> str:
        owned = copy(record)
        # Another handler may already have cached an unredacted traceback.
        owned.exc_text = None
        message = redact(super().format(owned))
        return f"{self.identity} {message}" if self.identity else message

    def formatException(self, exc_info: Any) -> str:
        current = exc_info[1]
        lines = []
        seen = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            name = type(current).__name__
            lines.append(name)
            frame = current.__traceback__
            while frame is not None:
                code = frame.tb_frame.f_code
                lines.append(f"  {PureWindowsPath(code.co_filename).name}:{frame.tb_lineno} {code.co_name}")
                frame = frame.tb_next
            cause = current.__cause__
            current = cause if cause is not None or current.__suppress_context__ else current.__context__
        return "\n".join(lines)


class _HumanFormatter(_SafeFormatter):
    def formatException(self, exc_info: Any) -> str:
        # The human channel carries the concise message; the file has the stack.
        return ""


class _ConsoleHandler(logging.StreamHandler):
    pass


class _QuietHandler(logging.NullHandler):
    pass


class _FileHandler(logging.FileHandler):
    """Serialize whole records, using short-lived file handles between writes."""

    warn_on_error = False
    reported_error = False

    def __init__(self, target: Path, max_bytes: int, backup_count: int):
        super().__init__(target, mode="a", encoding="utf-8", delay=True)
        self.target = target
        self.maxBytes = max_bytes
        self.backupCount = backup_count
        # Validate an unusable configured sink before replacing the active one.
        with exclusive_file(target), target.open("ab"):
            pass

    def _archive(self, pending: Path | None) -> None:
        # Move the active file first. A reader holding it cannot cause an
        # archive to be evicted before we know rollover can start.
        stem = self.target.name + ".rotating"
        if pending is None:
            pending = self.target.with_name(f"{stem}.{self.backupCount}")
            os.replace(self.target, pending)
        index = int(pending.suffix[1:])
        while index > 1:
            old = self.target.with_name(f"{self.target.name}.{index - 1}")
            if old.exists():
                os.replace(old, self.target.with_name(f"{self.target.name}.{index}"))
            # Persist which shift is next so a held archive or killed writer
            # cannot repeat earlier shifts and evict more retained files.
            next_pending = self.target.with_name(f"{stem}.{index - 1}")
            os.replace(pending, next_pending)
            pending = next_pending
            index -= 1
        os.replace(pending, self.target.with_name(f"{self.target.name}.1"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            data = (self.format(record) + "\n").encode("utf-8", "backslashreplace")
            with exclusive_file(self.target):
                try:
                    size = self.target.stat().st_size
                except FileNotFoundError:
                    size = 0
                if self.maxBytes > 0 and self.backupCount > 0:
                    self._rotate_if_needed(size, len(data))
                with self.target.open("ab") as stream:
                    stream.write(data)
        except (OSError, ValueError, TypeError):
            self.handleError(record)

    def _rotate_if_needed(self, size: int, record_bytes: int) -> None:
        prefix = self.target.name + ".rotating."
        pending = next(
            (path for path in self.target.parent.iterdir()
             if path.name.startswith(prefix) and path.name[len(prefix):].isdecimal()),
            None,
        )
        if pending is not None or (size and size + record_bytes > self.maxBytes):
            try:
                self._archive(pending)
            except PermissionError as exc:
                if os.name != "nt" or getattr(exc, "winerror", None) not in (5, 32, 33):
                    raise
                # A Windows reader can hold the active file or archive
                # without delete sharing. Preserve the current record.

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
    identity: str = "",
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
    file_handler = next(
        (handler for handler in logger.handlers
         if isinstance(handler, _FileHandler) and target == handler.target
         and handler.maxBytes == max_bytes and handler.backupCount == backup_count),
        None,
    )
    if target is not None and file_handler is None:
        target.parent.mkdir(parents=True, exist_ok=True)
        file_handler = _FileHandler(target, max_bytes, backup_count)
    quiet_handler = None
    for handler in list(logger.handlers):
        if isinstance(handler, _ConsoleHandler):
            if console and handler.stream is sys.stderr:
                console_handler = handler
            else:
                _remove_handler(logger, handler)
        elif isinstance(handler, _FileHandler) and handler is not file_handler:
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
    if file_handler is not None:
        file_handler.setFormatter(_SafeFormatter(log_format, datefmt=timestamp_format, identity=identity))
        if file_handler not in logger.handlers:
            logger.addHandler(file_handler)
        file_handler.warn_on_error = console
    return logger


def setup_config_logging(
    config: Mapping[str, Any], *, console: bool = True, identity: str = "", fallback: Path | None = None,
) -> logging.Logger:
    settings = config.get("logging")
    settings = settings if isinstance(settings, dict) else {}
    target = settings.get("log_file") if settings.get("log_to_file", True) else None
    return setup_logger(
        level=str(settings.get("level", "INFO")),
        log_file=str(target or fallback or ""),
        console=console,
        identity=identity,
    )


log = logging.getLogger("stock_downloader")


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


class DiagnosticArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        super().error(redact(message))


def configure_diagnostic_log(target: Path, *, console: bool, identity: str) -> bool:
    """Attach an owned sink while preserving the running operation on I/O failure."""
    try:
        setup_logger(log_file=str(target), console=console, identity=identity)
    except (OSError, RuntimeError, ValueError):
        log.warning("diagnostic log setup unavailable", exc_info=True)
        return False
    return True


@contextmanager
def entry_logging(
    entry: str, identity: tuple[str, str], version: str, root: Path, *,
    console: bool, notice_on_parser_failure: bool = True,
):
    run_id, attempt_id = identity
    label = f"entry={entry} run_id={run_id} attempt_id={attempt_id} code_version={version}"
    setup_logger(console=console)
    available = configure_diagnostic_log(root / "logs" / f"{entry}.log", console=console, identity=label)
    log.info("entry_started stage=arguments")
    try:
        yield available, label
    except SystemExit as exc:
        if exc.code == 2:
            log.warning("entry_refused stage=arguments exit_code=2", exc_info=True)
            if notice_on_parser_failure and (not available or diagnostic_file_failed()):
                diagnostic_notice(identity)
        elif exc.code == 0:
            log.info("entry_finished stage=arguments exit_code=0")
        raise


def diagnostic_notice(identity: tuple[str, str]) -> None:
    """Use stderr only, before any terminal machine response."""
    if sys.stderr is not None:
        try:
            message = f"SID diagnostics unavailable run_id={identity[0]} attempt_id={identity[1]}\n"
            sys.stderr.write(redact(message))
        except (OSError, ValueError):
            return
