#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
巨潮资讯网统一下载器

统一的参数化下载器，支持投资者关系活动记录表和财务报告下载
支持通过配置文件或命令行参数灵活配置

作者: Claude Code
日期: 2025-07-18
"""

import os
import re
import sys
import json
import time
import logging
import shutil
import random
import argparse
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from orgid_utils import get_org_id_by_code
from get_stock_name import get_stock_name
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException

# 尝试导入psutil，如果不可用则忽略
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cninfo_unified.log')
    ]
)
logger = logging.getLogger('cninfo_unified')

class DownloadType(Enum):
    """下载类型枚举"""
    INVESTOR_RELATIONS = "investor_relations"
    FINANCIAL_REPORTS = "financial_reports"

class ReportType(Enum):
    """财务报告类型枚举"""
    ANNUAL = "annual"
    SEMI_ANNUAL = "semi_annual"
    Q1 = "q1"
    Q3 = "q3"

@dataclass
class DownloadConfig:
    """下载配置数据类"""
    stock_code: str
    download_type: DownloadType = DownloadType.INVESTOR_RELATIONS
    save_dir: str = "downloads"
    mapping_file: str = "stock_orgid_mapping.json"
    headless: bool = True
    max_downloads_per_session: int = 5
    max_reports: int = 100
    report_types: List[ReportType] = field(default_factory=lambda: [ReportType.ANNUAL, ReportType.SEMI_ANNUAL, ReportType.Q1, ReportType.Q3])
    years: List[int] = field(default_factory=lambda: [2020, 2021, 2022, 2023, 2024])
    min_file_size: int = 10 * 1024  # 10KB
    max_retries: int = 3
    retry_wait_range: tuple = (5, 15)
    download_timeout: int = 60
    random_delay_range: tuple = (2, 8)

class ContentFilter:
    """内容过滤器基类"""
    
    def should_include(self, title: str, config: DownloadConfig) -> bool:
        """判断是否应包含该文档"""
        raise NotImplementedError
    
    def get_file_name(self, title: str, date: str = "") -> str:
        """生成文件名"""
        raise NotImplementedError

class InvestorRelationsFilter(ContentFilter):
    """投资者关系活动记录表过滤器"""
    
    KEYWORDS = [
        '投资者关系活动记录表',
        '投资者关系活动',
        '调研活动',
        '机构调研',
        '投资者调研',
        '接待调研',
        '现场参观',
        '电话会议',
        '业绩说明会'
    ]
    
    ENGLISH_KEYWORDS = ['英文版', 'english', '英文', 'english version', 'english edition']
    
    def should_include(self, title: str, config: DownloadConfig) -> bool:
        """判断是否应包含该投资者关系记录"""
        title_lower = title.lower()
        
        # 跳过英文版报告
        for keyword in self.ENGLISH_KEYWORDS:
            if keyword in title_lower:
                return False
        
        # 检查是否包含投资者关系关键词
        for keyword in self.KEYWORDS:
            if keyword in title:
                return True
        
        return False
    
    def get_file_name(self, title: str, date: str = "") -> str:
        """生成投资者关系文件名"""
        if date:
            return f"{title}_{date}.pdf"
        return f"{title}.pdf"

class FinancialReportFilter(ContentFilter):
    """财务报告过滤器"""
    
    ENGLISH_KEYWORDS = ['英文版', 'english', '英文', 'english version', 'english edition']
    
    def should_include(self, title: str, config: DownloadConfig) -> bool:
        """判断是否应包含该财务报告"""
        title_lower = title.lower()
        
        # 跳过英文版报告
        for keyword in self.ENGLISH_KEYWORDS:
            if keyword in title_lower:
                return False
        
        # 检查报告类型和年份
        type_match = False
        
        for report_type in config.report_types:
            if self._matches_report_type(title, report_type):
                type_match = True
                break
        
        if not type_match:
            return False
        
        # 检查年份
        if config.years:
            year_match = re.search(r'(20\d{2})', title)
            if year_match:
                report_year = int(year_match.group(1))
                return report_year in config.years
        
        return True
    
    def _matches_report_type(self, title: str, report_type: ReportType) -> bool:
        """检查是否匹配报告类型"""
        if report_type == ReportType.ANNUAL and ('年度报告' in title or '年报' in title):
            return True
        elif report_type == ReportType.SEMI_ANNUAL and ('半年度报告' in title or '中报' in title):
            return True
        elif report_type == ReportType.Q1 and ('第一季度报告' in title or '一季报' in title):
            return True
        elif report_type == ReportType.Q3 and ('第三季度报告' in title or '三季报' in title):
            return True
        return False
    
    def get_file_name(self, title: str, date: str = "") -> str:
        """生成财务报告文件名"""
        if date:
            return f"{title}_{date}.pdf"
        return f"{title}.pdf"

class ContentFilterFactory:
    """内容过滤器工厂"""
    
    @staticmethod
    def create(download_type: DownloadType) -> ContentFilter:
        """创建对应的内容过滤器"""
        if download_type == DownloadType.INVESTOR_RELATIONS:
            return InvestorRelationsFilter()
        elif download_type == DownloadType.FINANCIAL_REPORTS:
            return FinancialReportFilter()
        else:
            raise ValueError(f"Unsupported download type: {download_type}")

class WebDriverManager:
    """WebDriver管理器"""
    
    def __init__(self, config: DownloadConfig):
        self.config = config
        self.driver = None
        self.webdriver_process_id = None
        self.chromedriver_process_id = None
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
    
    def setup_driver(self) -> bool:
        """设置WebDriver"""
        try:
            if self.driver:
                self.close_driver()
            
            chrome_options = Options()
            
            # 基础设置
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--remote-debugging-port=0')
            
            # 随机User-Agent
            user_agent = random.choice(self.user_agents)
            chrome_options.add_argument(f'user-agent={user_agent}')
            logger.info(f"使用User-Agent: {user_agent}")
            
            if self.config.headless:
                chrome_options.add_argument('--headless')
            
            # 设置下载目录
            prefs = {
                "download.default_directory": os.path.abspath(self.config.save_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # 创建WebDriver
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    logger.info(f"正在初始化WebDriver (尝试 {attempt + 1}/{max_attempts})...")
                    
                    self._cleanup_webdriver_processes()
                    
                    self.driver = webdriver.Chrome(options=chrome_options)
                    self.driver.set_page_load_timeout(30)
                    self.driver.implicitly_wait(10)
                    
                    self._record_webdriver_processes()
                    
                    # 执行反检测脚本
                    self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    
                    # 测试driver是否正常工作
                    self.driver.get("about:blank")
                    
                    logger.info("WebDriver初始化成功")
                    return True
                    
                except Exception as e:
                    logger.warning(f"WebDriver初始化尝试 {attempt + 1} 失败: {e}")
                    
                    if self.driver:
                        try:
                            self.driver.quit()
                        except Exception:
                            pass
                        self.driver = None
                    
                    if attempt < max_attempts - 1:
                        wait_time = random.uniform(3, 8)
                        logger.info(f"等待 {wait_time:.2f} 秒后重试...")
                        time.sleep(wait_time)
                    else:
                        raise e
            
            return False
            
        except Exception as e:
            logger.error(f"WebDriver初始化失败: {e}")
            return False
    
    def _cleanup_webdriver_processes(self):
        """清理WebDriver相关进程"""
        try:
            import subprocess
            import platform
            
            logger.debug("开始清理WebDriver相关进程...")
            
            # 清理之前记录的WebDriver进程
            if self.webdriver_process_id:
                try:
                    if platform.system() == "Windows":
                        subprocess.run(['taskkill', '/f', '/pid', str(self.webdriver_process_id)], 
                                     capture_output=True, timeout=5)
                    else:
                        subprocess.run(['kill', '-9', str(self.webdriver_process_id)], 
                                     capture_output=True, timeout=5)
                    logger.debug(f"已清理WebDriver进程: {self.webdriver_process_id}")
                except Exception:
                    pass
                finally:
                    self.webdriver_process_id = None
            
            if self.chromedriver_process_id:
                try:
                    if platform.system() == "Windows":
                        subprocess.run(['taskkill', '/f', '/pid', str(self.chromedriver_process_id)], 
                                     capture_output=True, timeout=5)
                    else:
                        subprocess.run(['kill', '-9', str(self.chromedriver_process_id)], 
                                     capture_output=True, timeout=5)
                    logger.debug(f"已清理ChromeDriver进程: {self.chromedriver_process_id}")
                except Exception:
                    pass
                finally:
                    self.chromedriver_process_id = None
            
            # 使用psutil精确查找WebDriver相关进程
            if PSUTIL_AVAILABLE:
                try:
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                        try:
                            proc_info = proc.info
                            if not proc_info['cmdline']:
                                continue
                            
                            cmdline = ' '.join(proc_info['cmdline'])
                            
                            webdriver_indicators = [
                                '--test-type',
                                '--disable-extensions',
                                '--disable-dev-shm-usage',
                                '--no-sandbox',
                                '--remote-debugging-port',
                                '--disable-gpu',
                                'chromedriver'
                            ]
                            
                            if (proc_info['name'] and 
                                ('chrome' in proc_info['name'].lower() or 'chromedriver' in proc_info['name'].lower())):
                                
                                is_webdriver_process = any(indicator in cmdline for indicator in webdriver_indicators)
                                
                                if is_webdriver_process:
                                    try:
                                        proc.terminate()
                                        proc.wait(timeout=3)
                                        logger.debug(f"已清理WebDriver相关进程: {proc_info['pid']} - {proc_info['name']}")
                                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                                        try:
                                            proc.kill()
                                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                                            pass
                        
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            continue
                            
                except Exception as e:
                    logger.debug(f"使用psutil清理进程时发生错误: {e}")
            else:
                logger.debug("psutil不可用，只清理chromedriver进程")
                try:
                    if platform.system() == "Windows":
                        subprocess.run(['taskkill', '/f', '/im', 'chromedriver.exe'], 
                                     capture_output=True, timeout=5)
                    else:
                        subprocess.run(['pkill', '-f', 'chromedriver'], 
                                     capture_output=True, timeout=5)
                except Exception:
                    pass
            
            time.sleep(1)
            logger.debug("WebDriver进程清理完成")
            
        except Exception as e:
            logger.debug(f"清理WebDriver进程时发生错误: {e}")
    
    def close_driver(self):
        """关闭WebDriver"""
        if self.driver:
            try:
                try:
                    self.driver.close()
                except Exception:
                    pass
                
                self.driver.quit()
                logger.info("WebDriver已关闭")
            except Exception as e:
                logger.error(f"关闭WebDriver时发生错误: {e}")
            finally:
                self.driver = None
                time.sleep(2)
    
    def restart_driver(self) -> bool:
        """重启WebDriver"""
        logger.info("正在重启WebDriver...")
        
        self.close_driver()
        
        wait_time = random.uniform(5, 12)
        logger.info(f"等待 {wait_time:.2f} 秒确保进程完全结束...")
        time.sleep(wait_time)
        
        max_restart_attempts = 3
        for attempt in range(max_restart_attempts):
            try:
                logger.info(f"尝试重启WebDriver (第 {attempt + 1}/{max_restart_attempts} 次)...")
                if self.setup_driver():
                    logger.info("WebDriver重启成功")
                    return True
                else:
                    logger.warning(f"WebDriver重启尝试 {attempt + 1} 失败")
            except Exception as e:
                logger.error(f"WebDriver重启尝试 {attempt + 1} 异常: {e}")
            
            if attempt < max_restart_attempts - 1:
                retry_wait = random.uniform(8, 15)
                logger.info(f"等待 {retry_wait:.2f} 秒后重试...")
                time.sleep(retry_wait)
        
        logger.error("WebDriver重启失败，已尝试所有重试次数")
        return False
    
    def _record_webdriver_processes(self):
        """记录WebDriver相关进程ID"""
        try:
            if not PSUTIL_AVAILABLE:
                return
            
            if hasattr(self.driver, 'service') and hasattr(self.driver.service, 'process'):
                try:
                    self.chromedriver_process_id = self.driver.service.process.pid
                    logger.debug(f"记录ChromeDriver进程ID: {self.chromedriver_process_id}")
                except Exception:
                    pass
            
            try:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid']):
                    try:
                        proc_info = proc.info
                        if not proc_info['cmdline']:
                            continue
                        
                        cmdline = ' '.join(proc_info['cmdline'])
                        
                        if (proc_info['name'] and 'chrome' in proc_info['name'].lower() and
                            any(indicator in cmdline for indicator in [
                                '--test-type', '--disable-extensions', '--remote-debugging-port'
                            ])):
                            
                            if (self.chromedriver_process_id and 
                                proc_info['ppid'] == self.chromedriver_process_id):
                                self.webdriver_process_id = proc_info['pid']
                                logger.debug(f"记录WebDriver Chrome进程ID: {self.webdriver_process_id}")
                                break
                    
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                        
            except Exception as e:
                logger.debug(f"查找WebDriver Chrome进程时发生错误: {e}")
                    
        except Exception as e:
            logger.debug(f"记录WebDriver进程ID时发生错误: {e}")
    
    def simulate_human_behavior(self):
        """模拟人类行为"""
        try:
            if not self.driver:
                return
                
            # 随机滚动页面
            scroll_height = random.randint(100, 500)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_height});")
            time.sleep(random.uniform(0.5, 2))
            
            # 随机移动鼠标
            actions = ActionChains(self.driver)
            actions.move_by_offset(random.randint(-50, 50), random.randint(-50, 50))
            actions.perform()
            time.sleep(random.uniform(0.3, 1))
            
        except Exception as e:
            logger.debug(f"模拟人类行为时发生错误: {e}")
    
    def is_healthy(self) -> bool:
        """检查driver是否健康"""
        try:
            if not self.driver:
                return False
            
            current_url = self.driver.current_url
            return True
            
        except Exception as e:
            logger.debug(f"Driver健康检查失败: {e}")
            return False

class CninfoUnifiedDownloader:
    """巨潮资讯网统一下载器"""
    
    def __init__(self, config: DownloadConfig):
        self.config = config
        self.driver_manager = WebDriverManager(config)
        self.content_filter = ContentFilterFactory.create(config.download_type)
        self.download_count = 0
        
        # 创建保存目录
        if not os.path.exists(config.save_dir):
            os.makedirs(config.save_dir)
    
    def clean_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        return re.sub(r'[\\/:*?"<>|]', '_', filename)
    
    def get_org_id(self, stock_code: str, force_run: bool = False) -> Optional[str]:
        """获取股票代码对应的组织ID"""
        return get_org_id_by_code(stock_code, force_run=force_run, mapping_file=self.config.mapping_file)
    
    def download(self, stock_code: str = None) -> bool:
        """统一下载入口"""
        if stock_code is None:
            stock_code = self.config.stock_code
        
        if not stock_code:
            logger.error("未指定股票代码")
            return False
        
        # 获取组织ID
        org_id = self.get_org_id(stock_code)
        if not org_id:
            logger.error(f"无法获取 {stock_code} 的组织ID")
            return False
        
        # 获取股票名称
        stock_name = get_stock_name(stock_code, self.config.mapping_file)
        if not stock_name or stock_name.startswith('错误') or stock_name.startswith('网络'):
            stock_name = stock_code
        
        # 创建公司目录
        stock_dir = os.path.join(self.config.save_dir, self.clean_filename(stock_name))
        logger.info(f"保存目录: {stock_dir}")
        os.makedirs(stock_dir, exist_ok=True)
        
        # 设置WebDriver
        if not self.driver_manager.setup_driver():
            return False
        
        try:
            # 构造访问URL
            url_fragment = "#research" if self.config.download_type == DownloadType.INVESTOR_RELATIONS else "#periodicReports"
            url = f"https://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}{url_fragment}"
            
            logger.info(f"访问股票 {stock_code} 的页面: {url}")
            self.driver_manager.driver.get(url)
            
            self._random_delay(5, 10)
            logger.info('页面加载完成')
            
            # 更新下载目录
            download_dir = stock_dir
            prefs = {
                "download.default_directory": os.path.abspath(download_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True
            }
            self.driver_manager.driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': os.path.abspath(download_dir)
            })
            
            # 开始下载
            return self._download_all_pages(stock_code, download_dir)
            
        except Exception as e:
            logger.error(f"页面加载异常: {e}")
            return False
        finally:
            self.driver_manager.close_driver()
    
    def _download_all_pages(self, stock_code: str, stock_dir: str) -> bool:
        """下载所有页面的文档"""
        page_num = 1
        total_downloaded = 0
        
        while True:
            logger.info(f"正在处理第{page_num}页...")
            
            # 检查driver健康状态
            if not self.driver_manager.is_healthy():
                logger.warning("检测到driver异常，尝试重启...")
                if not self.driver_manager.restart_driver():
                    logger.error("重启WebDriver失败")
                    break
                
                # 重新访问页面
                try:
                    org_id = self.get_org_id(stock_code)
                    url_fragment = "#research" if self.config.download_type == DownloadType.INVESTOR_RELATIONS else "#periodicReports"
                    url = f"https://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}{url_fragment}"
                    self.driver_manager.driver.get(url)
                    self._random_delay(5, 10)
                    
                    # 导航到当前页（如果不是第一页）
                    if page_num > 1:
                        self._navigate_to_page(page_num)
                        
                except Exception as e:
                    logger.error(f"重新访问页面失败: {e}")
                    break
            
            # 模拟人类行为
            self.driver_manager.simulate_human_behavior()
            
            # 查找可下载的文档
            documents = self._find_documents(stock_code, stock_dir)
            
            if not documents:
                logger.info(f"第{page_num}页未找到符合条件的文档")
            else:
                logger.info(f"第{page_num}页发现{len(documents)}个待下载文档")
                
                # 下载当前页面的文件
                downloaded_count = self._download_page_files(documents)
                total_downloaded += downloaded_count
                
                if self.config.max_reports and total_downloaded >= self.config.max_reports:
                    logger.info(f"已达到最大报告数量 {self.config.max_reports}")
                    break
            
            # 检查是否需要重启浏览器
            if self.download_count >= self.config.max_downloads_per_session:
                logger.info("达到单次会话下载限制，重启浏览器...")
                if not self.driver_manager.restart_driver():
                    logger.error("重启WebDriver失败")
                    break
                
                # 重新访问页面并导航到当前页
                try:
                    org_id = self.get_org_id(stock_code)
                    url_fragment = "#research" if self.config.download_type == DownloadType.INVESTOR_RELATIONS else "#periodicReports"
                    url = f"https://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}{url_fragment}"
                    self.driver_manager.driver.get(url)
                    self._random_delay(5, 10)
                    
                    # 导航到当前页（如果不是第一页）
                    if page_num > 1:
                        self._navigate_to_page(page_num)
                        
                except Exception as e:
                    logger.error(f"重新访问页面失败: {e}")
                    break
                
                self.download_count = 0
            
            # 尝试翻页
            if not self._go_to_next_page():
                logger.info("已到达最后一页，下载完成")
                break
            
            page_num += 1
            self._random_delay(3, 8)
        
        logger.info(f"下载完成！共下载 {total_downloaded} 个文档")
        return total_downloaded > 0
    
    def _find_documents(self, stock_code: str, stock_dir: str) -> List[Dict[str, str]]:
        """查找可下载的文档"""
        documents = []
        
        try:
            # 等待页面元素加载
            WebDriverWait(self.driver_manager.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, 'a'))
            )
            
            # 查找所有相关的文档链接
            all_links = self.driver_manager.driver.find_elements(By.TAG_NAME, 'a')
            
            for link in all_links:
                try:
                    text = link.text.strip()
                    href = link.get_attribute('href')
                    
                    if not text or not href:
                        continue
                    
                    # 使用内容过滤器判断是否应包含
                    if not self.content_filter.should_include(text, self.config):
                        continue
                    
                    file_name = self.content_filter.get_file_name(text)
                    save_path = os.path.join(stock_dir, self.clean_filename(file_name))
                    
                    # 检查文件是否已存在
                    if os.path.exists(save_path) and os.path.getsize(save_path) > self.config.min_file_size:
                        logger.info(f"[跳过] 文件已存在: {file_name}")
                        continue
                    
                    documents.append({
                        'href': href,
                        'file_name': file_name,
                        'save_path': save_path
                    })
                    
                except Exception as e:
                    logger.debug(f"处理链接时发生错误: {e}")
                    continue
            
            # 同时查找表格形式的文档
            try:
                table_rows = self.driver_manager.driver.find_elements(By.CSS_SELECTOR, ".el-table__body .el-table__row")
                for row in table_rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 3:
                            title_cell = cells[1] if len(cells) > 1 else cells[0]
                            date_cell = cells[2] if len(cells) > 2 else None
                            
                            title = title_cell.text.strip()
                            date = date_cell.text.strip() if date_cell else ""
                            
                            if title and self.content_filter.should_include(title, self.config):
                                link = title_cell.find_element(By.TAG_NAME, "a")
                                href = link.get_attribute('href')
                                
                                if href:
                                    file_name = self.content_filter.get_file_name(title, date)
                                    save_path = os.path.join(stock_dir, self.clean_filename(file_name))
                                    
                                    if not (os.path.exists(save_path) and os.path.getsize(save_path) > self.config.min_file_size):
                                        documents.append({
                                            'href': href,
                                            'file_name': file_name,
                                            'save_path': save_path
                                        })
                    except Exception:
                        continue
            except Exception:
                pass
                
        except Exception as e:
            logger.error(f"查找文档时发生错误: {e}")
        
        return documents
    
    def _download_page_files(self, documents: List[Dict[str, str]]) -> int:
        """下载当前页面的所有文档"""
        downloaded_count = 0
        
        for idx, doc in enumerate(documents, 1):
            detail_url = doc['href']
            file_name = doc['file_name']
            save_path = doc['save_path']
            
            logger.info(f"正在下载 {idx}/{len(documents)}: {file_name}")
            
            # 尝试下载文件
            success = False
            
            for retry in range(self.config.max_retries):
                try:
                    if retry > 0:
                        logger.info(f"第 {retry + 1} 次重试下载: {file_name}")
                        if not self.driver_manager.restart_driver():
                            logger.error("重启WebDriver失败")
                            break
                    
                    # 清理pdf.txt文件
                    self._cleanup_pdf_txt()
                    
                    # 访问详情页
                    self.driver_manager.driver.get(detail_url)
                    self._random_delay(3, 8)
                    
                    # 模拟人类行为
                    self.driver_manager.simulate_human_behavior()
                    
                    # 查找并点击下载按钮
                    try:
                        download_btn = WebDriverWait(self.driver_manager.driver, 15).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(., '公告下载')]"))
                        )
                    except:
                        # 尝试其他下载按钮选择器
                        download_btn = WebDriverWait(self.driver_manager.driver, 15).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title*='下载'], button[onclick*='download']"))
                        )
                    
                    before_files = set(os.listdir(self.config.save_dir))
                    
                    # 模拟人类点击
                    actions = ActionChains(self.driver_manager.driver)
                    actions.move_to_element(download_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                    logger.info(f"已点击下载按钮，等待文件下载...")
                    
                    # 等待下载完成
                    if self._wait_for_download(before_files, save_path):
                        downloaded_count += 1
                        self.download_count += 1
                        logger.info(f"下载成功: {file_name}")
                        success = True
                        break
                    else:
                        logger.warning(f"下载超时: {file_name}")
                        
                except TimeoutException:
                    logger.warning(f"页面加载超时: {detail_url}")
                except Exception as e:
                    logger.error(f"下载文件失败 {detail_url}: {e}")
                
                # 重试前等待
                if retry < self.config.max_retries - 1:
                    wait_time = random.uniform(*self.config.retry_wait_range)
                    time.sleep(wait_time)
            
            if not success:
                logger.error(f"下载失败（已重试{self.config.max_retries}次）: {file_name}")
            
            # 下载间隔
            self._random_delay(2, 6)
        
        return downloaded_count
    
    def _wait_for_download(self, before_files: set, target_path: str) -> bool:
        """等待文件下载完成"""
        start_time = time.time()
        
        while time.time() - start_time < self.config.download_timeout:
            time.sleep(1)
            
            self._cleanup_pdf_txt()
            
            try:
                after_files = set(os.listdir(self.config.save_dir))
                new_files = after_files - before_files
                
                for file in new_files:
                    file_path = os.path.join(self.config.save_dir, file)
                    
                    if file.lower().endswith('.pdf') and os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        
                        if file_size > self.config.min_file_size:
                            if file_path != target_path:
                                try:
                                    shutil.move(file_path, target_path)
                                except Exception:
                                    pass
                            return True
                        else:
                            try:
                                os.remove(file_path)
                            except Exception:
                                pass
                
                if os.path.exists(target_path) and os.path.getsize(target_path) > self.config.min_file_size:
                    return True
                    
            except Exception as e:
                logger.debug(f"检查下载文件时发生错误: {e}")
        
        return False
    
    def _cleanup_pdf_txt(self):
        """清理pdf.txt文件"""
        try:
            for file in os.listdir(self.config.save_dir):
                if file.lower() == 'pdf.txt':
                    os.remove(os.path.join(self.config.save_dir, file))
        except Exception:
            pass
    
    def _go_to_next_page(self) -> bool:
        """尝试翻到下一页"""
        try:
            self.driver_manager.simulate_human_behavior()
            
            # 方法1: 查找下一页按钮
            next_btn = self.driver_manager.driver.find_element(By.XPATH, "//button[contains(@class, 'el-pagination__next') and not(@disabled)]")
            if next_btn.is_enabled():
                actions = ActionChains(self.driver_manager.driver)
                actions.move_to_element(next_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                self._random_delay(3, 6)
                return True
        except Exception:
            pass
        
        try:
            # 方法2: 查找右箭头按钮
            arrow_icon = self.driver_manager.driver.find_element(By.CSS_SELECTOR, "i.el-icon.el-icon-arrow-right")
            parent_btn = arrow_icon.find_element(By.XPATH, "./ancestor::button[not(@disabled)]")
            if parent_btn.is_enabled():
                actions = ActionChains(self.driver_manager.driver)
                actions.move_to_element(parent_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                self._random_delay(3, 6)
                return True
        except Exception:
            pass
        
        return False
    
    def _navigate_to_page(self, target_page: int):
        """导航到指定页面"""
        try:
            for _ in range(target_page - 1):
                if self._go_to_next_page():
                    self._random_delay(2, 5)
                else:
                    break
        except Exception as e:
            logger.error(f"导航到第{target_page}页失败: {e}")
    
    def _random_delay(self, min_seconds: float, max_seconds: float):
        """随机延迟"""
        delay = random.uniform(min_seconds, max_seconds)
        logger.debug(f"随机延迟 {delay:.2f} 秒")
        time.sleep(delay)

def load_config_from_file(config_file: str) -> Dict[str, Any]:
    """从配置文件加载配置"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        return {}

def create_config_from_dict(config_dict: Dict[str, Any]) -> DownloadConfig:
    """从字典创建配置对象"""
    # 处理枚举类型
    download_type = DownloadType(config_dict.get('download_type', 'investor_relations'))
    
    # 处理报告类型
    report_types_str = config_dict.get('report_types', ['annual', 'semi_annual', 'q1', 'q3'])
    report_types = [ReportType(rt) for rt in report_types_str]
    
    return DownloadConfig(
        stock_code=config_dict['stock_code'],
        download_type=download_type,
        save_dir=config_dict.get('save_dir', 'downloads'),
        mapping_file=config_dict.get('mapping_file', 'stock_orgid_mapping.json'),
        headless=config_dict.get('headless', True),
        max_downloads_per_session=config_dict.get('max_downloads_per_session', 5),
        max_reports=config_dict.get('max_reports', 100),
        report_types=report_types,
        years=config_dict.get('years', [2020, 2021, 2022, 2023, 2024]),
        min_file_size=config_dict.get('min_file_size', 10 * 1024),
        max_retries=config_dict.get('max_retries', 3)
    )

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='巨潮资讯网统一下载器')
    parser.add_argument('--stock-code', required=True, help='股票代码')
    parser.add_argument('--type', choices=['investor_relations', 'financial_reports'], 
                       default='investor_relations', help='下载类型')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--save-dir', default='downloads', help='保存目录')
    parser.add_argument('--headless', action='store_true', help='是否使用无头模式')
    parser.add_argument('--report-types', nargs='*', 
                       choices=['annual', 'semi_annual', 'q1', 'q3'],
                       default=['annual', 'semi_annual', 'q1', 'q3'],
                       help='财务报告类型（仅财务报告下载有效）')
    parser.add_argument('--years', nargs='*', type=int,
                       default=[2020, 2021, 2022, 2023, 2024],
                       help='年份范围（仅财务报告下载有效）')
    parser.add_argument('--max-reports', type=int, default=100, help='最大下载数量')
    
    args = parser.parse_args()
    
    # 加载配置文件（如果指定）
    config_dict = {}
    if args.config and os.path.exists(args.config):
        config_dict = load_config_from_file(args.config)
    
    # 合并命令行参数
    config_dict.update({
        'stock_code': args.stock_code,
        'download_type': args.type,
        'save_dir': args.save_dir,
        'headless': args.headless,
        'max_reports': args.max_reports
    })
    
    if args.type == 'financial_reports':
        config_dict.update({
            'report_types': args.report_types,
            'years': args.years
        })
    
    # 创建配置对象
    config = create_config_from_dict(config_dict)
    
    # 开始下载
    downloader = CninfoUnifiedDownloader(config)
    
    print("=" * 70)
    print(f"开始下载 {args.stock_code} 的{config.download_type.value}")
    print("=" * 70)
    
    success = downloader.download()
    
    if success:
        print(f"\n[SUCCESS] 下载完成！")
        print(f"文件保存在: {config.save_dir}/")
    else:
        print(f"\n[FAILED] 下载过程中遇到问题，请查看日志文件")

if __name__ == "__main__":
    main()