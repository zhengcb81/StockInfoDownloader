"""
Structured Error Logging Module
Provides unified error logging, analysis, and monitoring functionality
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .exceptions import (
    ErrorCode,
    ErrorSeverity,
    RecoveryStrategy,
    StockInfoError,
    error_handler,
)
from .logger import get_logger

logger = get_logger(__name__)


# Error log level enum
class ErrorLogLevel(Enum):
    """Error log level"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ErrorLogEntry:
    """Error log entry"""

    timestamp: datetime
    error_code: ErrorCode
    severity: ErrorSeverity
    message: str
    module: str
    function: str
    line_number: int
    file_path: str
    recovery_strategy: RecoveryStrategy
    recovery_attempted: bool
    recovery_successful: bool
    context: Dict[str, Any]
    stack_trace: str
    original_exception: Optional[str]
    user_action: Optional[str]
    system_state: Optional[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["error_code"] = self.error_code.value
        data["severity"] = self.severity.value
        data["recovery_strategy"] = self.recovery_strategy.value
        return data

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class ErrorLogger:
    """Structured error logger"""

    def __init__(
        self,
        log_dir: str = "logs/errors",
        max_file_size: int = 50 * 1024 * 1024,  # 50MB
        max_backup_count: int = 10,
        enable_console: bool = True,
        enable_file: bool = True,
        enable_json: bool = True,
    ):
        """
        Initialize error logger

        Args:
            log_dir: Log directory
            max_file_size: Maximum file size
            max_backup_count: Maximum number of backup files
            enable_console: Whether to enable console output
            enable_file: Whether to enable file output
            enable_json: Whether to enable JSON format output
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.max_file_size = max_file_size
        self.max_backup_count = max_backup_count
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.enable_json = enable_json

        # Log file paths
        self.text_log_path = self.log_dir / "errors.log"
        self.json_log_path = self.log_dir / "errors.json"

        # Error statistics
        self.error_counts: Dict[str, int] = {}
        self.recovery_stats: Dict[str, Dict[str, int]] = {}

        # Error pattern recognition
        self.error_patterns: Dict[str, List[ErrorLogEntry]] = {}

        # Initialize
        self._initialize_logger()

    def _initialize_logger(self) -> None:
        """Initialize logger"""
        # Create base log files
        if self.enable_file and not self.text_log_path.exists():
            self.text_log_path.touch()
            self._write_log_header(self.text_log_path)

        if self.enable_json and not self.json_log_path.exists():
            self.json_log_path.touch()
            self._write_json_header()

    def _write_log_header(self, file_path: Path) -> None:
        """Write log file header"""
        header = f"""# StockInfoDownloader Error Log
# Created: {datetime.now().isoformat()}
# Format: [timestamp] [error_code] [severity] module:function(line) message
#
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(header)

    def _write_json_header(self) -> None:
        """Write JSON log file header"""
        header_data = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "description": "StockInfoDownloader structured error log",
            "entries": [],
        }
        with open(self.json_log_path, "w", encoding="utf-8") as f:
            json.dump(header_data, f, ensure_ascii=False, indent=2)

    def log_error(
        self, error: StockInfoError, additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an error

        Args:
            error: Error object
            additional_context: Additional context information
        """
        try:
            # Create error log entry
            log_entry = self._create_log_entry(error, additional_context)

            # Update statistics
            self._update_statistics(log_entry)

            # Log to different destinations
            if self.enable_console:
                self._log_to_console(log_entry)

            if self.enable_file:
                self._log_to_text_file(log_entry)

            if self.enable_json:
                self._log_to_json_file(log_entry)

            # Analyze error patterns
            self._analyze_error_pattern(log_entry)

        except Exception as e:
            logger.error(f"Failed to log error: {e}")

    def _create_log_entry(
        self, error: StockInfoError, additional_context: Optional[Dict[str, Any]] = None
    ) -> ErrorLogEntry:
        """Create error log entry"""
        context = error.context.copy()
        if additional_context:
            context.update(additional_context)

        return ErrorLogEntry(
            timestamp=error.timestamp,
            error_code=error.error_code,
            severity=error.severity,
            message=error.message,
            module=error.caller_info.get("module", "unknown"),
            function=error.caller_info.get("function", "unknown"),
            line_number=error.caller_info.get("line_number", 0),
            file_path=error.caller_info.get("file_path", "unknown"),
            recovery_strategy=error.recovery_strategy,
            recovery_attempted=error.error_context.recovery_attempted,
            recovery_successful=error.error_context.recovery_successful,
            context=context,
            stack_trace=error.stack_trace,
            original_exception=(
                str(error.original_exception) if error.original_exception else None
            ),
            user_action=error.context.get("user_action"),
            system_state=error.context.get("system_state"),
        )

    def _update_statistics(self, log_entry: ErrorLogEntry) -> None:
        """Update error statistics"""
        error_key = log_entry.error_code.value

        # Update error count
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

        # Update recovery statistics
        if error_key not in self.recovery_stats:
            self.recovery_stats[error_key] = {"attempted": 0, "successful": 0}

        if log_entry.recovery_attempted:
            self.recovery_stats[error_key]["attempted"] += 1
            if log_entry.recovery_successful:
                self.recovery_stats[error_key]["successful"] += 1

    def _log_to_console(self, log_entry: ErrorLogEntry) -> None:
        """Log to console"""
        timestamp = log_entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        recovery_status = "✓" if log_entry.recovery_successful else "✗"

        console_msg = (
            f"[{timestamp}] [{log_entry.error_code.value}] "
            f"[{log_entry.severity.value}] "
            f"{log_entry.module}:{log_entry.function}({log_entry.line_number}) "
            f"{log_entry.message} {recovery_status}"
        )

        # Select output method based on severity
        if log_entry.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
            logger.error(console_msg)
        elif log_entry.severity == ErrorSeverity.ERROR:
            logger.error(console_msg)
        elif log_entry.severity == ErrorSeverity.WARNING:
            logger.warning(console_msg)
        else:
            logger.info(console_msg)

    def _log_to_text_file(self, log_entry: ErrorLogEntry) -> None:
        """Log to text file"""
        timestamp = log_entry.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        recovery_status = "SUCCESS" if log_entry.recovery_successful else "FAILED"

        log_line = (
            f"[{timestamp}] [{log_entry.error_code.value}] "
            f"[{log_entry.severity.value}] "
            f"{log_entry.module}:{log_entry.function}({log_entry.line_number}) "
            f"{log_entry.message} | Recovery: {recovery_status}"
        )

        # Check file size and rotate if needed
        self._rotate_log_file(self.text_log_path)

        with open(self.text_log_path, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")

            # If there is a stack trace, write it to file
            if log_entry.stack_trace:
                f.write("Stack Trace:\n")
                f.write(log_entry.stack_trace + "\n")
                f.write("-" * 80 + "\n")

    def _log_to_json_file(self, log_entry: ErrorLogEntry) -> None:
        """Log to JSON file"""
        # Check file size and rotate if needed
        self._rotate_log_file(self.json_log_path)

        # Read existing data
        try:
            with open(self.json_log_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = {"entries": []}

        # Add new entry
        data["entries"].append(log_entry.to_dict())

        # Write back to file
        with open(self.json_log_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _rotate_log_file(self, file_path: Path) -> None:
        """Rotate log file"""
        if not file_path.exists():
            return

        try:
            file_size = file_path.stat().st_size
            if file_size >= self.max_file_size:
                # Create backup file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = file_path.with_name(
                    f"{file_path.stem}_{timestamp}{file_path.suffix}"
                )

                # Move current file to backup
                file_path.rename(backup_path)

                # Create new file
                if file_path.suffix == ".json":
                    self._write_json_header()
                else:
                    self._write_log_header(file_path)

                # Clean up old backup files
                self._cleanup_old_backups(file_path)

        except Exception as e:
            logger.error(f"Failed to rotate log file: {e}")

    def _cleanup_old_backups(self, file_path: Path) -> None:
        """Clean up old backup files"""
        try:
            pattern = f"{file_path.stem}_*{file_path.suffix}"
            backup_files = list(file_path.parent.glob(pattern))

            # Sort by modification time
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Delete files beyond retention count
            for backup_file in backup_files[self.max_backup_count :]:
                backup_file.unlink()

        except Exception as e:
            logger.error(f"Failed to clean up backup files: {e}")

    def _analyze_error_pattern(self, log_entry: ErrorLogEntry) -> None:
        """Analyze error patterns"""
        error_key = f"{log_entry.module}:{log_entry.function}"

        if error_key not in self.error_patterns:
            self.error_patterns[error_key] = []

        # Keep last 100 error records
        self.error_patterns[error_key].append(log_entry)
        if len(self.error_patterns[error_key]) > 100:
            self.error_patterns[error_key] = self.error_patterns[error_key][-100:]

    def get_error_summary(
        self, hours: int = 24, module: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get error summary

        Args:
            hours: Statistics time range in hours
            module: Specify module

        Returns:
            Error summary information
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # Read data from log file
        recent_errors = self._load_recent_errors(cutoff_time, module)

        if not recent_errors:
            return {"total_errors": 0, "time_range": f"Last {hours} hours"}

        # Statistics
        total_errors = len(recent_errors)
        error_codes: Dict[str, int] = {}
        severities: Dict[str, int] = {}
        modules: Dict[str, int] = {}
        recovery_rate: float = 0.0

        for entry in recent_errors:
            # Error code statistics
            code = entry["error_code"]
            error_codes[code] = error_codes.get(code, 0) + 1

            # Severity statistics
            severity = entry["severity"]
            severities[severity] = severities.get(severity, 0) + 1

            # Module statistics
            mod = entry["module"]
            modules[mod] = modules.get(mod, 0) + 1

            # Recovery rate statistics
            if entry["recovery_attempted"]:
                recovery_rate += 1 if entry["recovery_successful"] else 0

        total_attempted = sum(1 for e in recent_errors if e["recovery_attempted"])
        recovery_rate = recovery_rate / total_attempted if total_attempted > 0 else 0

        return {
            "total_errors": total_errors,
            "time_range": f"Last {hours} hours",
            "error_codes": error_codes,
            "severities": severities,
            "modules": modules,
            "recovery_rate": recovery_rate,
            "most_common_error": (
                max(error_codes.items(), key=lambda x: x[1])[0] if error_codes else None
            ),
            "error_frequency": total_errors / hours if hours > 0 else 0,
        }

    def _load_recent_errors(
        self, cutoff_time: datetime, module: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Load recent error records"""
        try:
            if not self.json_log_path.exists():
                return []

            with open(self.json_log_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            entries = data.get("entries", [])
            recent_errors = []

            for entry in entries:
                entry_time = datetime.fromisoformat(entry["timestamp"])
                if entry_time >= cutoff_time:
                    if module is None or entry["module"] == module:
                        recent_errors.append(entry)

            return recent_errors

        except Exception as e:
            logger.error(f"Failed to load error records: {e}")
            return []

    def get_error_trends(self, days: int = 7) -> Dict[str, Any]:
        """
        Get error trends

        Args:
            days: Number of days to analyze

        Returns:
            Error trend data
        """
        trends = {}
        current_date = datetime.now().date()

        for i in range(days):
            date = current_date - timedelta(days=i)
            date_str = date.isoformat()

            # Calculate error count for this date
            day_start = datetime.combine(date, datetime.min.time())
            day_end = datetime.combine(date, datetime.max.time())

            day_errors = self._load_recent_errors(day_start)
            day_errors = [
                e
                for e in day_errors
                if day_start <= datetime.fromisoformat(e["timestamp"]) <= day_end
            ]

            trends[date_str] = {
                "total_errors": len(day_errors),
                "critical_errors": len(
                    [e for e in day_errors if e["severity"] in ["CRITICAL", "FATAL"]]
                ),
                "recovery_rate": self._calculate_recovery_rate(day_errors),
            }

        return trends

    def _calculate_recovery_rate(self, errors: List[Dict[str, Any]]) -> float:
        """Calculate recovery rate"""
        attempted = [e for e in errors if e["recovery_attempted"]]
        if not attempted:
            return 0.0

        successful = len([e for e in attempted if e["recovery_successful"]])
        return successful / len(attempted)

    def get_error_patterns(self, min_occurrences: int = 3) -> Dict[str, Any]:
        """
        Get error patterns

        Args:
            min_occurrences: Minimum number of occurrences

        Returns:
            Error pattern analysis results
        """
        patterns = {}

        for location, entries in self.error_patterns.items():
            if len(entries) >= min_occurrences:
                # Analyze pattern characteristics
                error_codes: Dict[str, int] = {}
                severities: Dict[str, int] = {}

                for entry in entries:
                    code = entry.error_code.value
                    severity = entry.severity.value

                    error_codes[code] = error_codes.get(code, 0) + 1
                    severities[severity] = severities.get(severity, 0) + 1

                patterns[location] = {
                    "total_occurrences": len(entries),
                    "most_common_error": max(error_codes.items(), key=lambda x: x[1])[
                        0
                    ],
                    "error_distribution": error_codes,
                    "severity_distribution": severities,
                    "recovery_rate": sum(1 for e in entries if e.recovery_successful)
                    / len(entries),
                    "first_occurrence": min(e.timestamp for e in entries).isoformat(),
                    "last_occurrence": max(e.timestamp for e in entries).isoformat(),
                }

        return patterns

    def cleanup_old_logs(self, days: int = 30) -> None:
        """
        Clean up old log files

        Args:
            days: Number of days to retain
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)

            # Clean up log files
            for log_file in self.log_dir.glob("*"):
                if (
                    log_file.is_file()
                    and log_file.stat().st_mtime < cutoff_time.timestamp()
                ):
                    log_file.unlink()
                    logger.info(f"Cleaned up old log file: {log_file.name}")

        except Exception as e:
            logger.error(f"Failed to clean up old log files: {e}")

    def export_error_report(
        self, output_path: str, hours: int = 24, format_type: str = "json"
    ) -> bool:
        """
        Export error report

        Args:
            output_path: Output path
            hours: Statistics time range
            format_type: Output format ('json' or 'html')

        Returns:
            Whether successful
        """
        try:
            summary = self.get_error_summary(hours=hours)
            trends = self.get_error_trends(days=min(7, hours // 24 + 1))
            patterns = self.get_error_patterns()

            report_data = {
                "generated_at": datetime.now().isoformat(),
                "summary": summary,
                "trends": trends,
                "patterns": patterns,
                "recommendations": self._generate_recommendations(summary, patterns),
            }

            if format_type.lower() == "json":
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(report_data, f, ensure_ascii=False, indent=2)
            elif format_type.lower() == "html":
                self._generate_html_report(report_data, output_path)

            logger.info(f"Error report exported to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export error report: {e}")
            return False

    def _generate_recommendations(
        self, summary: Dict[str, Any], patterns: Dict[str, Any]
    ) -> List[str]:
        """Generate error handling recommendations"""
        recommendations = []

        # Recommendations based on error frequency
        if summary.get("error_frequency", 0) > 10:
            recommendations.append("High error frequency, suggest checking system stability and error handling mechanism")

        # Recommendations based on recovery rate
        recovery_rate = summary.get("recovery_rate", 0)
        if recovery_rate < 0.5:
            recommendations.append("Low error recovery rate, suggest optimizing error recovery strategy")

        # Recommendations based on error patterns
        for location, pattern in patterns.items():
            if pattern["recovery_rate"] < 0.3:
                recommendations.append(f"{location} has low error recovery rate and needs attention")

        return recommendations

    def _generate_html_report(self, report_data: Dict[str, Any], output_path: str) -> None:
        """Generate HTML format report"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>StockInfoDownloader Error Report</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .error-critical {{ color: #d32f2f; }}
                .error-warning {{ color: #f57c00; }}
                .error-info {{ color: #1976d2; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>StockInfoDownloader Error Report</h1>
                <p>Generated at: {report_data['generated_at']}</p>
            </div>

            <div class="section">
                <h2>Error Summary</h2>
                <p>Total errors: {report_data['summary']['total_errors']}</p>
                <p>Error frequency: {report_data['summary']['error_frequency']:.2f} errors/hour</p>
                <p>Recovery rate: {report_data['summary']['recovery_rate']:.2%}</p>
            </div>

            <div class="section">
                <h2>Recommendations</h2>
                <ul>
                    {''.join(f'<li>{rec}</li>' for rec in report_data['recommendations'])}
                </ul>
            </div>
        </body>
        </html>
        """

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)


# Global error logger instance
error_logger = ErrorLogger()


# Convenience functions
def log_error(
    error: StockInfoError, additional_context: Optional[Dict[str, Any]] = None
) -> None:
    """Convenience function for error logging"""
    error_logger.log_error(error, additional_context)


def get_error_summary(hours: int = 24, module: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function for error summary"""
    return error_logger.get_error_summary(hours, module)


def get_error_trends(days: int = 7) -> Dict[str, Any]:
    """Convenience function for error trends"""
    return error_logger.get_error_trends(days)


def export_error_report(
    output_path: str, hours: int = 24, format_type: str = "json"
) -> bool:
    """Convenience function for error report export"""
    return error_logger.export_error_report(output_path, hours, format_type)


# Integrate with global error handler
def _integrate_with_error_handler() -> None:
    """Integrate with global error handler"""
    original_log_error = error_handler._log_error

    def enhanced_log_error(error: StockInfoError) -> None:
        # Call original logger
        original_log_error(error)

        # Log to structured error log
        log_error(error)

    error_handler._log_error = enhanced_log_error  # type: ignore[method-assign]


# Auto integrate
_integrate_with_error_handler()
