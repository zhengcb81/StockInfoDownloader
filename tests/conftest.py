import sys
import os
from pathlib import Path

# Legacy path injection for tests that need it
legacy_path = str(Path(__file__).parent.parent / "src" / "tools" / "legacy")
if legacy_path not in sys.path:
    sys.path.insert(0, legacy_path)

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "regression: Regression tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "network: Tests requiring network access")
    config.addinivalue_line("markers", "browser: Tests requiring browser")
    config.addinivalue_line("markers", "selenium: Tests using Selenium")
    config.addinivalue_line("markers", "playwright: Tests using Playwright")