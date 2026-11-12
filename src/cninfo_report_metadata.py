"""Pure CNINFO report metadata domain.

Both the announcement API reader and the company-wiki adapter need to turn an
official announcement title into a document kind / fiscal year / form type /
period / amendment flag.  That is a pure string decision: it must not depend on
the adapter, the downloader, the browser or Playwright.

This module is the single owner of that decision.  ``src.cninfo_api`` (lower
layer) and ``src.company_wiki_adapter`` (upper layer) both import *down* into
it, so the dependency direction stays API → domain ← adapter.
"""

from __future__ import annotations

import re

__all__ = ["report_metadata"]

# A fiscal year is a 4-digit 20xx number immediately followed by 年.
_YEAR_RE = re.compile(r"(?<!\d)(20\d{2})(?=年)")

_AMENDED_TOKENS = ("修订", "更正", "更新后", "修正版")


def report_metadata(title: str) -> tuple[str, int | None, str, str, bool]:
    """Classify an announcement title.

    Returns ``(document_kind, fiscal_year, form_type, fiscal_period, amended)``.

    ``document_kind`` is one of ``annual_report`` / ``semi_annual_report`` /
    ``quarterly_report`` / ``other``; ``fiscal_year`` is ``None`` when the title
    does not state one (callers must never invent it); ``fiscal_period`` is
    ``FY`` / ``H1`` / ``Q1`` / ``Q3`` / ``UNKNOWN``.
    """
    compact = "".join(title.split())
    year_match = _YEAR_RE.search(compact)
    fiscal_year = int(year_match.group(1)) if year_match else None
    amended = any(token in compact for token in _AMENDED_TOKENS)
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
