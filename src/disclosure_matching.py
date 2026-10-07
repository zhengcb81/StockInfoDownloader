"""Pure title-filter helpers for the provider runtime.

``src.downloader`` owns browser automation, a failed-download log and a lazy
Playwright handle; the company-wiki provider only needs these two string
predicates, so they live here with byte-identical behaviour.  The differential
counterexample in ``tests/unit/test_g5_provider_runtime.py`` proves the
equivalence against the historical downloader helpers.
"""

from __future__ import annotations

import re
from typing import List, Optional


def matches_excluded(text: str, keywords: Optional[List[str]]) -> bool:
    """Check if text matches any excluded keyword."""
    if not keywords:
        return False
    cleaned = "".join(text.split()).lower()
    for k in keywords:
        ck = "".join(k.split()).lower()
        if ck in cleaned:
            return True
    return False


def matches_keywords(text: str, keywords: Optional[List[str]]) -> bool:
    """Check if text matches any keyword.

    Supports date-based matching: if keyword contains an 8-digit date (e.g.
    "公告20250725"), extracts the date and checks if it appears in the text.
    """
    if not keywords:
        return True
    cleaned = "".join(text.split()).lower()
    for k in keywords:
        ck = "".join(k.split()).lower()
        if ck in cleaned:
            return True
        date_match = re.search(r"\d{8}", k)
        if date_match and date_match.group() in cleaned:
            return True
    return False


_matches_excluded = matches_excluded
_matches_keywords = matches_keywords

__all__ = ["matches_excluded", "matches_keywords"]
