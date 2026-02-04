"""
String Operation Performance Optimization Module
Provides efficient string processing functions as alternatives to inefficient
regular expressions and multiple replace operations
"""

import re
from typing import Any, Dict, Optional

from src.core.logger import get_logger


class StringOptimizer:
    """String operation optimizer for efficient text processing"""

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

        # Pre-compile commonly used regex patterns
        self._compile_patterns()

        # Create character translation tables
        self._create_translation_tables()

        self.logger.info("String optimizer initialized")

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for performance"""
        # Filename and path related patterns
        self.patterns = {
            # Filename illegal characters
            "filename_chars": re.compile(r'[\\/:*?"<>|]'),
            "path_separator": re.compile(r"[\\\/]+"),
            # Stock code validation
            "stock_code": re.compile(r"^\d{6}$"),
            "org_id": re.compile(r"^99\d{8}$"),
            # Company name validation (supports Chinese chars)
            "company_name": re.compile(r"^[\u4e00-\u9fa5a-zA-Z0-9\s\(\)（）\-\.·]+$"),
            # Pagination info extraction
            "pagination_current": re.compile(r"(\d+)\s*/\s*(\d+)"),
            "pagination_total": re.compile(r"共\s*(\d+)\s*页"),
            # Email and phone validation
            "email": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
            "phone": re.compile(r"^1[3-9]\d{9}$"),
            "phone_with_dash": re.compile(r"^\d{3}-\d{4}-\d{4}$"),
            # URL and path handling
            "windows_path": re.compile(r"[A-Za-z]:\\[^\\]+\\"),
            "unix_path": re.compile(r"/[^/\s]+/[^/\s]+/"),
            # Text cleanup
            "whitespace": re.compile(r"\s+"),
            "control_chars": re.compile(r"[\x00-\x1f\x7f-\x9f]"),
            # Date/time patterns
            "date_cn": re.compile(r"\d{4}年\d{1,2}月\d{1,2}日"),
            "date_std": re.compile(r"\d{4}-\d{1,2}-\d{1,2}"),
            "time_std": re.compile(r"\d{1,2}:\d{2}:\d{2}"),
        }

        self.logger.debug(f"Pre-compiled {len(self.patterns)} regex patterns")

    def _create_translation_tables(self) -> None:
        """Create character translation tables"""
        # Filename safe character translation table
        translation_map = {
            ord("/"): ord("_"),
            ord("\\"): ord("_"),
            ord(":"): ord("_"),
            ord("*"): ord("_"),
            ord("?"): ord("_"),
            ord('"'): ord("_"),
            ord("<"): ord("_"),
            ord(">"): ord("_"),
            ord("|"): ord("_"),
        }
        self.filename_translation = translation_map

        # Path separator unification translation table
        path_translation = {ord("\\"): ord("/")}
        self.path_separator_translation = path_translation

        # Control character removal table
        control_chars = "".join(chr(i) for i in range(32))
        self.control_char_translation = str.maketrans("", "", control_chars)

        # Dangerous path character translation table
        self.dangerous_path_translation = str.maketrans("", "", "")

        self.logger.debug("Created character translation tables")

    def sanitize_filename(self, filename: str, replacement: str = "_") -> str:
        """
        Efficient filename sanitization function

        Args:
            filename: Original filename
            replacement: Replacement character, defaults to '_'

        Returns:
            str: Sanitized safe filename
        """
        if not filename:
            return "unnamed"

        # Use translation table for fast character replacement
        sanitized = filename.translate(self.filename_translation)

        # Handle consecutive underscores
        if replacement == "_":
            sanitized = self.patterns["path_separator"].sub("_", sanitized)

        # Remove leading/trailing special characters
        sanitized = sanitized.strip("._- ")

        # Limit length
        if len(sanitized) > 200:
            sanitized = sanitized[:200].rstrip("._- ")

        # Ensure not empty
        if not sanitized:
            return "unnamed"

        return sanitized

    def standardize_stock_code(self, stock_code: str) -> Optional[str]:
        """
        Standardize stock code format

        Args:
            stock_code: Original stock code

        Returns:
            Optional[str]: Standardized 6-digit stock code, None if invalid
        """
        if not stock_code:
            return None

        # Quick cleanup
        cleaned = stock_code.strip().upper()

        # Remove non-digit characters
        cleaned = "".join(c for c in cleaned if c.isdigit())

        # Pad to 6 digits
        if len(cleaned) == 6:
            return cleaned
        elif len(cleaned) < 6:
            return cleaned.zfill(6)
        else:
            return None

    def normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace characters

        Args:
            text: Original text

        Returns:
            str: Normalized text
        """
        if not text:
            return ""

        # Use pre-compiled pattern
        return self.patterns["whitespace"].sub(" ", text).strip()

    def clean_text_content(self, text: str) -> str:
        """
        Clean text content by removing control characters and excess whitespace

        Args:
            text: Original text

        Returns:
            str: Cleaned text
        """
        if not text:
            return ""

        # Remove control characters
        cleaned = text.translate(self.control_char_translation)

        # Normalize whitespace
        cleaned = self.normalize_whitespace(cleaned)

        return cleaned

    def extract_pagination_info(self, text: str) -> Dict[str, Optional[int]]:
        """
        Extract pagination information from text

        Args:
            text: Text containing pagination info

        Returns:
            Dict[str, Optional[int]]: Pagination info dictionary
        """
        result: Dict[str, Optional[int]] = {"current": None, "total": None}

        if not text:
            return result

        # Extract current/total pages
        current_match = self.patterns["pagination_current"].search(text)
        if current_match:
            result["current"] = int(current_match.group(1))
            result["total"] = int(current_match.group(2))

        # If not found, try to extract total pages only
        if result["total"] is None:
            total_match = self.patterns["pagination_total"].search(text)
            if total_match:
                result["total"] = int(total_match.group(1))

        return result

    def validate_stock_code(self, stock_code: str) -> bool:
        """
        Validate stock code format

        Args:
            stock_code: Stock code to validate

        Returns:
            bool: True if valid
        """
        if not stock_code:
            return False

        standardized = self.standardize_stock_code(stock_code)
        return (
            standardized is not None
            and self.patterns["stock_code"].match(standardized) is not None
        )

    def validate_org_id(self, org_id: str) -> bool:
        """
        Validate organization ID format

        Args:
            org_id: Organization ID to validate

        Returns:
            bool: True if valid
        """
        if not org_id:
            return False

        cleaned = org_id.strip()
        return self.patterns["org_id"].match(cleaned) is not None

    def validate_company_name(self, name: str) -> bool:
        """
        Validate company name format

        Args:
            name: Company name to validate

        Returns:
            bool: True if valid
        """
        if not name:
            return False

        cleaned = name.strip()
        return bool(self.patterns["company_name"].match(cleaned))

    def redact_sensitive_paths(self, message: str) -> str:
        """
        Redact sensitive path information from messages

        Args:
            message: Original message

        Returns:
            str: Redacted message
        """
        if not message:
            return ""

        # Use pre-compiled patterns for path redaction
        redacted = self.patterns["windows_path"].sub("[REDACTED_PATH]\\", message)
        redacted = self.patterns["unix_path"].sub("[REDACTED_PATH]/", redacted)

        return redacted

    def extract_date_info(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract date information from text

        Args:
            text: Text containing dates

        Returns:
            Dict[str, Optional[str]]: Date information dictionary
        """
        result: Dict[str, Optional[str]] = {"date_cn": None, "date_std": None, "time": None}

        if not text:
            return result

        # Extract Chinese format date
        cn_date_match = self.patterns["date_cn"].search(text)
        if cn_date_match:
            result["date_cn"] = cn_date_match.group()

        # Extract standard format date
        std_date_match = self.patterns["date_std"].search(text)
        if std_date_match:
            result["date_std"] = std_date_match.group()

        # Extract time
        time_match = self.patterns["time_std"].search(text)
        if time_match:
            result["time"] = time_match.group()

        return result

    def join_text_parts(self, *parts: str) -> str:
        """
        Efficient text part joining function

        Args:
            *parts: Text parts to join

        Returns:
            str: Joined text
        """
        # Filter empty values
        non_empty_parts = [part.strip() for part in parts if part and part.strip()]

        if not non_empty_parts:
            return ""

        # Direct join, more efficient than multiple join calls
        return " ".join(non_empty_parts)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get optimizer statistics

        Returns:
            Dict[str, Any]: Statistics dictionary
        """
        return {
            "compiled_patterns": len(self.patterns),
            "translation_tables": 4,  # filename, path_separator, control_char, dangerous_path
            "available_patterns": list(self.patterns.keys()),
        }


# Global string optimizer instance
_string_optimizer: Optional[StringOptimizer] = None
_optimizer_lock = None

# Lazy import lock
try:
    import threading

    _optimizer_lock = threading.Lock()
except ImportError:
    _optimizer_lock = None


def get_string_optimizer() -> StringOptimizer:
    """Get global string optimizer instance"""
    global _string_optimizer
    if _string_optimizer is None:
        if _optimizer_lock:
            with _optimizer_lock:
                if _string_optimizer is None:
                    _string_optimizer = StringOptimizer()
        else:
            _string_optimizer = StringOptimizer()
    return _string_optimizer


# Convenience functions
def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """Convenience function: sanitize filename"""
    return get_string_optimizer().sanitize_filename(filename, replacement)


def standardize_stock_code(stock_code: str) -> Optional[str]:
    """Convenience function: standardize stock code"""
    return get_string_optimizer().standardize_stock_code(stock_code)


def normalize_whitespace(text: str) -> str:
    """Convenience function: normalize whitespace"""
    return get_string_optimizer().normalize_whitespace(text)


def clean_text_content(text: str) -> str:
    """Convenience function: clean text content"""
    return get_string_optimizer().clean_text_content(text)


def validate_stock_code(stock_code: str) -> bool:
    """Convenience function: validate stock code"""
    return get_string_optimizer().validate_stock_code(stock_code)


def validate_org_id(org_id: str) -> bool:
    """Convenience function: validate organization ID"""
    return get_string_optimizer().validate_org_id(org_id)
