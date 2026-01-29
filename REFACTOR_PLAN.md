# Refactoring Plan: StockInfoDownloader

## Objective
Implement architectural recommendations to consolidate factories, clean up dead code, and unify configuration management.

## Phase 1: Consolidate Factories & Cleanup Dead Code
**Status:** Completed
**Actions Taken:**
1. Identified `src/services/downloader_factory.py` as broken dead code (imported non-existent modules).
2. Deleted `src/services/downloader_factory.py`.
3. Verified system stability with E2E tests (Passed).

## Phase 2: Deprecation Strategy
**Status:** Completed
**Actions Taken:**
1. Added `DeprecationWarning` to `CninfoDownloaderAdapter`, `DownloadServiceV1Adapter`, `DownloadServiceV2Adapter`, and `RefactoredDownloaderAdapter` in `src/adapters/legacy_downloader_adapter.py`.
2. This ensures developers are warned when using legacy interfaces.

## Phase 3: Cleanup & Optimization
**Status:** Completed
**Actions Taken:**
1. **Microservice Repair:** Updated `microservices/download-service/download_service.py` to remove dependency on the non-existent `downloader_v2.py` and use `UnifiedDownloader` directly.
2. **Legacy Script Refactor:** Updated `cninfo_activity_downloader.py` to use `UnifiedDownloader` directly via the factory, proving the new architecture supports legacy use cases.
3. **Code Organization:** Extracted debug tracking logic (`DebugMarker`, etc.) from `src/services/unified_downloader.py` into `src/core/debug_tracker.py` to improve readability and separation of concerns.
4. **Import Cleanup:** Removed unused/broken imports in `tests/e2e/test_expected_data_validation.py`.

## Phase 4: Unified Configuration
**Status:** Deferred / Managed
**Findings:**
- `src/core/config.py` (ConfigManager) and `src/config/downloader_config.py` (DownloaderConfigManager) coexist.
- `src/factory/downloader_factory.py` effectively bridges these two config systems.
- **Decision:** Merging these fully would require significant refactoring of typed config usage across the codebase. The current "bridge" pattern in the factory is stable and sufficient.
