"""String utility functions."""
import re
from typing import Optional


def standardize_stock_code(code: str) -> Optional[str]:
    """Normalize a stock code to 6-digit string.

    Returns None if the code is invalid.
    """
    if not code:
        return None
    digits = re.sub(r"\D", "", str(code))
    if len(digits) == 6:
        return digits
    return None


def clean_filename(name: str) -> str:
    """Remove illegal characters from a filename."""
    return re.sub(r'[\\/:*?"<>|]', "_", name)
