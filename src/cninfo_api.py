"""Cninfo official announcement API + PDF transport.

CW-2.27F / Phase 5 replaces the historical SPA scraper with an API-first
discovery client backed by the official cninfo announcement JSON endpoint.
Uses ONLY stdlib (urllib + ssl); no new third-party dependencies.

Discovery returns ``CninfoAnnouncement`` records parsed from the official
announcement API JSON response. Transport downloads one PDF via HTTPS GET
against the frozen cninfo static host, writing ``*.part`` first, validating
size/PDF magic, then atomic OS-level rename into the caller-allocated
staging directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import json
from typing import Any
from urllib.parse import quote, urlencode, urlparse
import urllib.error
import urllib.request

from .acquisition_budget import (
    AcquisitionBudgetExceeded,
    ProviderAcquisitionBudget,
)
from . import constants as C
from .transport_states import LoadState


ANNOUNCEMENT_API_ENDPOINT = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
DETAIL_PAGE_BASE = "https://www.cninfo.com.cn/new/disclosure/detail"
TRANSPORT_HOSTS = frozenset({"static.cninfo.com.cn", "www.cninfo.com.cn"})

# latest windows start on Jan 1 of ``as_of.year - LATEST_WINDOW_YEARS``.
LATEST_WINDOW_YEARS = 2

# Official periodic categories differ. Quarterly discovery covers both Q1
# and Q3; existing title/period filters select the requested report.
_CATEGORY_PER_KIND = {
    "annual_report": "category_ndbg_szsh",
    "semi_annual_report": "category_bndbg_szsh",
    "quarterly_report": "category_yjdbg_szsh;category_sjdbg_szsh",
}


_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_READ_CHUNK_BYTES = 64 * 1024


class CninfoApiError(RuntimeError):
    """Typed error carrying stable ``error_code`` + ``retryable`` for upstream
    AdapterProcessError parsing. Never returned silently — always raises.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        retryable: bool,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.retryable = retryable
        self.http_status = http_status


@dataclass(frozen=True)
class CninfoAnnouncement:
    """Parsed single announcement record."""

    announcement_id: str
    filing_date: str  # disclosure calendar date in China (UTC+08:00)
    title: str
    sec_code: str
    sec_name: str
    org_id: str
    announcement_time_ms: int  # epoch milliseconds UTC
    adjunct_type: str
    adjunct_url: str  # relative path segment for transport URL
    transport_url: str  # frozen https://static.cninfo.com.cn/<adjunct_url>
    detail_url: str  # human-openable official detail page


@dataclass(frozen=True)
class _PageMeta:
    """Raw (pre-filter) facts about one announcement page.

    Pagination completeness is decided from these, never from how many records
    survived the metadata filter — a page whose filter yields zero still proves
    nothing about how many raw records remain.
    """

    total: int
    raw_count: int
    totalpages: int | None
    has_more: bool


class CninfoAnnouncementClient:
    """Minimal stdlib-only cninfo announcement API + PDF transport client."""

    def __init__(
        self,
        *,
        user_agent: str = _DEFAULT_USER_AGENT,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._user_agent = user_agent
        self._timeout = float(timeout_seconds)

    # ── PUBLIC API ──────────────────────────────────────────────────────

    def discover_announcements(
        self,
        *,
        stock_code: str,
        org_id: str,
        document_kind: str,
        fiscal_year: int | None = None,
        max_pages: int = 5,
        budget: ProviderAcquisitionBudget | None = None,
        as_of_date: str | None = None,
        fiscal_period: str | None = None,
        form_type: str | None = None,
    ) -> tuple[list[CninfoAnnouncement], LoadState]:
        """Discover announcements for one bounded window.

        ``as_of_date is None`` keeps the historical exact behaviour: one
        ``[fy-01-01, fy+1-12-31]`` window filtered on the requested year.
        ``as_of_date`` selects the latest mode: a single three-natural-year
        window ending at ``as_of_date``, completeness proven from raw API
        totals, and a non-retryable ``discovery_incomplete`` when the page cap
        cannot prove full coverage.
        """
        if as_of_date is not None:
            return self._discover_latest(
                stock_code=stock_code,
                org_id=org_id,
                document_kind=document_kind,
                as_of_date=as_of_date,
                fiscal_period=fiscal_period,
                form_type=form_type,
                max_pages=max_pages,
                budget=budget,
            )
        if isinstance(fiscal_year, bool) or not isinstance(fiscal_year, int):
            raise CninfoApiError(
                "exact discovery requires an integer fiscal_year",
                error_code="client_error",
                retryable=False,
            )
        records: list[CninfoAnnouncement] = []
        state = LoadState.INFRASTRUCTURE_FAIL  # default; overridden by valid response
        covered_raw = 0
        for page_num in range(1, max(max_pages, 1) + 1):
            body = self._build_request_body(
                stock_code=stock_code,
                org_id=org_id,
                document_kind=document_kind,
                fiscal_year=fiscal_year,
                page_num=page_num,
                page_size=30,
            )
            raw_json = self._post_json(body, budget=budget)
            page_records, page_state, meta = self._filter_page(
                raw_json,
                stock_code=stock_code,
                document_kind=document_kind,
                fiscal_year=fiscal_year,
            )
            if page_state == LoadState.READY:
                state = LoadState.READY
                records.extend(page_records)
            elif page_state == LoadState.CONFIRMED_EMPTY:
                if not records:
                    state = LoadState.CONFIRMED_EMPTY
            covered_raw += meta.raw_count
            # Pagination follows raw API totals, never a page whose metadata
            # filter happened to return zero records.
            if meta.totalpages is not None and meta.totalpages > 0:
                if page_num >= meta.totalpages:
                    break
            if meta.raw_count == 0 and not meta.has_more:
                break
            if not meta.has_more and covered_raw >= meta.total:
                break
        return records, state

    def _discover_latest(
        self,
        *,
        stock_code: str,
        org_id: str,
        document_kind: str,
        as_of_date: str,
        fiscal_period: str | None,
        form_type: str | None,
        max_pages: int,
        budget: ProviderAcquisitionBudget | None,
    ) -> tuple[list[CninfoAnnouncement], LoadState]:
        try:
            as_of = date.fromisoformat(as_of_date)
        except (TypeError, ValueError) as exc:
            raise CninfoApiError(
                f"as_of_date must be an ISO calendar date: {as_of_date!r}",
                error_code="client_error",
                retryable=False,
            ) from exc
        window_start = date(as_of.year - LATEST_WINDOW_YEARS, 1, 1)
        cutoff = as_of.isoformat()
        se_date = f"{window_start.isoformat()}~{cutoff}"
        page_cap = max(max_pages, 1)

        records: list[CninfoAnnouncement] = []
        covered_raw = 0
        total_declared: int | None = None
        pages_read = 0
        complete = False
        for page_num in range(1, page_cap + 1):
            body = self._build_request_body(
                stock_code=stock_code,
                org_id=org_id,
                document_kind=document_kind,
                fiscal_year=None,
                page_num=page_num,
                page_size=30,
                se_date=se_date,
            )
            raw_json = self._post_json(body, budget=budget)
            try:
                page_records, meta = self._filter_latest_page(
                    raw_json,
                    stock_code=stock_code,
                    document_kind=document_kind,
                    cutoff=cutoff,
                    fiscal_period=fiscal_period,
                    form_type=form_type,
                )
            except CninfoApiError as exc:
                if exc.error_code != "schema_drift":
                    raise
                # The page is structurally unusable, so coverage of this window
                # can no longer be proven. Report it as an honest gap rather
                # than as a normal (possibly stale) result.
                raise CninfoApiError(
                    f"discovery_incomplete: window {se_date} page {page_num} "
                    f"could not be interpreted: {exc}",
                    error_code="discovery_incomplete",
                    retryable=False,
                ) from exc
            pages_read += 1
            if total_declared is None:
                total_declared = meta.total
            elif meta.total != total_declared:
                raise CninfoApiError(
                    f"discovery_incomplete: window {se_date} page {page_num} "
                    f"totalRecordNum {meta.total} disagrees with {total_declared}",
                    error_code="discovery_incomplete",
                    retryable=False,
                )
            covered_raw += meta.raw_count
            records.extend(page_records)
            final_page = meta.totalpages is not None and page_num >= meta.totalpages
            covered_total = covered_raw >= meta.total
            if final_page or covered_total:
                # Terminal pagination facts must agree. A final page alone
                # does not prove that all declared records were received.
                if (
                    covered_raw != meta.total
                    or meta.has_more
                    or (meta.totalpages is not None and page_num < meta.totalpages)
                ):
                    raise CninfoApiError(
                        f"discovery_incomplete: window {se_date} page {page_num} "
                        f"has conflicting completion metadata: covered "
                        f"{covered_raw}/{meta.total}, totalpages={meta.totalpages}, "
                        f"hasMore={meta.has_more}",
                        error_code="discovery_incomplete",
                        retryable=False,
                    )
                complete = True
                break
            if meta.raw_count == 0 and not meta.has_more:
                break
        if not complete:
            raise CninfoApiError(
                f"discovery_incomplete: window {se_date} covered "
                f"{covered_raw}/{total_declared} raw records in {pages_read} "
                f"page(s) under a {page_cap} page cap",
                error_code="discovery_incomplete",
                retryable=False,
            )
        if not records:
            return records, LoadState.CONFIRMED_EMPTY
        return records, LoadState.READY

    def resolve_org_id(
        self,
        stock_code: str,
        *,
        budget: ProviderAcquisitionBudget | None = None,
    ) -> str | None:
        """Official, budgeted org-id lookup for one stock code.

        One page of the same announcement query the legacy ``src.orgid`` module
        used, issued through ``_post_json`` so the request is streamed through
        the caller's ``ProviderAcquisitionBudget`` with ``timeout`` capped by
        the remaining deadline.  ``None`` means the response did not
        unambiguously identify ``stock_code`` — a wrong security, several
        distinct org ids, or no match are all "unresolved"; the first record is
        never trusted.  Malformed payloads raise ``schema_drift`` and network
        problems keep their explicit ``CninfoApiError`` code/retryability.
        """
        body = urlencode(
            {
                "pageNum": "1",
                "pageSize": "30",
                "tabName": "fulltext",
                "stock": f"{stock_code},",
                "searchkey": stock_code,
                "column": "sse" if stock_code.startswith("6") else "szse",
                "category": "category_ndbg_szsh;",
                "seDate": "",
                "isHLtitle": "true",
            }
        ).encode("utf-8")
        payload = self._post_json(body, budget=budget)
        _total, raw, _totalpages, _has_more = self._validated_page(payload)
        matches: set[str] = set()
        for record in raw:
            if not isinstance(record, dict):
                raise CninfoApiError(
                    "identity record is not a JSON object",
                    error_code="schema_drift",
                    retryable=False,
                )
            if str(record.get("secCode") or "") != stock_code:
                continue
            org_id = record.get("orgId")
            if isinstance(org_id, str) and org_id.strip():
                matches.add(org_id.strip())
        if len(matches) > 1:
            return None
        return matches.pop() if matches else None

    def fetch_pdf(
        self,
        transport_url: str,
        staging_dir: Path,
        *,
        expected_filename: str | None = None,
        budget: ProviderAcquisitionBudget | None = None,
    ) -> Path:
        host = urlparse(transport_url).hostname
        if host not in TRANSPORT_HOSTS:
            raise CninfoApiError(
                f"transport_url host not allowed: {host!r}",
                error_code="transport_url_host_not_allowed",
                retryable=False,
            )
        staging_dir.mkdir(parents=True, exist_ok=True)
        allocated = staging_dir.resolve(strict=True)
        if not expected_filename:
            expected_filename = (
                Path(urlparse(transport_url).path).name or "document.pdf"
            )
        safe_name = expected_filename
        if not safe_name.lower().endswith(".pdf"):
            safe_name = f"{safe_name}.pdf"
        final_path = allocated / safe_name
        part_path = allocated / f"{safe_name}.part"
        if part_path.exists():
            try:
                part_path.unlink()
            except OSError:
                pass
        try:
            request = urllib.request.Request(
                transport_url,
                headers={
                    "User-Agent": self._user_agent,
                    "Accept": "application/pdf,*/*",
                    "Referer": "https://www.cninfo.com.cn/new/disclosure/detail",
                },
                method="GET",
            )
            try:
                if budget is not None:
                    budget.ensure_open()
                    if budget.remaining_response_bytes <= 0:
                        raise AcquisitionBudgetExceeded(
                            "acquisition response-byte budget exhausted"
                        )
                timeout = (
                    self._timeout
                    if budget is None
                    else min(self._timeout, budget.remaining_seconds)
                )
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    status = response.status
                    content_type = response.headers.get("Content-Type", "")
                    if budget is None:
                        body = response.read()
                        body_size = len(body)
                    else:
                        body = b""
                        with part_path.open("wb") as stream:
                            body_size = self._copy_bounded_response(
                                response, stream, budget
                            )
            except urllib.error.HTTPError as exc:
                raise CninfoApiError(
                    f"transport HTTP {exc.code}: {exc.reason}",
                    error_code="upstream_unavailable",
                    retryable=True,
                    http_status=exc.code,
                ) from exc
            except urllib.error.URLError as exc:
                raise CninfoApiError(
                    f"transport network: {exc.reason}",
                    error_code="upstream_unavailable",
                    retryable=True,
                ) from exc
            except TimeoutError as exc:
                raise CninfoApiError(
                    f"transport timeout: {exc}",
                    error_code="upstream_timeout",
                    retryable=True,
                ) from exc
            if status < 200 or status >= 300:
                raise CninfoApiError(
                    f"transport HTTP {status}",
                    error_code="upstream_unavailable",
                    retryable=True,
                    http_status=status,
                )
            # Reject HTML challenge pages even with 200 status
            if "text/html" in (content_type or "").lower():
                raise CninfoApiError(
                    "transport returned HTML (likely challenge/redirect page)",
                    error_code="upstream_unavailable",
                    retryable=True,
                    http_status=status,
                )
            if budget is None:
                part_path.write_bytes(body)
            if body_size <= C.MIN_FILE_SIZE:
                raise CninfoApiError(
                    f"content too small: {body_size} bytes <= MIN_FILE_SIZE={C.MIN_FILE_SIZE}",
                    error_code="content_too_small",
                    retryable=False,
                    http_status=status,
                )
            if budget is None:
                prefix = body[:5]
            else:
                with part_path.open("rb") as stream:
                    prefix = stream.read(5)
            if prefix != b"%PDF-":
                raise CninfoApiError(
                    "content failed PDF magic validation (expecting %PDF- prefix)",
                    error_code="pdf_magic_invalid",
                    retryable=False,
                    http_status=status,
                )
            # Atomic OS-level rename into final destination
            if final_path.exists():
                final_path.unlink()
            part_path.replace(final_path)
            return final_path
        except BaseException:
            if part_path.exists():
                try:
                    part_path.unlink()
                except OSError:
                    pass
            raise

    # ── INTERNAL: request construction ─────────────────────────────────

    def _build_request_body(
        self,
        *,
        stock_code: str,
        org_id: str,
        document_kind: str,
        page_num: int,
        page_size: int,
        fiscal_year: int | None = None,
        se_date: str | None = None,
    ) -> bytes:
        sc = stock_code.lstrip()
        # Shanghai stock codes start with 6; everything else defaults to Shenzhen.
        column = "sse" if sc.startswith("6") else "szse"
        category = _CATEGORY_PER_KIND.get(document_kind, "category_ndbg_szsh")
        if se_date is None:
            # Annual reports for FY{N} are typically published in Mar-Apr of
            # FY{N+1}; use [fy-01-01, fy+1-12-31] window so independent clients
            # capture them. latest callers pass an explicit as-of window instead.
            if isinstance(fiscal_year, bool) or not isinstance(fiscal_year, int):
                raise CninfoApiError(
                    "exact discovery requires an integer fiscal_year",
                    error_code="client_error",
                    retryable=False,
                )
            se_date = f"{fiscal_year}-01-01~{fiscal_year + 1}-12-31"
        params = {
            "pageNum": str(page_num),
            "pageSize": str(page_size),
            "column": column,
            "tabName": "fulltext",
            "stock": f"{stock_code},{org_id}",
            "seDate": se_date,
            "category": category,
            "isHLtitle": "true",
        }
        return urlencode(params).encode("utf-8")

    # ── INTERNAL: HTTP POST + JSON parsing ───────────────────────────────

    def _post_json(
        self,
        body_bytes: bytes,
        *,
        budget: ProviderAcquisitionBudget | None = None,
    ) -> dict:
        request = urllib.request.Request(
            ANNOUNCEMENT_API_ENDPOINT,
            data=body_bytes,
            method="POST",
            headers={
                "User-Agent": self._user_agent,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": "https://www.cninfo.com.cn/new/disclosure/stock",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        try:
            if budget is not None:
                budget.ensure_open()
                if budget.remaining_response_bytes <= 0:
                    raise AcquisitionBudgetExceeded(
                        "acquisition response-byte budget exhausted"
                    )
            timeout = (
                self._timeout
                if budget is None
                else min(self._timeout, budget.remaining_seconds)
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = response.status
                body = (
                    response.read()
                    if budget is None
                    else self._read_bounded_response(response, budget)
                )
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise CninfoApiError(
                    f"API rate limited (429): {exc.reason}",
                    error_code="rate_limited",
                    retryable=True,
                    http_status=429,
                ) from exc
            if 500 <= exc.code < 600:
                raise CninfoApiError(
                    f"API upstream error (HTTP {exc.code}): {exc.reason}",
                    error_code="upstream_unavailable",
                    retryable=True,
                    http_status=exc.code,
                ) from exc
            if 400 <= exc.code < 500:
                raise CninfoApiError(
                    f"API client error (HTTP {exc.code}): {exc.reason}",
                    error_code="client_error",
                    retryable=False,
                    http_status=exc.code,
                ) from exc
            raise CninfoApiError(
                f"API HTTP {exc.code}: {exc.reason}",
                error_code="upstream_unavailable",
                retryable=True,
                http_status=exc.code,
            ) from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", str(exc))
            # URLError wraps gaierror/timeout/etc; string-sniff for DNS
            reason_str = str(reason)
            if "getaddrinfo" in reason_str or "name or service" in reason_str.lower():
                raise CninfoApiError(
                    f"API DNS failure: {reason}",
                    error_code="upstream_unavailable",
                    retryable=True,
                ) from exc
            if "timed out" in reason_str.lower():
                raise CninfoApiError(
                    f"API timeout: {reason}",
                    error_code="upstream_timeout",
                    retryable=True,
                ) from exc
            raise CninfoApiError(
                f"API network: {reason}",
                error_code="upstream_unavailable",
                retryable=True,
            ) from exc
        except TimeoutError as exc:
            raise CninfoApiError(
                f"API timeout: {exc}",
                error_code="upstream_timeout",
                retryable=True,
            ) from exc
        if status != 200:
            raise CninfoApiError(
                f"API HTTP {status}",
                error_code="upstream_unavailable",
                retryable=True,
                http_status=status,
            )
        try:
            payload = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise CninfoApiError(
                f"API non-JSON response (first 200 chars: {body[:200]!r})",
                error_code="schema_drift",
                retryable=False,
                http_status=status,
            ) from exc
        if not isinstance(payload, dict):
            raise CninfoApiError(
                f"API root must be JSON object, got {type(payload).__name__}",
                error_code="schema_drift",
                retryable=False,
                http_status=status,
            )
        return payload

    @staticmethod
    def _declared_length(response: Any) -> int | None:
        raw = response.headers.get("Content-Length")
        if raw is None:
            return None
        try:
            length = int(raw)
        except (TypeError, ValueError):
            return None
        return length if length >= 0 else None

    @classmethod
    def _copy_bounded_response(
        cls,
        response: Any,
        destination: Any,
        budget: ProviderAcquisitionBudget,
    ) -> int:
        declared = cls._declared_length(response)
        if declared is not None and declared > budget.remaining_response_bytes:
            raise AcquisitionBudgetExceeded(
                "declared response size exceeds remaining response-byte budget"
            )
        total = 0
        while declared is None or total < declared:
            budget.ensure_open()
            remaining = budget.remaining_response_bytes
            if remaining <= 0:
                # Without a declared body length, probing EOF would require
                # reading beyond the cap. Refuse conservatively instead.
                raise AcquisitionBudgetExceeded(
                    "response-byte budget exhausted before body completion"
                )
            requested = min(_READ_CHUNK_BYTES, remaining)
            chunk = response.read(requested)
            if not chunk:
                break
            if len(chunk) > requested:
                raise AcquisitionBudgetExceeded(
                    "provider transport returned more bytes than requested"
                )
            budget.consume_response_bytes(len(chunk))
            destination.write(chunk)
            total += len(chunk)
        if declared is not None and total != declared:
            raise CninfoApiError(
                "response ended before declared Content-Length",
                error_code="upstream_unavailable",
                retryable=True,
            )
        return total

    @classmethod
    def _read_bounded_response(
        cls, response: Any, budget: ProviderAcquisitionBudget
    ) -> bytes:
        from io import BytesIO

        buffer = BytesIO()
        cls._copy_bounded_response(response, buffer, budget)
        return buffer.getvalue()

    # ── INTERNAL: schema-strict filtering ───────────────────────────────

    @staticmethod
    def _validated_page(payload: dict) -> tuple[int, list, int | None, bool]:
        """Validate one page and return ``(total, raw records, totalpages, hasMore)``."""
        if "totalRecordNum" not in payload:
            raise CninfoApiError(
                "API response missing required 'totalRecordNum'",
                error_code="schema_drift",
                retryable=False,
            )
        total = payload.get("totalRecordNum")
        if not isinstance(total, int):
            # Some responses use string; coerce defensively.
            try:
                total = int(total)
            except (TypeError, ValueError):
                raise CninfoApiError(
                    f"API 'totalRecordNum' must be int, got {type(total).__name__}",
                    error_code="schema_drift",
                    retryable=False,
                )
        announcements = payload.get("announcements")
        # The cninfo historical-announcement API returns ``announcements=null``
        # when the requested page has no more matches (totalRecordNum==0 on
        # that page). Phase 8 live probe confirmed this. Treat such empty
        # page as CONFIRMED_EMPTY, not schema drift — only require a list when
        # the API claims actual records on this page.
        if announcements is None:
            if total == 0:
                announcements = []
            else:
                raise CninfoApiError(
                    "API 'announcements' is null but totalRecordNum>0",
                    error_code="schema_drift",
                    retryable=False,
                )
        elif not isinstance(announcements, list):
            raise CninfoApiError(
                f"API 'announcements' must be a list, got {type(announcements).__name__}",
                error_code="schema_drift",
                retryable=False,
            )
        raw_totalpages = payload.get("totalpages")
        try:
            totalpages = int(raw_totalpages) if raw_totalpages is not None else None
        except (TypeError, ValueError):
            totalpages = None
        if totalpages is not None and totalpages <= 0:
            totalpages = None
        return total, announcements, totalpages, bool(payload.get("hasMore"))

    def _filter_page(
        self,
        payload: dict,
        *,
        stock_code: str,
        document_kind: str,
        fiscal_year: int,
    ) -> tuple[list[CninfoAnnouncement], LoadState, _PageMeta]:
        # Local import to keep cninfo_api self-contained and avoid a circular
        # import surface (company_wiki_adapter does not import cninfo_api at
        # module load; it resolves at discover() call time via the injected
        # client).
        from .company_wiki_adapter import _report_metadata

        total, raw, totalpages, has_more = self._validated_page(payload)
        meta = _PageMeta(
            total=total,
            raw_count=len(raw),
            totalpages=totalpages,
            has_more=has_more,
        )
        # Empty signal: total == 0 → CONFIRMED_EMPTY (regardless of announcements list)
        if total == 0:
            return [], LoadState.CONFIRMED_EMPTY, meta

        out: list[CninfoAnnouncement] = []
        for record in raw:
            parsed = self._parse_announcement(record, stock_code=stock_code)
            kind, year, _form_type, _period, _amended = _report_metadata(parsed.title)
            if year != fiscal_year or kind != document_kind:
                continue
            out.append(parsed)
        # Total > 0 means valid API response; READY even if filter yields 0.
        return out, LoadState.READY, meta

    def _filter_announcements_from_response(
        self,
        payload: dict,
        *,
        stock_code: str,
        document_kind: str,
        fiscal_year: int,
    ) -> tuple[list[CninfoAnnouncement], LoadState]:
        records, state, _meta = self._filter_page(
            payload,
            stock_code=stock_code,
            document_kind=document_kind,
            fiscal_year=fiscal_year,
        )
        return records, state

    def _filter_latest_page(
        self,
        payload: dict,
        *,
        stock_code: str,
        document_kind: str,
        cutoff: str,
        fiscal_period: str | None,
        form_type: str | None,
    ) -> tuple[list[CninfoAnnouncement], _PageMeta]:
        from .company_wiki_adapter import _report_metadata

        total, raw, totalpages, has_more = self._validated_page(payload)
        meta = _PageMeta(
            total=total,
            raw_count=len(raw),
            totalpages=totalpages,
            has_more=has_more,
        )
        if total == 0:
            return [], meta

        out: list[CninfoAnnouncement] = []
        for record in raw:
            parsed = self._parse_announcement(record, stock_code=stock_code)
            kind, year, form, period, _amended = _report_metadata(parsed.title)
            if kind != document_kind or year is None:
                continue
            if parsed.sec_code != stock_code:
                continue
            if parsed.filing_date > cutoff:
                continue
            if not parsed.title.strip() or not parsed.adjunct_url.strip():
                continue
            if fiscal_period is not None and period != fiscal_period:
                continue
            if form_type is not None and form != form_type:
                continue
            out.append(parsed)
        return out, meta

    def _parse_announcement(
        self,
        record: dict,
        *,
        stock_code: str,
    ) -> CninfoAnnouncement:
        try:
            announcement_id = str(record["announcementId"])
            announcement_time_ms = int(record["announcementTime"])
            title = str(record["announcementTitle"])
            sec_code = str(record.get("secCode") or stock_code)
            sec_name = str(record.get("secName") or "")
            org_id = str(record.get("orgId") or "")
            adjunct_type = str(record.get("adjunctType") or "PDF")
            adjunct_url = str(record["adjunctUrl"])
        except (KeyError, ValueError, TypeError) as exc:
            raise CninfoApiError(
                f"announcement record schema drift: {exc}",
                error_code="schema_drift",
                retryable=False,
            ) from exc
        # Epoch milliseconds are UTC instants; publication dates and the
        # official detail query use China disclosure time (UTC+08:00).
        dt = datetime.fromtimestamp(announcement_time_ms / 1000.0, tz=timezone(timedelta(hours=8)))
        filing_date = dt.date().isoformat()
        transport_url = f"https://static.cninfo.com.cn/{adjunct_url.lstrip('/')}"
        # detail URL: human-openable official detail page on www.cninfo.com.cn
        detail_time = dt.strftime("%Y-%m-%d %H:%M")
        detail_url = (
            f"{DETAIL_PAGE_BASE}?stockCode={sec_code}"
            f"&announcementId={announcement_id}"
            f"&announcementTime={quote(detail_time, safe='/:')}"
        )
        return CninfoAnnouncement(
            announcement_id=announcement_id,
            filing_date=filing_date,
            title=title,
            sec_code=sec_code,
            sec_name=sec_name,
            org_id=org_id,
            announcement_time_ms=announcement_time_ms,
            adjunct_type=adjunct_type,
            adjunct_url=adjunct_url,
            transport_url=transport_url,
            detail_url=detail_url,
        )


__all__ = [
    "CninfoAnnouncementClient",
    "CninfoAnnouncement",
    "CninfoApiError",
    "ANNOUNCEMENT_API_ENDPOINT",
    "TRANSPORT_HOSTS",
]


# Backwards-compat alias for callers expecting the historical endpoint name.
AnnounceMentApiEndpoint = ANNOUNCEMENT_API_ENDPOINT
