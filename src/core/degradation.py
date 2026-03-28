"""
Graceful Degradation Strategy Module
Provides graceful degradation handling for network and file system errors
"""

import shutil
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from .exceptions import (
    ErrorCode,
    ErrorSeverity,
    FileSystemError,
    NetworkError,
    RecoveryStrategy,
)
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class DegradationLevel:
    """Degradation level"""

    name: str
    priority: int  # Priority, smaller number means higher priority
    description: str
    is_available: bool = True
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    max_consecutive_failures: int = 3
    cooldown_period: timedelta = timedelta(minutes=5)


# Define degradation levels
DEGRADATION_LEVELS = {
    "full": DegradationLevel(
        name="full",
        priority=1,
        description="Full functionality",
        is_available=True,
        max_consecutive_failures=5,
        cooldown_period=timedelta(minutes=1),
    ),
    "cache_only": DegradationLevel(
        name="cache_only",
        priority=2,
        description="Cache only",
        is_available=True,
        max_consecutive_failures=3,
        cooldown_period=timedelta(minutes=2),
    ),
    "offline_mode": DegradationLevel(
        name="offline_mode",
        priority=3,
        description="Offline mode",
        is_available=True,
        max_consecutive_failures=5,
        cooldown_period=timedelta(minutes=5),
    ),
    "minimal": DegradationLevel(
        name="minimal",
        priority=4,
        description="Minimal functionality",
        is_available=True,
        max_consecutive_failures=10,
        cooldown_period=timedelta(minutes=10),
    ),
    "emergency": DegradationLevel(
        name="emergency",
        priority=5,
        description="Emergency mode",
        is_available=True,
        max_consecutive_failures=20,
        cooldown_period=timedelta(minutes=30),
    ),
}


class NetworkDegradationManager:
    """Network degradation manager"""

    def __init__(self) -> None:
        self.current_level = DEGRADATION_LEVELS["full"]
        self.connection_history: List[Dict[str, Any]] = []
        self.fallback_strategies: Dict[str, Callable] = {}
        self.circuit_breaker_open = False
        self.circuit_breaker_timeout: Optional[datetime] = None
        self.max_history_size = 100

        # Register default degradation strategies
        self._register_default_strategies()

    def _register_default_strategies(self) -> None:
        """Register default degradation strategies"""
        self.fallback_strategies = {
            "timeout_increase": self._increase_timeout,
            "cache_fallback": self._use_cache_data,
            "retry_with_backoff": self._retry_with_exponential_backoff,
            "alternative_endpoint": self._use_alternative_endpoint,
            "offline_mode": self._switch_to_offline_mode,
        }

    def check_network_health(self) -> bool:
        """
        Check network health status

        Returns:
            bool: Whether network is healthy
        """
        try:
            import requests

            # Test basic connection
            test_urls = [
                "https://www.cninfo.com.cn",
                "https://www.baidu.com",
                "https://www.google.com",  # As connectivity test
            ]

            for url in test_urls:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        self._record_success()
                        return True
                except (requests.RequestException, OSError, TimeoutError):
                    # Network or timeout error, try next URL
                    continue

            self._record_failure()
            return False

        except Exception as e:
            logger.warning(f"Network health check failed: {e}")
            self._record_failure()
            return False

    def _record_success(self) -> None:
        """Record successful connection"""
        self.connection_history.append(
            {"timestamp": datetime.now(), "success": True, "response_time": 0.0}
        )

        # Reset circuit breaker
        if self.circuit_breaker_open:
            self.circuit_breaker_open = False
            self.circuit_breaker_timeout = None
            logger.info("Circuit breaker reset")

        # Clean up history
        self._cleanup_history()

    def _record_failure(self) -> None:
        """Record connection failure"""
        self.connection_history.append(
            {
                "timestamp": datetime.now(),
                "success": False,
                "error": "Connection failed",
            }
        )

        # Check if circuit breaker needs to be opened
        self._check_circuit_breaker()

        # Adjust degradation level
        self._adjust_degradation_level()

        # Clean up history
        self._cleanup_history()

    def _check_circuit_breaker(self) -> None:
        """Check circuit breaker status"""
        recent_failures = [
            entry
            for entry in self.connection_history[-10:]
            if not entry["success"]
            and (datetime.now() - entry["timestamp"]).total_seconds() < 300
        ]

        if len(recent_failures) >= 5:
            self.circuit_breaker_open = True
            self.circuit_breaker_timeout = datetime.now() + timedelta(minutes=5)
            logger.warning("Network circuit breaker opened, will retry in 5 minutes")

    def _adjust_degradation_level(self) -> None:
        """Adjust degradation level"""
        recent_failures = [
            entry for entry in self.connection_history[-20:] if not entry["success"]
        ]

        failure_rate = len(recent_failures) / min(len(self.connection_history), 20)

        # Adjust degradation level based on failure rate
        if failure_rate >= 0.8:
            self._set_degradation_level("emergency")
        elif failure_rate >= 0.6:
            self._set_degradation_level("minimal")
        elif failure_rate >= 0.4:
            self._set_degradation_level("offline_mode")
        elif failure_rate >= 0.2:
            self._set_degradation_level("cache_only")
        else:
            self._set_degradation_level("full")

    def _set_degradation_level(self, level_name: str) -> None:
        """Set degradation level"""
        if level_name in DEGRADATION_LEVELS:
            new_level = DEGRADATION_LEVELS[level_name]
            if new_level.priority > self.current_level.priority:
                logger.info(f"Network degradation level adjusted to: {level_name}")
                self.current_level = new_level

    def _cleanup_history(self) -> None:
        """Clean up history records"""
        if len(self.connection_history) > self.max_history_size:
            self.connection_history = self.connection_history[-self.max_history_size :]

    def execute_with_fallback(
        self,
        primary_operation: Callable,
        fallback_strategies: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute operation with degradation strategies

        Args:
            primary_operation: Primary operation
            fallback_strategies: List of fallback strategies
            context: Operation context

        Returns:
            Operation result
        """
        context = context or {}

        # Check circuit breaker status
        if self.circuit_breaker_open:
            if self.circuit_breaker_timeout is not None and datetime.now() < self.circuit_breaker_timeout:
                raise NetworkError(
                    "Network circuit breaker is open, cannot execute operation temporarily",
                    error_code=ErrorCode.NETWORK_CONNECTION_ERROR,
                    severity=ErrorSeverity.WARNING,
                    recovery_strategy=RecoveryStrategy.NONE,
                    context={
                        "circuit_breaker": "open",
                        "timeout": self.circuit_breaker_timeout.isoformat(),
                    },
                )
            else:
                # Try to reset circuit breaker
                if self.check_network_health():
                    logger.info("Circuit breaker reset successful")
                else:
                    raise NetworkError(
                        "Circuit breaker reset failed, network still unavailable",
                        error_code=ErrorCode.NETWORK_CONNECTION_ERROR,
                        severity=ErrorSeverity.WARNING,
                        recovery_strategy=RecoveryStrategy.NONE,
                        context={"circuit_breaker": "reset_failed"},
                    )

        # Try primary operation
        try:
            result = primary_operation()
            self._record_success()
            return result

        except Exception as e:
            logger.warning(f"Primary operation failed: {e}")
            self._record_failure()

            # Try fallback strategies
            for strategy_name in fallback_strategies:
                if strategy_name in self.fallback_strategies:
                    try:
                        logger.info(f"Trying fallback strategy: {strategy_name}")
                        fallback_result = self.fallback_strategies[strategy_name](
                            context
                        )

                        if fallback_result is not None:
                            logger.info(f"Fallback strategy {strategy_name} executed successfully")
                            return fallback_result

                    except Exception as fallback_error:
                        logger.warning(
                            f"Fallback strategy {strategy_name} failed: {fallback_error}"
                        )
                        continue

            # All strategies failed
            raise NetworkError(
                f"All operation strategies failed, last error: {e}",
                error_code=ErrorCode.NETWORK_CONNECTION_ERROR,
                severity=ErrorSeverity.ERROR,
                recovery_strategy=RecoveryStrategy.NONE,
                context={
                    "attempted_strategies": fallback_strategies,
                    "original_error": str(e),
                },
            )

    def _increase_timeout(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Increase timeout duration"""
        base_timeout = context.get("timeout", 30)
        new_timeout = min(base_timeout * 2, 300)  # Max 5 minutes

        logger.info(f"Increasing timeout: {base_timeout}s -> {new_timeout}s")
        context["timeout"] = new_timeout
        context["strategy_used"] = "timeout_increase"

        return context

    def _use_cache_data(self, context: Dict[str, Any]) -> Optional[Any]:
        """Use cached data"""
        cache_key = context.get("cache_key")
        if not cache_key:
            return None

        # Should integrate with cache system here
        logger.info(f"Trying to use cached data: {cache_key}")
        context["strategy_used"] = "cache_fallback"

        # Return cached data or None
        return context.get("cached_data")

    def _retry_with_exponential_backoff(self, context: Dict[str, Any]) -> Optional[Any]:
        """Retry with exponential backoff"""
        retry_count = context.get("retry_count", 0)
        max_retries = context.get("max_retries", 3)

        if retry_count >= max_retries:
            return None

        # Calculate backoff time
        backoff_time = min(2**retry_count, 60)  # Max 60 seconds
        logger.info(f"Exponential backoff retry: waiting {backoff_time}s")

        time.sleep(backoff_time)
        context["retry_count"] = retry_count + 1
        context["strategy_used"] = "retry_with_backoff"

        return context

    def _use_alternative_endpoint(self, context: Dict[str, Any]) -> Optional[Any]:
        """Use alternative endpoint"""
        original_url = context.get("url")
        if not original_url:
            return None

        # Should have alternative endpoint configuration here
        alternative_endpoints = {
            "https://www.cninfo.com.cn": [
                "https://backup1.cninfo.com.cn",
                "https://backup2.cninfo.com.cn",
            ]
        }

        for domain, alternatives in alternative_endpoints.items():
            if domain in original_url:
                for alt_domain in alternatives:
                    alt_url = original_url.replace(domain, alt_domain)
                    logger.info(f"Trying alternative endpoint: {alt_url}")

                    context["url"] = alt_url
                    context["strategy_used"] = "alternative_endpoint"
                    return context

        return None

    def _switch_to_offline_mode(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Switch to offline mode"""
        logger.info("Switching to offline mode")
        context["strategy_used"] = "offline_mode"
        context["offline_mode"] = True

        return context

    def get_network_status(self) -> Dict[str, Any]:
        """Get network status"""
        recent_history = self.connection_history[-20:]

        if not recent_history:
            return {"status": "unknown", "message": "No historical data"}

        success_count = sum(1 for entry in recent_history if entry["success"])
        success_rate = success_count / len(recent_history)

        return {
            "status": (
                "healthy"
                if success_rate > 0.8
                else "degraded" if success_rate > 0.5 else "unhealthy"
            ),
            "success_rate": success_rate,
            "current_level": self.current_level.name,
            "circuit_breaker": "open" if self.circuit_breaker_open else "closed",
            "recent_attempts": len(recent_history),
            "successful_attempts": success_count,
        }


class FileSystemDegradationManager:
    """File system degradation manager"""

    def __init__(self) -> None:
        self.temp_dir = Path(tempfile.gettempdir()) / "stockinfo_downloader"
        self.temp_dir.mkdir(exist_ok=True)
        self.fallback_directories: List[Path] = []
        self.space_thresholds = {
            "minimal": 100 * 1024 * 1024,  # 100MB
            "warning": 500 * 1024 * 1024,  # 500MB
            "critical": 1 * 1024 * 1024 * 1024,  # 1GB
        }

        # Register fallback directories
        self._register_fallback_directories()

    def _register_fallback_directories(self) -> None:
        """Register fallback directories"""
        # System temp directory
        self.fallback_directories.append(Path(tempfile.gettempdir()))

        # User directories
        user_dir = Path.home()
        self.fallback_directories.extend(
            [user_dir / "Downloads", user_dir / "Documents", user_dir / "Desktop"]
        )

        # Program directory
        program_dir = Path.cwd()
        self.fallback_directories.append(program_dir / "temp")

    def check_disk_space(self, path: Union[str, Path]) -> Dict[str, Any]:
        """
        Check disk space

        Args:
            path: Path to check

        Returns:
            Disk space information
        """
        try:
            path = Path(path)
            if not path.exists():
                path = path.parent

            disk_usage = shutil.disk_usage(path)

            space_info = {
                "total": disk_usage.total,
                "used": disk_usage.used,
                "free": disk_usage.free,
                "percent_used": (disk_usage.used / disk_usage.total) * 100,
                "status": "healthy",
            }

            # Set status based on available space
            if disk_usage.free < self.space_thresholds["minimal"]:
                space_info["status"] = "critical"
            elif disk_usage.free < self.space_thresholds["warning"]:
                space_info["status"] = "warning"

            return space_info

        except Exception as e:
            logger.error(f"Failed to check disk space: {e}")
            return {"status": "error", "error": str(e)}

    def ensure_directory_exists(
        self, path: Union[str, Path], create_fallback: bool = True
    ) -> Path:
        """
        Ensure directory exists, use fallback if fails

        Args:
            path: Target path
            create_fallback: Whether to create fallback directory

        Returns:
            Actual directory path used
        """
        original_path = Path(path)

        try:
            # Try original path first
            if not original_path.exists():
                original_path.mkdir(parents=True, exist_ok=True)

            # Check write permission
            test_file = original_path / "test_write.tmp"
            test_file.touch()
            test_file.unlink()

            return original_path

        except Exception as e:
            logger.warning(f"Cannot access original directory {original_path}: {e}")

            if not create_fallback:
                raise FileSystemError(
                    f"Cannot access directory: {original_path}",
                    error_code=ErrorCode.FILE_PERMISSION_ERROR,
                    severity=ErrorSeverity.ERROR,
                    recovery_strategy=RecoveryStrategy.FALLBACK,
                    context={"original_path": str(original_path), "error": str(e)},
                )

            # Try fallback directory
            for fallback_dir in self.fallback_directories:
                try:
                    fallback_path = fallback_dir / original_path.name
                    fallback_path.mkdir(parents=True, exist_ok=True)

                    # Check write permission
                    test_file = fallback_path / "test_write.tmp"
                    test_file.touch()
                    test_file.unlink()

                    logger.info(f"Using fallback directory: {fallback_path}")
                    return fallback_path

                except Exception as fallback_error:
                    logger.warning(
                        f"Fallback directory {fallback_dir} also unavailable: {fallback_error}"
                    )
                    continue

            # All fallback directories failed
            raise FileSystemError(
                f"All directories unavailable, original path: {original_path}",
                error_code=ErrorCode.FILE_PERMISSION_ERROR,
                severity=ErrorSeverity.CRITICAL,
                recovery_strategy=RecoveryStrategy.NONE,
                context={
                    "original_path": str(original_path),
                    "attempted_fallbacks": [str(d) for d in self.fallback_directories],
                },
            )

    def safe_write_file(
        self,
        file_path: Union[str, Path],
        content: Union[str, bytes],
        encoding: str = "utf-8",
    ) -> bool:
        """
        Safe file writing

        Args:
            file_path: File path
            content: File content
            encoding: Encoding format

        Returns:
            Whether successful
        """
        try:
            file_path = Path(file_path)

            # Ensure directory exists
            directory = self.ensure_directory_exists(file_path.parent)
            actual_path = directory / file_path.name

            # Check disk space
            space_info = self.check_disk_space(directory)
            if space_info["status"] == "critical":
                logger.warning("Disk space critically low")
                return False

            # Atomic write: write to temp file first, then rename
            temp_path = actual_path.with_suffix(actual_path.suffix + ".tmp")

            if isinstance(content, str):
                with open(temp_path, "w", encoding=encoding) as f:
                    f.write(content)
            else:
                with open(temp_path, "wb") as f:
                    f.write(content)

            # Rename to target location
            temp_path.replace(actual_path)

            logger.info(f"File written successfully: {actual_path}")
            return True

        except Exception as e:
            logger.error(f"File write failed: {e}")
            return False

    def cleanup_temp_files(self, max_age_hours: int = 24) -> None:
        """
        Clean up temporary files

        Args:
            max_age_hours: Maximum retention time in hours
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            # Clean up main temp directory
            self._cleanup_directory(self.temp_dir, cutoff_time)

            # Clean up temp files in fallback directories
            for fallback_dir in self.fallback_directories:
                if fallback_dir.exists():
                    temp_files = fallback_dir.glob("*.tmp")
                    for temp_file in temp_files:
                        try:
                            if temp_file.stat().st_mtime < cutoff_time.timestamp():
                                temp_file.unlink()
                                logger.info(f"Cleaned up temp file: {temp_file}")
                        except Exception as e:
                            logger.warning(f"Failed to clean up temp file {temp_file}: {e}")

        except Exception as e:
            logger.error(f"Failed to clean up temp files: {e}")

    def _cleanup_directory(self, directory: Path, cutoff_time: datetime) -> None:
        """Clean up specified directory"""
        if not directory.exists():
            return

        for file_path in directory.glob("*"):
            try:
                if (
                    file_path.is_file()
                    and file_path.stat().st_mtime < cutoff_time.timestamp()
                ):
                    file_path.unlink()
                    logger.info(f"Cleaned up file: {file_path}")
                elif file_path.is_dir():
                    # Recursively clean subdirectories
                    self._cleanup_directory(file_path, cutoff_time)
                    # Delete directory if empty
                    try:
                        if not any(file_path.iterdir()):
                            file_path.rmdir()
                            logger.info(f"Cleaned up empty directory: {file_path}")
                    except (OSError, PermissionError):
                        # Directory may not be empty or lack permissions
                        pass
            except Exception as e:
                logger.warning(f"Cleanup failed {file_path}: {e}")


# Global instances
network_degradation_manager = NetworkDegradationManager()
file_system_degradation_manager = FileSystemDegradationManager()


# Convenience functions
def execute_with_network_fallback(
    primary_operation: Callable,
    fallback_strategies: List[str],
    context: Optional[Dict[str, Any]] = None,
) -> Any:
    """Convenience function for network fallback execution"""
    return network_degradation_manager.execute_with_fallback(
        primary_operation, fallback_strategies, context
    )


def ensure_directory_exists(
    path: Union[str, Path], create_fallback: bool = True
) -> Path:
    """Convenience function for directory existence"""
    return file_system_degradation_manager.ensure_directory_exists(
        path, create_fallback
    )


def safe_write_file(
    file_path: Union[str, Path], content: Union[str, bytes], encoding: str = "utf-8"
) -> bool:
    """Convenience function for safe file writing"""
    return file_system_degradation_manager.safe_write_file(file_path, content, encoding)


def get_network_status() -> Dict[str, Any]:
    """Convenience function for getting network status"""
    return network_degradation_manager.get_network_status()


def check_disk_space(path: Union[str, Path]) -> Dict[str, Any]:
    """Convenience function for checking disk space"""
    return file_system_degradation_manager.check_disk_space(path)
