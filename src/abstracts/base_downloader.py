"""
Downloader Abstract Base Class
Provides general implementation and shared functionality for downloaders
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from datetime import datetime

from src.interfaces.downloader_interface import (
    IDownloader,
    IBrowserStrategy,
    IAntiCrawlerStrategy,
    DownloadRequest,
    DownloadResult,
    DownloadStatus
)
from src.core.logger import get_logger


class BaseDownloader(IDownloader):
    """
    Downloader Abstract Base Class
    Provides general download functionality and status management
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.logger = get_logger(f"{self.__class__.__name__}")
        self.browser_strategy: Optional[IBrowserStrategy] = None
        self.anti_crawler_strategy: Optional[IAntiCrawlerStrategy] = None

        # Default configuration
        self.default_config = {
            'browser_strategy': 'playwright',
            'timeout': 180,
            'max_pages': 5,
            'anti_crawler_enabled': True,
            'retry_count': 3,
            'retry_delay': 1.0,
            'user_agent': None
        }

        # Merge configuration
        self.config = {**self.default_config, **(config or {})}
        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize components"""
        try:
            self._init_browser_strategy()
            self._init_anti_crawler_strategy()
            self.logger.info("Components initialized successfully")
        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
            raise

    def _init_browser_strategy(self) -> None:
        """Initialize browser strategy"""
        strategy_name = self.config.get('browser_strategy', 'playwright')
        try:
            if strategy_name == 'playwright':
                from src.web.playwright_strategy import PlaywrightStrategy
                self.browser_strategy = PlaywrightStrategy(self.config)
            elif strategy_name == 'selenium':
                from src.web.selenium_strategy import SeleniumStrategy
                self.browser_strategy = SeleniumStrategy(self.config)
            else:
                raise ValueError(f"Unsupported browser strategy: {strategy_name}")

            self.logger.info(f"Browser strategy initialized: {strategy_name}")
        except Exception as e:
            self.logger.error(f"Browser strategy initialization failed: {e}")
            raise

    def _init_anti_crawler_strategy(self) -> None:
        """Initialize anti-crawler strategy"""
        if not self.config.get('anti_crawler_enabled', True):
            self.logger.info("Anti-crawler strategy disabled")
            return

        try:
            from src.web.anti_crawler import AntiCrawlerStrategy
            self.anti_crawler_strategy = AntiCrawlerStrategy()
            self.logger.info("Anti-crawler strategy initialized successfully")
        except Exception as e:
            self.logger.error(f"Anti-crawler strategy initialization failed: {e}")
            # Do not block downloader if anti-crawler fails
            self.anti_crawler_strategy = None

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure downloader"""
        self.config.update(config)
        self.logger.info("Downloader configuration updated")

        # Re-initialize components
        self._initialize_components()

    def get_supported_browsers(self) -> List[str]:
        """Get supported browsers list"""
        return ['playwright', 'selenium']

    def _update_status(self, **kwargs) -> None:
        """Update status"""
        for key, value in kwargs.items():
            if hasattr(self._status, key):
                setattr(self._status, key, value)

    def _validate_and_prepare_request(self, request: DownloadRequest) -> None:
        """Validate and prepare request"""
        # Validate request
        errors = self.validate_request(request)
        if errors:
            error_msg = "; ".join(errors)
            self.logger.error(f"Request validation failed: {error_msg}")
            raise ValueError(error_msg)

        # Set defaults
        if not request.save_dir:
            request.save_dir = Path("downloads")

        # Ensure directory exists
        save_path = Path(request.save_dir)
        save_path.mkdir(parents=True, exist_ok=True)

    def _execute_download_with_retry(
        self, request: DownloadRequest
    ) -> DownloadResult:
        """Execute download with retry logic"""
        retry_count = self.config.get('retry_count', 3)
        retry_delay = self.config.get('retry_delay', 1.0)

        for attempt in range(retry_count + 1):
            try:
                # Pre-request processing
                if self.anti_crawler_strategy:
                    self.anti_crawler_strategy.before_request({
                        'stock_code': request.stock_code,
                        'attempt': attempt + 1,
                        'timestamp': datetime.now().isoformat()
                    })

                # Perform download
                result = self._perform_download(request)

                # Post-request processing
                if self.anti_crawler_strategy:
                    self.anti_crawler_strategy.after_request({
                        'success': result.success,
                        'file_count': len(result.downloaded_files),
                        'attempt': attempt + 1,
                        'timestamp': datetime.now().isoformat()
                    })

                return result

            except Exception as e:
                self.logger.warning(f"Download attempt {attempt + 1}/{retry_count + 1} failed: {e}")

                # Check if should retry
                should_retry = (
                    attempt < retry_count and
                    (not self.anti_crawler_strategy or
                     self.anti_crawler_strategy.should_retry(e))
                )

                if should_retry:
                    time.sleep(retry_delay * (attempt + 1))  # Incremental delay
                else:
                    # Return failure result
                    return DownloadResult(
                        success=False,
                        downloaded_files=[],
                        total_files=0,
                        errors=[str(e)],
                        duration_seconds=0,
                        metadata={
                            'attempts': attempt + 1,
                            'final_error': str(e)
                        }
                    )

    @abstractmethod
    def _perform_download(self, request: DownloadRequest) -> DownloadResult:
        """
        Perform actual download logic
        Subclasses must implement this method
        """
        pass

    def get_download_history(self) -> List[Dict[str, Any]]:
        """
        Get download history records

        Returns:
            List[Dict[str, Any]]: Download history records
        """
        # Default implementation returns empty list
        return []

    def export_download_log(self, file_path: Union[str, Path]) -> None:
        """
        Export download log

        Args:
            file_path: Log file path
        """
        history = self.get_download_history()
        if not history:
            self.logger.warning("No download history to export")
            return

        try:
            import json
            log_path = Path(file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'export_time': datetime.now().isoformat(),
                    'total_records': len(history),
                    'records': history
                }, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Download log exported to: {log_path}")

        except Exception as e:
            self.logger.error(f"Failed to export download log: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        try:
            self.cleanup()
        except Exception as e:
            self.logger.error(f"Failed to cleanup resources: {e}")


class BaseBrowserStrategy(IBrowserStrategy):
    """浏览器策略抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger(f"{self.__class__.__name__}")
        self._initialized = False

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    def _mark_initialized(self, success: bool) -> None:
        """标记初始化状态"""
        self._initialized = success

    def _handle_error(self, operation: str, error: Exception) -> None:
        """统一错误处理"""
        self.logger.error(f"{operation}失败: {error}")
        raise


class BaseAntiCrawlerStrategy(IAntiCrawlerStrategy):
    """反爬虫策略抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger(f"{self.__class__.__name__}")
        self.request_count = 0
        self.last_request_time = 0.0
        self.session_requests = 0
        self.session_start_time = time.time()

    def _get_base_delay(self) -> float:
        """获取基础延迟时间"""
        return self.config.get('base_delay', 1.0)

    def _get_session_limit(self) -> int:
        """获取会话请求限制"""
        return self.config.get('session_limit', 50)

    def _should_delay_request(self) -> bool:
        """判断是否需要延迟请求"""
        base_delay = self._get_base_delay()
        current_time = time.time()

        # 计算上次请求后的延迟
        time_since_last = current_time - self.last_request_time
        if time_since_last < base_delay:
            return True

        # 检查会话限制
        session_duration = current_time - self.session_start_time
        if (self.session_requests >= self._get_session_limit() and
            session_duration < 300):  # 5分钟内的会话限制
            return True

        return False

    def _apply_delay(self) -> None:
        """应用延迟"""
        if self._should_delay_request():
            delay = self._get_base_delay()
            self.logger.debug(f"应用反爬虫延迟: {delay}秒")
            time.sleep(delay)

    def before_request(self, request_info: Dict[str, Any]) -> None:
        """请求前处理"""
        self._apply_delay()
        self.request_count += 1
        self.session_requests += 1
        self.last_request_time = time.time()

    def after_request(self, response_info: Dict[str, Any]) -> None:
        """请求后处理"""
        if response_info.get('success', False):
            self.logger.debug("请求成功")
        else:
            self.logger.warning("请求失败，可能触发反爬虫保护")

        # 检查是否需要重置会话
        current_time = time.time()
        session_duration = current_time - self.session_start_time
        if session_duration > 300:  # 5分钟后重置会话
            self.session_requests = 0
            self.session_start_time = current_time
            self.logger.debug("会话计数器已重置")

    def should_retry(self, error: Exception) -> bool:
        """判断是否应该重试"""
        # 默认重试逻辑
        error_str = str(error).lower()

        # 不重试的情况
        no_retry_patterns = [
            'timeout',
            'connection refused',
            'dns lookup failed',
            'ssl error'
        ]

        for pattern in no_retry_patterns:
            if pattern in error_str:
                return False

        return True