"""
Test Configuration Manager Module
Provides test environment specific configuration management
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, cast

from .config_constants import ConfigConstants
from .exceptions import ConfigError, ErrorCode, ErrorSeverity, RecoveryStrategy
from .logger import get_logger


class TestConfigManager:
    """Test configuration manager for test environment"""

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self._test_config: Optional[Dict[str, Any]] = None
        self._config_path: Optional[str] = None

    def load_test_config(
        self, config_path: str = "configs/test_config.json"
    ) -> Dict[str, Any]:
        """
        Load test configuration file

        Args:
            config_path: Test configuration file path

        Returns:
            Dict[str, Any]: Test configuration dictionary
        """
        try:
            config_path_obj = Path(config_path)
            if not config_path_obj.exists():
                # Try relative to project root
                project_root = Path(__file__).parent.parent.parent
                config_path_obj = project_root / config_path

            if not config_path_obj.exists():
                raise ConfigError(
                    f"Test configuration file does not exist: {config_path}",
                    error_code=ErrorCode.CONFIG_FILE_NOT_FOUND,
                    severity=ErrorSeverity.ERROR,
                    recovery_strategy=RecoveryStrategy.FALLBACK,
                    context={"config_path": str(config_path_obj)},
                )

            with open(config_path_obj, "r", encoding="utf-8") as f:
                self._test_config = json.load(f)
                self._config_path = str(config_path_obj)

            return self._test_config

        except Exception as e:
            raise ConfigError(
                f"Failed to load test configuration file: {e}",
                error_code=ErrorCode.CONFIG_LOAD_ERROR,
                severity=ErrorSeverity.ERROR,
                recovery_strategy=RecoveryStrategy.FALLBACK,
                context={"config_path": str(config_path)},
                original_exception=e,
            )

    def get_test_config(self, key: Optional[str] = None, default: Any = None) -> Any:
        """
        Get test configuration value

        Args:
            key: Configuration key, supports dot notation
            default: Default value

        Returns:
            Any: Configuration value
        """
        if self._test_config is None:
            self.load_test_config()

        if key is None:
            return self._test_config.copy() if self._test_config else {}

        # Support dot notation
        keys = key.split(".")
        value = self._test_config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            elif isinstance(value, list) and k.isdigit() and int(k) < len(value):
                value = value[int(k)]
            else:
                return default

        return value

    def get_test_stock(self, stock_code: str) -> Dict[str, Any]:
        """
        Get test stock information

        Args:
            stock_code: Stock code

        Returns:
            Dict[str, Any]: Stock information dictionary
        """
        test_stocks = self.get_test_config("test_data.stocks", [])
        for stock in test_stocks:
            if stock.get("code") == stock_code:
                return cast(Dict[str, Any], stock)
        return cast(Dict[str, Any], {})

    def get_test_timeout(self, timeout_type: str = "validation") -> int:
        """
        Get test timeout value

        Args:
            timeout_type: Timeout type

        Returns:
            int: Timeout value
        """
        return cast(
            int,
            self.get_test_config(
                f"test_environment.{timeout_type}",
                ConfigConstants.get_timeout(timeout_type),
            ),
        )

    def get_test_directory(self, dir_name: str) -> str:
        """
        Get test directory path

        Args:
            dir_name: Directory name

        Returns:
            str: Directory path
        """
        return cast(str, self.get_test_config(f"test_directories.{dir_name}", ""))

    def is_test_environment(self, environment: str) -> bool:
        """Check if test environment"""
        return environment == "test"

    def reload(self) -> Dict[str, Any]:
        """Reload test configuration"""
        self._test_config = None
        return self.load_test_config(self._config_path or "configs/test_config.json")
