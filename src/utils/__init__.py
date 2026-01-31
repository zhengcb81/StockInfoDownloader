#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
工具模块

提供各种通用工具函数和类，包括：
- 浏览器工具 (browser_utils)
- 清理工具 (cleanup_utils)
- 目录管理 (directory_manager)
- 关键词匹配 (keyword_matcher)
- 字符串优化 (string_optimizer)
- 安全工具 (security)
- 缓存管理 (cache_manager)
- 验证工具 (validation)

Usage:
    from src.utils import BrowserConfig, cleanup_directory, KeywordMatcher
"""

# Browser utilities
from ..core.constants import (
    BrowserConfig,
    TimeoutConfig,
    AntiCrawlerConfig,
    PaginationConfig,
    RetryConfig,
)
from .browser_utils import (
    get_default_user_agents,
    get_common_chrome_args,
    validate_and_normalize_timeout,
)

# Cleanup utilities
from .cleanup_utils import (
    safe_cleanup,
    cleanup_directory,
    cleanup_file,
    cleanup_path,
    cleanup_multiple_paths,
    cleanup_temp_files,
    cleanup_empty_directories,
    get_directory_size,
    safe_remove_tree,
    safe_move_file,
    safe_copy_file,
)

# Keyword matcher
from .keyword_matcher import (
    KeywordConfig,
    KeywordMatcher,
)

# Directory manager
from .directory_manager import (
    DirectoryManager,
    create_directory_manager,
)

# String optimizer
from .string_optimizer import (
    StringOptimizer,
    get_string_optimizer,
    sanitize_filename,
    standardize_stock_code,
    normalize_whitespace,
    clean_text_content,
    validate_stock_code,
    validate_org_id,
)

# Security utilities
from .security import (
    sanitize_filename as security_sanitize_filename,
    safe_join_path,
    validate_stock_code as security_validate_stock_code,
    validate_org_id as security_validate_org_id,
    sanitize_url,
    is_safe_file_content,
    sanitize_log_message,
    validate_directory_path,
    SecurityValidator,
)

# Validation utilities
from .validation import (
    DataValidator,
    data_validator,
    validate_data,
    validate_batch_data,
)

# Cache manager
from .cache_manager import (
    CacheManager,
    get_cache_manager,
    cached_file_exists,
    cached_stock_info,
    clear_all_cache,
    get_cache_stats,
)

# Debug marker
from .debug_marker import (
    DebugMarker,
)

# Enhanced error handler
from .enhanced_error_handler import (
    ErrorSeverity,
    ErrorCategory,
    RetryStrategy,
    ErrorInfo,
    RetryConfig,
    CircuitBreakerState,
    CircuitBreakerConfig,
    EnhancedErrorHandler,
    get_global_error_handler,
    handle_error,
    execute_with_protection,
    error_protected,
    error_protected_async,
)

# Intelligent cache
from .intelligent_cache import (
    CacheLevel,
    EvictionPolicy,
    CacheConfig,
    IntelligentCache,
    get_global_cache,
    get_cached,
    set_cached,
    delete_cached,
    cached,
)

__all__ = [
    # Browser utilities
    "BrowserConfig",
    "TimeoutConfig",
    "DownloadConfig",
    "AntiCrawlerConfig",
    "PaginationConfig",
    "RetryConfig",
    "get_default_user_agents",
    "get_common_chrome_args",
    "validate_and_normalize_timeout",
    # Cleanup utilities
    "safe_cleanup",
    "cleanup_directory",
    "cleanup_file",
    "cleanup_path",
    "cleanup_multiple_paths",
    "cleanup_temp_files",
    "cleanup_empty_directories",
    "get_directory_size",
    "safe_remove_tree",
    "safe_move_file",
    "safe_copy_file",
    # Keyword matcher
    "KeywordConfig",
    "KeywordMatcher",
    # Directory manager
    "DirectoryManager",
    "create_directory_manager",
    # String optimizer
    "StringOptimizer",
    "get_string_optimizer",
    "sanitize_filename",
    "standardize_stock_code",
    "normalize_whitespace",
    "clean_text_content",
    "validate_stock_code",
    "validate_org_id",
    # Security utilities
    "safe_join_path",
    "sanitize_url",
    "is_safe_file_content",
    "sanitize_log_message",
    "validate_directory_path",
    "SecurityValidator",
    # Validation utilities
    "DataValidator",
    "data_validator",
    "validate_data",
    "validate_batch_data",
    # Cache manager
    "CacheManager",
    "get_cache_manager",
    "cached_file_exists",
    "cached_stock_info",
    "clear_all_cache",
    "get_cache_stats",
    # Debug marker
    "DebugMarker",
    # Enhanced error handler
    "ErrorSeverity",
    "ErrorCategory",
    "RetryStrategy",
    "ErrorInfo",
    "RetryConfig",
    "CircuitBreakerState",
    "CircuitBreakerConfig",
    "EnhancedErrorHandler",
    "get_global_error_handler",
    "handle_error",
    "execute_with_protection",
    "error_protected",
    "error_protected_async",
    # Intelligent cache
    "CacheLevel",
    "EvictionPolicy",
    "CacheConfig",
    "IntelligentCache",
    "get_global_cache",
    "get_cached",
    "set_cached",
    "delete_cached",
    "cached",
]
