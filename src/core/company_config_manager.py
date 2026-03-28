"""
Company Configuration Manager Module
Provides multi-company configuration management functionality
"""

from typing import Any, Dict, List, Optional, Tuple

from .config_manager import BaseConfigManager
from .exceptions import OrgIdError
from .logger import get_logger


class CompanyConfigManager:
    """Company configuration manager for multi-company support"""

    def __init__(self, base_manager: BaseConfigManager):
        self._base = base_manager
        self.logger = get_logger(self.__class__.__name__)

    def get_companies(self) -> List[Dict[str, Any]]:
        """
        Get configured company list

        Returns:
            List[Dict[str, Any]]: Company configuration list
        """
        companies = self._base.get("companies", [])

        # If no companies configured, try to create from old stock_code config
        if not companies and self._base.get("stock_code"):
            stock_code = self._base.get("stock_code")
            # Try to get company name
            from src.data.mapping import MappingManager

            try:
                mapping_manager = MappingManager()
                company_name = mapping_manager.get_stock_name(stock_code)
            except (OSError, KeyError, OrgIdError):
                # Mapping not found or unable to load
                company_name = f"Stock {stock_code}"

            companies = [
                {
                    "stock_code": stock_code,
                    "company_name": company_name,
                    "enabled": True,
                    "priority": 1,
                    "custom_pages": None,
                }
            ]

        # Filter enabled companies and sort by priority
        enabled_companies = [c for c in companies if c.get("enabled", True)]
        enabled_companies.sort(key=lambda x: x.get("priority", 1))

        return enabled_companies

    def get_company_config(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        Get specific company configuration

        Args:
            stock_code: Stock code

        Returns:
            Optional[Dict[str, Any]]: Company configuration, None if not exists
        """
        companies = self.get_companies()
        for company in companies:
            if company.get("stock_code") == stock_code:
                return company
        return None

    def add_company(
        self,
        stock_code: str,
        company_name: Optional[str] = None,
        priority: int = 1,
        enabled: bool = True,
        custom_pages: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Add company configuration

        Args:
            stock_code: Stock code
            company_name: Company name (optional)
            priority: Priority (lower number = higher priority)
            enabled: Whether enabled
            custom_pages: Custom page configuration

        Returns:
            bool: Whether added successfully
        """
        try:
            # Get existing company list
            companies = self._base.get("companies", [])

            # Check if already exists
            for company in companies:
                if company.get("stock_code") == stock_code:
                    self.logger.warning(f"Company {stock_code} already exists, updating config")
                    # Update existing config
                    company.update(
                        {
                            "company_name": company_name
                            or company.get("company_name", f"Stock {stock_code}"),
                            "priority": priority,
                            "enabled": enabled,
                            "custom_pages": custom_pages,
                        }
                    )
                    break
            else:
                # Add new company
                if not company_name:
                    # Try to get company name
                    from src.data.mapping import MappingManager

                    try:
                        mapping_manager = MappingManager()
                        company_name = mapping_manager.get_stock_name(stock_code)
                    except (OSError, KeyError, OrgIdError):
                        # Mapping not found or unable to load
                        company_name = f"Stock {stock_code}"

                companies.append(
                    {
                        "stock_code": stock_code,
                        "company_name": company_name,
                        "enabled": enabled,
                        "priority": priority,
                        "custom_pages": custom_pages,
                    }
                )

            # Save configuration
            self._base.set("companies", companies)
            self._base.save_config()

            return True

        except Exception as e:
            self.logger.error(f"Failed to add company config: {e}")
            return False

    def remove_company(self, stock_code: str) -> bool:
        """
        Remove company configuration

        Args:
            stock_code: Stock code

        Returns:
            bool: Whether removed successfully
        """
        try:
            companies = self._base.get("companies", [])
            original_count = len(companies)

            # Filter out specified company
            companies = [c for c in companies if c.get("stock_code") != stock_code]

            if len(companies) == original_count:
                # Company not found
                self.logger.warning(f"Company {stock_code} not found")
                return False

            # Save configuration
            self._base.set("companies", companies)
            self._base.save_config()

            return True

        except Exception as e:
            self.logger.error(f"Failed to remove company config: {e}")
            return False

    def enable_company(self, stock_code: str) -> bool:
        """
        Enable company

        Args:
            stock_code: Stock code

        Returns:
            bool: Whether enabled successfully
        """
        return self._update_company_status(stock_code, True)

    def disable_company(self, stock_code: str) -> bool:
        """
        Disable company

        Args:
            stock_code: Stock code

        Returns:
            bool: Whether disabled successfully
        """
        return self._update_company_status(stock_code, False)

    def _update_company_status(self, stock_code: str, enabled: bool) -> bool:
        """
        Update company status

        Args:
            stock_code: Stock code
            enabled: Whether enabled

        Returns:
            bool: Whether updated successfully
        """
        try:
            companies = self._base.get("companies", [])
            updated = False

            for company in companies:
                if company.get("stock_code") == stock_code:
                    company["enabled"] = enabled
                    updated = True
                    break

            if updated:
                self._base.set("companies", companies)
                self._base.save_config()

            return updated

        except Exception as e:
            self.logger.error(f"Failed to update company status: {e}")
            return False

    def validate_companies_config(self) -> Tuple[bool, List[str]]:
        """
        Validate company configuration

        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        errors = []
        companies = self.get_companies()

        if not companies:
            errors.append("No companies configured")
            return False, errors

        stock_codes = set()
        for i, company in enumerate(companies):
            stock_code = company.get("stock_code")

            # Validate stock code format
            if (
                not stock_code
                or not str(stock_code).isdigit()
                or len(str(stock_code)) != 6
            ):
                errors.append(f"Company {i+1} stock code format error: {stock_code}")

            # Check duplicates
            if stock_code in stock_codes:
                errors.append(f"Stock code {stock_code} duplicate configuration")
            stock_codes.add(stock_code)

            # Validate priority
            priority = company.get("priority", 1)
            if not isinstance(priority, int) or priority < 1:
                errors.append(f"Company {stock_code} priority setting error: {priority}")

            # Validate custom page configuration
            custom_pages = company.get("custom_pages")
            if custom_pages is not None:
                if not isinstance(custom_pages, list):
                    errors.append(f"Company {stock_code} custom_pages must be array")
                else:
                    for j, page in enumerate(custom_pages):
                        if not isinstance(page, dict):
                            errors.append(
                                f"Company {stock_code} page {j+1} config format error"
                            )
                        elif "suffix" not in page:
                            errors.append(
                                f"Company {stock_code} page {j+1} config missing suffix field"
                            )

        return len(errors) == 0, errors

    def get_companies_summary(self) -> Dict[str, Any]:
        """
        Get company configuration summary

        Returns:
            Dict[str, Any]: Company configuration summary
        """
        # Get all companies (including disabled)
        all_companies = self._base.get("companies", [])
        enabled_companies = self.get_companies()  # This returns enabled companies

        enabled_count = len(enabled_companies)
        disabled_count = len(all_companies) - enabled_count

        priorities = set()
        for company in all_companies:
            priorities.add(company.get("priority", 1))

        return {
            "total_companies": len(all_companies),
            "enabled_companies": enabled_count,
            "disabled_companies": disabled_count,
            "priority_levels": sorted(priorities),
            "stock_codes": [c.get("stock_code") for c in all_companies],
            "parallel_download_enabled": self._base.is_parallel_download_enabled(),
            "proxy_enabled": self._base.is_proxy_enabled(),
            "max_workers": self._base.get_max_workers(),
        }
