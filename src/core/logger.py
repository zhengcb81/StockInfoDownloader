"""
Unified Logging Management Module
Provides structured logging configuration and management, supports Chinese encoding and JSON context
"""

import json
import logging
import logging.handlers
from pathlib import Path
from typing import Any, Dict, Optional


class SafeStreamHandler(logging.StreamHandler):
    """Safe stream handler that handles encoding issues robustly"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            # Standardize on UTF-8 for internal consistency, but adapt to stream if needed
            stream = self.stream
            if hasattr(stream, "encoding") and stream.encoding:
                try:
                    # Attempt to encode/decode to ensure compatibility with the current terminal
                    msg.encode(stream.encoding, errors="replace").decode(
                        stream.encoding
                    )
                except Exception:
                    # Fallback to UTF-8 if current encoding is broken
                    pass

            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


class StructuredLogger:
    """Structured logger with Chinese encoding support and JSON context"""

    def __init__(
        self, name: str, log_file: Optional[str] = None, level: int = logging.INFO
    ):
        """
        Initialize structured logger

        Args:
            name: Logger name
            log_file: Log file path
            level: Log level
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.name = name

        # Avoid adding duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers(log_file)

    def _setup_handlers(self, log_file: Optional[str]) -> None:
        """Set up log handlers"""
        # Set log format
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console handler - handles Chinese encoding issues
        console_handler = SafeStreamHandler()
        console_handler.setLevel(self.logger.level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler
        if log_file:
            log_path = Path(log_file)
            # Ensure log directory exists
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(self.logger.level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

            # Force create file and write a test log to ensure file exists
            original_level = self.logger.level
            self.logger.setLevel(logging.INFO)
            self.info("Logger initialized")
            self.logger.handlers[-1].flush()  # Force flush
            self.logger.setLevel(original_level)

    def _format_message(self, message: str, **kwargs: Any) -> str:
        """Format message with context information"""
        if kwargs:
            context = json.dumps(kwargs, ensure_ascii=False)
            return f"{message} | Context: {context}"
        return message

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message"""
        formatted_message = self._format_message(message, **kwargs)
        self.logger.debug(formatted_message)
        self._flush_handlers()

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message"""
        formatted_message = self._format_message(message, **kwargs)
        self.logger.info(formatted_message)
        self._flush_handlers()

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message"""
        formatted_message = self._format_message(message, **kwargs)
        self.logger.warning(formatted_message)
        self._flush_handlers()

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message"""
        formatted_message = self._format_message(message, **kwargs)
        self.logger.error(formatted_message)
        self._flush_handlers()

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message"""
        formatted_message = self._format_message(message, **kwargs)
        self.logger.critical(formatted_message)
        self._flush_handlers()

    def _flush_handlers(self) -> None:
        """Force flush all handlers with defensive checks for closed streams"""
        for handler in self.logger.handlers:
            try:
                # Check if stream exists and is not closed
                if hasattr(handler, "stream") and handler.stream:
                    if hasattr(handler.stream, "closed") and handler.stream.closed:
                        continue
                    handler.flush()
            except (ValueError, RuntimeError):
                # Ignore errors from closed files or invalid streams
                self.logger.debug(
                    "Failed to flush handler stream (stream may be closed)"
                )


class LoggerManager:
    """Unified logger manager, singleton pattern"""

    _instance = None
    _loggers: Dict[str, "StructuredLogger"] = {}

    def __new__(cls) -> "LoggerManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._log_dir = Path("logs")
            self._log_dir.mkdir(exist_ok=True)

    def get_logger(
        self,
        name: str,
        log_file: Optional[str] = None,
        level: int = logging.INFO,
        structured: bool = True,
    ) -> StructuredLogger:
        """
        Get structured logger

        Args:
            name: Logger name
            log_file: Log file path, if None uses name.log
            level: Log level
            structured: Whether to use structured logger

        Returns:
            StructuredLogger: Structured logger instance
        """
        if name in self._loggers:
            return self._loggers[name]

        # Set log file path
        if log_file is None:
            log_file = str(self._log_dir / f"{name}.log")

        # Create structured logger
        logger = StructuredLogger(name, log_file, level)

        self._loggers[name] = logger
        return logger

    def configure_logging(self, config: Dict[str, Any]) -> None:
        """
        Configure logging system according to config

        Args:
            config: Logging configuration dictionary
        """
        log_level = config.get("level", "INFO")
        log_format = config.get(
            "format",
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        )
        log_dir = Path(config.get("log_dir", "logs"))
        log_dir.mkdir(exist_ok=True)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))

        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Console handler - handles Chinese encoding issues
        console_handler = SafeStreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_formatter = logging.Formatter(log_format)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=config.get("max_bytes", 10 * 1024 * 1024),
            backupCount=config.get("backup_count", 5),
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    def set_log_level(self, name: str, level: int) -> None:
        """
        Set logger level

        Args:
            name: Logger name
            level: Log level
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)

    def get_log_files(self) -> Dict[str, str]:
        """Get all log file paths"""
        log_files = {}
        for log_file in self._log_dir.glob("*.log*"):
            log_files[log_file.stem] = str(log_file)
        return log_files

    def cleanup_logs(self, days: int = 30) -> int:
        """
        Clean up old log files

        Args:
            days: Number of days to retain

        Returns:
            int: Number of files cleaned
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0

        for log_file in self._log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                try:
                    log_file.unlink()
                    cleaned_count += 1
                except Exception:
                    pass

        return cleaned_count


# Logger alias for backward compatibility
Logger = StructuredLogger


# Global logger manager instance
logger_manager = LoggerManager()


def get_logger(
    name: str, log_file: Optional[str] = None, level: int = logging.INFO
) -> StructuredLogger:
    """
    Convenience function to get structured logger

    Args:
        name: Logger name
        log_file: Log file path
        level: Log level

    Returns:
        StructuredLogger: Structured logger instance
    """
    return logger_manager.get_logger(name, log_file, level)


def setup_global_logging(log_dir: str, level: int = logging.INFO) -> None:
    """
    Set up global logging configuration

    Args:
        log_dir: Log directory path
        level: Log level
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = SafeStreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler
    app_log_file = log_path / "application.log"
    file_handler = logging.handlers.RotatingFileHandler(
        app_log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",  # 10MB
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
