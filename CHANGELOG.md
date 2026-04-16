# Changelog

## v2.0.0 (2026-04-16)

Initial release of the rewritten Stock Downloader.

### Changes from V1
- Reduced from 29,335 lines to ~2,000 lines
- Dropped Selenium, Playwright only
- Removed microservice architecture
- Removed 205 classes → ~15 classes
- Removed 32 config files → 2 config files
- Clean download logic with 3-step fallback (direct download → event capture → button click)

### Features
- Playwright browser automation
- Auto org_id resolution (local mapping + web crawling)
- Stock name lookup (Tencent Finance API)
- Multi-page download (forward and reverse order)
- Keyword filtering with date matching
- Skip existing files
- Anti-crawler random delays

### Tests
- 29 unit tests (config, models, mapping, downloader, storage)
- 24 E2E behavior tests (pagination, skip existing files)
- Official E2E test passing (3/3 verified files)

### Preserved from V1
- E2E test suite (adapted import paths)
- All download functionality
- org_id mapping + crawling
- Stock name lookup
- config_e2e_official.json format compatibility
