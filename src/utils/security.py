"""
Security Utility Module
Provides path sanitization, input validation, and other security features
"""

import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from src.utils.string_optimizer import get_string_optimizer


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing dangerous characters

    Args:
        filename: Original filename

    Returns:
        str: Safe filename
    """
    # Use optimized string processing
    optimizer = get_string_optimizer()
    sanitized = optimizer.sanitize_filename(filename)

    # Ensure filename is not empty
    if not sanitized.strip():
        sanitized = "unnamed_file"

    # Limit length
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[: 255 - len(ext)] + ext

    return sanitized.strip()


def safe_join_path(base_path: str, *path_parts: str) -> str:
    """
    Safely join paths to prevent directory traversal attacks

    Args:
        base_path: Base path
        path_parts: Path parts to join

    Returns:
        str: Safe full path
    """
    # Ensure base path is absolute
    base_path = os.path.abspath(base_path)

    # Sanitize each path part
    safe_parts = []
    for part in path_parts:
        # Remove dangerous characters
        safe_part = sanitize_filename(part)
        safe_parts.append(safe_part)

    # Build full path
    full_path = os.path.join(base_path, *safe_parts)

    # Normalize path and check if still within base path
    full_path = os.path.abspath(full_path)

    # Check for path traversal attacks
    if not full_path.startswith(os.path.abspath(base_path)):
        raise ValueError(f"Path traversal attempt detected: {full_path}")

    return full_path


def validate_stock_code(stock_code: str) -> bool:
    """
    Validate stock code format

    Args:
        stock_code: Stock code

    Returns:
        bool: Whether valid stock code format
    """
    # Use optimized validation function
    return get_string_optimizer().validate_stock_code(stock_code)


def validate_org_id(org_id: str) -> bool:
    """
    Validate org ID format

    Args:
        org_id: Organization ID

    Returns:
        bool: Whether valid org ID format
    """
    # Use optimized validation function
    return get_string_optimizer().validate_org_id(org_id)


def sanitize_url(url: str) -> str:
    """
    Sanitize URL by removing dangerous parameters

    Args:
        url: Original URL

    Returns:
        str: Safe URL
    """
    try:
        parsed = urlparse(url)

        # Only allow http and https
        if parsed.scheme not in ["http", "https"]:
            raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

        # Remove potentially sensitive parameters
        safe_query = []
        if parsed.query:
            for param in parsed.query.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    # Skip potentially sensitive parameters
                    if key.lower() in ["password", "token", "secret", "key"]:
                        continue
                    safe_query.append(f"{key}={value}")

        # Reconstruct URL
        safe_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if safe_query:
            safe_url += "?" + "&".join(safe_query)
        if parsed.fragment:
            safe_url += "#" + parsed.fragment

        return safe_url

    except Exception as e:
        raise ValueError(f"Invalid URL: {url}") from e


def is_safe_file_content(content: bytes, max_size: int = 10 * 1024 * 1024) -> bool:
    """
    Check if file content is safe

    Args:
        content: File content
        max_size: Maximum allowed size (bytes)

    Returns:
        bool: Whether file content is safe
    """
    # Check file size
    if len(content) > max_size:
        return False

    # Check file signature (magic numbers)
    if len(content) >= 4:
        # Check common dangerous file types
        dangerous_signatures = [
            b"\x4d\x5a",  # PE file (EXE/DLL)
            b"\x7f\x45\x4c\x46",  # ELF file
            b"\x25\x50\x44\x46",  # PDF file header (potentially malicious code)
        ]

        for signature in dangerous_signatures:
            if content.startswith(signature):
                return False

    return True


def sanitize_log_message(message: str) -> str:
    """
    Sanitize log message by removing sensitive information

    Args:
        message: Original log message

    Returns:
        str: Safe log message
    """
    # Use optimized path redaction function
    message = get_string_optimizer().redact_sensitive_paths(message)

    # Remove potentially sensitive information
    sensitive_patterns = [
        (r"password=[^&\s]+", "password=***"),
        (r"token=[^&\s]+", "token=***"),
        (r"secret=[^&\s]+", "secret=***"),
        (r"key=[^&\s]+", "key=***"),
        (r"api_key=[^&\s]+", "api_key=***"),
    ]

    for pattern, replacement in sensitive_patterns:
        message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)

    return message


def validate_directory_path(path: str, must_exist: bool = True) -> bool:
    """
    Validate if directory path is safe

    Args:
        path: Directory path
        must_exist: Whether directory must exist

    Returns:
        bool: Whether path is safe and valid
    """
    try:
        path_obj = Path(path)

        # Check for path traversal
        if ".." in str(path_obj):
            return False

        # Check if absolute path
        if not path_obj.is_absolute():
            return False

        # Check existence if required
        if must_exist and not path_obj.exists():
            return False

        # Check if directory
        if must_exist and not path_obj.is_dir():
            return False

        return True

    except Exception:
        return False


class SecurityValidator:
    """Security Validator Class"""

    def __init__(self):
        self.sensitive_fields = {
            "password",
            "token",
            "secret",
            "key",
            "api_key",
            "access_token",
            "refresh_token",
            "auth_token",
        }

    def sanitize_dict(self, data: dict, sensitive_keys: Optional[set] = None) -> dict:
        """
        Sanitize dictionary by removing sensitive fields

        Args:
            data: Original dictionary
            sensitive_keys: Set of sensitive fields

        Returns:
            dict: Sanitized dictionary
        """
        if sensitive_keys is None:
            sensitive_keys = self.sensitive_fields

        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value

        return sanitized

    def validate_input(self, input_data: str, input_type: str = "general") -> bool:
        """
        Validate input data

        Args:
            input_data: Input data
            input_type: Input type ('general', 'stock_code', 'org_id', 'filename')

        Returns:
            bool: Whether input is valid
        """
        if not input_data or not isinstance(input_data, str):
            return False

        input_data = input_data.strip()

        if input_type == "stock_code":
            return validate_stock_code(input_data)
        elif input_type == "org_id":
            return validate_org_id(input_data)
        elif input_type == "filename":
            return len(input_data) > 0 and len(input_data) <= 255
        else:  # general
            # Basic security checks
            dangerous_chars = ["<", ">", '"', "'", "&", "script", "javascript"]
            return not any(danger in input_data.lower() for danger in dangerous_chars)

    def is_safe_path_operation(self, path: str, operation: str = "read") -> bool:
        """
        Check if path operation is safe

        Args:
            path: File path
            operation: Operation type ('read', 'write', 'delete')

        Returns:
            bool: Whether operation is safe
        """
        try:
            path_obj = Path(path)

            # Check for path traversal
            if ".." in str(path_obj):
                return False

            # Check for dangerous extensions
            dangerous_extensions = [".exe", ".bat", ".cmd", ".scr", ".pif"]
            if operation == "write" and path_obj.suffix.lower() in dangerous_extensions:
                return False

            # Check for system directories
            import platform

            system = platform.system().lower()
            if system == "windows":
                system_dirs = [
                    "C:\\Windows",
                    "C:\\System",
                    os.environ.get("SystemRoot", "C:\\Windows"),
                ]
            else:
                system_dirs = ["/etc", "/bin", "/usr/bin", "/sbin", "/usr/sbin"]

            if any(str(path_obj).startswith(sys_dir) for sys_dir in system_dirs):
                return False

            return True

        except Exception:
            return False
