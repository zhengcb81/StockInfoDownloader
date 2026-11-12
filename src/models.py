"""Data models for the stock downloader."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .transport_states import LoadState


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
    # Trailing optional field (CW-2.27D acceptance).  The announcement API may
    # already have proven that this exact company + period has zero official
    # announcements.  That proof belongs to the *request*, never to the
    # downloader instance: a later request for another company or period must
    # re-observe instead of inheriting an earlier empty result.
    confirmed_empty: bool = False


@dataclass(frozen=True)
class VerificationIssue:
    """One machine-readable post-download verification finding."""

    code: str
    message: str


@dataclass(frozen=True)
class VerificationResult:
    """Machine-readable verification outcome owned by the downloader.

    ``ok`` is the authoritative success signal for the post-download check.
    ``issues`` is structured so the CLI can log or aggregate findings without
    parsing English prose.
    """

    ok: bool = True
    issues: Tuple[VerificationIssue, ...] = ()


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
    # CW-2.27D typed load state: replaces the historical boolean ``success``
    # folding for zero-link / infrastructure conditions. Defaults preserve
    # legacy behavior for callers that do not opt into the typed state.
    load_state: Optional[LoadState] = None
    error_code: Optional[str] = None
    retryable: Optional[bool] = None
    # Post-download verification, decided by the download owner.  Callers must
    # read ``success`` (already folded with ``verification.ok``) instead of
    # re-judging diagnostics.
    verification: VerificationResult = field(default_factory=VerificationResult)
