# StockInfoDownloader

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-557%2B-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-40%25-yellow.svg)]()

> A highly automated download engine for fetching stock information from Cninfo (巨潮资讯网).

---

## Table of Contents

- [Quick Start](#quick-start)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Testing](#-testing)
- [Architecture](#-architecture)
- [Docker Deployment](#-docker-deployment)
- [Development](#-development)
- [Configuration](#configuration)
- [Contributing](#-contributing)

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
playwright install

# Download with default config
python main.py 000001

# Parallel download multiple companies
python main.py --parallel --workers 3
```

---

## Features

| Feature | Description |
|---------|-------------|
| Dual Browser Engine | Playwright (modern, fast) & Selenium (stable, compatible) |
| Configuration-Driven | JSON config with multi-company, multi-page support |
| Anti-Crawler | Built-in detection, rate limiting, session management |
| Test Coverage | 557+ test cases (unit + integration + E2E) |
| Microservice Architecture | Docker containerization support |
| Structured Logging | Comprehensive logging and error tracking |

---

## Project Structure

```
StockInfoDownloader/
├── main.py                      # Unified entry point
├── cninfo_activity_downloader.py # Legacy entry (compat)
├── config.json                  # Main config
├── src/                         # Core source
│   ├── core/                    # Infrastructure (config, logging, exceptions)
│   ├── services/                # Business services (UnifiedDownloader)
│   ├── web/                     # Browser strategies (Playwright/Selenium)
│   ├── factory/                 # Factory pattern
│   └── adapters/                # Adapter layer (legacy compat)
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests (540+)
│   ├── integration/             # Integration tests
│   ├── e2e/                     # End-to-end tests
│   └── fake_browser_strategy.py # Fake test double
├── docs/                        # Documentation
├── microservices/               # Microservice architecture
└── docker-compose.yml           # Docker orchestration
```

---

## Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# E2E tests (Playwright)
python tests/e2e/official_e2e_test.py --browser-strategy=playwright

# E2E tests (Selenium)
python tests/e2e/official_e2e_test.py --browser-strategy=selenium

# With coverage report
pytest --cov=src --cov-report=html
```

### Phase Exit Requirement

> **All E2E tests must pass (100%) before completing each phase.**

---

## Architecture

### Layered Architecture

```
Application Layer (main.py, CLI)
    ↓
Factory Layer (downloader_factory.py) ← Dependency Injection
    ↓
Service Layer (UnifiedDownloader) ← Core Business Logic
    ↓
Strategy Layer (PlaywrightStrategy, SeleniumStrategy) ← Strategy Pattern
    ↓
Infrastructure Layer (Config, Logger, Exceptions)
```

### Design Patterns

| Pattern | Implementation |
|---------|----------------|
| Strategy | `BrowserStrategy` interface, Playwright/Selenium interchangeable |
| Factory | `DownloaderFactory` unified creation |
| Adapter | `LegacyDownloaderAdapter` for backward compatibility |
| Singleton | `ConfigManager` unified configuration |

---

## Docker Deployment

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f download-service
```

### Services

| Service | Port |
|---------|------|
| API Gateway | 8000 |
| Download Service | 8001 |
| Cache Service | 8002 |
| Error Service | 8003 |
| Config Service | 8004 |
| Prometheus | 9090 |
| Grafana | 3000 |

---

## Development

### Code Standards

- **Naming**: Classes `PascalCase`, functions/variables `snake_case`, constants `UPPER_SNAKE_CASE`
- **Type Annotations**: All public methods must have type annotations
- **Docstrings**: Classes and methods must have docstrings
- **Error Handling**: Catch specific exceptions, avoid empty `except` blocks

### Code Quality Tools

```bash
# Type checking
mypy src/ --ignore-missing-imports

# Code formatting
black src/ tests/
isort src/ tests/
```

---

## Configuration

### Example `config.json`

```json
{
  "stock_code": "000001",
  "save_dir": "downloads",
  "headless": true,
  "browser": {
    "strategy": "playwright"
  },
  "pages": [
    {"name": "Research", "suffix": "research"},
    {"name": "Periodic Reports", "suffix": "periodicReports"}
  ]
}
```

### Configuration Reference

- [Configuration Guide](docs/guides/CONFIGURATION_REFERENCE.md)
- [Migration Guide](docs/guides/MIGRATION_GUIDE.md)
- [Browser Strategy Guide](docs/guides/BROWSER_STRATEGY_GUIDE.md)
- [Debugging Guide](docs/guides/DEBUGGING_GUIDE.md)
- [Code Standards](docs/core/CODE_STANDARDS.md)

---

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

> **Important**: Ensure all E2E tests pass before submitting!

---

## Project Stats

| Metric | Value |
|--------|-------|
| Total Code | ~2,180 KB (~70,000+ lines) |
| Source Files | 86 Python files |
| Test Files | 116 Python files |
| Test/Source Ratio | 1.35:1 |
| Documentation | 36 Markdown files |
| Overall Score | **8.38/10** |

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [Playwright](https://playwright.dev/) - Modern browser automation
- [Selenium](https://www.selenium.dev/) - Classic browser automation
- [pytest](https://docs.pytest.org/) - Powerful testing framework

---

<p align="center">
  <b>StockInfoDownloader</b> - Professional Stock Information Download Engine
</p>
