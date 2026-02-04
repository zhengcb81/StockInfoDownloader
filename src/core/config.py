"""
Configuration Management Module
Provides unified configuration loading and management functionality

This module re-exports from the split configuration managers for backward compatibility.
The ConfigManager class has been split into:
- BaseConfigManager: Core configuration management
- CompanyConfigManager: Multi-company configuration management
- TestConfigManager: Test environment configuration management
"""

from typing import Any, Dict, List, Optional, Tuple

from .config_manager import BaseConfigManager
from .company_config_manager import CompanyConfigManager
from .test_config_manager import TestConfigManager
from .exceptions import ConfigError  # Re-export for backward compatibility
from .logger import get_logger


class ConfigManager(BaseConfigManager):
    """
    Unified Configuration Manager (Backward Compatible)

    This class combines BaseConfigManager, CompanyConfigManager, and TestConfigManager
    for backward compatibility. New code should use the specific managers directly.

    Attributes:
        companies: CompanyConfigManager instance for company-related operations
        test: TestConfigManager instance for test-related operations
    """

    def __init__(self, config_file=None, environment="production"):
        super().__init__(config_file, environment)
        self.logger = get_logger(self.__class__.__name__)

        # Initialize specialized managers
        self._company_manager = CompanyConfigManager(self)
        self._test_manager = TestConfigManager()

    # Company configuration methods (delegated to CompanyConfigManager)
    def get_companies(self) -> List[Dict[str, Any]]:
        """Get configured company list"""
        return self._company_manager.get_companies()

    def get_company_config(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """Get specific company configuration"""
        return self._company_manager.get_company_config(stock_code)

    def add_company(
        self,
        stock_code: str,
        company_name: Optional[str] = None,
        priority: int = 1,
        enabled: bool = True,
        custom_pages: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Add company configuration"""
        return self._company_manager.add_company(
            stock_code, company_name, priority, enabled, custom_pages
        )

    def remove_company(self, stock_code: str) -> bool:
        """Remove company configuration"""
        return self._company_manager.remove_company(stock_code)

    def enable_company(self, stock_code: str) -> bool:
        """Enable company"""
        return self._company_manager.enable_company(stock_code)

    def disable_company(self, stock_code: str) -> bool:
        """Disable company"""
        return self._company_manager.disable_company(stock_code)

    def validate_companies_config(self) -> Tuple[bool, List[str]]:
        """Validate company configuration"""
        return self._company_manager.validate_companies_config()

    def get_companies_summary(self) -> Dict[str, Any]:
        """Get company configuration summary"""
        return self._company_manager.get_companies_summary()

    # Test configuration methods (delegated to TestConfigManager)
    def load_test_config(
        self, config_path: str = "configs/test_config.json"
    ) -> Dict[str, Any]:
        """Load test configuration file"""
        return self._test_manager.load_test_config(config_path)

    def get_test_config(self, key: Optional[str] = None, default: Any = None) -> Any:
        """Get test configuration value"""
        return self._test_manager.get_test_config(key, default)

    def get_test_stock(self, stock_code: str) -> Dict[str, str]:
        """Get test stock information"""
        return self._test_manager.get_test_stock(stock_code)

    def get_test_timeout(self, timeout_type: str = "validation") -> int:
        """Get test timeout value"""
        return self._test_manager.get_test_timeout(timeout_type)

    def get_test_directory(self, dir_name: str) -> str:
        """Get test directory path"""
        return self._test_manager.get_test_directory(dir_name)

    def is_test_environment(self) -> bool:
        """Check if test environment"""
        return self._test_manager.is_test_environment(self._environment)


# Export all configuration manager classes
__all__ = [
    "ConfigManager",
    "BaseConfigManager",
    "CompanyConfigManager",
    "TestConfigManager",
    "ConfigError",  # Re-export for backward compatibility
]
