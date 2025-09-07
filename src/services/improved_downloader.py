#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
改进的下载服务模块
结合新旧下载器的优点，提供更稳定的下载功能
"""

import os
import re
import time
import random
import shutil
from typing import List, Optional, Dict, Any
from pathlib import Path
from urllib.parse import urljoin, urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains

from ..core.logger import get_logger
from ..core.config import ConfigManager
from ..data.models import StockInfo, DownloadRecord, DownloadStatus
from ..data.mapping import MappingManager
from ..web.driver import WebDriverManager
from ..web.anti_crawler import AntiCrawlerStrategy

logger = get_logger(__name__)


class ImprovedDownloadService:
    """改进的下载服务，结合新旧下载器的优点"""
    
    def __init__(self, 
                 save_dir: str = "downloads",
                 mapping_file: str = "stock_orgid_mapping.json"):
        """
        初始化下载服务
        
        Args:
            save_dir: 下载文件保存目录
            mapping_file: 映射文件路径
        """
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)
        
        self.mapping_manager = MappingManager(mapping_file)
        self.driver_manager = WebDriverManager(headless=True, download_dir=str(self.save_dir))
        self.anti_crawler = AntiCrawlerStrategy()
        
        # 配置反爬虫策略
        self.anti_crawler.set_session_parameters(
            min_delay=2.0,
            max_delay=8.0,
            max_downloads=5
        )
        
        # 从旧下载器借鉴的属性
        self.download_count = 0
        self.max_downloads_per_session = 5
    
    def clean_filename(self, filename):
        """清理文件名中的非法字符（从旧下载器复制）"""
        return re.sub(r'[\\/:*?"<>|]', '_', filename)
    
    def dynamic_delay(self, base_min=2, base_max=8):
        """动态延迟（从旧下载器复制）"""
        delay_factor = 1 + (self.download_count / 20)
        min_delay = base_min * delay_factor
        max_delay = base_max * delay_factor
        
        delay = random.uniform(min_delay, max_delay)
        logger.debug(f"动态延迟 {delay:.2f} 秒 (因子: {delay_factor:.2f})")
        time.sleep(delay)
    
    def simulate_human_behavior(self):
        """模拟人类行为（简化版）"""
        try:
            if not hasattr(self, '_driver') or not self._driver:
                return
                
            # 随机滚动
            scroll_amount = random.randint(200, 600)
            self._driver.execute_script(f"window.scrollBy(0, {scroll_amount})")
            time.sleep(random.uniform(0.5, 1.5))
            
            # 随机延迟
            time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            logger.debug(f"模拟人类行为失败: {e}")
    
    def download_stock_pdfs(self, 
                          stock_code: str,
                          stock_name: str,
                          suffix: str = "research",
                          allowed_keywords: Optional[List[str]] = None,
                          max_pages: int = 5,
                          max_retries: int = 3) -> bool:
        """
        下载指定股票的PDF文件（借鉴旧下载器的成功算法）
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            suffix: 页面后缀
            allowed_keywords: 允许的关键词列表
            max_pages: 最大页数
            max_retries: 最大重试次数
            
        Returns:
            bool: 下载是否成功
        """
        # 获取组织ID
        org_id = self.mapping_manager.get_org_id(stock_code)
        if not org_id:
            logger.error(f"无法获取组织ID: {stock_code}")
            return False
        
        # 创建公司目录
        company_dir = self.save_dir / self.clean_filename(stock_name)
        company_dir.mkdir(exist_ok=True)
        
        # 设置WebDriver
        try:
            self._driver = self.driver_manager.create_driver()
            
            # 构造访问URL
            url = f"https://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#{suffix}"
            
            # 访问页面
            logger.info(f"访问页面: {url}")
            self._driver.get(url)
            self.dynamic_delay(5, 10)
            
            # 分页下载
            return self._download_all_pages(
                stock_code=stock_code,
                company_dir=company_dir,
                allowed_keywords=allowed_keywords,
                max_pages=max_pages,
                max_retries=max_retries
            )
            
        except Exception as e:
            logger.error(f"下载失败: {e}")
            return False
        finally:
            if hasattr(self, '_driver') and self._driver:
                self.driver_manager.close_driver()
    
    def _download_all_pages(self, 
                           stock_code: str,
                           company_dir: Path,
                           allowed_keywords: Optional[List[str]],
                           max_pages: int,
                           max_retries: int) -> bool:
        """下载所有页面的文件（借鉴旧下载器的算法）"""
        page_num = 1
        total_downloaded = 0
        
        while page_num <= max_pages:
            logger.info(f"正在处理第 {page_num} 页...")
            
            try:
                # 查找所有链接
                all_links = self._driver.find_elements(By.TAG_NAME, 'a')
                detail_infos = []
                
                for link in all_links:
                    try:
                        text = link.text.strip()
                        href = link.get_attribute('href')
                        
                        # 1. 检查基本条件：必须是详情页链接
                        if not (href and '/new/disclosure/detail' in href
                                and f'stockCode={stock_code}' in href):
                            continue
                        
                        # 2. 检查关键词过滤
                        if allowed_keywords:
                            keyword_match = any(keyword in text for keyword in allowed_keywords)
                            if not keyword_match:
                                logger.debug(f"[跳过] 文件名不包含关键词: {text}")
                                continue
                        
                        # 3. 检查文件是否已存在
                        file_name = f"{self.clean_filename(text)}.pdf"
                        save_path = company_dir / file_name
                        
                        if save_path.exists() and save_path.stat().st_size > 10 * 1024:
                            logger.info(f"[跳过] 文件已存在: {file_name}")
                            continue
                        
                        # 4. 添加到下载列表
                        detail_infos.append({
                            'href': href,
                            'file_name': file_name,
                            'save_path': save_path
                        })
                        
                    except Exception as e:
                        logger.debug(f"处理链接时发生错误: {e}")
                        continue
                
                # 下载本页的文件
                page_downloaded = 0
                for detail_info in detail_infos:
                    if self._download_single_file(detail_info):
                        page_downloaded += 1
                        total_downloaded += 1
                        self.download_count += 1
                        
                        # 检查会话限制
                        if self.download_count >= self.max_downloads_per_session:
                            logger.info("达到会话下载限制，重启浏览器")
                            self._driver = self.driver_manager.restart_driver()
                            self.download_count = 0
                
                if page_downloaded > 0:
                    logger.info(f"第 {page_num} 页下载了 {page_downloaded} 个文件")
                else:
                    logger.info(f"第 {page_num} 页未找到目标文件")
                
                # 检查是否需要翻页
                if page_num >= max_pages:
                    logger.info(f"已达到最大页数限制: {max_pages}")
                    break
                
                # 尝试翻到下一页
                if not self._go_to_next_page():
                    logger.info("已到达最后一页")
                    break
                
                page_num += 1
                self.dynamic_delay(3, 6)
                
            except Exception as e:
                logger.error(f"处理第 {page_num} 页时发生错误: {e}")
                break
        
        logger.info(f"总共下载了 {total_downloaded} 个文件")
        return total_downloaded > 0
    
    def _download_single_file(self, detail_info: Dict[str, Any]) -> bool:
        """下载单个文件（借鉴旧下载器的成功算法）"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                detail_url = detail_info['href']
                file_name = detail_info['file_name']
                save_path = detail_info['save_path']
                
                logger.info(f"正在下载: {file_name}")
                
                # 访问详情页
                self._driver.get(detail_url)
                self.dynamic_delay(3, 8)
                
                # 模拟人类行为
                self.simulate_human_behavior()
                
                # 查找并点击下载按钮
                download_btn = WebDriverWait(self._driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., '公告下载')]"))
                )
                
                # 记录下载前的文件
                before_files = set(os.listdir(self.save_dir))
                
                # 模拟人类点击
                actions = ActionChains(self._driver)
                actions.move_to_element(download_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                logger.info("已点击下载按钮，等待文件下载...")
                
                # 等待下载完成
                if self._wait_for_download(before_files, save_path, timeout=60):
                    logger.info(f"下载成功: {file_name}")
                    return True
                else:
                    logger.warning(f"下载超时: {file_name}")
                    
            except TimeoutException:
                logger.warning(f"页面加载超时: {detail_info['href']}")
            except Exception as e:
                logger.error(f"下载失败: {e}")
            
            if attempt < max_retries - 1:
                self.dynamic_delay(5, 10)
        
        return False
    
    def _wait_for_download(self, before_files: set, save_path: Path, timeout: int = 60) -> bool:
        """等待文件下载完成（从旧下载器复制）"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 检查目标文件
            if save_path.exists() and save_path.stat().st_size > 10 * 1024:
                return True
            
            # 检查下载目录中的新文件
            current_files = set(os.listdir(self.save_dir))
            new_files = current_files - before_files
            
            for new_file in new_files:
                if new_file.endswith('.pdf'):
                    new_file_path = self.save_dir / new_file
                    if new_file_path.stat().st_size > 10 * 1024:
                        # 移动文件到正确位置
                        shutil.move(str(new_file_path), str(save_path))
                        return True
            
            time.sleep(1)
        
        return False
    
    def _go_to_next_page(self) -> bool:
        """翻到下一页（完全复制旧下载器的算法）"""
        try:
            # 模拟人类行为
            self.simulate_human_behavior()
            
            # 方法1: 查找下一页按钮
            try:
                next_btn = self._driver.find_element(By.XPATH, "//button[contains(@class, 'el-pagination__next') and not(@disabled)]")
                if next_btn.is_enabled():
                    actions = ActionChains(self._driver)
                    actions.move_to_element(next_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                    self.dynamic_delay(3, 6)
                    return True
            except Exception:
                pass
            
            # 方法2: 查找右箭头按钮
            try:
                arrow_icon = self._driver.find_element(By.CSS_SELECTOR, "i.el-icon.el-icon-arrow-right")
                parent_btn = arrow_icon.find_element(By.XPATH, "./ancestor::button[not(@disabled)]")
                if parent_btn.is_enabled():
                    actions = ActionChains(self._driver)
                    actions.move_to_element(parent_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                    self.dynamic_delay(3, 6)
                    return True
            except Exception:
                pass
            
            # 方法3: 查找页码输入框（备用方法）
            try:
                # 获取当前页码
                page_input = self._driver.find_element(By.CLASS_NAME, 'page-input')
                current_page = int(page_input.get_attribute('value') or '1')
                
                # 输入下一页
                page_input.clear()
                page_input.send_keys(str(current_page + 1))
                
                # 查找并点击跳转按钮
                go_button = self._driver.find_element(By.CLASS_NAME, 'page-go')
                go_button.click()
                
                # 等待页面加载
                self.dynamic_delay(3, 6)
                return True
            except Exception:
                pass
                
        except Exception as e:
            logger.debug(f"翻页失败: {e}")
        
        return False