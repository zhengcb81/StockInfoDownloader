#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
巨潮资讯网财务报告实际下载器

基于成功的投资者关系下载器架构，专门用于下载财务报告
包括：年度报告、半年度报告、季度报告
"""

import os
import re
import sys
import json
import time
import logging
import shutil
import random
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
        logging.FileHandler('cninfo_financial_real.log')
    ]
)
logger = logging.getLogger('cninfo_financial_real')

class CninfoFinancialRealDownloader:
    """巨潮资讯网财务报告实际下载器"""
    
    def __init__(self, save_dir='downloads', mapping_file='stock_orgid_mapping.json'):
        """
        初始化下载器
        
        参数:
            save_dir: 保存文件的目录
            mapping_file: 股票代码与组织ID的映射文件
        """
        self.save_dir = save_dir
        self.mapping_file = mapping_file
        self.driver = None
        self.download_count = 0  # 下载计数器
        self.max_downloads_per_session = 5  # 每个会话最大下载数
        self.webdriver_process_id = None  # WebDriver进程ID
        self.chromedriver_process_id = None  # ChromeDriver进程ID
        
        # 创建保存目录
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # User-Agent池
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
    
    def clean_filename(self, filename):
        """清理文件名中的非法字符"""
        return re.sub(r'[\\/:*?"<>|]', '_', filename)
    
    def get_org_id(self, stock_code, force_run=False):
        """获取股票代码对应的组织ID"""
        return get_org_id_by_code(stock_code, force_run=force_run, mapping_file=self.mapping_file)
    
    def setup_driver(self, headless=True):
        """设置WebDriver，复用投资者关系下载器的成功配置"""
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
            
            if headless:
                chrome_options.add_argument('--headless')
            
            # 设置下载目录
            prefs = {
                "download.default_directory": os.path.abspath(self.save_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # 创建WebDriver，增加重试机制
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
                    
                    if hasattr(self, 'driver') and self.driver:
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
    
    def download_financial_reports(self, stock_code, report_types=None, years=None, max_reports=50, headless=True):
        """
        下载财务报告，使用与投资者关系下载器相同的成功模式
        
        参数:
            stock_code: 股票代码
            report_types: 报告类型列表 ['annual', 'semi_annual', 'q1', 'q3']
            years: 年份列表
            max_reports: 最大报告数量
            headless: 是否使用无头模式
        """
        if report_types is None:
            report_types = ['annual', 'semi_annual', 'q1', 'q3']
        
        # 获取组织ID
        org_id = self.get_org_id(stock_code)
        if not org_id:
            logger.error(f"无法获取 {stock_code} 的组织ID")
            return False
        
        # 设置WebDriver
        if not self.setup_driver(headless):
            return False
        
        try:
            # 获取股票名称并创建目录（直接放在downloads/公司名称下）
            stock_name = get_stock_name(stock_code, self.mapping_file)
            if not stock_name or stock_name.startswith('错误') or stock_name.startswith('网络'):
                stock_name = stock_code
            
            stock_dir = os.path.join(self.save_dir, self.clean_filename(stock_name))
            logger.info(f"保存目录: {stock_dir}")
            os.makedirs(stock_dir, exist_ok=True)
            
            # 构造访问URL - 直接访问定期报告页面
            url = f"https://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#periodicReports"
            
            logger.info(f"访问股票 {stock_code} 的定期报告页面: {url}")
            self.driver.get(url)
            
            self.random_delay(5, 10)  # 等待页面加载
            logger.info('页面加载完成')
            
            # 分页下载财务报告
            return self._download_all_financial_reports(
                driver=self.driver, 
                stock_code=stock_code, 
                stock_dir=stock_dir,
                report_types=report_types,
                years=years,
                max_reports=max_reports,
                headless=headless
            )
            
        except Exception as e:
            logger.error(f"页面加载异常: {e}")
            return False
        finally:
            self.close_driver()
    
    def _download_all_financial_reports(self, driver, stock_code, stock_dir, report_types, years, max_reports, headless=True):
        """下载所有页面的财务报告"""
        page_num = 1
        total_downloaded = 0
        
        while True:
            logger.info(f"正在处理第{page_num}页...")
            
            # 模拟人类行为
            self.random_delay(2, 5)
            
            # 查找当前页面的财务报告
            financial_reports = self._find_financial_reports(driver, stock_code, stock_dir, report_types, years)
            
            if not financial_reports:
                logger.info(f"第{page_num}页未找到符合条件的财务报告")
            else:
                logger.info(f"第{page_num}页发现{len(financial_reports)}个待下载报告")
                
                # 下载当前页面的文件
                downloaded_count = self._download_page_files(driver, financial_reports, headless)
                total_downloaded += downloaded_count
                
                if max_reports and total_downloaded >= max_reports:
                    logger.info(f"已达到最大报告数量 {max_reports}")
                    break
            
            # 检查是否需要重启浏览器
            if self.download_count >= self.max_downloads_per_session:
                logger.info("达到单次会话下载限制，重启浏览器...")
                if not self.restart_driver(headless):
                    logger.error("重启WebDriver失败")
                    break
                
                # 更新driver引用为新的实例
                driver = self.driver
                
                # 重新访问页面并导航到当前页
                try:
                    org_id = self.get_org_id(stock_code)
                    url = f"https://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#periodicReports"
                    driver.get(url)
                    self.random_delay(5, 10)
                    
                    # 导航到当前页（如果不是第一页）
                    if page_num > 1:
                        self._navigate_to_page(driver, page_num)
                        
                except Exception as e:
                    logger.error(f"重新访问页面失败: {e}")
                    break
                
                self.download_count = 0
            
            # 尝试翻页
            if not self._go_to_next_page(driver):
                logger.info("已到达最后一页，下载完成")
                break
            
            page_num += 1
            self.random_delay(3, 8)  # 翻页后随机等待
        
        logger.info(f"下载完成！共下载 {total_downloaded} 个财务报告")
        return total_downloaded > 0
    
    def _find_financial_reports(self, driver, stock_code, stock_dir, report_types, years):
        """查找当前页面的财务报告"""
        reports = []
        
        try:
            # 等待页面元素加载
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, 'a'))
            )
            
            # 查找所有相关的财务报告链接
            all_links = driver.find_elements(By.TAG_NAME, 'a')
            
            for link in all_links:
                try:
                    text = link.text.strip()
                    href = link.get_attribute('href')
                    
                    if not text or not href:
                        continue
                    
                    # 跳过英文版报告
                    text_lower = text.lower()
                    english_keywords = ['英文版', 'english', '英文', 'english version', 'english edition']
                    for keyword in english_keywords:
                        if keyword in text_lower:
                            continue
                    
                    # 检查是否是财务报告
                    is_financial_report = False
                    report_type = None
                    
                    # 检查报告类型
                    if '年度报告' in text and 'annual' in report_types:
                        is_financial_report = True
                        report_type = 'annual'
                    elif '半年度报告' in text and 'semi_annual' in report_types:
                        is_financial_report = True
                        report_type = 'semi_annual'
                    elif '第一季度报告' in text and 'q1' in report_types:
                        is_financial_report = True
                        report_type = 'q1'
                    elif '第三季度报告' in text and 'q3' in report_types:
                        is_financial_report = True
                        report_type = 'q3'
                    
                    if is_financial_report:
                        # 检查年份
                        if years:
                            year_match = re.search(r'(20\d{2})', text)
                            if year_match:
                                report_year = int(year_match.group(1))
                                if report_year not in years:
                                    continue
                        
                        file_name = f"{self.clean_filename(text)}.pdf"
                        save_path = os.path.join(stock_dir, file_name)
                        
                        # 检查文件是否已存在
                        if os.path.exists(save_path) and os.path.getsize(save_path) > 10 * 1024:
                            logger.info(f"[跳过] 文件已存在: {file_name}")
                            continue
                        
                        reports.append({
                            'href': href,
                            'file_name': file_name,
                            'save_path': save_path,
                            'report_type': report_type
                        })
                        
                except Exception as e:
                    logger.debug(f"处理链接时发生错误: {e}")
                    continue
            
            # 同时查找表格形式的报告
            try:
                table_rows = driver.find_elements(By.CSS_SELECTOR, ".el-table__body .el-table__row")
                for row in table_rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 3:
                            title_cell = cells[1] if len(cells) > 1 else cells[0]
                            date_cell = cells[2] if len(cells) > 2 else None
                            
                            title = title_cell.text.strip()
                            date = date_cell.text.strip() if date_cell else ""
                            
                            # 跳过英文版报告
                            title_lower = title.lower()
                            english_keywords = ['英文版', 'english', '英文', 'english version', 'english edition']
                            skip_english = any(keyword in title_lower for keyword in english_keywords)
                            
                            # 检查报告类型和年份
                            if not skip_english and self._is_desired_report(title, report_types, years):
                                link = title_cell.find_element(By.TAG_NAME, "a")
                                href = link.get_attribute('href')
                                
                                if href:
                                    file_name = f"{self.clean_filename(title)}_{date}.pdf"
                                    save_path = os.path.join(stock_dir, file_name)
                                    
                                    if not (os.path.exists(save_path) and os.path.getsize(save_path) > 10 * 1024):
                                        reports.append({
                                            'href': href,
                                            'file_name': file_name,
                                            'save_path': save_path
                                        })
                    except Exception:
                        continue
            except Exception:
                pass
                
        except Exception as e:
            logger.error(f"查找财务报告时发生错误: {e}")
        
        return reports
    
    def _is_desired_report(self, title, report_types, years):
        """检查是否是所需的报告类型和年份"""
        title_lower = title.lower()
        
        # 跳过英文版报告
        english_keywords = ['英文版', 'english', '英文', 'english version', 'english edition']
        for keyword in english_keywords:
            if keyword in title_lower:
                return False
        
        # 检查报告类型
        type_match = False
        if 'annual' in report_types and ('年度报告' in title or '年报' in title):
            type_match = True
        elif 'semi_annual' in report_types and ('半年度报告' in title or '中报' in title):
            type_match = True
        elif 'q1' in report_types and ('第一季度报告' in title or '一季报' in title):
            type_match = True
        elif 'q3' in report_types and ('第三季度报告' in title or '三季报' in title):
            type_match = True
        
        if not type_match:
            return False
        
        # 检查年份
        if years:
            year_match = re.search(r'(20\d{2})', title)
            if year_match:
                report_year = int(year_match.group(1))
                return report_year in years
        
        return True
    
    def _download_page_files(self, driver, reports, headless=True):
        """下载当前页面的所有财务报告"""
        downloaded_count = 0
        
        for idx, report in enumerate(reports, 1):
            detail_url = report['href']
            file_name = report['file_name']
            save_path = report['save_path']
            
            logger.info(f"正在下载 {idx}/{len(reports)}: {file_name}")
            
            # 尝试下载文件
            success = False
            max_retries = 3
            
            for retry in range(max_retries):
                try:
                    if retry > 0:
                        logger.info(f"第 {retry + 1} 次重试下载: {file_name}")
                        if not self.restart_driver(headless):
                            logger.error("重启WebDriver失败")
                            break
                        driver = self.driver
                    
                    # 清理pdf.txt文件
                    self._cleanup_pdf_txt()
                    
                    # 访问详情页
                    driver.get(detail_url)
                    self.random_delay(3, 8)
                    
                    # 模拟人类行为
                    self.simulate_human_behavior()
                    
                    # 查找并点击下载按钮
                    try:
                        download_btn = WebDriverWait(driver, 15).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(., '公告下载')]"))
                        )
                    except:
                        # 尝试其他下载按钮选择器
                        download_btn = WebDriverWait(driver, 15).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title*='下载'], button[onclick*='download']"))
                        )
                    
                    before_files = set(os.listdir(self.save_dir))
                    
                    # 模拟人类点击
                    actions = ActionChains(driver)
                    actions.move_to_element(download_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                    logger.info(f"已点击下载按钮，等待文件下载...")
                    
                    # 等待下载完成
                    if self._wait_for_download(before_files, save_path, timeout=60):
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
                if retry < max_retries - 1:
                    self.random_delay(5, 15)
            
            if not success:
                logger.error(f"下载失败（已重试{max_retries}次）: {file_name}")
            
            # 下载间隔
            self.random_delay(2, 6)
        
        return downloaded_count
    
    def _wait_for_download(self, before_files, target_path, timeout=60):
        """等待文件下载完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            time.sleep(1)
            
            self._cleanup_pdf_txt()
            
            try:
                after_files = set(os.listdir(self.save_dir))
                new_files = after_files - before_files
                
                for file in new_files:
                    file_path = os.path.join(self.save_dir, file)
                    
                    if file.lower().endswith('.pdf') and os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        
                        if file_size > 10 * 1024:
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
                
                if os.path.exists(target_path) and os.path.getsize(target_path) > 10 * 1024:
                    return True
                    
            except Exception as e:
                logger.debug(f"检查下载文件时发生错误: {e}")
        
        return False
    
    def _cleanup_pdf_txt(self):
        """清理pdf.txt文件"""
        try:
            for file in os.listdir(self.save_dir):
                if file.lower() == 'pdf.txt':
                    os.remove(os.path.join(self.save_dir, file))
        except Exception:
            pass
    
    def _go_to_next_page(self, driver):
        """尝试翻到下一页"""
        try:
            self.simulate_human_behavior()
            
            # 方法1: 查找下一页按钮
            next_btn = driver.find_element(By.XPATH, "//button[contains(@class, 'el-pagination__next') and not(@disabled)]")
            if next_btn.is_enabled():
                actions = ActionChains(driver)
                actions.move_to_element(next_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                self.random_delay(3, 6)
                return True
        except Exception:
            pass
        
        try:
            # 方法2: 查找右箭头按钮
            arrow_icon = driver.find_element(By.CSS_SELECTOR, "i.el-icon.el-icon-arrow-right")
            parent_btn = arrow_icon.find_element(By.XPATH, "./ancestor::button[not(@disabled)]")
            if parent_btn.is_enabled():
                actions = ActionChains(driver)
                actions.move_to_element(parent_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                self.random_delay(3, 6)
                return True
        except Exception:
            pass
        
        return False
    
    def _navigate_to_page(self, driver, target_page):
        """导航到指定页面"""
        try:
            for _ in range(target_page - 1):
                if self._go_to_next_page(driver):
                    self.random_delay(2, 5)
                else:
                    break
        except Exception as e:
            logger.error(f"导航到第{target_page}页失败: {e}")
    
    def random_delay(self, min_seconds=2, max_seconds=8):
        """随机延迟"""
        delay = random.uniform(min_seconds, max_seconds)
        logger.debug(f"随机延迟 {delay:.2f} 秒")
        time.sleep(delay)
    
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

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='下载指定股票的财务报告')
    parser.add_argument('--stock-code', default='300416', help='股票代码，默认为300416')
    parser.add_argument('--stock-name', default='苏试试验', help='股票名称，默认为苏试试验')
    parser.add_argument('--report-types', nargs='+', 
                       default=['annual', 'semi_annual', 'q1', 'q3'],
                       help='报告类型: annual, semi_annual, q1, q3')
    parser.add_argument('--years', nargs='+', type=int,
                       default=[2020, 2021, 2022, 2023, 2024],
                       help='年份范围')
    parser.add_argument('--max-reports', type=int, default=50,
                       help='最大下载数量')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='是否使用无头模式')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"{args.stock_name}历年财务报告下载")
    print("=" * 60)
    
    save_dir = f'downloads/{args.stock_name}'
    downloader = CninfoFinancialRealDownloader(save_dir=save_dir)
    
    success = downloader.download_financial_reports(
        stock_code=args.stock_code,
        report_types=args.report_types,
        years=args.years,
        max_reports=args.max_reports,
        headless=args.headless
    )
    
    if success:
        print(f"\n[SUCCESS] {args.stock_name}历年财报下载完成！")
        print(f"文件保存在: {save_dir}/")
    else:
        print("\n[FAILED] 下载过程中遇到问题，请查看日志文件")

if __name__ == "__main__":
    main()