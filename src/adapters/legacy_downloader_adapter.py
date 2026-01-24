#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Legacy Downloader Adapter
Provides backward-compatible interfaces for existing code
"""

from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from src.interfaces.downloader_interface import (
    DownloadRequest,
    DownloadResult,
    DownloadStatus
)
from src.services.unified_downloader import UnifiedDownloader
from src.core.logger import get_logger


class CninfoDownloaderAdapter:
    """
    CninfoDownloader Adapter
    Provides compatible interface for the old CninfoDownloader class
    """

    def __init__(self, save_dir: Optional[str] = None, **kwargs):
        """
        Initialize adapter

        Args:
            save_dir: Save directory
            **kwargs: Other configuration parameters
        """
        self.logger = get_logger("CninfoDownloaderAdapter")

        # Create unified downloader
        config = {'save_dir': save_dir, **kwargs}
        self._unified_downloader = UnifiedDownloader(config)

        # Preserve old method signature for compatibility
        self.save_dir = save_dir or "downloads"

        self.logger.info("CninfoDownloader Adapter initialized")

    def download_stock_pdfs(
        self,
        stock_code: str,
        target_pages: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Download stock PDF files (compatible with old interface)

        Args:
            stock_code: Stock code
            target_pages: Target number of pages
            **kwargs: Other parameters

        Returns:
            Dict[str, Any]: Result in old format
        """
        try:
            # Create new request object
            request = DownloadRequest(
                stock_code=stock_code,
                max_pages=target_pages,
                save_dir=self.save_dir,
                **kwargs
            )

            # Execute download using unified downloader
            result = self._unified_downloader.download_stock_pdfs(request)

            # Convert to old format and return
            return {
                'success': result.success,
                'downloaded_files': result.downloaded_files,
                'total_files': result.total_files,
                'errors': result.errors,
                'duration_seconds': result.duration_seconds,
                'metadata': result.metadata
            }

        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return {
                'success': False,
                'downloaded_files': [],
                'total_files': 0,
                'errors': [str(e)],
                'duration_seconds': 0,
                'metadata': {}
            }

    def __getattr__(self, name: str):
        """
        Delegate all undefined methods to internal unified downloader
        """
        return getattr(self._unified_downloader, name)

    # Preserve some possibly useful old methods
    def cleanup(self) -> None:
        """Cleanup resources"""
        if self._unified_downloader:
            self._unified_downloader.cleanup()

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure downloader"""
        if self._unified_downloader:
            self._unified_downloader.configure(config)


class DownloadServiceV1Adapter:
    """
    DownloadService (v1) Adapter
    Provides compatible interface for old version of DownloadService class
    """

    def __init__(self, save_dir: Optional[str] = None, **kwargs):
        """
        Initialize adapter

        Args:
            save_dir: Save directory
            **kwargs: Other configuration parameters
        """
        self.logger = get_logger("DownloadServiceV1Adapter")

        # Create unified downloader
        config = {'save_dir': save_dir, **kwargs}
        self._unified_downloader = UnifiedDownloader(config)

        # Preserve old method signature for compatibility
        self.save_dir = save_dir or "downloads"

        self.logger.info("DownloadServiceV1 Adapter initialized")

    def download_stock_pdfs(
        self,
        stock_code: str,
        max_retries: int = 3,
        **kwargs
    ) -> List[str]:
        """
        Download stock PDF files (compatible with old interface)

        Args:
            stock_code: Stock code
            max_retries: Max retries
            **kwargs: Other parameters

        Returns:
            List[str]: List of downloaded file paths
        """
        try:
            # Create new request object
            request = DownloadRequest(
                stock_code=stock_code,
                max_pages=kwargs.get('max_pages', 5),
                save_dir=self.save_dir,
                timeout_seconds=kwargs.get('timeout', 180),
                **kwargs
            )

            # Set retry count
            self._unified_downloader.config['retry_count'] = max_retries

            # Execute download using unified downloader
            result = self._unified_downloader.download_stock_pdfs(request)

            # Return backward-compatible format (filename list)
            return result.downloaded_files if hasattr(result, 'downloaded_files') else []

        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return []

    def __getattr__(self, name: str):
        """
        Delegate all undefined methods to internal unified downloader
        """
        return getattr(self._unified_downloader, name)

    def get_status(self) -> DownloadStatus:
        """Get download status"""
        return self._unified_downloader.get_status()

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure downloader"""
        if self._unified_downloader:
            self._unified_downloader.configure(config)


class DownloadServiceV2Adapter:
    """
    DownloadServiceV2 Adapter
    Provides compatible interface for DownloadServiceV2 class
    """

    def __init__(self, browser_strategy: str = "playwright", **kwargs):
        """
        Initialize adapter

        Args:
            browser_strategy: Browser strategy
            **kwargs: Other configuration parameters
        """
        self.logger = get_logger("DownloadServiceV2Adapter")

        # Create unified downloader
        config = {'browser_strategy': browser_strategy, **kwargs}
        self._unified_downloader = UnifiedDownloader(config)

        # Preserve old method signature for compatibility
        self.browser_strategy = browser_strategy

        self.logger.info(f"DownloadServiceV2 Adapter initialized, using strategy: {browser_strategy}")

    def download_stock_pdfs(
        self,
        stock_code: str,
        max_pages: int = 5,
        timeout_seconds: int = 180,
        target_pages: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> DownloadResult:
        """
        Download stock PDF files (compatible with old interface)

        Args:
            stock_code: Stock code
            max_pages: Max pages
            timeout_seconds: Timeout in seconds
            target_pages: Target page configuration list (backward compatible)
            **kwargs: Other parameters

        Returns:
            DownloadResult: Download result
        """
        try:
            # Extract parameters from kwargs to avoid passing them to DownloadRequest
            save_dir = kwargs.pop('save_dir', "downloads")
            stock_name = kwargs.pop('stock_name', None)
            suffix = kwargs.pop('suffix', None)
            allowed_keywords = kwargs.pop('allowed_keywords', None)
            max_retries = kwargs.pop('max_retries', None)  # Extract max_retries, do not pass to DownloadRequest

            # If stock_name not provided, try to get from mapping manager
            if not stock_name:
                try:
                    from src.data.mapping import MappingManager
                    mapping_manager = MappingManager("stock_orgid_mapping.json")
                    stock_name = mapping_manager.get_stock_name(stock_code)
                    if not stock_name:
                        stock_name = f"Stock{stock_code}"
                except Exception as e:
                    self.logger.warning(f"Failed to get stock name: {e}")
                    stock_name = f"Stock{stock_code}"

            # Set retry count to unified downloader config
            if max_retries is not None:
                # Set to UnifiedDownloader config
                self._unified_downloader.config['retry_count'] = max_retries

            # If target_pages exists, extract allowed_keywords and suffix from it
            if target_pages and len(target_pages) > 0:
                first_page = target_pages[0]
                if 'allowed_keywords' in first_page and first_page['allowed_keywords']:
                    allowed_keywords = first_page['allowed_keywords']
                if 'suffix' in first_page and first_page['suffix']:
                    suffix = first_page['suffix']

            # Create new request object
            request = DownloadRequest(
                stock_code=stock_code,
                stock_name=stock_name,
                suffix=suffix,
                allowed_keywords=allowed_keywords,
                max_pages=max_pages,
                timeout_seconds=timeout_seconds,
                save_dir=save_dir,
                **kwargs  # Remaining unknown parameters
            )

            # Execute download using unified downloader
            result = self._unified_downloader.download_stock_pdfs(request)

            return result

        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return DownloadResult(
                success=False,
                downloaded_files=[],
                total_files=0,
                errors=[str(e)],
                duration_seconds=0,
                metadata={'adapter_error': str(e)}
            )

    def __getattr__(self, name: str):
        """
        Delegate all undefined methods to internal unified downloader
        """
        return getattr(self._unified_downloader, name)

    def get_status(self) -> DownloadStatus:
        """Get download status"""
        return self._unified_downloader.get_status()

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure downloader"""
        if self._unified_downloader:
            self._unified_downloader.configure(config)


class RefactoredDownloaderAdapter:
    """
    RefactoredDownloader Adapter
    Provides compatible interface for RefactoredDownloader class
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, save_dir: Optional[str] = None, **kwargs):
        """
        Initialize adapter

        Args:
            config: Configuration dictionary
            save_dir: Save directory (backward compatible)
            **kwargs: Other parameters
        """
        self.logger = get_logger("RefactoredDownloaderAdapter")

        # Merge config parameters - unify usage of save_dir
        merged_config = config or {}
        if save_dir:
            merged_config['save_dir'] = save_dir
        merged_config.update(kwargs)

        # Create unified downloader
        self._unified_downloader = UnifiedDownloader(merged_config)

        self.logger.info("RefactoredDownloader Adapter initialized")

    def download_stock_pdfs(
        self,
        stock_code: str,
        stock_name: str,
        suffix: str,
        allowed_keywords: List[str],
        max_pages: int = 5,
        **kwargs
    ) -> DownloadResult:
        """
        Download stock PDF files (compatible with old interface)

        Args:
            stock_code: Stock code
            stock_name: Stock name
            suffix: Suffix
            allowed_keywords: Allowed keywords
            max_pages: Max pages
            **kwargs: Other parameters

        Returns:
            DownloadResult: Download result
        """
        try:
            # Create new request object
            request = DownloadRequest(
                stock_code=stock_code,
                stock_name=stock_name,
                suffix=suffix,
                allowed_keywords=allowed_keywords,
                max_pages=max_pages,
                save_dir=kwargs.get('save_dir', "downloads"),
                **kwargs
            )

            # Execute download using unified downloader
            result = self._unified_downloader.download_stock_pdfs(request)

            return result

        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return DownloadResult(
                success=False,
                downloaded_files=[],
                total_files=0,
                errors=[str(e)],
                duration_seconds=0,
                metadata={'adapter_error': str(e)}
            )

    def __getattr__(self, name: str):
        """
        Delegate all undefined methods to internal unified downloader
        """
        return getattr(self._unified_downloader, name)

    def get_status(self) -> DownloadStatus:
        """Get download status"""
        return self._unified_downloader.get_status()

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure downloader"""
        if self._unified_downloader:
            self._unified_downloader.configure(config)


def create_legacy_adapter(class_name: str, **kwargs) -> Any:
    """
    Factory function to create legacy downloader adapter

    Args:
        class_name: Class name
        **kwargs: Constructor arguments

    Returns:
        Any: Adapter instance
    """
    adapters = {
        'CninfoDownloader': CninfoDownloaderAdapter,
        'DownloadService': DownloadServiceV1Adapter,
        'DownloadServiceV2': DownloadServiceV2Adapter,
        'RefactoredDownloader': RefactoredDownloaderAdapter
    }

    adapter_class = adapters.get(class_name)
    if not adapter_class:
        raise ValueError(f"Unsupported downloader type: {class_name}")

    return adapter_class(**kwargs)


# For maximum compatibility, create a universal wrapper
class UniversalDownloaderWrapper:
    """
    Universal Downloader Wrapper
    Can automatically select appropriate adapter based on arguments
    """

    def __init__(self, downloader_type: str = "auto", **kwargs):
        """
        Initialize universal wrapper

        Args:
            downloader_type: Downloader type, "auto" means automatic selection
            **kwargs: Constructor arguments
        """
        self.logger = get_logger("UniversalDownloaderWrapper")

        if downloader_type == "auto":
            # Automatically detect which adapter to use
            if 'browser_strategy' in kwargs:
                self._downloader = DownloadServiceV2Adapter(**kwargs)
            elif 'max_retries' in kwargs:
                self._downloader = DownloadServiceV1Adapter(**kwargs)
            elif 'allowed_keywords' in kwargs:
                self._downloader = RefactoredDownloaderAdapter(**kwargs)
            else:
                # Default to DownloadServiceV2
                self._downloader = DownloadServiceV2Adapter(**kwargs)
        else:
            # Use specified adapter
            self._downloader = create_legacy_adapter(downloader_type, **kwargs)

        self.logger.info(f"Universal wrapper initialized, using type: {downloader_type}")

    def __getattr__(self, name: str):
        """
        Delegate all undefined methods to internal downloader
        """
        return getattr(self._downloader, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self._downloader, 'cleanup'):
            self._downloader.cleanup()