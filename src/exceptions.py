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


class PaginationError(BrowserError):
    """The browser could not confirm a requested page transition."""

    def __init__(self, operation: str, page: int, target_page: int):
        self.operation = operation
        self.page = page
        self.target_page = target_page
        super().__init__(f"Pagination {operation} failed from page {page} to page {target_page}")


class ConfigError(DownloaderError):
    """Raised when configuration is invalid or missing."""


class DownloadError(DownloaderError):
    """Raised when a file download fails."""


class BrowserDownloadError(DownloadError):
    """Expose the stage and the last known provider effect to the caller."""

    def __init__(self, phase: str, sent: str):
        self.phase = phase
        self.sent = sent
        super().__init__(f"Browser download failed at {phase}")


class MappingError(DownloaderError):
    """Raised when mapping file is corrupted or unreadable."""
