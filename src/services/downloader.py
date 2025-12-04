"""
下载服务模块
提供投资者关系活动记录表的下载功能
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
    """股票信息服务类，提供股票相关的基础服务"""
    
    def __init__(self, mapping_file: str = "stock_orgid_mapping.json"):
        """
        初始化股票服务
        
        Args:
            mapping_file: 映射文件路径
        """
        self.mapping_manager = MappingManager(mapping_file)
        self.config = ConfigManager()
    
    def get_stock_info(self, stock_code: str) -> Optional[Dict[str, str]]:
        """
        获取股票信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Optional[Dict[str, str]]: 股票信息字典，包含org_id和stock_name
        """
        try:
            # 获取组织ID
            org_id = self.mapping_manager.get_org_id(stock_code)
            if not org_id:
                logger.warning(f"未找到股票代码 {stock_code} 的组织ID")
                return None
            
            # 获取股票名称
            stock_name = self.mapping_manager.get_stock_name(stock_code)
            if not stock_name:
                stock_name = stock_code
                logger.warning(f"使用股票代码作为名称: {stock_code}")
            
            return {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'org_id': org_id
            }
            
        except Exception as e:
            logger.error(f"获取股票信息失败: {e}")
            return None
    
    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """
        获取股票名称
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Optional[str]: 股票名称
        """
        return self.mapping_manager.get_stock_name(stock_code)
    
    def get_org_id(self, stock_code: str, force_refresh: bool = False) -> Optional[str]:
        """
        获取组织ID
        
        Args:
            stock_code: 股票代码
            force_refresh: 是否强制刷新
            
        Returns:
            Optional[str]: 组织ID
        """
        return self.mapping_manager.get_org_id(stock_code, force_refresh)
    
    def validate_stock_code(self, stock_code: str) -> bool:
        """
        验证股票代码格式
        
        Args:
            stock_code: 股票代码
            
        Returns:
            bool: 是否有效
        """
        if not stock_code:
            return False
        
        # 使用优化的股票代码标准化
        standardized = standardize_stock_code(stock_code)
        return standardized is not None
    
    def get_all_stock_codes(self) -> List[str]:
        """
        获取所有股票代码
        
        Returns:
            List[str]: 股票代码列表
        """
        return self.mapping_manager.get_all_stock_codes()
    
    def get_stock_statistics(self) -> Dict[str, int]:
        """
        获取股票统计信息
        
        Returns:
            Dict[str, int]: 统计信息
        """
        return self.mapping_manager.get_statistics()


class DownloadService:
    """投资者关系活动记录表下载服务"""
    
    def __init__(self,
                 save_dir: str = "downloads",
                 mapping_file: str = "stock_orgid_mapping.json",
                 config_file: Optional[str] = None):
        """
        初始化下载服务（增强版，对齐旧下载器）
        
        Args:
            save_dir: 下载文件保存目录
            mapping_file: 映射文件路径
        """
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.mapping_file = mapping_file
        
        self.mapping_manager = MappingManager(mapping_file)

        # 初始化浏览器策略管理器
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

        # 兼容旧的WebDriverManager（用于过渡）
        self.driver_manager = WebDriverManager(
            headless=True,
            download_dir=str(self.save_dir),
            max_downloads_per_session=10,
            page_load_timeout=8,
            implicit_wait=2,
            config_file=config_file
        )
        self.anti_crawler = AntiCrawlerStrategy()

        # 加载配置
        self.config = ConfigManager(config_file)
        self.logger = logger  # 添加实例级logger属性用于测试
        
        # 从旧下载器复制的关键属性
        self.download_count = 0  # 下载计数器
        self.max_downloads_per_session = self.config.get('download.max_downloads_per_session', 5)  # 每个会话最大下载数
        
        # 配置反爬虫策略
        human_behavior_delay = self.config.get('download.human_behavior_delay', 3)
        # 确保 human_behavior_delay 是整数
        if isinstance(human_behavior_delay, list):
            # 如果是列表，取第一个元素或平均值
            human_behavior_delay = human_behavior_delay[0] if human_behavior_delay else 3
        elif not isinstance(human_behavior_delay, (int, float)):
            # 如果不是数字类型，使用默认值
            human_behavior_delay = 3
        
        # 确保是整数
        human_behavior_delay = int(human_behavior_delay)
        
        self.anti_crawler.set_session_parameters(
            min_delay=max(1, human_behavior_delay - 1),
            max_delay=human_behavior_delay + 2,  # 减少最大延迟
            max_downloads=self.max_downloads_per_session
        )
        
        # 当前公司目录（用于文件管理）
        self._current_stock_dir = None
        
        # 错误恢复机制
        self._consecutive_errors = 0
        self._max_consecutive_errors = 3
        self._circuit_breaker_active = False
        self._last_error_time = None
        self._circuit_breaker_timeout = 60  # 60秒后重试
    
    def clean_filename(self, filename):
        """清理文件名中的非法字符（从旧下载器复制）"""
        if not filename:
            return filename
        # 去除首尾空格
        filename = filename.strip()
        # 替换非法字符
        filename = re.sub(r'[\\\/:*?"<>|]', '_', filename)
        # 处理空格和点的组合：将连续的空格和点序列替换为单个点
        # 首先将空格点序列标准化：将空格和点交错序列替换为单个点
        # 使用正则表达式匹配任意数量的空格和点（至少一个点），替换为单个点
        filename = re.sub(r'(?:\s*\.)+\s*', '.', filename)
        # 确保没有连续的点（可能由上述替换产生）
        filename = re.sub(r'\.{2,}', '.', filename)
        return filename
    
    def get_org_id(self, stock_code, force_run=False):
        """获取股票代码对应的组织ID（从旧下载器复制）"""
        return self.mapping_manager.get_org_id(stock_code, force_refresh=force_run)
    
    @monitor_performance("DownloadService.download_stock_pdfs")
    def download_stock_pdfs(self,
                          stock_code: str,
                          target_pages: Optional[List[Union[str, Dict[str, Any]]]] = None,
                          max_retries: int = 3,
                          proxy_info: Optional[Dict[str, Any]] = None) -> List[DownloadRecord]:
        """
        下载指定股票的PDF文件

        Args:
            stock_code: 股票代码
            target_pages: 目标页面列表（支持字符串格式或字典格式）
            max_retries: 最大重试次数
            proxy_info: 代理信息（用于多公司并行下载）

        Returns:
            List[DownloadRecord]: 下载记录列表
        """
        if target_pages is None:
            target_pages = ["research"]

        # 转换字典格式的target_pages为字符串格式
        normalized_target_pages = []
        for page in target_pages:
            if isinstance(page, dict):
                # 字典格式: {'suffix': 'research', 'allowed_keywords': None}
                suffix = page.get('suffix', 'research')
                normalized_target_pages.append(suffix)
            else:
                # 字符串格式: 'research'
                normalized_target_pages.append(page)

        target_pages = normalized_target_pages

        # 如果提供了代理信息，配置代理
        if proxy_info:
            self._configure_proxy(proxy_info)

        stock_info = self._get_stock_info(stock_code)
        if not stock_info or not stock_info.org_id:
            logger.error(f"无法获取组织ID: {stock_code}")
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
        """获取股票信息（与旧下载器对齐）"""
        try:
            # 使用与旧下载器相同的股票名称获取逻辑
            from get_stock_name import get_stock_name
            
            stock_name = get_stock_name(stock_code, self.mapping_file)
            
            # 如果获取失败，使用股票代码作为名称
            if not stock_name or stock_name.startswith('错误') or stock_name.startswith('网络'):
                stock_name = stock_code
                logger.warning(f"使用股票代码作为名称: {stock_name}")
            
            org_id = self.mapping_manager.get_org_id(stock_code)
            if not org_id:
                raise DownloadError(
                    f"无法获取组织ID: {stock_code}",
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
                f"获取股票信息失败: {e}",
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
        """执行下载任务"""
        records = []

        try:
            # 暂时使用WebDriver管理器，因为Playwright策略需要修复
            with self.driver_manager as driver:
                for page in task.target_pages:
                    # 处理不同格式的page参数
                    if isinstance(page, dict):
                        # 字典格式: {'suffix': 'research', 'allowed_keywords': None}
                        page_type = page.get("suffix", "research")
                        allowed_keywords = page.get("allowed_keywords")
                    else:
                        # 字符串格式: 'research'
                        page_type = page
                        allowed_keywords = None
                    records.extend(
                        self._download_from_page(driver, task.stock_info, page_type, task.max_retries, allowed_keywords)
                    )

                    # 检查会话限制
                    if self.anti_crawler.check_session_limit(len(records)):
                        logger.info("达到会话下载限制，重启浏览器")
                        driver = self.driver_manager.restart_driver()
                        self.anti_crawler.apply_anti_detection(driver)
        
        except Exception as e:
            if isinstance(e, (WebDriverError, NetworkError, DownloadError)):
                raise
            raise DownloadError(
                f"执行下载任务失败: {e}",
                error_code=ErrorCode.DOWNLOAD_TASK_ERROR,
                severity=ErrorSeverity.ERROR,
                recovery_strategy=RecoveryStrategy.RETRY,
                context={"task_id": task.task_id, "stock_code": task.stock_info.stock_code},
                original_exception=e
            )
        
        return records
    
    @monitor_performance("DownloadService._download_from_page")
    def _download_from_page(self, 
                          driver,
                          stock_info: StockInfo,
                          page_type: str,
                          max_retries: int,
                          allowed_keywords: List[str] = None) -> List[DownloadRecord]:
        """从指定页面下载PDF，支持分页和关键词匹配"""
        records = []
        
        # 检查断路器状态
        if not self._check_circuit_breaker():
            logger.error("断路器激活中，跳过下载")
            return records
        
        # 获取页面配置
        page_config = self._get_page_config(page_type)
        max_pages = page_config.get("max_pages", self.config.get("max_pages", 5))
        
        try:
            base_url = "https://www.cninfo.com.cn"
            # 使用配置中的suffix构建正确的URL格式
            url = f"{base_url}/new/disclosure/stock?orgId={stock_info.org_id}&stockCode={stock_info.stock_code}#{page_type}"

            # 移除硬编码的页面类型检查，支持所有配置的页面类型
            scraper = WebScraper(driver)

            for attempt in range(max_retries + 1):
                try:
                    logger.info(f"访问页面: {url} (尝试 {attempt + 1})")
                    
                    driver.get(url)
                    self.anti_crawler.random_delay(0.5, 1)
                    
                    # 等待页面加载 - 优化超时时间
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    # 模拟人类行为
                    self.anti_crawler.simulate_human_behavior(driver)
                    
                    # 分页下载
                    page_records = self._download_with_pagination(
                        driver, stock_info, page_config, max_pages, allowed_keywords
                    )
                    records.extend(page_records)
                    
                    # 记录成功
                    self._record_success()
                    break  # 成功完成
                    
                except Exception as e:
                    logger.error(f"下载失败 (尝试 {attempt + 1}): {e}")
                    self._record_error()
                    
                    if attempt < max_retries:
                        self.anti_crawler.handle_rate_limit(driver, attempt)
                        if attempt > 0:  # 重启浏览器
                            driver = self.driver_manager.restart_driver()
                            self.anti_crawler.apply_anti_detection(driver)
                    else:
                        logger.error(f"达到最大重试次数: {max_retries}")

        except Exception as e:
            logger.error(f"下载过程失败: {e}")
            self._record_error()

        return records

    def _configure_proxy(self, proxy_info: Dict[str, Any]):
        """
        配置代理设置

        Args:
            proxy_info: 代理信息字典
        """
        try:
            proxy_host = proxy_info.get('host')
            proxy_port = proxy_info.get('port')
            proxy_type = proxy_info.get('type', 'http')

            if proxy_host and proxy_port:
                # 创建代理选项
                proxy_options = {
                    'proxy': {
                        proxy_type: f"{proxy_host}:{proxy_port}"
                    }
                }

                logger.info(f"应用代理设置: {proxy_type}://{proxy_host}:{proxy_port}")

                # 为新的浏览器策略配置代理
                if hasattr(self, 'browser_strategy_manager'):
                    current_type = self.browser_strategy_manager.get_current_type()
                    if current_type:
                        # 重新创建浏览器策略以应用代理
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

                # 兼容旧的WebDriverManager
                if self.driver_manager.driver:
                    # 关闭现有驱动并创建新的带代理的驱动
                    self.driver_manager.close_driver()
                    self.driver_manager.create_driver(custom_options=proxy_options)
            else:
                logger.warning("代理信息不完整，跳过代理配置")
        except Exception as e:
            logger.error(f"配置代理失败: {e}")

    def _find_detail_links(self, driver, stock_info: StockInfo, allowed_keywords: List[str] = None) -> List[Dict[str, str]]:
        """查找当前页面的下载链接（精确复制旧版本算法）"""
        detail_infos = []
        total_links = 0
        detail_links_found = 0
        keyword_filtered = 0
        file_exists_filtered = 0
        start_time = time.time()

        try:
            # 等待页面元素加载 - 优化超时时间
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.TAG_NAME, 'a'))
            )

            # 检查页面是否正常加载
            if "cninfo.com.cn" not in driver.current_url:
                logger.warning("页面未正确加载，URL不包含cninfo.com.cn")
                return []

            all_links = driver.find_elements(By.TAG_NAME, 'a')
            total_links = len(all_links)
            logger.debug(f"页面中共找到 {total_links} 个链接")

            for link in all_links:
                try:
                    text = link.text.strip()
                    href = link.get_attribute('href')

                    # 调试：记录前几个链接
                    if detail_links_found < 5:
                        logger.debug(f"[调试] 链接 {detail_links_found + 1}: text={text[:50]}, href={href[:100] if href else 'None'}")

                    # 1. 首先检查基本条件：必须是详情页链接
                    if not (href and '/new/disclosure/detail' in href
                            and f'stockCode={stock_info.stock_code}' in href):
                        continue

                    detail_links_found += 1

                    # 2. 然后检查关键词过滤
                    if allowed_keywords is not None:
                        # 使用更灵活的关键词匹配
                        keyword_match = self._matches_keywords(text, allowed_keywords)
                        if not keyword_match:
                            keyword_filtered += 1
                            logger.debug(f"[跳过] 文件名不包含关键词: {text}")
                            logger.debug(f"[调试] 关键词: {allowed_keywords}, 文本: {text}")
                            continue

                    # 3. 立即生成文件名并检查文件是否已存在
                    safe_title = re.sub(r'[\\/:*?"<>|]', '_', text)
                    file_name = f"{safe_title}.pdf"

                    # 尽早检查文件存在性，避免不必要的处理
                    # 检查股票子目录和根目录（兼容旧版本文件位置）
                    file_exists = False

                    # 首先检查股票子目录
                    stock_dir = self.save_dir / stock_info.stock_name
                    stock_file_path = stock_dir / file_name
                    if stock_file_path.exists() and stock_file_path.stat().st_size > 10 * 1024:
                        file_exists = True
                        file_exists_filtered += 1
                        logger.info(f"[跳过] 文件已存在 (股票目录): {file_name}")
                    else:
                        # 然后检查根目录（兼容旧版本文件位置）
                        root_file_path = self.save_dir / file_name
                        if root_file_path.exists() and root_file_path.stat().st_size > 10 * 1024:
                            file_exists = True
                            file_exists_filtered += 1
                            logger.info(f"[跳过] 文件已存在 (根目录): {file_name}")

                    if file_exists:
                        continue

                    # 4. 只有需要下载的文件才构建详细信息（对齐旧下载器数据结构）
                    detail_infos.append({
                        'href': href,
                        'file_name': file_name,
                        'save_path': str(stock_dir / file_name)
                    })

                except Exception as e:
                    logger.debug(f"处理链接时发生错误: {e}")
                    continue

        except Exception as e:
            logger.error(f"查找下载链接时发生错误: {e}")

        processing_time = time.time() - start_time
        logger.info(f"链接查找完成 - 总链接: {total_links}, 详情链接: {detail_links_found}, "
                   f"关键词过滤: {keyword_filtered}, 文件存在过滤: {file_exists_filtered}, "
                   f"需要下载: {len(detail_infos)}, 处理时间: {processing_time:.3f}s")
        return detail_infos

    def _find_detail_links_with_config(self, driver, stock_info: StockInfo, page_config: Dict[str, Any]) -> List[Dict[str, str]]:
        """查找当前页面的下载链接（使用页面配置进行完整关键词匹配）"""
        detail_infos = []
        total_links = 0
        detail_links_found = 0
        keyword_filtered = 0
        file_exists_filtered = 0
        start_time = time.time()

        # 创建关键词匹配器
        keyword_matcher = self._create_keyword_matcher(page_config)

        try:
            # 等待页面元素加载 - 优化超时时间
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.TAG_NAME, 'a'))
            )

            # 检查页面是否正常加载
            if "cninfo.com.cn" not in driver.current_url:
                logger.warning("页面未正确加载，URL不包含cninfo.com.cn")
                return []

            all_links = driver.find_elements(By.TAG_NAME, 'a')
            total_links = len(all_links)
            logger.debug(f"页面中共找到 {total_links} 个链接")

            for link in all_links:
                try:
                    text = link.text.strip()
                    href = link.get_attribute('href')

                    # 调试：记录前几个链接
                    if detail_links_found < 5:
                        logger.debug(f"[调试] 链接 {detail_links_found + 1}: text={text[:50]}, href={href[:100] if href else 'None'}")

                    # 1. 首先检查基本条件：必须是详情页链接
                    if not (href and '/new/disclosure/detail' in href
                            and f'stockCode={stock_info.stock_code}' in href):
                        continue

                    detail_links_found += 1

                    # 2. 使用KeywordMatcher进行关键词匹配（包含允许和排除关键词）
                    keyword_match = keyword_matcher.matches(text=text, title=text)
                    if not keyword_match:
                        keyword_filtered += 1
                        logger.debug(f"[跳过] 文件名不符合关键词配置: {text}")
                        logger.debug(f"[调试] 页面配置: {page_config}")
                        continue

                    # 3. 立即生成文件名并检查文件是否已存在
                    safe_title = re.sub(r'[\\/:*?"<>|]', '_', text)
                    file_name = f"{safe_title}.pdf"

                    # 尽早检查文件存在性，避免不必要的处理
                    # 检查股票子目录和根目录（兼容旧版本文件位置）
                    file_exists = False

                    # 首先检查股票子目录
                    stock_dir = self.save_dir / stock_info.stock_name
                    stock_file_path = stock_dir / file_name
                    if stock_file_path.exists() and stock_file_path.stat().st_size > 10 * 1024:
                        file_exists = True
                        file_exists_filtered += 1
                        logger.info(f"[跳过] 文件已存在 (股票目录): {file_name}")
                    else:
                        # 然后检查根目录（兼容旧版本文件位置）
                        root_file_path = self.save_dir / file_name
                        if root_file_path.exists() and root_file_path.stat().st_size > 10 * 1024:
                            file_exists = True
                            file_exists_filtered += 1
                            logger.info(f"[跳过] 文件已存在 (根目录): {file_name}")

                    if file_exists:
                        continue

                    # 4. 只有需要下载的文件才构建详细信息（对齐旧下载器数据结构）
                    detail_infos.append({
                        'href': href,
                        'file_name': file_name,
                        'save_path': str(stock_dir / file_name)
                    })

                except Exception as e:
                    logger.debug(f"处理链接时发生错误: {e}")
                    continue

        except Exception as e:
            logger.error(f"查找下载链接时发生错误: {e}")

        processing_time = time.time() - start_time
        logger.info(f"链接查找完成 - 总链接: {total_links}, 详情链接: {detail_links_found}, "
                   f"关键词过滤: {keyword_filtered}, 文件存在过滤: {file_exists_filtered}, "
                   f"需要下载: {len(detail_infos)}, 处理时间: {processing_time:.3f}s")
        return detail_infos
    
    def _extract_date_from_link(self, link) -> str:
        """从链接元素提取日期"""
        try:
            # 尝试从父元素中查找日期
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
        """从公告条目提取日期"""
        try:
            # 尝试多种日期选择器
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
        """获取下载历史"""
        records = []
        
        try:
            for file_path in self.save_dir.glob("*.pdf"):
                stat = file_path.stat()
                
                # 创建下载记录（文件名格式与老版本保持一致，只包含标题）
                record = DownloadRecord(
                    id=str(uuid.uuid4()),
                    stock_code="unknown",  # 老版本文件名不包含股票代码信息
                    file_name=file_path.name,
                    file_path=str(file_path),
                    file_size=stat.st_size,
                    status=DownloadStatus.COMPLETED
                )
                records.append(record)
        
        except Exception as e:
            logger.error(f"获取下载历史失败: {e}")
        
        return records
    
    def cleanup_downloads(self, days: int = 30) -> int:
        """
        清理旧下载文件
        
        Args:
            days: 保留天数
            
        Returns:
            int: 清理的文件数量
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
                        logger.info(f"清理旧文件: {file_path.name}")
                    except Exception as e:
                        logger.error(f"清理文件失败 {file_path.name}: {e}")
        
        except Exception as e:
            logger.error(f"清理下载文件失败: {e}")
        
        return cleaned_count

    def _get_page_config(self, page_type: str) -> Dict[str, Any]:
        """获取页面特定配置"""
        pages = self.config.get("pages", [])
        for page in pages:
            if page.get("suffix") == page_type:
                return page
        return {}

    def _create_keyword_matcher(self, page_config: Dict[str, Any]):
        """创建关键词匹配器"""
        from ..utils.keyword_matcher import KeywordMatcher
        return KeywordMatcher.from_dict(page_config)

    def _download_with_pagination(self,
                                driver,
                                stock_info: StockInfo,
                                page_config: Dict[str, Any],
                                max_pages: int,
                                allowed_keywords: List[str] = None) -> List[DownloadRecord]:
        """支持分页的下载（增强版，对齐旧下载器）"""
        records = []
        scraper = WebScraper(driver)
        keyword_matcher = self._create_keyword_matcher(page_config)
        
        for page_num in range(1, max_pages + 1):
            logger.info(f"正在处理第 {page_num} 页")
            
            # 检查driver健康状态（从旧下载器复制）
            if not self.driver_manager.is_driver_healthy():
                logger.warning("检测到driver异常，尝试重启...")
                if not self.driver_manager.restart_driver():
                    logger.error("重启WebDriver失败")
                    break
                driver = self.driver_manager.get_driver()
                scraper = WebScraper(driver)
                
                # 重新访问页面
                try:
                    base_url = "https://www.cninfo.com.cn"
                    suffix = page_config.get("suffix", "research")
                    url = f"{base_url}/new/disclosure/stock?orgId={stock_info.org_id}&stockCode={stock_info.stock_code}#{suffix}"
                    driver.get(url)
                    self.anti_crawler.dynamic_delay(0.5, 1)
                    
                    # 导航到当前页（如果不是第一页）
                    if page_num > 1:
                        self._navigate_to_page(driver, page_num)
                        
                except Exception as e:
                    logger.error(f"重新访问页面失败: {e}")
                    break
            
            # 模拟人类行为（从旧下载器复制）
            self.anti_crawler.simulate_complex_browsing(driver)
            
            # 查找详情页链接（使用页面配置进行关键词匹配）
            detail_links = self._find_detail_links_with_config(driver, stock_info, page_config)
            
            # 下载详情页中的PDF文件（使用旧下载器的数据结构）
            for link_data in detail_links:
                # 将旧数据结构转换为新格式
                converted_link_data = {
                    'title': link_data['file_name'].replace('.pdf', ''),
                    'detail_url': link_data['href'],
                    'date': None
                }
                record = self._download_from_detail_page(driver, stock_info, converted_link_data)
                if record:
                    records.append(record)
                    # 增加下载计数
                    self.download_count += 1
            
            # 检查是否需要重启浏览器（从旧下载器复制）
            if self.download_count >= self.max_downloads_per_session:
                logger.info("达到单次会话下载限制，重启浏览器...")
                if not self.driver_manager.restart_driver():
                    logger.error("重启WebDriver失败")
                    break
                driver = self.driver_manager.get_driver()
                scraper = WebScraper(driver)
                self.download_count = 0  # 重置计数
            
            # 检查是否需要翻页
            if page_num >= max_pages:
                logger.info(f"已达到最大页数限制: {max_pages}")
                break
                
            # 尝试翻到下一页（优先使用直接页码导航，失败时使用旧算法）
            try:
                pagination_success = scraper.go_to_page(page_num + 1)
                if not pagination_success:
                    pagination_success = self._go_to_next_page_old_style(driver)
                
                if not pagination_success:
                    logger.info("已到达最后一页")
                    break
            except Exception as pagination_error:
                if "chrome" in str(pagination_error).lower() or "tab crashed" in str(pagination_error).lower():
                    logger.warning(f"翻页时发生ChromeDriver错误: {pagination_error}")
                    # 尝试重启driver
                    if self.driver_manager.restart_driver():
                        driver = self.driver_manager.get_driver()
                        scraper = WebScraper(driver)
                        continue
                    else:
                        logger.error("无法重启WebDriver，停止翻页")
                        break
                else:
                    logger.error(f"翻页失败: {pagination_error}")
                    break
                
            # 等待页面加载（优化延迟时间）
            scraper.wait_for_page_load()
            self.anti_crawler.dynamic_delay(0.5, 1.5)
        
        return records
    
    def _navigate_to_page(self, driver, page_num):
        """导航到指定页面（从旧下载器复制）"""
        try:
            # 查找页码输入框和跳转按钮
            page_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='number']")
            go_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), '跳转') or contains(text(), 'Go')]")
            
            if page_inputs and go_buttons:
                page_input = page_inputs[0]
                go_button = go_buttons[0]
                
                # 输入页码
                page_input.clear()
                page_input.send_keys(str(page_num))
                
                # 点击跳转按钮
                go_button.click()
                
                # 等待页面加载
                time.sleep(1)
                
                logger.info(f"已导航到第{page_num}页")
                return True
            else:
                # 尝试点击下一页按钮
                next_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), '下一页') or contains(@class, 'next')]")
                if next_buttons:
                    for _ in range(page_num - 1):
                        next_buttons[0].click()
                        time.sleep(1)
                    logger.info(f"已导航到第{page_num}页")
                    return True
                
        except Exception as e:
            logger.error(f"导航到第{page_num}页失败: {e}")
        
        return False

    def _go_to_next_page_old_style(self, driver) -> bool:
        """使用旧下载器的成熟分页算法"""
        try:
            # 模拟人类行为
            self.anti_crawler.simulate_human_behavior(driver)
            
            # 方法1: 查找下一页按钮
            try:
                next_btn = driver.find_element(By.XPATH, "//button[contains(@class, 'el-pagination__next') and not(@disabled)]")
                if next_btn.is_enabled():
                    actions = ActionChains(driver)
                    actions.move_to_element(next_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                    self.anti_crawler.dynamic_delay(0.5, 1)
                    return True
            except Exception:
                pass
            
            # 方法2: 查找右箭头按钮
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
            
            # 方法3: 查找页码输入框（备用方法）
            try:
                # 获取当前页码
                page_input = driver.find_element(By.CLASS_NAME, 'page-input')
                current_page = int(page_input.get_attribute('value') or '1')
                
                # 输入下一页
                page_input.clear()
                page_input.send_keys(str(current_page + 1))
                
                # 查找并点击跳转按钮
                go_button = driver.find_element(By.CLASS_NAME, 'page-go')
                go_button.click()
                
                # 等待页面加载
                self.anti_crawler.dynamic_delay(0.5, 1)
                return True
            except Exception:
                pass
                
        except Exception as e:
            logger.debug(f"翻页失败: {e}")
        
        return False

    def _filter_links_by_keywords(self,
                                pdf_links: List[Dict[str, str]],
                                keyword_matcher) -> List[Dict[str, str]]:
        """根据关键词过滤PDF链接"""
        filtered_links = []
        
        for link_data in pdf_links:
            try:
                title = link_data.get("title", "")
                if keyword_matcher.matches(text=title, title=title):
                    filtered_links.append(link_data)
                else:
                    logger.debug(f"跳过不匹配的关键词: {title}")
            except Exception as e:
                logger.warning(f"关键词匹配失败: {e}")
                # 关键词匹配失败时默认包含
                filtered_links.append(link_data)
        
        return filtered_links
    
    @monitor_performance("DownloadService._download_from_detail_page")
    def _download_from_detail_page(self, driver, stock_info: StockInfo, link_data: Dict[str, str]) -> Optional[DownloadRecord]:
        """从详情页下载PDF文件（优化版本：移除重复的文件存在检查）"""
        start_time = time.time()
        detail_url = link_data['detail_url']
        title = link_data['title']
        
        # 创建文件名（与老版本保持一致）
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
        file_name = f"{safe_title}.pdf"
        
        logger.debug(f"开始处理详情页: {title}")
        
        # 文件存在性检查已经在 _find_detail_links 中完成
        # 使用公司子目录作为保存路径（与旧版本保持一致）
        stock_dir = self.save_dir / stock_info.stock_name
        stock_dir.mkdir(parents=True, exist_ok=True)
        file_path = stock_dir / file_name
        
        # 设置当前公司目录，用于文件管理
        self._current_stock_dir = stock_dir
        
        # 如果需要日期，在下载阶段提取（性能优化）
        date = link_data.get('date')
        if date is None:
            # 从详情页提取日期
            try:
                # 访问详情页获取日期信息
                driver.get(detail_url)
                self.anti_crawler.random_delay(0.5, 1.5)
                
                # 查找详情页中的链接元素来提取日期
                detail_links = driver.find_elements(By.TAG_NAME, 'a')
                for link in detail_links:
                    if link.text.strip() == title:
                        date = self._extract_date_from_link(link)
                        break
            except Exception as e:
                logger.debug(f"提取日期失败: {e}")
                date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"访问详情页开始下载: {title}")
        
        # 添加重试机制处理tab crashed错误和ChromeDriver错误（增强版）
        max_retries = 3  # 增加重试次数
        for attempt in range(max_retries + 1):
            try:
                # 访问详情页 - 添加更好的错误处理
                try:
                    driver.get(detail_url)
                except Exception as get_error:
                    if "tab crashed" in str(get_error).lower() or "chrome" in str(get_error).lower():
                        logger.warning(f"ChromeDriver错误，尝试重启driver (尝试 {attempt + 1}/{max_retries + 1}): {get_error}")
                        if attempt < max_retries:
                            # 等待更长时间让Chrome完全重启
                            time.sleep(3)
                            # 重启WebDriver
                            if self.driver_manager.restart_driver():
                                driver = self.driver_manager.get_driver()
                                if driver:
                                    logger.info("WebDriver重启成功，继续执行")
                                    continue
                                else:
                                    logger.error("WebDriver重启失败")
                                    raise get_error
                            else:
                                logger.error("无法重启WebDriver")
                                raise get_error
                        else:
                            logger.error(f"ChromeDriver重试失败，放弃: {get_error}")
                            raise get_error
                    else:
                        raise get_error
                
                self.anti_crawler.random_delay(0.5, 1.5)
                
                # 模拟人类行为
                self.anti_crawler.simulate_human_behavior(driver)
                
                # 查找并点击下载按钮 - 优化等待时间
                try:
                    download_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., '公告下载')]"))
                    )
                    
                    # 记录点击前的文件列表（分别记录两个目录）
                    before_files_save_dir = set(os.listdir(self.save_dir))
                    
                    # 记录Chrome默认下载目录的文件
                    chrome_default_downloads = os.path.expanduser("~/Downloads")
                    before_files_chrome = set()
                    if os.path.exists(chrome_default_downloads):
                        before_files_chrome = set(os.listdir(chrome_default_downloads))
                    
                    # 保存两个目录的初始文件列表用于传递给_wait_for_download
                    before_files = (before_files_save_dir, before_files_chrome)
                    
                    # 模拟人类点击
                    actions = ActionChains(driver)
                    actions.move_to_element(download_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                    logger.info(f"已点击下载按钮，等待文件下载...")
                    
                    # 等待下载完成 - 优化超时时间
                    if self._wait_for_download(before_files, str(file_path), timeout=60):
                        file_size = file_path.stat().st_size
                        total_time = time.time() - start_time
                        logger.info(f"下载成功: {file_name} ({file_size} bytes), 总耗时: {total_time:.3f}s")
                        
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
                        logger.warning(f"下载可能失败: {file_name}")
                        return DownloadRecord(
                            id=str(uuid.uuid4()),
                            stock_code=stock_info.stock_code,
                            file_name=file_name,
                            file_path=str(file_path),
                            status=DownloadStatus.FAILED,
                            error_message="文件未找到或文件大小异常"
                        )
                        
                except TimeoutException:
                    logger.error(f"找不到下载按钮: {title}")
                    return DownloadRecord(
                        id=str(uuid.uuid4()),
                        stock_code=stock_info.stock_code,
                        file_name=file_name,
                        file_path=str(file_path),
                        status=DownloadStatus.FAILED,
                        error_message="找不到下载按钮"
                    )
                
            except WebDriverException as e:
                if "tab crashed" in str(e).lower() and attempt < max_retries:
                    logger.warning(f"标签页崩溃，尝试重启WebDriver (尝试 {attempt + 1}/{max_retries})")
                    # 重启WebDriver
                    driver = self.driver_manager.restart_driver()
                    self.anti_crawler.apply_anti_detection(driver)
                    continue
                else:
                    logger.error(f"从详情页下载失败: {e}")
                    return DownloadRecord(
                        id=str(uuid.uuid4()),
                        stock_code=stock_info.stock_code,
                        file_name=link_data.get('title', 'unknown'),
                        file_path=str(self.save_dir / 'unknown.pdf'),
                        status=DownloadStatus.FAILED,
                        error_message=str(e)
                    )
            except Exception as e:
                logger.error(f"从详情页下载失败: {e}")
                return DownloadRecord(
                    id=str(uuid.uuid4()),
                    stock_code=stock_info.stock_code,
                    file_name=link_data.get('title', 'unknown'),
                    file_path=str(self.save_dir / 'unknown.pdf'),
                    status=DownloadStatus.FAILED,
                    error_message=str(e)
                )
        
        # 所有重试都失败
        total_time = time.time() - start_time
        logger.error(f"从详情页下载失败: 达到最大重试次数 {max_retries}, 总耗时: {total_time:.3f}s")
        return DownloadRecord(
            id=str(uuid.uuid4()),
            stock_code=stock_info.stock_code,
            file_name=link_data.get('title', 'unknown'),
            file_path=str(self.save_dir / 'unknown.pdf'),
            status=DownloadStatus.FAILED,
            error_message=f"达到最大重试次数 {max_retries}"
        )
    
    @monitor_performance("DownloadService._wait_for_download")
    def _wait_for_download(self, before_files, target_path, timeout=60):
        """等待文件下载完成（性能优化版本）"""
        start_time = time.time()
        check_interval = 0.5  # 开始时使用0.5秒间隔
        
        while time.time() - start_time < timeout:
            time.sleep(check_interval)
            # 渐进式增加检查间隔，最大2.0秒
            check_interval = min(check_interval * 1.2, 2.0)
            
            # 清理pdf.txt文件
            self._cleanup_pdf_txt()
            
            # 检查新文件（对齐旧下载器：先检查整个下载目录）
            try:
                # 解析两个目录的初始文件列表
                before_files_save_dir, before_files_chrome = before_files
                
                # 方法1: 检查配置的下载目录
                after_files_save_dir = set(os.listdir(self.save_dir))
                new_files_save_dir = after_files_save_dir - before_files_save_dir
                
                # 方法2: 检查Chrome默认下载目录
                chrome_default_downloads = os.path.expanduser("~/Downloads")
                new_files_chrome = set()
                if os.path.exists(chrome_default_downloads):
                    after_files_chrome = set(os.listdir(chrome_default_downloads))
                    new_files_chrome = after_files_chrome - before_files_chrome
                        
                # 合并两个目录的新文件
                new_files = new_files_save_dir.union(new_files_chrome)
                
                # 将Chrome默认目录中的新文件移动到配置的下载目录
                for file in new_files_chrome:
                    chrome_file_path = os.path.join(chrome_default_downloads, file)
                    if file.lower().endswith('.pdf') and os.path.exists(chrome_file_path):
                        target_file_path = os.path.join(self.save_dir, file)
                        try:
                            shutil.move(chrome_file_path, target_file_path)
                            logger.info(f"从Chrome默认目录移动文件: {chrome_file_path} -> {target_file_path}")
                        except Exception as e:
                            logger.error(f"移动Chrome默认目录文件失败: {e}")
                
                for file in new_files:
                    file_path = os.path.join(self.save_dir, file)
                    
                    if file.lower().endswith('.pdf') and os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        
                        if file_size > 10 * 1024:  # 文件大于10KB
                            # 移动文件到目标位置（确保移动到正确的子目录）
                            if file_path != target_path:
                                try:
                                    # 确保目标目录存在
                                    target_dir = Path(target_path).parent
                                    target_dir.mkdir(parents=True, exist_ok=True)
                                    
                                    # 如果目标文件已存在，先删除
                                    if Path(target_path).exists():
                                        Path(target_path).unlink()
                                    
                                    shutil.move(file_path, target_path)
                                    logger.info(f"文件移动成功: {file_path} -> {target_path}")
                                except Exception as e:
                                    logger.error(f"文件移动失败: {file_path} -> {target_path}, 错误: {e}")
                                    # 如果移动失败，至少确保文件在正确的子目录中
                                    try:
                                        target_dir = Path(target_path).parent
                                        fallback_path = target_dir / Path(file).name
                                        if fallback_path != file_path:
                                            shutil.move(file_path, fallback_path)
                                            logger.info(f"文件移动到备用位置: {file_path} -> {fallback_path}")
                                    except Exception:
                                        pass
                            return True
                        else:
                            # 删除过小的文件
                            try:
                                os.remove(file_path)
                                logger.info(f"删除过小文件: {file_path}")
                            except Exception:
                                pass
                
                # 方法2: 检查目标文件是否已存在且大小合适
                if os.path.exists(target_path) and os.path.getsize(target_path) > 10 * 1024:
                    return True
                
                # 方法3: 检查公司子目录（作为补充）
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
                logger.debug(f"检查下载文件时发生错误: {e}")
        
        # 超时后，清理根目录中可能残留的文件
        try:
            after_files = set(os.listdir(self.save_dir))
            new_files = after_files - before_files
            
            for file in new_files:
                file_path = os.path.join(self.save_dir, file)
                if file.lower().endswith('.pdf') and os.path.exists(file_path):
                    logger.warning(f"清理超时未处理的文件: {file_path}")
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"清理残留文件失败: {e}")
        
        return False
    
    def _cleanup_pdf_txt(self):
        """清理pdf.txt文件（只清理公司目录）"""
        try:
            # 检查当前使用的公司目录
            if hasattr(self, '_current_stock_dir') and self._current_stock_dir and self._current_stock_dir.exists():
                for file in os.listdir(self._current_stock_dir):
                    if file.lower() == 'pdf.txt':
                        os.remove(os.path.join(self._current_stock_dir, file))
            else:
                # 回退到检查所有可能的目录
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
    
    # 新增方法以对齐旧下载器
    def dynamic_delay(self, base_min=2, base_max=8):
        """动态延迟（从旧下载器复制）"""
        return self.anti_crawler.dynamic_delay(base_min, base_max)
    
    @property
    def retry_count(self):
        """获取重试次数（从旧下载器复制）"""
        return getattr(self, '_retry_count', 0)
    
    @retry_count.setter
    def retry_count(self, value):
        """设置重试次数"""
        self._retry_count = value
    
    @property
    def max_retries(self):
        """获取最大重试次数"""
        return getattr(self, '_max_retries', 3)
    
    def should_retry(self):
        """检查是否应该重试"""
        return self.retry_count < self.max_retries
    
    def log_info(self, message):
        """记录信息日志"""
        logger.info(message)
    
    def log_error(self, message):
        """记录错误日志"""
        logger.error(message)
    
    def log_warning(self, message):
        """记录警告日志"""
        logger.warning(message)
    
    def get_status(self):
        """获取状态信息"""
        return {
            'download_count': self.download_count,
            'retry_count': self.retry_count,
            'success_count': getattr(self, '_success_count', 0),
            'error_count': getattr(self, '_error_count', 0)
        }
    
    def cleanup(self):
        """清理资源"""
        try:
            self.driver_manager.close_driver()
            self._cleanup_pdf_txt()
        except Exception as e:
            logger.error(f"清理资源失败: {e}")
    
    def _build_disclosure_url(self, stock_code, org_id):
        """构建披露页面URL（从旧下载器复制）"""
        return f"https://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#research"
    
    def _generate_file_path(self, stock_name, file_title):
        """生成文件路径（从旧下载器复制）"""
        company_dir = self.save_dir / stock_name
        company_dir.mkdir(exist_ok=True)
        
        clean_title = self.clean_filename(file_title)
        if not clean_title.lower().endswith('.pdf'):
            clean_title += '.pdf'
        
        return str(company_dir / clean_title)
    
    def _file_exists_and_valid(self, file_path):
        """检查文件是否存在且有效"""
        try:
            return os.path.exists(file_path) and os.path.getsize(file_path) > 10 * 1024
        except Exception:
            return False
    
    def _clean_filename(self, filename):
        """清理文件名（兼容方法）"""
        return self.clean_filename(filename)
    
    def _matches_keywords(self, text, allowed_keywords):
        """检查文本是否匹配关键词"""
        if not allowed_keywords:
            return True
        
        text_lower = text.lower()
        for keyword in allowed_keywords:
            if keyword.lower() in text_lower:
                return True
        return False
    
    def _check_circuit_breaker(self):
        """检查断路器状态"""
        if not self._circuit_breaker_active:
            return True
        
        if self._last_error_time is None:
            return True
        
        # 检查是否超时
        if time.time() - self._last_error_time > self._circuit_breaker_timeout:
            logger.info("断路器超时，重置状态")
            self._reset_circuit_breaker()
            return True
        
        return False
    
    def _activate_circuit_breaker(self):
        """激活断路器"""
        self._circuit_breaker_active = True
        self._last_error_time = time.time()
        logger.warning(f"断路器激活，等待 {self._circuit_breaker_timeout} 秒后重试")
    
    def _reset_circuit_breaker(self):
        """重置断路器"""
        self._circuit_breaker_active = False
        self._consecutive_errors = 0
        self._last_error_time = None
        logger.info("断路器重置")
    
    def _record_error(self):
        """记录错误"""
        self._consecutive_errors += 1
        self._last_error_time = time.time()
        
        if self._consecutive_errors >= self._max_consecutive_errors:
            self._activate_circuit_breaker()
    
    def _record_success(self):
        """记录成功"""
        self._consecutive_errors = 0
        if self._circuit_breaker_active:
            logger.info("成功恢复，重置断路器")
            self._reset_circuit_breaker()
    
    def __del__(self):
        """析构函数"""
        try:
            self.driver_manager.close_driver()
        except Exception:
            pass