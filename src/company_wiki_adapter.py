"""Typed, staging-only CNINFO adapter for company-wiki.

This module deliberately does not choose company-wiki canonical paths.  It
discovers official disclosure identities and downloads one selected asset only
to a caller-allocated staging directory.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import hashlib
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

from . import constants as C
from .downloader import StockDownloader, _matches_excluded, _matches_keywords
from .string_utils import clean_filename

if TYPE_CHECKING:
    from .acquisition_budget import ProviderAcquisitionBudget
    from .cninfo_api import CninfoAnnouncementClient


ADAPTER_NAME = "stockinfo-cninfo"
ADAPTER_VERSION = "1.2.0"
_YEAR_RE = re.compile(r"(?<!\d)(20\d{2})(?=年)")


class AdapterError(RuntimeError):
    """Raised when discovery or staged transport violates the adapter contract."""


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be non-empty trimmed text")
    return value


def _optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, name)


@dataclass(frozen=True)
class AdapterDiscoveryRequest:
    stock_code: str
    stock_name: str
    document_kind: str
    fiscal_year: int
    org_id: str | None = None
    suffix: str = "periodicReports"
    allowed_keywords: tuple[str, ...] = ()
    excluded_keywords: tuple[str, ...] = ()
    max_pages: int = 1

    def __post_init__(self) -> None:
        for name in ("stock_code", "stock_name", "document_kind", "suffix"):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        object.__setattr__(self, "org_id", _optional_text(self.org_id, "org_id"))
        object.__setattr__(self, "document_kind", self.document_kind.lower())
        if isinstance(self.fiscal_year, bool) or not isinstance(self.fiscal_year, int):
            raise TypeError("fiscal_year must be an integer")
        if not 1990 <= self.fiscal_year <= 2200:
            raise ValueError("fiscal_year is outside the supported range")
        if (
            isinstance(self.max_pages, bool)
            or not isinstance(self.max_pages, int)
            or self.max_pages <= 0
        ):
            raise ValueError("max_pages must be a positive integer")
        for name in ("allowed_keywords", "excluded_keywords"):
            value = getattr(self, name)
            if not isinstance(value, tuple) or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                raise TypeError(f"{name} must be a tuple of non-empty strings")


@dataclass(frozen=True)
class DisclosureCandidate:
    candidate_id: str
    provider: str
    provider_document_id: str
    identity_method: str
    market: str
    entity: str
    title: str
    source_url: str
    document_kind: str
    form_type: str
    filing_date: str
    fiscal_year: int
    fiscal_period: str
    language: str
    amended: bool
    # CW-2.27F / Phase 5: transport_url is the official PDF download URL on
    # ``static.cninfo.com.cn``. It is intentionally NOT a ``source_url``
    # candidate — ``source_url`` is always the human-openable detail page so
    # the catalog record preserves the legitimate provenance URL. The CLI
    # carries transport_url inside the opaque adapter_payload_json so company
    # wiki never mislabels transport URL as the source of truth.
    transport_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StagedDownloadReceipt:
    candidate_id: str
    provider: str
    provider_document_id: str
    source_url: str
    staged_path: str
    content_sha256: str
    byte_size: int
    mime_type: str
    retrieved_at: str
    http_status: int
    adapter_name: str
    adapter_version: str
    etag: str | None = None
    last_modified: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _first_query_value(query: dict[str, list[str]], *names: str) -> str | None:
    folded = {key.casefold(): value for key, value in query.items()}
    for name in names:
        values = folded.get(name.casefold())
        if values and values[0].strip():
            return values[0].strip()
    return None


def _announcement_identity(source_url: str) -> tuple[str, str]:
    parsed = urlparse(source_url)
    query = parse_qs(parsed.query)
    announcement_id = _first_query_value(
        query,
        "announcementId",
        "announcement_id",
        "docId",
        "documentId",
    )
    if announcement_id:
        return announcement_id, "announcement_id"
    digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    return digest, "derived_from_url_hash"


def _filing_date(source_url: str) -> str | None:
    query = parse_qs(urlparse(source_url).query)
    raw = _first_query_value(query, "announcementTime", "announcementDate", "date")
    if raw is None:
        return None
    normalized = raw.strip().replace("/", "-")
    if re.fullmatch(r"\d{8}", normalized):
        normalized = f"{normalized[:4]}-{normalized[4:6]}-{normalized[6:]}"
    # Real cninfo announcementTime may carry HH:MM[:SS]; canonicalize to date only.
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed.date().isoformat()
    except ValueError:
        pass
    try:
        parsed = date.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed.isoformat()


# company-wiki 专用 filing request 的默认安全排除：调用者可增加但不能移除。
_DEFAULT_EXCLUDED_TOKENS: tuple[str, ...] = ("摘要",)


def _report_metadata(title: str) -> tuple[str, int | None, str, str, bool]:
    compact = "".join(title.split())
    year_match = _YEAR_RE.search(compact)
    fiscal_year = int(year_match.group(1)) if year_match else None
    amended = any(token in compact for token in ("修订", "更正", "更新后", "修正版"))
    if any(token in compact for token in ("半年度报告", "半年报")):
        return "semi_annual_report", fiscal_year, "interim_report", "H1", amended
    if any(token in compact for token in ("季度报告", "一季报", "三季报")):
        period = (
            "Q1" if any(token in compact for token in ("一季度", "一季报")) else "Q3"
        )
        return "quarterly_report", fiscal_year, "quarterly_report", period, amended
    if any(token in compact for token in ("年度报告", "年报")):
        return "annual_report", fiscal_year, "annual_report", "FY", amended
    return "other", fiscal_year, "other", "UNKNOWN", amended


class StockInfoCompanyWikiAdapter:
    """API-first CNINFO adapter.

    CW-2.27F / Phase 5: discover() exclusively calls ``CninfoAnnouncementClient``
    (official announcement JSON API) rather than the historical SPA scraper
    (``_navigate_to_stock_page / _switch_tab / _get_links``). ``fetch()`` uses
    the API client's HTTPS PDF transport (``*.part`` + atomic rename) instead
    of the Playwright browser download path.
    """

    name = ADAPTER_NAME
    version = ADAPTER_VERSION

    def __init__(
        self,
        downloader: StockDownloader,
        *,
        cninfo_client: "CninfoAnnouncementClient | None" = None,
    ):
        self.downloader = downloader
        if cninfo_client is None:
            from .cninfo_api import CninfoAnnouncementClient

            cninfo_client = CninfoAnnouncementClient()
        self._cninfo_client = cninfo_client

    def discover(
        self,
        request: AdapterDiscoveryRequest,
        *,
        acquisition_budget: ProviderAcquisitionBudget | None = None,
    ) -> tuple[DisclosureCandidate, ...]:
        if not isinstance(request, AdapterDiscoveryRequest):
            raise TypeError("request must be AdapterDiscoveryRequest")
        # Resolve org_id via downloader.mapping only when not supplied by caller
        if request.org_id:
            org_id = request.org_id
        else:
            org_id = self.downloader.mapping.get_org_id(request.stock_code)
            if not org_id:
                raise AdapterError(f"cannot resolve org_id for {request.stock_code}")

        from .cninfo_api import CninfoApiError  # local import for cycle-safety

        try:
            call_args: dict[str, Any] = {
                "stock_code": request.stock_code,
                "org_id": org_id,
                "document_kind": request.document_kind,
                "fiscal_year": request.fiscal_year,
                "max_pages": request.max_pages,
            }
            if acquisition_budget is not None:
                call_args["budget"] = acquisition_budget
            records, state = self._cninfo_client.discover_announcements(
                **call_args
            )
        except CninfoApiError as exc:
            raise AdapterError(
                f"cninfo_api_discover failed: {exc.error_code}: {exc}"
            ) from exc

        # Adapter-level safety defaults: caller may ADD excluded keywords but
        # never remove the canonical "摘要" exclusion.
        effective_excluded = tuple(
            dict.fromkeys((*request.excluded_keywords, *_DEFAULT_EXCLUDED_TOKENS))
        )

        candidates: dict[str, DisclosureCandidate] = {}
        for record in records:
            title = record.title
            if _matches_excluded(title, list(effective_excluded)):
                continue
            if request.allowed_keywords and not _matches_keywords(
                title, list(request.allowed_keywords)
            ):
                continue
            kind, year, form_type, fiscal_period, amended = _report_metadata(title)
            # Defense-in-depth: API client already filtered on kind+year, but
            # the adapter re-validates to make double-distance from upstream
            # schema drift.
            if kind != request.document_kind or year != request.fiscal_year:
                continue
            candidate_id = f"cninfo:{record.announcement_id}"
            candidate = DisclosureCandidate(
                candidate_id=candidate_id,
                provider="cninfo",
                provider_document_id=record.announcement_id,
                identity_method="announcement_id",
                market="CN",
                entity=request.stock_code,
                title=title,
                source_url=record.detail_url,  # human-openable official detail page
                document_kind=kind,
                form_type=form_type,
                filing_date=record.filing_date,
                fiscal_year=year,
                fiscal_period=fiscal_period,
                language="zh-CN",
                amended=amended,
                transport_url=record.transport_url,  # opaque to company-wiki
            )
            candidates[candidate_id] = candidate
        return tuple(candidates[key] for key in sorted(candidates))

    def fetch(
        self,
        candidate: DisclosureCandidate,
        staging_dir: Path,
        *,
        acquisition_budget: ProviderAcquisitionBudget | None = None,
    ) -> StagedDownloadReceipt:
        if not isinstance(candidate, DisclosureCandidate):
            raise TypeError("candidate must be DisclosureCandidate")
        if not isinstance(staging_dir, Path):
            raise TypeError("staging_dir must be pathlib.Path")
        if not candidate.transport_url:
            raise AdapterError("candidate missing transport_url")
        staging_dir.mkdir(parents=True, exist_ok=True)
        allocated = staging_dir.resolve(strict=True)
        safe_title = clean_filename(candidate.title)[:120] or "document"
        safe_id = clean_filename(candidate.provider_document_id)[:80]
        safe_filename = f"{safe_id}__{safe_title}.pdf"

        from .cninfo_api import CninfoApiError  # local import

        try:
            fetch_args: dict[str, Any] = {
                "transport_url": candidate.transport_url,
                "staging_dir": allocated,
                "expected_filename": safe_filename,
            }
            if acquisition_budget is not None:
                fetch_args["budget"] = acquisition_budget
            staged_path = self._cninfo_client.fetch_pdf(
                **fetch_args
            )
        except CninfoApiError as exc:
            raise AdapterError(
                f"cninfo_transport failed: {exc.error_code}: {exc}"
            ) from exc

        # Resolve symlinked/case paths for staging edge check.
        try:
            resolved = staged_path.resolve(strict=True)
            resolved.relative_to(allocated)
        except ValueError as exc:
            raise AdapterError("derived destination escaped staging") from exc

        stat = resolved.stat()
        if stat.st_size <= C.MIN_FILE_SIZE:
            raise AdapterError("staged file is too small")
        with resolved.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise AdapterError("staged file failed PDF magic validation")
        digest = hashlib.sha256()
        with resolved.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return StagedDownloadReceipt(
            candidate_id=candidate.candidate_id,
            provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            source_url=candidate.source_url,
            staged_path=str(resolved),
            content_sha256=digest.hexdigest(),
            byte_size=stat.st_size,
            mime_type="application/pdf",
            retrieved_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            http_status=200,
            adapter_name=self.name,
            adapter_version=self.version,
        )


__all__ = [
    "ADAPTER_NAME",
    "ADAPTER_VERSION",
    "AdapterDiscoveryRequest",
    "AdapterError",
    "DisclosureCandidate",
    "StagedDownloadReceipt",
    "StockInfoCompanyWikiAdapter",
]
