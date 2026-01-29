#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Browser automation utility functions"""

import os
import sys
from typing import Any, Dict, List


def is_test_environment() -> bool:
    """
    Detect if running in a test environment

    Returns:
        bool: True if in test environment, False otherwise
    """
    return (
        os.environ.get("TEST_ENV") == "true"
        or "test" in sys.argv[0].lower()
        or "pytest" in sys.argv[0].lower()
        or os.environ.get("PYTEST_CURRENT_TEST") is not None
    )


def get_default_user_agents() -> List[str]:
    """
    Get list of default user agents

    Returns:
        List[str]: List of user agent strings
    """
    return [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]


def validate_and_normalize_timeout(timeout_value: int) -> int:
    """
    Validate and normalize timeout configuration (unified conversion to milliseconds)

    Args:
        timeout_value: Timeout value (seconds or milliseconds)

    Returns:
        int: Normalized timeout in milliseconds

    Raises:
        ValueError: If timeout value is invalid
    """
    if timeout_value <= 0:
        raise ValueError("timeout must be greater than 0")

    # If value >= 1000, assume it's already in milliseconds
    # If value < 1000, assume it's in seconds and convert to milliseconds
    return timeout_value if timeout_value >= 1000 else timeout_value * 1000


def get_common_chrome_args() -> List[str]:
    """
    Get common Chrome launch arguments

    Returns:
        List[str]: List of Chrome launch arguments
    """
    return [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-blink-features=AutomationControlled",
        "--remote-debugging-port=0",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-sync",
        "--disable-translate",
        "--disable-default-apps",
        "--disable-notifications",
        "--disable-popup-blocking",
        "--log-level=3",
        "--disable-features=TranslateUI",
        "--disable-component-extensions-with-background-pages",
        "--disable-domain-reliability",
        "--disable-setuid-sandbox",
        "--disable-features=VizDisplayCompositor",
        "--disable-ipc-flooding-protection",
    ]


def get_download_file_size_threshold() -> int:
    """
    Get download file size threshold (bytes)

    Returns:
        int: Minimum valid file size (10KB)
    """
    return 10 * 1024


def get_download_check_interval() -> float:
    """
    Get download check interval (seconds)

    Returns:
        float: Check interval
    """
    return 0.5


def get_download_stability_wait() -> int:
    """
    Get download stability wait time (seconds)

    Returns:
        int: Wait time
    """
    return 1


def get_temp_file_extensions() -> List[str]:
    """
    Get list of temporary file extensions

    Returns:
        List[str]: List of temporary file extensions
    """
    return [".tmp", ".crdownload"]


def get_pdf_extension() -> str:
    """
    Get PDF file extension

    Returns:
        str: PDF extension
    """
    return ".pdf"


def get_default_window_size() -> Dict[str, int]:
    """
    Get default window size configuration

    Returns:
        Dict[str, int]: Window width and height configuration
    """
    return {"width": 1920, "height": 1080}


def get_default_window_size_string() -> str:
    """
    Get default window size in string format

    Returns:
        str: "width,height" formatted string
    """
    return "1920,1080"


def get_max_downloads_per_session() -> int:
    """
    Get maximum downloads per session

    Returns:
        int: Maximum download count
    """
    return 10


def get_default_implicit_wait() -> int:
    """
    Get default implicit wait time (seconds)

    Returns:
        int: Wait time
    """
    return 3


def get_default_page_load_timeout() -> int:
    """
    Get default page load timeout (seconds)

    Returns:
        int: Timeout value
    """
    return 30


def get_default_download_timeout() -> int:
    """
    Get default download timeout (seconds)

    Returns:
        int: Timeout value
    """
    return 300


def get_default_element_wait_timeout() -> int:
    """
    Get default element wait timeout (seconds)

    Returns:
        int: Timeout value
    """
    return 10


def get_default_navigation_timeout() -> int:
    """
    Get default navigation timeout (seconds)

    Returns:
        int: Timeout value
    """
    return 10


def get_default_button_click_timeout() -> int:
    """
    Get default button click timeout (seconds)

    Returns:
        int: Timeout value
    """
    return 5


def get_retry_config() -> Dict[str, Any]:
    """
    Get retry configuration

    Returns:
        Dict[str, Any]: Retry configuration parameters
    """
    return {"max_retries": 3, "base_delay": 1.0, "backoff_factor": 2.0}


def get_anti_crawler_config() -> Dict[str, Any]:
    """
    Get anti-crawler configuration

    Returns:
        Dict[str, Any]: Anti-crawler configuration parameters
    """
    return {
        "min_delay": 2.0,
        "max_delay": 8.0,
        "max_downloads": 5,
        "scroll_range": [200, 600],
        "behavior_delay": [0.5, 1.5],
    }


def get_pagination_config() -> Dict[str, Any]:
    """
    Get pagination configuration

    Returns:
        Dict[str, Any]: Pagination configuration parameters
    """
    return {"max_pages": 3, "pagination_wait": 2, "human_behavior_delay": 3}
