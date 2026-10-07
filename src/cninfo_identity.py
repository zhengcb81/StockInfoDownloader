"""Read-only org-id cache plus bounded official org-id resolution.

The company-wiki provider resolves an org id in three steps and never touches
the browser-backed ``StockDownloader.mapping`` / ``src.orgid`` chain:

1. the org id already present on the request;
2. the historical read-only ``stock_orgid_mapping.json`` cache, located with
   the exact candidate order the legacy ``MappingManager`` used;
3. one official cninfo identity query issued by the same
   ``CninfoAnnouncementClient`` and charged to the same
   ``ProviderAcquisitionBudget`` as the announcement pages.

A cache hit is only a *clue*: the official candidate is still validated against
security code, period, publication date and completeness by the announcement
filters.  Nothing here ever writes back to the cache file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import constants as C
from .logger import log
from .string_utils import standardize_stock_code

if TYPE_CHECKING:
    from .acquisition_budget import ProviderAcquisitionBudget
    from .cninfo_api import CninfoAnnouncementClient


def candidate_paths(mapping_file: str | Path | None = None) -> list[Path]:
    """Legacy cache candidate order: explicit file, then src, cwd, configs."""
    if mapping_file:
        return [Path(mapping_file)]
    return [
        Path(__file__).parent / C.DEFAULT_MAPPING_FILE,
        Path(C.DEFAULT_MAPPING_FILE),
        Path("configs") / C.DEFAULT_MAPPING_FILE,
    ]


def _select_path(mapping_file: str | Path | None) -> Path:
    paths = candidate_paths(mapping_file)
    if mapping_file:
        return paths[0]
    return next((path for path in paths if path.exists()), paths[0])


def _read_entries(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.warning(f"Failed to read org-id cache {path}: {exc}")
        return {}
    if not isinstance(raw, dict):
        log.warning(f"Ignoring org-id cache {path}: root is not a JSON object")
        return {}
    entries: dict[str, str] = {}
    for stock_code, item in raw.items():
        if not isinstance(item, dict):
            continue
        org_id = item.get("orgId") or item.get("org_id")
        if not isinstance(org_id, str) or not org_id.strip():
            continue
        entries[str(stock_code)] = org_id.strip()
    return entries


class LocalOrgIdCache:
    """Read-only ``stock_code → org_id`` lookup over the legacy cache files."""

    def __init__(self, mapping_file: str | Path | None = None) -> None:
        self._path = _select_path(mapping_file)
        self._entries: dict[str, str] | None = None

    @property
    def path(self) -> Path:
        return self._path

    def get_org_id(self, stock_code: str) -> str | None:
        code = standardize_stock_code(stock_code)
        if not code:
            return None
        if self._entries is None:
            self._entries = _read_entries(self._path)
        return self._entries.get(code)


class OrgIdIdentityResolver:
    """Resolves org id from request → local cache → budgeted official query."""

    def __init__(
        self,
        *,
        client: "CninfoAnnouncementClient",
        cache: LocalOrgIdCache | None = None,
    ) -> None:
        self._client = client
        self._cache = cache

    @property
    def cache(self) -> LocalOrgIdCache:
        if self._cache is None:
            self._cache = LocalOrgIdCache()
        return self._cache

    def resolve_org_id(
        self,
        stock_code: str,
        *,
        budget: "ProviderAcquisitionBudget | None" = None,
    ) -> str | None:
        code = standardize_stock_code(stock_code)
        if not code:
            return None
        cached = self.cache.get_org_id(code)
        if cached:
            return cached
        return self._client.resolve_org_id(code, budget=budget)


__all__ = [
    "LocalOrgIdCache",
    "OrgIdIdentityResolver",
    "candidate_paths",
]
