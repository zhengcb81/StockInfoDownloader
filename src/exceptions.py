"""Custom exceptions for the stock downloader."""


class DownloaderError(Exception):
    """Base exception for all downloader errors."""

    def __init__(self, message: str, stock_code: str = ""):
        self.stock_code = stock_code
        super().__init__(message)


class OrgIdError(DownloaderError):
    """Raised when org_id cannot be resolved for a stock code."""


class BrowserError(DownloaderError):
    """Raised when browser automation fails."""


class ConfigError(DownloaderError):
    """Raised when configuration is invalid or missing."""


class DownloadError(DownloaderError):
    """Raised when a file download fails."""


class MappingError(DownloaderError):
    """Raised when mapping file is corrupted or unreadable."""
