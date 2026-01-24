"""
Download Service Module
Provides download functionality for Investor Relations Activity Record Sheets
"""

import os
import re
import time
import uuid
import random
import shutil
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains

from ..core.exceptions import (
    DownloadError, WebDriverError, NetworkError, FileSystemError,
    ErrorCode, ErrorSeverity, RecoveryStrategy,
    with_error_handling, handle_error
)
from ..core.logger import get_logger
from ..core.config import ConfigManager
from ..core.performance_monitor import monitor_performance, monitor_operation, performance_monitor
from ..utils.string_optimizer import standardize_stock_code
from ..data.models import StockInfo, DownloadRecord, DownloadStatus, DownloadTask
from ..data.mapping import MappingManager
from ..web.driver import WebDriverManager
from ..web.anti_crawler import AntiCrawlerStrategy
from ..web.scraper import WebScraper
from ..web.browser_strategy_manager import BrowserStrategyManager, BrowserType
from ..utils.keyword_matcher import KeywordMatcher

logger = get_logger(__name__)


class StockService:
    """Stock information service class, provides basic stock-related services"""
    
    def __init__(self, mapping_file: str = "stock_orgid_mapping.json"):
        """
        Initialize stock service
        
        Args:
            mapping_file: Mapping file path
        """
        self.mapping_manager = MappingManager(mapping_file)
        self.config = ConfigManager()
    
    def get_stock_info(self, stock_code: str) -> Optional[Dict[str, str]]:
        """
        Get stock information
        
        Args:
            stock_code: Stock code
            
        Returns:
            Optional[Dict[str, str]]: Stock info dictionary, containing org_id and stock_name
        """
        try:
            # Get Org ID
            org_id = self.mapping_manager.get_org_id(stock_code)
            if not org_id:
                logger.warning(f"Org ID not found for stock code {stock_code}")
                return None
            
            # Get stock name
            stock_name = self.mapping_manager.get_stock_name(stock_code)
            if not stock_name:
                stock_name = stock_code
                logger.warning(f"Using stock code as name: {stock_code}")
            
            return {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'org_id': org_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get stock info: {e}")
            return None
    
    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """
        Get stock name
        
        Args:
            stock_code: Stock code
            
        Returns:
            Optional[str]: Stock name
        """
        return self.mapping_manager.get_stock_name(stock_code)
    
    def get_org_id(self, stock_code: str, force_refresh: bool = False) -> Optional[str]:
        """
        Get Org ID
        
        Args:
            stock_code: Stock code
            force_refresh: Whether to force refresh
            
        Returns:
            Optional[str]: Org ID
        """
        return self.mapping_manager.get_org_id(stock_code, force_refresh)
    
    def validate_stock_code(self, stock_code: str) -> bool:
        """
        Validate stock code format
        
        Args:
            stock_code: Stock code
            
        Returns:
            bool: Whether valid
        """
        if not stock_code:
            return False
        
        # Use optimized stock code standardization
        standardized = standardize_stock_code(stock_code)
        return standardized is not None
    
    def get_all_stock_codes(self) -> List[str]:
        """
        Get all stock codes
        
        Returns:
            List[str]: List of stock codes
        """
        return self.mapping_manager.get_all_stock_codes()
    
    def get_stock_statistics(self) -> Dict[str, int]:
        """
        Get stock statistics
        
        Returns:
            Dict[str, int]: Statistics info
        """
        return self.mapping_manager.get_statistics()


class DownloadService:
    """Investor Relations Activity Record Sheet Download Service"""
    
    def __init__(self,
                 save_dir: str = "downloads",
                 mapping_file: str = "stock_orgid_mapping.json",
                 config_file: Optional[str] = None):
        """
        Initialize download service (Enhanced version, aligned with old downloader)
        
        Args:
            save_dir: Download file save directory
            mapping_file: Mapping file path
        """
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.mapping_file = mapping_file
        
        self.mapping_manager = MappingManager(mapping_file)

        # Initialize browser strategy manager
        self.browser_strategy_manager = BrowserStrategyManager(config_file)
        self.browser_strategy = self.browser_strategy_manager.get_strategy(
            headless=True,
            download_dir=str(self.save_dir),
            config={
                'window_size': '1920,1080',
                'page_load_timeout': 8,
                'implicit_wait': 2,
                'max_downloads_per_session': 10
            }
        )

        # Compatible old WebDriverManager (for transition)
        self.driver_manager = WebDriverManager(
            headless=True,
            download_dir=str(self.save_dir),
            max_downloads_per_session=10,
            page_load_timeout=8,
            implicit_wait=2,
            config_file=config_file
        )
        self.anti_crawler = AntiCrawlerStrategy()

        # Load config
        self.config = ConfigManager(config_file)
        self.logger = logger  # Add instance-level logger attribute for testing
        
        # Key attributes copied from old downloader
        self.download_count = 0  # Download counter
        self.max_downloads_per_session = self.config.get('download.max_downloads_per_session', 5)  # Max downloads per session
        
        # Configure anti-crawler strategy
        human_behavior_delay = self.config.get('download.human_behavior_delay', 3)
        # Ensure human_behavior_delay is integer
        if isinstance(human_behavior_delay, list):
            # If list, take first element or average
            human_behavior_delay = human_behavior_delay[0] if human_behavior_delay else 3
        elif not isinstance(human_behavior_delay, (int, float)):
            # If not number type, use default value
            human_behavior_delay = 3
        
        # Ensure is integer
        human_behavior_delay = int(human_behavior_delay)
        
        self.anti_crawler.set_session_parameters(
            min_delay=max(1, human_behavior_delay - 1),
            max_delay=human_behavior_delay + 2,  # Reduce max delay
            max_downloads=self.max_downloads_per_session
        )
        
        # Current stock directory (for file management)
        self._current_stock_dir = None
        
        # Error recovery mechanism
        self._consecutive_errors = 0
        self._max_consecutive_errors = 3
        self._circuit_breaker_active = False
        self._last_error_time = None
        self._circuit_breaker_timeout = 60  # Retry after 60 seconds
    
    def clean_filename(self, filename):
        """Clean illegal characters in filename (copied from old downloader)"""
        if not filename:
            return filename
        # Remove leading/trailing spaces
        filename = filename.strip()
        # Replace illegal characters
        filename = re.sub(r'[\\[*?"<>|]', '_', filename)
        # Handle space and dot combination: replace consecutive space and dot sequence with single dot
        # First standardize space dot sequence: replace space and dot interleaved sequence with single dot
        # Use regex to match any amount of spaces and dots (at least one dot), replace with single dot
        filename = re.sub(r'(?:\s*\.)+\s*', '.', filename)
        # Ensure no consecutive dots (might be generated by above replacement)
        filename = re.sub(r'\.{2,}', '.', filename)
        return filename
    
    def get_org_id(self, stock_code, force_run=False):
        """Get Org ID for stock code (copied from old downloader)"""
        return self.mapping_manager.get_org_id(stock_code, force_refresh=force_run)
    
    @monitor_performance("DownloadService.download_stock_pdfs")
    def download_stock_pdfs(
                          stock_code: str,
                          target_pages: Optional[List[Union[str, Dict[str, Any]]]] = None,
                          max_retries: int = 3,
                          proxy_info: Optional[Dict[str, Any]] = None) -> List[DownloadRecord]:
        """
        Download PDF files for specified stock

        Args:
            stock_code: Stock code
            target_pages: Target page list (supports string or dict format)
            max_retries: Max retries
            proxy_info: Proxy info (for multi-company parallel download)

        Returns:
            List[DownloadRecord]: List of download records
        """
        if target_pages is None:
            target_pages = ["research"]

        # Convert dict format target_pages to string format
        normalized_target_pages = []
        for page in target_pages:
            if isinstance(page, dict):
                # Dict format: {'suffix': 'research', 'allowed_keywords': None}
                suffix = page.get('suffix', 'research')
                normalized_target_pages.append(suffix)
            else:
                # String format: 'research'
                normalized_target_pages.append(page)

        target_pages = normalized_target_pages

        # If proxy info provided, configure proxy
        if proxy_info:
            self._configure_proxy(proxy_info)

        stock_info = self._get_stock_info(stock_code)
        if not stock_info or not stock_info.org_id:
            logger.error(f"Cannot get Org ID: {stock_code}")
            return []
        
        task = DownloadTask(
            task_id=str(uuid.uuid4()),
            stock_info=stock_info,
            target_pages=target_pages,
            save_directory=str(self.save_dir),
            max_retries=max_retries
        )
        
        return self._execute_download_task(task)
    
    @with_error_handling(
        error_code=ErrorCode.DOWNLOAD_STOCK_INFO_ERROR,
        severity=ErrorSeverity.ERROR,
        recovery_strategy=RecoveryStrategy.SKIP
    )
    def _get_stock_info(self, stock_code: str) -> Optional[StockInfo]:
        """Get stock info (aligned with old downloader)"""
        try:
            # Use same stock name retrieval logic as old downloader
            from get_stock_name import get_stock_name
            
            stock_name = get_stock_name(stock_code, self.mapping_file)
            
            # If retrieval failed, use stock code as name
            if not stock_name or stock_name.startswith('错误') or stock_name.startswith('网络'):
                stock_name = stock_code
                logger.warning(f"Using stock code as name: {stock_name}")
            
            org_id = self.mapping_manager.get_org_id(stock_code)
            if not org_id:
                raise DownloadError(
                    f"Cannot get Org ID: {stock_code}",
                    error_code=ErrorCode.DOWNLOAD_ORG_ID_ERROR,
                    severity=ErrorSeverity.ERROR,
                    recovery_strategy=RecoveryStrategy.SKIP,
                    context={"stock_code": stock_code, "operation": "get_stock_info"}
                )
            
            return StockInfo(
                stock_code=stock_code,
                stock_name=stock_name,
                org_id=org_id
            )
            
        except Exception as e:
            if isinstance(e, DownloadError):
                raise
            raise DownloadError(
                f"Failed to get stock info: {e}",
                error_code=ErrorCode.DOWNLOAD_STOCK_INFO_ERROR,
                severity=ErrorSeverity.ERROR,
                recovery_strategy=RecoveryStrategy.SKIP,
                context={"stock_code": stock_code, "operation": "get_stock_info"},
                original_exception=e
            )
    
    @monitor_performance("DownloadService._execute_download_task")
    @with_error_handling(
        error_code=ErrorCode.DOWNLOAD_TASK_ERROR,
        severity=ErrorSeverity.ERROR,
        recovery_strategy=RecoveryStrategy.RETRY,
        max_retries=2
    )
    def _execute_download_task(self, task: DownloadTask) -> List[DownloadRecord]:
        """Execute download task"""
        records = []

        try:
            # Temporarily use WebDriver manager as Playwright strategy needs fixing
            with self.driver_manager as driver:
                for page in task.target_pages:
                    # Handle different formats of page parameter
                    if isinstance(page, dict):
                        # Dict format: {'suffix': 'research', 'allowed_keywords': None}
                        page_type = page.get("suffix", "research")
                        allowed_keywords = page.get("allowed_keywords")
                    else:
                        # String format: 'research'
                        page_type = page
                        allowed_keywords = None
                    records.extend(
                        self._download_from_page(driver, task.stock_info, page_type, task.max_retries, allowed_keywords)
                    )

                    # Check session limit
                    if self.anti_crawler.check_session_limit(len(records)):
                        logger.info("Session download limit reached, restarting browser")
                        driver = self.driver_manager.restart_driver()
                        self.anti_crawler.apply_anti_detection(driver)
        
        except Exception as e:
            if isinstance(e, (WebDriverError, NetworkError, DownloadError)):
                raise
            raise DownloadError(
                f"Failed to execute download task: {e}",
                error_code=ErrorCode.DOWNLOAD_TASK_ERROR,
                severity=ErrorSeverity.ERROR,
                recovery_strategy=RecoveryStrategy.RETRY,
                context={"task_id": task.task_id, "stock_code": task.stock_info.stock_code},
                original_exception=e
            )
        
        return records
    
    @monitor_performance("DownloadService._download_from_page")
    def _download_from_page(
                          driver,
                          stock_info: StockInfo,
                          page_type: str,
                          max_retries: int,
                          allowed_keywords: List[str] = None) -> List[DownloadRecord]:
        """Download PDFs from specified page, supports pagination and keyword matching"""
        records = []
        
        # Check circuit breaker status
        if not self._check_circuit_breaker():
            logger.error("Circuit breaker active, skipping download")
            return records
        
        # Get page configuration
        page_config = self._get_page_config(page_type)
        max_pages = page_config.get("max_pages", self.config.get("max_pages", 5))
        
        try:
            base_url = "https://www.cninfo.com.cn"
            # Use suffix from config to build correct URL format
            url = f"{base_url}/new/disclosure/stock?orgId={stock_info.org_id}&stockCode={stock_info.stock_code}#{page_type}"

            # Remove hardcoded page type check, support all configured page types
            scraper = WebScraper(driver)

            for attempt in range(max_retries + 1):
                try:
                    logger.info(f"Accessing page: {url} (Attempt {attempt + 1})")
                    
                    driver.get(url)
                    self.anti_crawler.random_delay(0.5, 1)
                    
                    # Wait for page load - optimize timeout
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    # Simulate human behavior
                    self.anti_crawler.simulate_human_behavior(driver)
                    
                    # Pagination download
                    page_records = self._download_with_pagination(
                        driver, stock_info, page_config, max_pages, allowed_keywords
                    )
                    records.extend(page_records)
                    
                    # Record success
                    self._record_success()
                    break  # Completed successfully
                    
                except Exception as e:
                    logger.error(f"Download failed (Attempt {attempt + 1}): {e}")
                    self._record_error()
                    
                    if attempt < max_retries:
                        self.anti_crawler.handle_rate_limit(driver, attempt)
                        if attempt > 0:  # Restart browser
                            driver = self.driver_manager.restart_driver()
                            self.anti_crawler.apply_anti_detection(driver)
                    else:
                        logger.error(f"Reached max retries: {max_retries}")

        except Exception as e:
            logger.error(f"Download process failed: {e}")
            self._record_error()

        return records

    def _configure_proxy(self, proxy_info: Dict[str, Any]):
        """
        Configure proxy settings

        Args:
            proxy_info: Proxy info dictionary
        """
        try:
            proxy_host = proxy_info.get('host')
            proxy_port = proxy_info.get('port')
            proxy_type = proxy_info.get('type', 'http')

            if proxy_host and proxy_port:
                # Create proxy options
                proxy_options = {
                    'proxy': {
                        proxy_type: f"{proxy_host}:{proxy_port}"
                    }
                }

                logger.info(f"Applying proxy settings: {proxy_type}://{proxy_host}:{proxy_port}")

                # Configure proxy for new browser strategy
                if hasattr(self, 'browser_strategy_manager'):
                    current_type = self.browser_strategy_manager.get_current_type()
                    if current_type:
                        # Recreate browser strategy to apply proxy
                        config = {
                            'window_size': '1920,1080',
                            'page_load_timeout': 8,
                            'implicit_wait': 2,
                            'max_downloads_per_session': 10,
                            **proxy_options
                        }
                        self.browser_strategy = self.browser_strategy_manager.get_strategy(
                            browser_type=current_type,
                            headless=True,
                            download_dir=str(self.save_dir),
                            config=config
                        )

                # Compatible with old WebDriverManager
                if self.driver_manager.driver:
                    # Close existing driver and create new driver with proxy
                    self.driver_manager.close_driver()
                    self.driver_manager.create_driver(custom_options=proxy_options)
            else:
                logger.warning("Proxy info incomplete, skipping proxy configuration")
        except Exception as e:
            logger.error(f"Failed to configure proxy: {e}")

    def _find_detail_links(self, driver, stock_info: StockInfo, allowed_keywords: List[str] = None) -> List[Dict[str, str]]:
        """Find download links on current page (exactly replicate old version algorithm)"""
        detail_infos = []
        total_links = 0
        detail_links_found = 0
        keyword_filtered = 0
        file_exists_filtered = 0
        start_time = time.time()

        try:
            # Wait for page elements to load - optimize timeout
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.TAG_NAME, 'a'))
            )

            # Check if page loaded correctly
            if "cninfo.com.cn" not in driver.current_url:
                logger.warning("Page not loaded correctly, URL does not contain cninfo.com.cn")
                return []

            all_links = driver.find_elements(By.TAG_NAME, 'a')
            total_links = len(all_links)
            logger.debug(f"Found {total_links} links on page")

            for link in all_links:
                try:
                    text = link.text.strip()
                    href = link.get_attribute('href')

                    # Debug: Log first few links
                    if detail_links_found < 5:
                        logger.debug(f"[Debug] Link {detail_links_found + 1}: text={text[:50]}, href={href[:100] if href else 'None'}")

                    # 1. First check basic condition: must be detail page link
                    if not (href and '/new/disclosure/detail' in href
                            and f'stockCode={stock_info.stock_code}' in href):
                        continue

                    detail_links_found += 1

                    # 2. Then check keyword filtering
                    if allowed_keywords is not None:
                        # Use more flexible keyword matching
                        keyword_match = self._matches_keywords(text, allowed_keywords)
                        if not keyword_match:
                            keyword_filtered += 1
                            logger.debug(f"[Skip] Filename does not contain keywords: {text}")
                            logger.debug(f"[Debug] Keywords: {allowed_keywords}, Text: {text}")
                            continue

                    # 3. Immediately generate filename and check if file already exists
                    safe_title = re.sub(r'[\\/:*?"<>|]', '_', text)
                    file_name = f"{safe_title}.pdf"

                    # Check file existence early to avoid unnecessary processing
                    # Check stock subdirectory and root directory (compatible with old version file location)
                    file_exists = False

                    # First check stock subdirectory
                    stock_dir = self.save_dir / stock_info.stock_name
                    stock_file_path = stock_dir / file_name
                    if stock_file_path.exists() and stock_file_path.stat().st_size > 10 * 1024:
                        file_exists = True
                        file_exists_filtered += 1
                        logger.info(f"[Skip] File already exists (stock directory): {file_name}")
                    else:
                        # Then check root directory (compatible with old version file location)
                        root_file_path = self.save_dir / file_name
                        if root_file_path.exists() and root_file_path.stat().st_size > 10 * 1024:
                            file_exists = True
                            file_exists_filtered += 1
                            logger.info(f"[Skip] File already exists (root directory): {file_name}")

                    if file_exists:
                        continue

                    # 4. Only build detail info for files that need to be downloaded (aligned with old downloader data structure)
                    detail_infos.append({
                        'href': href,
                        'file_name': file_name,
                        'save_path': str(stock_dir / file_name)
                    })

                except Exception as e:
                    logger.debug(f"Error processing link: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error finding download links: {e}")

        processing_time = time.time() - start_time
        logger.info(f"Link search complete - Total links: {total_links}, Detail links: {detail_links_found}, "
                   f"Keyword filtered: {keyword_filtered}, File exists filtered: {file_exists_filtered}, "
                   f"Need download: {len(detail_infos)}, Processing time: {processing_time:.3f}s")
        return detail_infos

    def _find_detail_links_with_config(self, driver, stock_info: StockInfo, page_config: Dict[str, Any]) -> List[Dict[str, str]]:
        """Find download links on current page (using page config for complete keyword matching)"""
        detail_infos = []
        total_links = 0
        detail_links_found = 0
        keyword_filtered = 0
        file_exists_filtered = 0
        start_time = time.time()

        # Create keyword matcher
        keyword_matcher = self._create_keyword_matcher(page_config)

        try:
            # Wait for page elements to load - optimize timeout
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.TAG_NAME, 'a'))
            )

            # Check if page loaded correctly
            if "cninfo.com.cn" not in driver.current_url:
                logger.warning("Page not loaded correctly, URL does not contain cninfo.com.cn")
                return []

            all_links = driver.find_elements(By.TAG_NAME, 'a')
            total_links = len(all_links)
            logger.debug(f"Found {total_links} links on page")

            for link in all_links:
                try:
                    text = link.text.strip()
                    href = link.get_attribute('href')

                    # Debug: Log first few links
                    if detail_links_found < 5:
                        logger.debug(f"[Debug] Link {detail_links_found + 1}: text={text[:50]}, href={href[:100] if href else 'None'}")

                    # 1. First check basic condition: must be detail page link
                    if not (href and '/new/disclosure/detail' in href
                            and f'stockCode={stock_info.stock_code}' in href):
                        continue

                    detail_links_found += 1

                    # 2. Use KeywordMatcher for keyword matching (including allowed and excluded keywords)
                    keyword_match = keyword_matcher.matches(text=text, title=text)
                    if not keyword_match:
                        keyword_filtered += 1
                        logger.debug(f"[Skip] Filename does not match keyword config: {text}")
                        logger.debug(f"[Debug] Page config: {page_config}")
                        continue

                    # 3. Immediately generate filename and check if file already exists
                    safe_title = re.sub(r'[\\/:*?"<>|]', '_', text)
                    file_name = f"{safe_title}.pdf"

                    # Check file existence early to avoid unnecessary processing
                    # Check stock subdirectory and root directory (compatible with old version file location)
                    file_exists = False

                    # First check stock subdirectory
                    stock_dir = self.save_dir / stock_info.stock_name
                    stock_file_path = stock_dir / file_name
                    if stock_file_path.exists() and stock_file_path.stat().st_size > 10 * 1024:
                        file_exists = True
                        file_exists_filtered += 1
                        logger.info(f"[Skip] File already exists (stock directory): {file_name}")
                    else:
                        # Then check root directory (compatible with old version file location)
                        root_file_path = self.save_dir / file_name
                        if root_file_path.exists() and root_file_path.stat().st_size > 10 * 1024:
                            file_exists = True
                            file_exists_filtered += 1
                            logger.info(f"[Skip] File already exists (root directory): {file_name}")

                    if file_exists:
                        continue

                    # 4. Only build detail info for files that need to be downloaded (aligned with old downloader data structure)
                    detail_infos.append({
                        'href': href,
                        'file_name': file_name,
                        'save_path': str(stock_dir / file_name)
                    })

                except Exception as e:
                    logger.debug(f"Error processing link: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error finding download links: {e}")

        processing_time = time.time() - start_time
        logger.info(f"Link search complete - Total links: {total_links}, Detail links: {detail_links_found}, "
                   f"Keyword filtered: {keyword_filtered}, File exists filtered: {file_exists_filtered}, "
                   f"Need download: {len(detail_infos)}, Processing time: {processing_time:.3f}s")
        return detail_infos
    
    def _extract_date_from_link(self, link) -> str:
        """Extract date from link element"""
        try:
            # Try finding date from parent element
            parent = link.find_element(By.XPATH, "./ancestor::tr")
            date_selectors = [
                "td:nth-child(3)",
                ".el-table_1_column_3",
                ".date",
                ".time",
                "[class*='date']"
            ]
            
            for selector in date_selectors:
                try:
                    date_elem = parent.find_element(By.CSS_SELECTOR, selector)
                    date_text = date_elem.text.strip()
                    if date_text and re.match(r'\d{4}-\d{2}-\d{2}', date_text):
                        return date_text
                except:
                    continue
            
            return datetime.now().strftime("%Y-%m-%d")
        except:
            return datetime.now().strftime("%Y-%m-%d")
    
    def _extract_date_from_item(self, item) -> str:
        """Extract date from announcement item"""
        try:
            # Try multiple date selectors
            date_selectors = [
                "td:nth-child(3)",
                ".el-table_1_column_3",
                ".date",
                ".time",
                "[class*='date']"
            ]
            
            for selector in date_selectors:
                try:
                    date_elem = item.find_element(By.CSS_SELECTOR, selector)
                    date_text = date_elem.text.strip()
                    if date_text and re.match(r'\d{4}-\d{2}-\d{2}', date_text):
                        return date_text
                except:
                    continue
            
            return datetime.now().strftime("%Y-%m-%d")
        except:
            return datetime.now().strftime("%Y-%m-%d")
    
    
    def get_download_history(self) -> List[DownloadRecord]:
        """Get download history"""
        records = []
        
        try:
            for file_path in self.save_dir.glob("*.pdf"):
                stat = file_path.stat()
                
                # Create download record (filename format consistent with old version, only contains title)
                record = DownloadRecord(
                    id=str(uuid.uuid4()),
                    stock_code="unknown",  # Old version filename does not contain stock code info
                    file_name=file_path.name,
                    file_path=str(file_path),
                    file_size=stat.st_size,
                    status=DownloadStatus.COMPLETED
                )
                records.append(record)
        
        except Exception as e:
            logger.error(f"Failed to get download history: {e}")
        
        return records
    
    def cleanup_downloads(self, days: int = 30) -> int:
        """
        Cleanup old downloaded files
        
        Args:
            days: Days to keep
            
        Returns:
            int: Number of files cleaned
        """
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        try:
            for file_path in self.save_dir.glob("*.pdf"):
                if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_date:
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                        logger.info(f"Cleaned old file: {file_path.name}")
                    except Exception as e:
                        logger.error(f"Failed to clean file {file_path.name}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to clean downloaded files: {e}")
        
        return cleaned_count

    def _get_page_config(self, page_type: str) -> Dict[str, Any]:
        """Get page specific configuration"""
        pages = self.config.get("pages", [])
        for page in pages:
            if page.get("suffix") == page_type:
                return page
        return {}

    def _create_keyword_matcher(self, page_config: Dict[str, Any]):
        """Create keyword matcher"""
        from ..utils.keyword_matcher import KeywordMatcher
        return KeywordMatcher.from_dict(page_config)

    def _download_with_pagination(
                                driver,
                                stock_info: StockInfo,
                                page_config: Dict[str, Any],
                                max_pages: int,
                                allowed_keywords: List[str] = None) -> List[DownloadRecord]:
        """Pagination supported download (Enhanced version, aligned with old downloader)"""
        records = []
        scraper = WebScraper(driver)
        keyword_matcher = self._create_keyword_matcher(page_config)
        
        for page_num in range(1, max_pages + 1):
            logger.info(f"Processing page {page_num}")
            
            # Check driver health status (copied from old downloader)
            if not self.driver_manager.is_driver_healthy():
                logger.warning("Driver anomaly detected, attempting restart...")
                if not self.driver_manager.restart_driver():
                    logger.error("Failed to restart WebDriver")
                    break
                driver = self.driver_manager.get_driver()
                scraper = WebScraper(driver)
                
                # Re-access page
                try:
                    base_url = "https://www.cninfo.com.cn"
                    suffix = page_config.get("suffix", "research")
                    url = f"{base_url}/new/disclosure/stock?orgId={stock_info.org_id}&stockCode={stock_info.stock_code}#{suffix}"
                    driver.get(url)
                    self.anti_crawler.dynamic_delay(0.5, 1)
                    
                    # Navigate to current page (if not first page)
                    if page_num > 1:
                        self._navigate_to_page(driver, page_num)
                        
                except Exception as e:
                    logger.error(f"Failed to re-access page: {e}")
                    break
            
            # Simulate human behavior (copied from old downloader)
            self.anti_crawler.simulate_complex_browsing(driver)
            
            # Find detail page links (using page config for keyword matching)
            detail_links = self._find_detail_links_with_config(driver, stock_info, page_config)
            
            # Download PDF files in detail pages (using old downloader data structure)
            for link_data in detail_links:
                # Convert old data structure to new format
                converted_link_data = {
                    'title': link_data['file_name'].replace('.pdf', ''),
                    'detail_url': link_data['href'],
                    'date': None
                }
                record = self._download_from_detail_page(driver, stock_info, converted_link_data)
                if record:
                    records.append(record)
                    # Increment download count
                    self.download_count += 1
            
            # Check if browser restart is needed (copied from old downloader)
            if self.download_count >= self.max_downloads_per_session:
                logger.info("Reached single session download limit, restarting browser...")
                if not self.driver_manager.restart_driver():
                    logger.error("Failed to restart WebDriver")
                    break
                driver = self.driver_manager.get_driver()
                scraper = WebScraper(driver)
                self.download_count = 0  # Reset count
            
            # Check if pagination is needed
            if page_num >= max_pages:
                logger.info(f"Reached max pages limit: {max_pages}")
                break
                
            # Try going to next page (prefer direct page number navigation, fallback to old algorithm)
            try:
                pagination_success = scraper.go_to_page(page_num + 1)
                if not pagination_success:
                    pagination_success = self._go_to_next_page_old_style(driver)
                
                if not pagination_success:
                    logger.info("Reached last page")
                    break
            except Exception as pagination_error:
                if "chrome" in str(pagination_error).lower() or "tab crashed" in str(pagination_error).lower():
                    logger.warning(f"ChromeDriver error during pagination: {pagination_error}")
                    # Try restarting driver
                    if self.driver_manager.restart_driver():
                        driver = self.driver_manager.get_driver()
                        scraper = WebScraper(driver)
                        continue
                    else:
                        logger.error("Unable to restart WebDriver, stopping pagination")
                        break
                else:
                    logger.error(f"Pagination failed: {pagination_error}")
                    break
                
            # Wait for page load (optimize delay time)
            scraper.wait_for_page_load()
            self.anti_crawler.dynamic_delay(0.5, 1.5)
        
        return records
    
    def _navigate_to_page(self, driver, page_num):
        """Navigate to specified page (copied from old downloader)"""
        try:
            # Find page input box and go button
            page_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='number']")
            go_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), '跳转') or contains(text(), 'Go')]")
            
            if page_inputs and go_buttons:
                page_input = page_inputs[0]
                go_button = go_buttons[0]
                
                # Enter page number
                page_input.clear()
                page_input.send_keys(str(page_num))
                
                # Click go button
                go_button.click()
                
                # Wait for page load
                time.sleep(1)
                
                logger.info(f"Navigated to page {page_num}")
                return True
            else:
                # Try clicking next page button
                next_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), '下一页') or contains(@class, 'next')]")
                if next_buttons:
                    for _ in range(page_num - 1):
                        next_buttons[0].click()
                        time.sleep(1)
                    logger.info(f"Navigated to page {page_num}")
                    return True
                
        except Exception as e:
            logger.error(f"Failed to navigate to page {page_num}: {e}")
        
        return False

    def _go_to_next_page_old_style(self, driver) -> bool:
        """Use old downloader's mature pagination algorithm"""
        try:
            # Simulate human behavior
            self.anti_crawler.simulate_human_behavior(driver)
            
            # Method 1: Find next page button
            try:
                next_btn = driver.find_element(By.XPATH, "//button[contains(@class, 'el-pagination__next') and not(@disabled)]")
                if next_btn.is_enabled():
                    actions = ActionChains(driver)
                    actions.move_to_element(next_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                    self.anti_crawler.dynamic_delay(0.5, 1)
                    return True
            except Exception:
                pass
            
            # Method 2: Find right arrow button
            try:
                arrow_icon = driver.find_element(By.CSS_SELECTOR, "i.el-icon.el-icon-arrow-right")
                parent_btn = arrow_icon.find_element(By.XPATH, "./ancestor::button[not(@disabled)]")
                if parent_btn.is_enabled():
                    actions = ActionChains(driver)
                    actions.move_to_element(parent_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                    self.anti_crawler.dynamic_delay(0.5, 1)
                    return True
            except Exception:
                pass
            
            # Method 3: Find page input box (backup method)
            try:
                # Get current page number
                page_input = driver.find_element(By.CLASS_NAME, 'page-input')
                current_page = int(page_input.get_attribute('value') or '1')
                
                # Enter next page
                page_input.clear()
                page_input.send_keys(str(current_page + 1))
                
                # Find and click go button
                go_button = driver.find_element(By.CLASS_NAME, 'page-go')
                go_button.click()
                
                # Wait for page load
                self.anti_crawler.dynamic_delay(0.5, 1)
                return True
            except Exception:
                pass
                
        except Exception as e:
            logger.debug(f"Pagination failed: {e}")
        
        return False

    def _filter_links_by_keywords(
                                pdf_links: List[Dict[str, str]],
                                keyword_matcher) -> List[Dict[str, str]]:
        """Filter PDF links by keywords"""
        filtered_links = []
        
        for link_data in pdf_links:
            try:
                title = link_data.get("title", "")
                if keyword_matcher.matches(text=title, title=title):
                    filtered_links.append(link_data)
                else:
                    logger.debug(f"Skipping non-matching keywords: {title}")
            except Exception as e:
                logger.warning(f"Keyword matching failed: {e}")
                # Default include when matching fails
                filtered_links.append(link_data)
        
        return filtered_links
    
    @monitor_performance("DownloadService._download_from_detail_page")
    def _download_from_detail_page(self, driver, stock_info: StockInfo, link_data: Dict[str, str]) -> Optional[DownloadRecord]:
        """Download PDF file from detail page (Optimized version: removed duplicate file existence check)"""
        start_time = time.time()
        detail_url = link_data['detail_url']
        title = link_data['title']
        
        # Create filename (consistent with old version)
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
        file_name = f"{safe_title}.pdf"
        
        logger.debug(f"Processing detail page: {title}")
        
        # File existence check already done in _find_detail_links
        # Use company subdirectory as save path (consistent with old version)
        stock_dir = self.save_dir / stock_info.stock_name
        stock_dir.mkdir(parents=True, exist_ok=True)
        file_path = stock_dir / file_name
        
        # Set current stock directory, used for file management
        self._current_stock_dir = stock_dir
        
        # If date is needed, extract during download stage (performance optimization)
        date = link_data.get('date')
        if date is None:
            # Extract date from detail page
            try:
                # Access detail page to get date info
                driver.get(detail_url)
                self.anti_crawler.random_delay(0.5, 1.5)
                
                # Find link element in detail page to extract date
                detail_links = driver.find_elements(By.TAG_NAME, 'a')
                for link in detail_links:
                    if link.text.strip() == title:
                        date = self._extract_date_from_link(link)
                        break
            except Exception as e:
                logger.debug(f"Failed to extract date: {e}")
                date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"Accessing detail page to start download: {title}")
        
        # Add retry mechanism to handle tab crashed error and ChromeDriver error (Enhanced version)
        max_retries = 3  # Increase max retries
        for attempt in range(max_retries + 1):
            try:
                # Access detail page - add better error handling
                try:
                    driver.get(detail_url)
                except Exception as get_error:
                    if "tab crashed" in str(get_error).lower() or "chrome" in str(get_error).lower():
                        logger.warning(f"ChromeDriver error, attempting to restart driver (Attempt {attempt + 1}/{max_retries + 1}): {get_error}")
                        if attempt < max_retries:
                            # Wait longer for Chrome to fully restart
                            time.sleep(3)
                            # Restart WebDriver
                            if self.driver_manager.restart_driver():
                                driver = self.driver_manager.get_driver()
                                if driver:
                                    logger.info("WebDriver restarted successfully, continuing")
                                    continue
                                else:
                                    logger.error("WebDriver restart failed")
                                    raise get_error
                            else:
                                logger.error("Unable to restart WebDriver")
                                raise get_error
                        else:
                            logger.error(f"ChromeDriver retry failed, giving up: {get_error}")
                            raise get_error
                    else:
                        raise get_error
                
                self.anti_crawler.random_delay(0.5, 1.5)
                
                # Simulate human behavior
                self.anti_crawler.simulate_human_behavior(driver)
                
                # Find and click download button - optimize wait time
                try:
                    download_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., '公告下载')]" ))
                    )
                    
                    # Record file list before click (record both directories separately)
                    before_files_save_dir = set(os.listdir(self.save_dir))
                    
                    # Record Chrome default download directory files
                    chrome_default_downloads = os.path.expanduser("~/Downloads")
                    before_files_chrome = set()
                    if os.path.exists(chrome_default_downloads):
                        before_files_chrome = set(os.listdir(chrome_default_downloads))
                    
                    # Save initial file lists of both directories to pass to _wait_for_download
                    before_files = (before_files_save_dir, before_files_chrome)
                    
                    # Simulate human click
                    actions = ActionChains(driver)
                    actions.move_to_element(download_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                    logger.info(f"Clicked download button, waiting for file download...")
                    
                    # Wait for download complete - optimize timeout
                    if self._wait_for_download(before_files, str(file_path), timeout=60):
                        file_size = file_path.stat().st_size
                        total_time = time.time() - start_time
                        logger.info(f"Download successful: {file_name} ({file_size} bytes), Total time: {total_time:.3f}s")
                        
                        return DownloadRecord(
                            id=str(uuid.uuid4()),
                            stock_code=stock_info.stock_code,
                            file_name=file_name,
                            file_path=str(file_path),
                            file_size=file_size,
                            download_url=detail_url,
                            status=DownloadStatus.COMPLETED
                        )
                    else:
                        logger.warning(f"Download might have failed: {file_name}")
                        return DownloadRecord(
                            id=str(uuid.uuid4()),
                            stock_code=stock_info.stock_code,
                            file_name=file_name,
                            file_path=str(file_path),
                            status=DownloadStatus.FAILED,
                            error_message="File not found or file size abnormal"
                        )
                        
                except TimeoutException:
                    logger.error(f"Download button not found: {title}")
                    return DownloadRecord(
                        id=str(uuid.uuid4()),
                        stock_code=stock_info.stock_code,
                        file_name=file_name,
                        file_path=str(file_path),
                        status=DownloadStatus.FAILED,
                        error_message="Download button not found"
                    )
                
            except WebDriverException as e:
                if "tab crashed" in str(e).lower() and attempt < max_retries:
                    logger.warning(f"Tab crashed, attempting to restart WebDriver (Attempt {attempt + 1}/{max_retries})")
                    # Restart WebDriver
                    driver = self.driver_manager.restart_driver()
                    self.anti_crawler.apply_anti_detection(driver)
                    continue
                else:
                    logger.error(f"Download from detail page failed: {e}")
                    return DownloadRecord(
                        id=str(uuid.uuid4()),
                        stock_code=stock_info.stock_code,
                        file_name=link_data.get('title', 'unknown'),
                        file_path=str(self.save_dir / 'unknown.pdf'),
                        status=DownloadStatus.FAILED,
                        error_message=str(e)
                    )
            except Exception as e:
                logger.error(f"Download from detail page failed: {e}")
                return DownloadRecord(
                    id=str(uuid.uuid4()),
                    stock_code=stock_info.stock_code,
                    file_name=link_data.get('title', 'unknown'),
                    file_path=str(self.save_dir / 'unknown.pdf'),
                    status=DownloadStatus.FAILED,
                    error_message=str(e)
                )
        
        # All retries failed
        total_time = time.time() - start_time
        logger.error(f"Download from detail page failed: Reached max retries {max_retries}, Total time: {total_time:.3f}s")
        return DownloadRecord(
            id=str(uuid.uuid4()),
            stock_code=stock_info.stock_code,
            file_name=link_data.get('title', 'unknown'),
            file_path=str(self.save_dir / 'unknown.pdf'),
            status=DownloadStatus.FAILED,
            error_message=f"Reached max retries {max_retries}"
        )
    
    @monitor_performance("DownloadService._wait_for_download")
    def _wait_for_download(self, before_files, target_path, timeout=60):
        """Wait for file download complete (Performance optimized version)"""
        start_time = time.time()
        check_interval = 0.5  # Start with 0.5s interval
        
        while time.time() - start_time < timeout:
            time.sleep(check_interval)
            # Progressively increase check interval, max 2.0s
            check_interval = min(check_interval * 1.2, 2.0)
            
            # Clean pdf.txt file
            self._cleanup_pdf_txt()
            
            # Check for new file (Aligned with old downloader: check entire download directory first)
            try:
                # Parse initial file lists of two directories
                before_files_save_dir, before_files_chrome = before_files
                
                # Method 1: Check configured download directory
                after_files_save_dir = set(os.listdir(self.save_dir))
                new_files_save_dir = after_files_save_dir - before_files_save_dir
                
                # Method 2: Check Chrome default download directory
                chrome_default_downloads = os.path.expanduser("~/Downloads")
                new_files_chrome = set()
                if os.path.exists(chrome_default_downloads):
                    after_files_chrome = set(os.listdir(chrome_default_downloads))
                    new_files_chrome = after_files_chrome - before_files_chrome
                        
                # Merge new files from both directories
                new_files = new_files_save_dir.union(new_files_chrome)
                
                # Move new files from Chrome default directory to configured download directory
                for file in new_files_chrome:
                    chrome_file_path = os.path.join(chrome_default_downloads, file)
                    if file.lower().endswith('.pdf') and os.path.exists(chrome_file_path):
                        target_file_path = os.path.join(self.save_dir, file)
                        try:
                            shutil.move(chrome_file_path, target_file_path)
                            logger.info(f"Moved file from Chrome default dir: {chrome_file_path} -> {target_file_path}")
                        except Exception as e:
                            logger.error(f"Failed to move Chrome default dir file: {e}")
                
                for file in new_files:
                    file_path = os.path.join(self.save_dir, file)
                    
                    if file.lower().endswith('.pdf') and os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        
                        if file_size > 10 * 1024:  # File larger than 10KB
                            # Move file to target location (ensure moving to correct subdirectory)
                            if file_path != target_path:
                                try:
                                    # Ensure target directory exists
                                    target_dir = Path(target_path).parent
                                    target_dir.mkdir(parents=True, exist_ok=True)
                                    
                                    # If target file exists, delete first
                                    if Path(target_path).exists():
                                        Path(target_path).unlink()
                                    
                                    shutil.move(file_path, target_path)
                                    logger.info(f"File move successful: {file_path} -> {target_path}")
                                except Exception as e:
                                    logger.error(f"File move failed: {file_path} -> {target_path}, Error: {e}")
                                    # If move failed, at least ensure file is in correct subdirectory
                                    try:
                                        target_dir = Path(target_path).parent
                                        fallback_path = target_dir / Path(file).name
                                        if fallback_path != file_path:
                                            shutil.move(file_path, fallback_path)
                                            logger.info(f"File moved to fallback location: {file_path} -> {fallback_path}")
                                    except Exception:
                                        pass
                            return True
                        else:
                            # Delete too small file
                            try:
                                os.remove(file_path)
                                logger.info(f"Deleted too small file: {file_path}")
                            except Exception:
                                pass
                
                # Method 2: Check if target file already exists and size is appropriate
                if os.path.exists(target_path) and os.path.getsize(target_path) > 10 * 1024:
                    return True
                
                # Method 3: Check company subdirectory (as supplement)
                target_path_obj = Path(target_path)
                stock_dir = target_path_obj.parent
                if stock_dir.exists() and stock_dir != Path(self.save_dir):
                    after_files_stock = set(os.listdir(stock_dir))
                    new_files_stock = after_files_stock - before_files
                    
                    for file in new_files_stock:
                        file_path = os.path.join(stock_dir, file)
                        if file.lower().endswith('.pdf') and os.path.exists(file_path):
                            file_size = os.path.getsize(file_path)
                            if file_size > 10 * 1024:
                                if file_path != target_path:
                                    try:
                                        shutil.move(file_path, target_path)
                                    except Exception:
                                        pass
                                return True
                            
            except Exception as e:
                logger.debug(f"Error checking download file: {e}")
        
        # After timeout, clean up potentially residual files in root directory
        try:
            after_files = set(os.listdir(self.save_dir))
            new_files = after_files - before_files
            
            for file in new_files:
                file_path = os.path.join(self.save_dir, file)
                if file.lower().endswith('.pdf') and os.path.exists(file_path):
                    logger.warning(f"Cleaning timeout unprocessed file: {file_path}")
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Failed to clean residual files: {e}")
        
        return False
    
    def _cleanup_pdf_txt(self):
        """Clean pdf.txt file (clean root directory and company directory)"""
        try:
            # Clean pdf.txt under root directory
            root_pdf_txt = os.path.join(self.save_dir, 'pdf.txt')
            if os.path.exists(root_pdf_txt):
                try:
                    os.remove(root_pdf_txt)
                except Exception:
                    pass

            # Check current used company directory
            if hasattr(self, '_current_stock_dir') and self._current_stock_dir and self._current_stock_dir.exists():
                for file in os.listdir(self._current_stock_dir):
                    if file.lower() == 'pdf.txt':
                        os.remove(os.path.join(self._current_stock_dir, file))
            else:
                # Fallback to check all possible directories
                for item in os.listdir(self.save_dir):
                    item_path = os.path.join(self.save_dir, item)
                    if os.path.isdir(item_path):
                        for file in os.listdir(item_path):
                            if file.lower() == 'pdf.txt':
                                try:
                                    os.remove(os.path.join(item_path, file))
                                except Exception:
                                    pass
        except Exception:
            pass
    
    # New method to align with old downloader
    def dynamic_delay(self, base_min=2, base_max=8):
        """Dynamic delay (copied from old downloader)"""
        return self.anti_crawler.dynamic_delay(base_min, base_max)
    
    @property
    def retry_count(self):
        """Get retry count (copied from old downloader)"""
        return getattr(self, '_retry_count', 0)
    
    @retry_count.setter
    def retry_count(self, value):
        """Set retry count"""
        self._retry_count = value
    
    @property
    def max_retries(self):
        """Get max retries"""
        return getattr(self, '_max_retries', 3)
    
    def should_retry(self):
        """Check if should retry"""
        return self.retry_count < self.max_retries
    
    def log_info(self, message):
        """Log info message"""
        logger.info(message)
    
    def log_error(self, message):
        """Log error message"""
        logger.error(message)
    
    def log_warning(self, message):
        """Log warning message"""
        logger.warning(message)
    
    def get_status(self):
        """Get status info"""
        return {
            'download_count': self.download_count,
            'retry_count': self.retry_count,
            'success_count': getattr(self, '_success_count', 0),
            'error_count': getattr(self, '_error_count', 0)
        }
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.driver_manager.close_driver()
            self._cleanup_pdf_txt()
        except Exception as e:
            logger.error(f"Failed to cleanup resources: {e}")
    
    def _build_disclosure_url(self, stock_code, org_id):
        """Build disclosure page URL (copied from old downloader)"""
        return f"https://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#research"
    
    def _generate_file_path(self, stock_name, file_title):
        """Generate file path (copied from old downloader)"""
        company_dir = self.save_dir / stock_name
        company_dir.mkdir(exist_ok=True)
        
        clean_title = self.clean_filename(file_title)
        if not clean_title.lower().endswith('.pdf'):
            clean_title += '.pdf'
        
        return str(company_dir / clean_title)
    
    def _file_exists_and_valid(self, file_path):
        """Check if file exists and is valid"""
        try:
            return os.path.exists(file_path) and os.path.getsize(file_path) > 10 * 1024
        except Exception:
            return False
    
    def _clean_filename(self, filename):
        """Clean filename (compatible method)"""
        return self.clean_filename(filename)
    
    def _matches_keywords(self, text, allowed_keywords):
        """Check if text matches keywords"""
        if not allowed_keywords:
            return True
        
        text_lower = text.lower()
        for keyword in allowed_keywords:
            if keyword.lower() in text_lower:
                return True
        return False
    
    def _check_circuit_breaker(self):
        """Check circuit breaker status"""
        if not self._circuit_breaker_active:
            return True
        
        if self._last_error_time is None:
            return True
        
        # Check if timeout
        if time.time() - self._last_error_time > self._circuit_breaker_timeout:
            logger.info("Circuit breaker timeout, resetting status")
            self._reset_circuit_breaker()
            return True
        
        return False
    
    def _activate_circuit_breaker(self):
        """Activate circuit breaker"""
        self._circuit_breaker_active = True
        self._last_error_time = time.time()
        logger.warning(f"Circuit breaker activated, wait {self._circuit_breaker_timeout} seconds before retry")
    
    def _reset_circuit_breaker(self):
        """Reset circuit breaker"""
        self._circuit_breaker_active = False
        self._consecutive_errors = 0
        self._last_error_time = None
        logger.info("Circuit breaker reset")
    
    def _record_error(self):
        """Record error"""
        self._consecutive_errors += 1
        self._last_error_time = time.time()
        
        if self._consecutive_errors >= self._max_consecutive_errors:
            self._activate_circuit_breaker()
    
    def _record_success(self):
        """Record success"""
        self._consecutive_errors = 0
        if self._circuit_breaker_active:
            logger.info("Successfully recovered, resetting circuit breaker")
            self._reset_circuit_breaker()
    
    def __del__(self):
        """Destructor"""
        try:
            self.driver_manager.close_driver()
        except Exception:
            pass
