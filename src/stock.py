"""Stock name lookup — fetches stock name from public APIs."""
from typing import Optional

import requests

from .constants import STOCK_NAME_API_TEMPLATE
from .logger import log
from .string_utils import standardize_stock_code


def get_stock_name(stock_code: str) -> Optional[str]:
    """Get stock name from public APIs (Tencent Finance)."""
    code = standardize_stock_code(stock_code)
    if not code:
        return None

    # Try Tencent Finance API
    name = _get_from_tencent(code)
    if name:
        return name

    # Fallback: try cninfo API
    name = _get_from_cninfo(code)
    if name:
        return name

    log.warning(f"Could not find stock name for {code}")
    return None


def _get_from_tencent(stock_code: str) -> Optional[str]:
    """Fetch stock name from Tencent Finance API."""
    try:
        exchange = "sh" if stock_code.startswith(("6", "5", "9")) else "sz"
        url = STOCK_NAME_API_TEMPLATE.format(
            exchange=exchange, stock_code=stock_code
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Parse response
        stock_key = f"{exchange}{stock_code}"
        if "data" in data and stock_key in data["data"]:
            stock_data = data["data"][stock_key]
            if "day" in stock_data and stock_data["day"]:
                # Return the name from metadata if available
                name = stock_data.get("name", "")
                if name:
                    return name
    except Exception as e:
        log.debug(f"Tencent API failed for {stock_code}: {e}")
    return None


def _get_from_cninfo(stock_code: str) -> Optional[str]:
    """Fetch stock name from cninfo API."""
    try:
        url = f"https://www.cninfo.com.cn/new/data/szse_stock.json"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        for stock in data.get("stockList", []):
            if stock.get("code") == stock_code:
                return stock.get("name", "")
    except Exception as e:
        log.debug(f"Cninfo API failed for {stock_code}: {e}")
    return None
