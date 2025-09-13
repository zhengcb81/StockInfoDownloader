"""
下载服务模块 v2 - 使用浏览器策略模式
提供投资者关系活动记录表的下载功能，支持多种浏览器自动化框架
"""

import os
import re
import time
import uuid
import random
import shutil
from typing import List, Optional, Dict, Any
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime

from ..core.exceptions import (
    DownloadError, WebDriverError, NetworkError, FileSystemError, 
    ErrorCode, ErrorSeverity, RecoveryStrategy,
    with_error_handling, handle_error
)
from ..core.logger import get_logger
from ..core.config import ConfigManager
from ..core.performance_monitor import monitor_performance, monitor_operation, performance_monitor
from ..data.models import StockInfo, DownloadRecord, DownloadStatus, DownloadTask
from ..data.mapping import MappingManager
from ..web.browser_strategy import BrowserStrategyFactory
from ..web.anti_crawler import AntiCrawlerStrategy
from ..web.scraper import WebScraper
from ..utils.keyword_matcher import KeywordMatcher

logger = get_logger(__name__)


class DownloadServiceV2:
    """投资者关系活动记录表下载服务（策略模式版本）"""
    
    def __init__(self, 
                 save_dir: str = "downloads",
                 mapping_file: str = "stock_orgid_mapping.json",
                 browser_strategy: str = "selenium"):
        """
        初始化下载服务（策略模式版本）
        
        Args:
            save_dir: 下载文件保存目录
            mapping_file: 映射文件路径
            browser_strategy: 浏览器策略类型（selenium/playwright）
        """
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)
        self.mapping_file = mapping_file
        self.browser_strategy_type = browser_strategy
        
        self.mapping_manager = MappingManager(mapping_file)
        
        # 加载配置
        self.config = ConfigManager()
        
        # 从配置获取浏览器策略类型，但优先使用传入的参数
        config_strategy = self.config.get('browser.strategy', 'selenium')
        if browser_strategy:
            self.browser_strategy_type = browser_strategy
        elif config_strategy:
            self.browser_strategy_type = config_strategy
        else:
            self.browser_strategy_type = 'selenium'
        
        # 创建浏览器策略实例
        self.browser_strategy = BrowserStrategyFactory.create_strategy(
            strategy_type=self.browser_strategy_type,
            headless=True,
            download_dir=str(self.save_dir),
            config=self._get_browser_config()
        )
        
        self.anti_crawler = AntiCrawlerStrategy()
        
        # 从旧下载器复制的关键属性
        self.download_count = 0  # 下载计数器
        self.retry_count = 0  # 重试计数器
        self.max_downloads_per_session = self.config.get('download.max_downloads_per_session', 5)
        self.max_retries = self.config.get('download.max_retries', 3)
        
        # 配置反爬虫策略
        human_behavior_delay = self.config.get('download.human_behavior_delay', 3)
        if isinstance(human_behavior_delay, list):
            human_behavior_delay = human_behavior_delay[0] if human_behavior_delay else 3
        elif not isinstance(human_behavior_delay, (int, float)):
            human_behavior_delay = 3
        
        human_behavior_delay = int(human_behavior_delay)
        
        self.anti_crawler.set_session_parameters(
            min_delay=max(1, human_behavior_delay - 1),
            max_delay=human_behavior_delay + 2,
            max_downloads=self.max_downloads_per_session
        )
        
        logger.info(f"使用浏览器策略: {self.browser_strategy_type}")
    
    def _get_browser_config(self) -> Dict[str, Any]:
        """获取浏览器配置"""
        return {
            'window_size': self.config.get('webdriver.window_size', '1920,1080'),
            'page_load_timeout': self.config.get('timeout.page_load', 15),
            'implicit_wait': self.config.get('timeout.element_wait', 3),
            'max_downloads_per_session': self.config.get('download.max_downloads_per_session', 10),
            'user_agents': self.config.get('webdriver.user_agents', [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            ])
        }
    
    @monitor_performance("DownloadServiceV2.download_stock_pdfs")
    @with_error_handling(
        error_code=ErrorCode.DOWNLOAD_FILE_ERROR,
        severity=ErrorSeverity.ERROR,
        recovery_strategy=RecoveryStrategy.RETRY,
        max_retries=3
    )
    def download_stock_pdfs(self, 
                          stock_code: str,
                          target_pages: Optional[List[Dict[str, Any]]] = None,
                          max_retries: int = 3) -> List[DownloadRecord]:
        """
        下载指定股票的PDF文件
        
        Args:
            stock_code: 股票代码
            target_pages: 目标页面配置列表
            max_retries: 最大重试次数
            
        Returns:
            List[DownloadRecord]: 下载记录列表
        """
        logger.info(f"开始下载股票 {stock_code} 的PDF文件")
        
        # 获取股票信息
        stock_info = self._get_stock_info(stock_code)
        if not stock_info:
            logger.error(f"无法获取股票 {stock_code} 的信息")
            return []
        
        # 设置默认目标页面
        if target_pages is None:
            target_pages = [
                {'suffix': 'research', 'allowed_keywords': None},
                {'suffix': 'periodicReports', 'allowed_keywords': None},
                {'suffix': 'latestAnnouncement', 'allowed_keywords': ["招股说明书"]}
            ]
        
        download_records = []
        
        try:
            # 创建浏览器实例
            self.browser_strategy.create_driver()
            
            # 处理每个目标页面
            for page_config in target_pages:
                page_records = self._process_page(
                    stock_info, page_config, max_retries
                )
                download_records.extend(page_records)
                
                # 页面间延迟
                self.anti_crawler.random_delay()
                
        except Exception as e:
            logger.error(f"下载过程中发生错误: {e}")
            raise DownloadError(f"下载失败: {e}")
        
        finally:
            # 确保浏览器关闭
            self.browser_strategy.close()
        
        logger.info(f"下载完成，共下载 {len(download_records)} 个文件")
        return download_records
    
    def _get_stock_info(self, stock_code: str) -> Optional[Dict[str, str]]:
        """获取股票信息"""
        try:
            org_id = self.mapping_manager.get_org_id(stock_code)
            if not org_id:
                logger.warning(f"未找到股票代码 {stock_code} 的组织ID")
                return None
            
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
    
    def _process_page(self, stock_info: Dict[str, str],
                     page_config: Dict[str, Any], max_retries: int) -> List[DownloadRecord]:
        """处理单个页面，支持分页下载"""
        suffix = page_config.get('suffix', 'research')
        allowed_keywords = page_config.get('allowed_keywords')
        max_pages = page_config.get('max_pages', 5)  # 默认最多5页

        logger.info(f"处理页面: {suffix}, 最大页数: {max_pages}")
        if allowed_keywords:
            logger.info(f"关键词过滤: {allowed_keywords}")

        page_url = self._build_page_url(stock_info, suffix)

        for attempt in range(max_retries):
            try:
                logger.info(f"尝试访问页面 (第 {attempt + 1}/{max_retries} 次): {page_url}")

                if not self.browser_strategy.navigate(page_url):
                    raise NetworkError(f"无法导航到页面: {page_url}")

                # 等待页面加载 - 增加等待时间确保JavaScript执行完成
                time.sleep(5)

                # 如果是research页面，需要执行JavaScript导航到正确的tab
                if suffix == 'research':
                    try:
                        self.browser_strategy.execute_script("""
                            // 等待页面加载完成后执行导航
                            setTimeout(function() {
                                if (window.location.hash !== '#research') {
                                    window.location.hash = 'research';
                                    // 触发页面更新
                                    window.dispatchEvent(new Event('hashchange'));
                                }
                            }, 2000);
                        """)
                        logger.info('已执行research页面导航脚本')
                    except Exception as e:
                        logger.warning(f'research导航脚本执行失败: {e}')

                # 增强等待时间，确保JavaScript渲染完成
                time.sleep(8)

                # 检查页面标题确认页面加载成功
                try:
                    page_title = self.browser_strategy.get_page_title()
                    logger.info(f"页面标题: {page_title}")
                    if not page_title or "巨潮资讯网" not in page_title:
                        logger.warning("页面可能未正确加载，标题异常")
                except Exception as e:
                    logger.warning(f"获取页面标题失败: {e}")

                # 分页下载处理
                download_records = []
                current_page = 1

                while current_page <= max_pages:
                    logger.info(f"处理第 {current_page} 页")

                    # 查找当前页的下载链接
                    download_links = self._find_download_links(stock_info['stock_code'], allowed_keywords)

                    if download_links:
                        logger.info(f"第 {current_page} 页找到 {len(download_links)} 个下载链接")
                        # 下载当前页的文件
                        for link_info in download_links:
                            record = self._download_file(link_info, stock_info['stock_name'])
                            if record:
                                download_records.append(record)
                    else:
                        logger.info(f"第 {current_page} 页未找到下载链接")

                    # 检查是否有下一页
                    if current_page < max_pages and self.browser_strategy.has_next_page():
                        logger.info(f"准备翻到第 {current_page + 1} 页")
                        if self.browser_strategy.go_to_next_page():
                            current_page += 1
                            # 等待页面加载
                            time.sleep(3)
                        else:
                            logger.info("翻页失败，停止处理")
                            break
                    else:
                        logger.info(f"已达到最大页数或没有下一页，停止处理")
                        break

                if download_records:
                    logger.info(f"总共下载 {len(download_records)} 个文件")
                    return download_records
                else:
                    logger.warning(f"页面 {suffix} 未找到符合条件的下载链接")
                    return []

            except Exception as e:
                logger.error(f"第 {attempt + 1} 次尝试失败: {e}")

                if attempt < max_retries - 1:
                    # 重启浏览器并重试
                    if not self.browser_strategy.restart():
                        logger.error("浏览器重启失败")
                        break

                    # 重试前延迟
                    retry_delay = random.uniform(3, 8)
                    logger.info(f"等待 {retry_delay:.2f} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"所有 {max_retries} 次尝试均失败")
                    raise

        return []
    
    def _build_page_url(self, stock_info: Dict[str, str], suffix: str) -> str:
        """构建页面URL"""
        base_url = "https://www.cninfo.com.cn/new/disclosure/stock"
        return f"{base_url}?orgId={stock_info['org_id']}&stockCode={stock_info['stock_code']}#{suffix}"
    
    def _build_disclosure_url(self, stock_code, org_id):
        """构建披露页面URL（兼容旧测试）"""
        return f"https://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#research"
    
    def _find_download_links(self, stock_code: str, allowed_keywords: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """查找下载链接"""
        try:
            # 使用浏览器策略查找元素
            links = self.browser_strategy.find_elements("a")
            
            download_links = []
            total_links = 0
            detail_links = 0
            
            for link in links:
                try:
                    # 获取链接文本和URL
                    text = self.browser_strategy.get_text(link)
                    href = self.browser_strategy.get_attribute(link, "href")
                    
                    total_links += 1
                    
                    if not (text and href):
                        continue
                        
                    # 检查是否是详情页链接（不是直接PDF链接）
                    is_detail_link = False
                    if href and '/new/disclosure/detail' in href:
                        is_detail_link = True
                        detail_links += 1
                        logger.debug(f"找到详情页链接: {text} -> {href}")
                    
                    # 检查是否包含股票代码
                    has_stock_code = f'stockCode={stock_code}' in href
                    
                    if is_detail_link and has_stock_code:
                        
                        # 检查关键词过滤
                        if allowed_keywords:
                            text_lower = text.lower()
                            if not any(keyword.lower() in text_lower for keyword in allowed_keywords):
                                logger.debug(f"[跳过] 链接文本不包含关键词: {text}")
                                continue
                        
                        # 修复相对URL
                        full_url = href
                        if href and href.startswith('/'):
                            full_url = f'https://www.cninfo.com.cn{href}'
                        
                        download_links.append({
                            'text': text,
                            'url': full_url,
                            'title': text
                        })
                        logger.info(f"[添加] 符合条件的链接: {text}")
                        
                except Exception as e:
                    logger.debug(f"处理链接时出错: {e}")
                    continue
            
            logger.info(f"扫描完成: 总共 {total_links} 个链接, 其中 {detail_links} 个详情页链接, 找到 {len(download_links)} 个符合条件的详情页链接")
            return download_links
            
        except Exception as e:
            logger.error(f"查找下载链接失败: {e}")
            return []
    
    def _generate_file_path(self, stock_name, file_title):
        """生成文件路径（兼容旧测试）"""
        from ..utils.directory_manager import create_directory_manager

        # 使用目录管理器创建公司目录
        directory_manager = create_directory_manager(self.mapping_file)
        company_dir = directory_manager.create_company_directory(
            self._get_stock_code_from_name(stock_name), self.save_dir
        )
        
        clean_title = self._clean_filename(file_title)
        if not clean_title.lower().endswith('.pdf'):
            clean_title += '.pdf'
        
        return str(company_dir / clean_title)
    
    def _clean_filename(self, filename):
        """清理文件名（兼容方法）"""
        # 移除非法字符
        import re
        clean_name = re.sub(r'[<>:"/\\|?*]', '', filename)
        # 限制长度
        if len(clean_name) > 200:
            clean_name = clean_name[:200]
        return clean_name

    def _get_stock_code_from_name(self, stock_name):
        """从公司名称获取股票代码"""
        # 这里需要实现从公司名称反向查找股票代码的逻辑
        # 目前先简单处理，假设stock_name就是股票代码
        # 在实际应用中应该使用映射管理器进行反向查找
        return stock_name

    def _file_exists_and_valid(self, file_path):
        """检查文件是否存在且有效"""
        try:
            return os.path.exists(file_path) and os.path.getsize(file_path) > 10 * 1024
        except Exception:
            return False
    
    def _matches_keywords(self, text, allowed_keywords):
        """检查文本是否匹配关键词"""
        if not allowed_keywords:
            return True
        
        text_lower = text.lower()
        for keyword in allowed_keywords:
            if keyword.lower() in text_lower:
                return True
        return False
    
    def _download_file(self, link_info: Dict[str, str], stock_name: str) -> Optional[DownloadRecord]:
        """下载单个文件"""
        try:
            url = link_info.get('url')
            title = link_info.get('title', '')
            
            if not url:
                return None
                
            # 生成文件路径
            file_path = self._generate_file_path(stock_name, title)
            
            # 检查文件是否已存在
            if self._file_exists_and_valid(file_path):
                logger.info(f"文件已存在，跳过下载: {file_path}")
                return DownloadRecord(
                    id=str(uuid.uuid4()),
                    stock_code=stock_name,
                    file_name=os.path.basename(file_path),
                    file_path=file_path,
                    status=DownloadStatus.SKIPPED,
                    file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0
                )
            
            # 使用浏览器策略下载文件
            if not self.browser_strategy.download_file(url, file_path, timeout=60):
                logger.error(f"文件下载失败: {url}")
                return None
            
            # 检查文件是否下载成功
            if self._file_exists_and_valid(file_path):
                file_size = os.path.getsize(file_path)
                logger.info(f"下载成功: {file_path} ({file_size} bytes)")
                
                return DownloadRecord(
                    id=str(uuid.uuid4()),
                    stock_code=stock_name,
                    file_name=os.path.basename(file_path),
                    file_path=file_path,
                    status=DownloadStatus.COMPLETED,
                    file_size=file_size
                )
            else:
                logger.error(f"文件下载失败或文件太小: {file_path}")
                return None
                
        except Exception as e:
            logger.error(f"下载文件时出错: {e}")
            return None
    
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
            'success_count': 0,
            'error_count': 0
        }
    
    def should_retry(self):
        """检查是否应该重试"""
        return self.retry_count < self.max_retries
    
    def dynamic_delay(self, base_min=2, base_max=8):
        """动态延迟（从旧下载器复制）"""
        return self.anti_crawler.dynamic_delay(base_min, base_max)
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.browser_strategy:
                self.browser_strategy.close()
        except Exception as e:
            logger.error(f"清理资源失败: {e}")
        # 暂时返回None，需要根据实际下载逻辑实现
        return None
    
    def switch_browser_strategy(self, strategy_type: str) -> bool:
        """切换浏览器策略"""
        try:
            # 关闭当前浏览器
            self.browser_strategy.close()
            
            # 创建新的策略实例
            self.browser_strategy = BrowserStrategyFactory.create_strategy(
                strategy_type=strategy_type,
                headless=True,
                download_dir=str(self.save_dir),
                config=self._get_browser_config()
            )
            
            self.browser_strategy_type = strategy_type
            logger.info(f"已切换到浏览器策略: {strategy_type}")
            return True
            
        except Exception as e:
            logger.error(f"切换浏览器策略失败: {e}")
            return False


# 向后兼容性别名
DownloadService = DownloadServiceV2