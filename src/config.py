"""Configuration loader — reads JSON config with sensible defaults."""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import constants as C
from .exceptions import ConfigError
from .logger import log


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """Load configuration from a JSON file.

    Returns a dict with all expected keys populated with defaults if missing.
    Raises ConfigError if the file exists but cannot be parsed.
    """
    path = Path(config_path)
    if not path.exists():
        log.warning(f"Config file not found: {config_path}, using defaults")
        return _default_config()

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise ConfigError(f"Cannot parse config file {config_path}: {e}")

    return _merge_defaults(raw)


def _default_config() -> Dict[str, Any]:
    """Return default configuration."""
    return {
        "save_dir": C.DEFAULT_SAVE_DIR,
        "headless": True,
        "max_retries": 3,
        "timeout_seconds": 180,
        "browser": {"strategy": "playwright", "headless": True},
        "download": {
            "max_pages": 5,
            "download_delay": 0.5,
        },
        "anti_crawler": {
            "enabled": True,
            "base_delay": 1.0,
            "random_delay_range": list(C.DEFAULT_DELAY_RANGE),
        },
        "logging": {
            "level": "INFO",
            "log_to_file": True,
            "log_file": f"{C.DEFAULT_LOG_DIR}/downloader.log",
        },
        "pages": [],
        "companies": [],
        "test_cases": [],
    }


def _merge_defaults(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Merge user config over defaults."""
    defaults = _default_config()
    merged = {**defaults, **raw}

    # Deep merge nested dicts
    for key in ("browser", "download", "anti_crawler", "logging"):
        if key in raw and isinstance(raw[key], dict):
            merged[key] = {**defaults.get(key, {}), **raw[key]}

    return merged



