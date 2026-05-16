"""Data models for the stock downloader."""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class OrgIdMapping:
    """Maps a stock code to its org_id and stock name."""

    stock_code: str
    org_id: str
    stock_name: str = "Unknown"
    source: str = "auto"  # "auto", "manual", "cached"
    confidence: float = 0.8
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class DownloadRequest:
    """Request to download files for a stock."""

    stock_code: str
    stock_name: Optional[str] = None
    org_id: Optional[str] = None
    suffix: Optional[str] = None
    allowed_keywords: Optional[List[str]] = None
    excluded_keywords: Optional[List[str]] = None
    max_pages: int = 5
    delete_later: bool = False
    timeout_seconds: int = 180
    save_dir: Optional[Union[str, Path]] = None
    save_subdir: Optional[str] = None  # e.g. "raw/prospectus"
    reverse_order: bool = False


@dataclass
class DownloadResult:
    """Result of a download operation."""

    success: bool
    downloaded_files: List[str] = field(default_factory=list)
    total_files: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    skipped_files: List[str] = field(default_factory=list)
    pages_traversed: int = 0
