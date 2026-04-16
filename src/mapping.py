"""Mapping manager — maps stock codes to org_ids and stock names.

Supports local JSON lookup + automatic web crawling when local data is missing.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .exceptions import MappingError
from .logger import log
from .models import OrgIdMapping
from .storage import JsonStorage
from .string_utils import standardize_stock_code


class MappingManager:
    """Manages stock_code → org_id mappings with auto-fetch from web."""

    def __init__(
        self,
        mapping_file: Optional[str] = None,
        auto_fetch: bool = True,
        browser_strategy: Optional[Any] = None,
        browser_strategy_type: str = "playwright",
    ):
        self._auto_fetch = auto_fetch
        self._browser_strategy = browser_strategy
        self._browser_strategy_type = browser_strategy_type
        self._mappings: Dict[str, OrgIdMapping] = {}

        # Resolve mapping file path
        if mapping_file:
            self.mapping_file = Path(mapping_file)
        else:
            candidates = [
                Path(__file__).parent / "stock_orgid_mapping.json",
                Path("stock_orgid_mapping.json"),
                Path("configs/stock_orgid_mapping.json"),
            ]
            self.mapping_file = next(
                (p for p in candidates if p.exists()), candidates[0]
            )

        self.storage = JsonStorage(str(self.mapping_file))
        self._load()

    # ── Public API ────────────────────────────────────────────────────

    @property
    def mapping_data(self) -> Dict[str, OrgIdMapping]:
        return self._mappings.copy()

    def get_org_id(
        self, stock_code: str, force_refresh: bool = False
    ) -> Optional[str]:
        """Get org_id for a stock code. Crawls from web if not found locally."""
        code = standardize_stock_code(stock_code)
        if not code:
            return None

        # 1. Local cache
        if not force_refresh and code in self._mappings:
            return self._mappings[code].org_id

        # 2. Crawl from web
        if self._auto_fetch:
            log.info(f"Local mapping not found for {code}, crawling from web...")
            org_id = self._crawl_org_id(code)
            if org_id:
                return org_id

        return None

    def get_stock_name(
        self, stock_code: str, auto_crawl: Optional[bool] = None
    ) -> Optional[str]:
        """Get stock name. Crawls from web if not found locally."""
        code = standardize_stock_code(stock_code)
        if not code:
            return None

        # 1. Local cache
        if code in self._mappings:
            name = self._mappings[code].stock_name
            if name and not name.startswith("Stock_"):
                return name

        # 2. Crawl from web
        should_crawl = auto_crawl if auto_crawl is not None else self._auto_fetch
        if should_crawl:
            name = self._crawl_stock_name(code)
            if name:
                # Update existing mapping if present
                if code in self._mappings:
                    self._mappings[code].stock_name = name
                    self._save()
                return name

        return None

    def add_mapping(
        self,
        stock_code: str,
        org_id: str,
        stock_name: str,
        source: str = "auto",
        confidence: float = 0.8,
    ) -> bool:
        """Add a new mapping. Returns False if already exists or save fails."""
        code = standardize_stock_code(stock_code)
        if not code or code in self._mappings:
            return False
        self._mappings[code] = OrgIdMapping(
            stock_code=code,
            org_id=org_id,
            stock_name=stock_name,
            source=source,
            confidence=confidence,
        )
        return self._save()

    def remove_mapping(self, stock_code: str) -> bool:
        """Remove a mapping."""
        code = standardize_stock_code(stock_code)
        if code and code in self._mappings:
            del self._mappings[code]
            return self._save()
        return False

    def reload(self) -> bool:
        """Reload mappings from file."""
        try:
            self._load()
            return True
        except Exception:
            return False

    def get_all_stock_codes(self) -> List[str]:
        return list(self._mappings.keys())

    def get_statistics(self) -> Dict[str, Any]:
        sources: Dict[str, int] = {}
        for m in self._mappings.values():
            sources[m.source] = sources.get(m.source, 0) + 1
        return {
            "total": len(self._mappings),
            "source_distribution": sources,
        }

    # ── Internal ──────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load mappings from JSON file."""
        self._mappings = {}
        try:
            data = self.storage.load()
        except Exception as e:
            log.error(f"Failed to load mapping: {e}")
            return

        if not data:
            return

        for stock_code, item in data.items():
            try:
                if not isinstance(item, dict):
                    continue
                org_id = item.get("orgId") or item.get("org_id")
                stock_name = item.get("name") or item.get("stock_name") or "Unknown"
                if not org_id:
                    continue

                mapping = OrgIdMapping(
                    stock_code=stock_code,
                    org_id=org_id,
                    stock_name=stock_name,
                    source=item.get("source", "auto"),
                    confidence=float(item.get("confidence", 0.8)),
                )
                # Handle timestamp
                if "timestamp" in item:
                    try:
                        mapping.last_updated = datetime.fromtimestamp(
                            item["timestamp"]
                        )
                    except (TypeError, ValueError, OSError):
                        pass
                elif "last_updated" in item:
                    try:
                        mapping.last_updated = datetime.fromisoformat(
                            item["last_updated"]
                        )
                    except (ValueError, TypeError):
                        pass

                self._mappings[stock_code] = mapping
            except Exception as e:
                log.warning(f"Skipping invalid mapping {stock_code}: {e}")

        log.info(f"Loaded {len(self._mappings)} mappings from {self.mapping_file}")

    def _save(self) -> bool:
        """Save mappings to JSON file."""
        data = {}
        for code, m in self._mappings.items():
            data[code] = {
                "orgId": m.org_id,
                "name": m.stock_name,
                "source": m.source,
                "timestamp": m.last_updated.timestamp(),
                "confidence": m.confidence,
            }
        return self.storage.save(data)

    def _crawl_org_id(self, stock_code: str) -> Optional[str]:
        """Crawl org_id from web and save to local mapping."""
        try:
            from .orgid import OrgIdCrawler

            crawler = OrgIdCrawler(
                browser_strategy=self._browser_strategy,
                strategy_type=self._browser_strategy_type,
            )
            org_id = crawler.get_org_id(stock_code)
            if org_id:
                log.info(f"Crawled org_id: {stock_code} → {org_id}")
                stock_name = self._crawl_stock_name(stock_code) or f"Stock_{stock_code}"
                self.add_mapping(
                    stock_code=stock_code,
                    org_id=org_id,
                    stock_name=stock_name,
                    source="auto",
                    confidence=0.7,
                )
                return org_id
        except Exception as e:
            log.error(f"Failed to crawl org_id for {stock_code}: {e}")
        return None

    def _crawl_stock_name(self, stock_code: str) -> Optional[str]:
        """Crawl stock name from web."""
        try:
            from .stock import get_stock_name

            return get_stock_name(stock_code)
        except Exception as e:
            log.debug(f"Failed to crawl stock name for {stock_code}: {e}")
            return None
