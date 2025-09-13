#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from src.core.logger import get_logger
"""
巨潮资讯网投资者关系活动记录表下载器

本程序用于自动下载巨潮资讯网上的投资者关系活动记录表PDF文件。
支持通过股票代码查询，自动从映射表中查找组织ID，下载PDF格式的投资者关系活动记录表。

作者: Manus
日期: 2025-05-17
"""

import sys
import locale

# 设置控制台编码为UTF-8
if sys.platform == 'win32':
    try:
        # Windows下设置控制台编码为UTF-8
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        # 如果设置失败，忽略错误
        pass

import os
import re
import sys
import json
import time
import logging
import shutil
import random
from pathlib import Path
from orgid_utils import get_org_id_by_code
from get_stock_name import get_stock_name

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException

# 添加配置管理
sys.path.insert(0, str(Path(__file__).parent / "src"))
from core.config import ConfigManager

# 初始化结构化日志记录器
logger = get_logger('cninfo_downloader', 'logs/cninfo_downloader.log')

class CninfoDownloader:
    """巨潮资讯网投资者关系活动记录表下载器"""
    
    def __init__(self, save_dir='downloads', mapping_file='stock_orgid_mapping.json', config_file=None):
        """
        初始化下载器
        
        参数:
            save_dir: 保存文件的目录
            mapping_file: 股票代码与组织ID的映射文件
            config_file: 配置文件路径
        """
        self.save_dir = save_dir
        self.mapping_file = mapping_file
        self.driver = None
        self.download_count = 0  # 下载计数器
        
        # 初始化配置管理器
        self.config_manager = ConfigManager(config_file)
        
        # 从配置获取参数
        self.max_downloads_per_session = self.config_manager.get('download.max_downloads_per_session', 5)
        self.user_agents = self.config_manager.get('webdriver.user_agents', [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ])
        
        # 创建保存目录
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
    
    def clean_filename(self, filename):
        """清理文件名中的非法字符"""
        return re.sub(r'[\\/:*?"<>|]', '_', filename)
    
    def get_org_id(self, stock_code, force_run=False):
        """
        获取股票代码对应的组织ID
        
        参数：
            stock_code: 股票代码
            force_run: 是否强制重新爬取org id
        返回：
            str: 组织ID，如果获取失败则返回None
        """
        return get_org_id_by_code(stock_code, force_run=force_run, mapping_file=self.mapping_file)
    
    def setup_driver(self, headless=True):
        """设置WebDriver，增强反检测能力"""
        try:
            # 确保之前的driver完全关闭
            if self.driver:
                self.close_driver()
            
            chrome_options = Options()
            
            # 从配置获取参数
            window_size = self.config_manager.get('webdriver.window_size', '1920,1080')
            page_load_timeout = self.config_manager.get('timeout.page_load', 30)
            max_attempts = self.config_manager.get('retries.max_attempts', 3)
            
            # 增加页面加载超时时间以处理JavaScript渲染
            if page_load_timeout < 15:
                page_load_timeout = 30
                logger.info(f"页面加载超时时间增加到 {page_load_timeout} 秒以处理JavaScript渲染")
            
            # 基础设置
            chrome_options.add_argument(f'--window-size={window_size}')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--remote-debugging-port=0')  # 使用随机端口
            
            # 增强稳定性选项
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-features=TranslateUI')
            chrome_options.add_argument('--disable-component-extensions-with-background-pages')
            chrome_options.add_argument('--disable-domain-reliability')
            chrome_options.add_argument('--disable-background-mode')
            chrome_options.add_argument('--disable-setuid-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--no-default-browser-check')
            chrome_options.add_argument('--disable-sync')
            chrome_options.add_argument('--disable-translate')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-ipc-flooding-protection')
            chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
            chrome_options.add_argument('--disable-webgl')
            chrome_options.add_argument('--disable-webrtc')
            chrome_options.add_argument('--disable-features=WebRtcHideLocalIpsWithMdns')
            
            # 随机User-Agent
            user_agent = random.choice(self.user_agents)
            chrome_options.add_argument(f'user-agent={user_agent}')
            logger.info(f"使用User-Agent: {user_agent}", user_agent=user_agent)
            
            if headless:
                chrome_options.add_argument('--headless')
            
            # 设置下载目录
            prefs = {
                "download.default_directory": os.path.abspath(self.save_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True,
                "safebrowsing.enabled": False,
                "profile.default_content_settings.popups": 0,
                "profile.default_content_setting_values.automatic_downloads": 1,
                "profile.content_settings.exceptions.automatic_downloads.*.setting": 1
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # 反自动化检测
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 创建WebDriver，增加重试机制
            for attempt in range(max_attempts):
                try:
                    logger.info(f"正在初始化WebDriver (尝试 {attempt + 1}/{max_attempts})...", attempt=attempt+1, max_attempts=max_attempts)
                    
                    # 清理可能存在的僵尸进程
                    self._cleanup_chrome_processes()
                    
                    self.driver = webdriver.Chrome(options=chrome_options)
                    self.driver.set_page_load_timeout(page_load_timeout)
                    element_wait_timeout = self.config_manager.get('timeout.element_wait', 5)
                    self.driver.implicitly_wait(element_wait_timeout)
                    
                    # 执行增强反检测脚本
                    self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    self.driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
                    self.driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en-US', 'en']})")
                    self.driver.execute_script("Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8})")
                    self.driver.execute_script("Object.defineProperty(navigator, 'deviceMemory', {get: () => 8})")
                    self.driver.execute_script("Object.defineProperty(screen, 'width', {get: () => 1920})")
                    self.driver.execute_script("Object.defineProperty(screen, 'height', {get: () => 1080})")
                    self.driver.execute_script("Object.defineProperty(screen, 'availWidth', {get: () => 1920})")
                    self.driver.execute_script("Object.defineProperty(screen, 'availHeight', {get: () => 1040})")
                    
                    # 清除自动化特征
                    self.driver.delete_all_cookies()
                    
                    # 测试driver是否正常工作
                    self.driver.get("about:blank")
                    
                    logger.info("WebDriver初始化成功")
                    return True
                    
                except Exception as e:
                    logger.warning(f"WebDriver初始化尝试 {attempt + 1} 失败: {e}", attempt=attempt+1, error=str(e))
                    
                    # 清理失败的driver
                    if hasattr(self, 'driver') and self.driver:
                        try:
                            self.driver.quit()
                        except Exception:
                            pass
                        self.driver = None
                    
                    if attempt < max_attempts - 1:
                        wait_between = self.config_manager.get('retries.wait_between', 5)
                        wait_time = random.uniform(wait_between - 2, wait_between + 3)
                        logger.info(f"等待 {wait_time:.2f} 秒后重试...", wait_time=round(wait_time, 2))
                        time.sleep(wait_time)
                    else:
                        raise e
            
            return False
            
        except Exception as e:
            logger.error(f"WebDriver初始化失败: {e}", error=str(e))
            return False
    
    def _cleanup_chrome_processes(self):
        """清理可能存在的Chrome僵尸进程"""
        try:
            import subprocess
            import platform
            
            # 只清理chromedriver进程，不清理chrome浏览器进程
            if platform.system() == "Windows":
                # Windows系统只清理chromedriver进程
                try:
                    subprocess.run(['taskkill', '/f', '/im', 'chromedriver.exe'], 
                                 capture_output=True, timeout=10)
                except Exception:
                    pass
            else:
                # Linux/Mac系统只清理chromedriver进程
                try:
                    subprocess.run(['pkill', '-f', 'chromedriver'], 
                                 capture_output=True, timeout=10)
                except Exception:
                    pass
                    
            time.sleep(1)  # 等待进程完全结束
            
        except Exception as e:
            logger.debug(f"清理Chrome进程时发生错误: {e}")
    
    def close_driver(self):
        """关闭WebDriver"""
        if self.driver:
            try:
                # 先尝试关闭所有窗口
                try:
                    self.driver.close()
                except Exception:
                    pass
                
                # 然后退出WebDriver
                self.driver.quit()
                logger.info("WebDriver已关闭")
            except Exception as e:
                logger.error(f"关闭WebDriver时发生错误: {e}")
            finally:
                # 确保driver引用被清空
                self.driver = None
                
                # 额外等待确保进程完全结束
                time.sleep(2)
    
    def restart_driver(self, headless=True):
        """重启WebDriver"""
        logger.info("正在重启WebDriver...")
        
        # 彻底关闭当前driver
        self.close_driver()
        
        # 等待更长时间确保进程完全结束
        wait_between = self.config_manager.get('retries.wait_between', 5)
        wait_time = random.uniform(wait_between + 3, wait_between + 8)
        logger.info(f"等待 {wait_time:.2f} 秒确保进程完全结束...")
        time.sleep(wait_time)
        
        # 尝试多次重启
        max_restart_attempts = 3
        for attempt in range(max_restart_attempts):
            try:
                logger.info(f"尝试重启WebDriver (第 {attempt + 1}/{max_restart_attempts} 次)...")
                if self.setup_driver(headless):
                    logger.info("WebDriver重启成功")
                    return True
                else:
                    logger.warning(f"WebDriver重启尝试 {attempt + 1} 失败")
            except Exception as e:
                logger.error(f"WebDriver重启尝试 {attempt + 1} 异常: {e}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_restart_attempts - 1:
                retry_wait = random.uniform(8, 15)
                logger.info(f"等待 {retry_wait:.2f} 秒后重试...")
                time.sleep(retry_wait)
        
        logger.error("WebDriver重启失败，已尝试所有重试次数")
        return False
    
    def random_delay(self, min_seconds=2, max_seconds=8):
        """随机延迟"""
        delay = random.uniform(min_seconds, max_seconds)
        logger.debug(f"随机延迟 {delay:.2f} 秒")
        time.sleep(delay)
    
    def smart_delay(self, min_seconds=2, max_seconds=8):
        """智能延迟，根据配置选择使用动态或随机延迟"""
        # 这里可以根据配置决定使用哪种延迟方式
        # 目前默认使用动态延迟
        self.dynamic_delay(min_seconds, max_seconds)
    
    def _is_driver_healthy(self):
        """检查driver是否健康"""
        try:
            if not self.driver:
                return False
            
            # 尝试获取当前URL来测试driver是否响应
            current_url = self.driver.current_url
            return True
            
        except Exception as e:
            logger.debug(f"Driver健康检查失败: {e}")
            return False
    
    def dynamic_delay(self, base_min=2, base_max=8):
        """动态延迟，根据下载次数调整延迟时间"""
        # 下载次数越多，延迟越长
        delay_factor = 1 + (self.download_count / 20)
        min_delay = base_min * delay_factor
        max_delay = base_max * delay_factor
        
        delay = random.uniform(min_delay, max_delay)
        logger.debug(f"动态延迟 {delay:.2f} 秒 (因子: {delay_factor:.2f})")
        time.sleep(delay)
    
    def simulate_real_mouse_movement(self, element=None):
        """模拟真实的鼠标移动轨迹"""
        try:
            if not self.driver:
                return
                
            # 生成轨迹点
            if element:
                # 移动到元素
                location = element.location
                start_x, start_y = 100, 100
                end_x, end_y = location['x'], location['y']
            else:
                # 随机移动
                start_x, start_y = 100, 100
                end_x, end_y = random.randint(200, 500), random.randint(200, 500)
            
            # 生成轨迹点
            points = []
            num_points = random.randint(8, 15)
            for t in [i/num_points for i in range(num_points + 1)]:
                x = start_x + (end_x - start_x) * t + random.randint(-15, 15)
                y = start_y + (end_y - start_y) * t + random.randint(-15, 15)
                points.append((x, y))
            
            actions = ActionChains(self.driver)
            
            # 移动到起始点
            actions.move_by_offset(points[0][0], points[0][1])
            
            # 沿着轨迹移动
            for i in range(1, len(points)):
                dx = points[i][0] - points[i-1][0]
                dy = points[i][1] - points[i-1][1]
                actions.move_by_offset(dx, dy)
                actions.pause(random.uniform(0.01, 0.08))  # 随机暂停
            
            actions.perform()
            
        except Exception as e:
            logger.debug(f"模拟鼠标移动时发生错误: {e}")
    
    def simulate_complex_browsing(self):
        """模拟复杂的浏览行为"""
        try:
            if not self.driver:
                return
            
            behaviors = [
                self._simulate_scrolling,
                self._simulate_random_clicks,
                self._simulate_tab_switching
            ]
            
            # 随机选择2-3个行为
            num_behaviors = random.randint(2, 3)
            selected_behaviors = random.sample(behaviors, num_behaviors)
            
            for behavior in selected_behaviors:
                behavior()
                time.sleep(random.uniform(0.5, 2))
                
        except Exception as e:
            logger.debug(f"模拟复杂浏览行为时发生错误: {e}")
    
    def _simulate_scrolling(self):
        """模拟页面滚动"""
        scroll_direction = random.choice(['up', 'down'])
        scroll_amount = random.randint(200, 800)
        
        if scroll_direction == 'down':
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        else:
            self.driver.execute_script(f"window.scrollBy(0, -{scroll_amount});")
    
    def _simulate_random_clicks(self):
        """模拟随机点击"""
        try:
            # 查找所有可点击元素
            clickable_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                "a, button, input[type='button'], input[type='submit']")
            
            if clickable_elements:
                # 随机选择一个可见元素
                visible_elements = [e for e in clickable_elements if e.is_displayed() and e.is_enabled()]
                if visible_elements:
                    element = random.choice(visible_elements)
                    # 模拟鼠标移动到元素并点击
                    self.simulate_real_mouse_movement(element)
                    element.click()
                    logger.debug("模拟随机点击")
                    
        except Exception:
            pass
    
    def _simulate_tab_switching(self):
        """模拟标签页切换"""
        try:
            # 打开新标签页
            self.driver.execute_script("window.open('about:blank');")
            time.sleep(0.5)
            
            # 切换回原标签页
            self.driver.switch_to.window(self.driver.window_handles[0])
            
        except Exception:
            pass
    
    def simulate_human_behavior(self):
        """模拟人类行为（兼容旧版本）"""
        try:
            if not self.driver:
                return
                
            # 使用新的复杂浏览行为模拟
            self.simulate_complex_browsing()
            
        except Exception as e:
            logger.debug(f"模拟人类行为时发生错误: {e}")
    
    def download_activity_records(self, stock_code, org_id=None, headless=True, max_retries=3, suffix='', allowed_keywords=None, max_pages=None):
        """
        下载投资者关系活动记录表
        
        参数:
            stock_code: 股票代码
            org_id: 组织ID，如果为None则自动获取
            headless: 是否使用无头模式
            max_retries: 最大重试次数
            suffix: 页面后缀，如research、periodicReports等
            allowed_keywords: 允许的关键词列表，None表示不过滤
            max_pages: 最大下载数，None表示下载所有页
            
        返回:
            bool: 下载是否成功
        """
        # 获取组织ID
        if not org_id:
            org_id = self.get_org_id(stock_code)
            if not org_id:
                logger.error(f"无法获取 {stock_code} 的组织ID")
                return False
        
        # 设置WebDriver
        if not self.setup_driver(headless):
            return False
        
        try:
            # 构造访问URL
            base_url = self.config_manager.get('base_url', 'https://www.cninfo.com.cn')
            target_suffix = suffix if suffix else 'research'  # 默认使用research后缀
            
            # 优化URL构造，避免使用hash fragment
            if target_suffix == 'research':
                url = f"{base_url}/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}"
            else:
                url = f"{base_url}/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#{target_suffix}"
            
            logger.info(f"访问URL: {url}")
            
            # 使用JavaScript处理页面加载 - 增强版本，包含超时重试机制
            max_page_load_attempts = 3
            page_load_success = False
            current_timeout = self.config_manager.get('timeout.page_load', 30)  # 默认值
            
            for attempt in range(max_page_load_attempts):
                # 动态调整超时时间
                if attempt == 0:
                    current_timeout = self.config_manager.get('timeout.page_load', 30)
                elif attempt == 1:
                    current_timeout = 45  # 第二次尝试增加超时时间
                else:
                    current_timeout = 60  # 第三次尝试使用更长超时时间
                
                try:
                    logger.info(f'页面加载尝试 {attempt + 1}/{max_page_load_attempts}')
                    
                    self.driver.set_page_load_timeout(current_timeout)
                    logger.info(f'设置页面加载超时时间: {current_timeout} 秒')
                    
                    # 首先访问基础页面
                    self.driver.get(url)
                    
                    # 等待页面基础加载
                    self.dynamic_delay(3, 6)
                    
                    # 如果是research页面，执行JavaScript导航
                    if target_suffix == 'research':
                        try:
                            self.driver.execute_script("""
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
                    self.dynamic_delay(8, 15)
                    
                    # 验证页面是否真正加载成功
                    try:
                        page_title = self.driver.title
                        if page_title and "巨潮资讯网" in page_title:
                            logger.info(f'页面加载成功，标题: {page_title}')
                            page_load_success = True
                            break
                        else:
                            logger.warning(f'页面标题异常: {page_title}')
                    except Exception as title_e:
                        logger.warning(f'获取页面标题失败: {title_e}')
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    logger.error(f'页面加载尝试 {attempt + 1} 失败: {e}')
                    
                    if "timeout" in error_msg:
                        logger.warning(f'检测到页面加载超时，当前超时设置: {current_timeout} 秒')
                        
                        # 在超时情况下，尝试停止页面加载并重新获取driver状态
                        try:
                            self.driver.execute_script("window.stop();")
                        except Exception:
                            pass
                        
                        # 如果不是最后一次尝试，等待后重试
                        if attempt < max_page_load_attempts - 1:
                            wait_time = min(5 + attempt * 3, 15)
                            logger.info(f'等待 {wait_time} 秒后重试...')
                            time.sleep(wait_time)
                            
                            # 尝试重启driver
                            if attempt == 1:  # 第二次失败时重启driver
                                logger.info('尝试重启WebDriver...')
                                if self.restart_driver(headless):
                                    logger.info('WebDriver重启成功')
                                else:
                                    logger.error('WebDriver重启失败')
                                    break
                    else:
                        # 非超时错误，直接抛出
                        raise e
            
            if not page_load_success:
                logger.error(f'页面加载失败，已尝试 {max_page_load_attempts} 次')
                raise Exception(f'页面加载失败，已尝试 {max_page_load_attempts} 次')
            
            logger.info(f'页面加载完成，后缀: {target_suffix}')
            
            # 获取股票名称并创建子目录
            stock_name = get_stock_name(stock_code, self.mapping_file)
            if not stock_name or stock_name.startswith('错误') or stock_name.startswith('网络'):
                stock_name = stock_code
            
            stock_dir = os.path.join(self.save_dir, self.clean_filename(stock_name))
            logger.info(f"保存目录: {stock_dir}", stock_dir=stock_dir, stock_code=stock_code)
            os.makedirs(stock_dir, exist_ok=True)
            
            # 分页下载
            return self._download_all_pages(
                driver=self.driver, 
                stock_code=stock_code, 
                stock_dir=stock_dir, 
                headless=headless, 
                max_retries=max_retries,
                allowed_keywords=allowed_keywords,
                max_pages=max_pages
            )
            
        except Exception as e:
            logger.error(f"页面加载异常: {e}")
            return False
        finally:
            self.close_driver()
    
    def _download_all_pages(self, driver, stock_code, stock_dir, headless=True, max_retries=3, allowed_keywords=None, max_pages=None):
        """下载所有页面的投资者关系活动记录表"""
        page_num = 1
        total_downloaded = 0
        
        while True:
            # 检查是否超过最大页数限制
            if max_pages and page_num > max_pages:
                logger.info(f"已达到最大页数限制 {max_pages}，停止处理")
                break
                
            logger.info(f"正在处理第{page_num}页...")
            
            # 检查driver健康状态
            if not self._is_driver_healthy():
                logger.warning("检测到driver异常，尝试重启...")
                if not self.restart_driver(headless):
                    logger.error("重启WebDriver失败")
                    break
                driver = self.driver
                
                # 重新访问页面
                try:
                    org_id = self.get_org_id(stock_code)
                    base_url = self.config_manager.get('base_url', 'https://www.cninfo.com.cn')
                    url = f"{base_url}/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#research"
                    driver.get(url)
                    self.dynamic_delay(5, 10)
                    
                    # 导航到当前页（如果不是第一页）
                    if page_num > 1:
                        self._navigate_to_page(driver, page_num)
                        
                except Exception as e:
                    logger.error(f"重新访问页面失败: {e}")
                    break
            
            # 模拟人类行为
            self.simulate_human_behavior()
            
            # 查找当前页面的下载链接
            detail_infos = self._find_download_links(driver, stock_code, stock_dir, allowed_keywords)
            
            if not detail_infos:
                logger.info(f"第{page_num}页未找到目标链接")
            else:
                logger.info(f"第{page_num}页发现{len(detail_infos)}个待下载链接")
                
                # 下载当前页面的文件
                downloaded_count = self._download_page_files(driver, detail_infos, headless, max_retries)
                total_downloaded += downloaded_count
            
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
                    base_url = self.config_manager.get('base_url', 'https://www.cninfo.com.cn')
                    url = f"{base_url}/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#research"
                    driver.get(url)
                    self.dynamic_delay(5, 10)
                    
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
            self.dynamic_delay(3, 8)  # 翻页后动态等待
        
        logger.info(f"下载完成！共下载 {total_downloaded} 个文件")
        return total_downloaded > 0
    
    def _navigate_to_page(self, driver, target_page):
        """导航到指定页面"""
        try:
            for _ in range(target_page - 1):
                if self._go_to_next_page(driver):
                    self.dynamic_delay(2, 5)
                else:
                    break
        except Exception as e:
            logger.error(f"导航到第{target_page}页失败: {e}")
    
    def _find_download_links(self, driver, stock_code, stock_dir, allowed_keywords=None):
        """查找当前页面的下载链接"""
        detail_infos = []
        
        try:
            # 等待页面元素加载
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, 'a'))
            )
            
            # 首先尝试从表格行中提取完整的文件名信息
            table_rows = driver.find_elements(By.CSS_SELECTOR, ".el-table__row, .table-row, tbody tr")
            
            # 构建链接文本到完整文件名的映射
            text_to_fullname_map = {}
            for row in table_rows:
                try:
                    row_text = row.text.strip()
                    if row_text:
                        # 提取链接文本（通常是标题部分）
                        link_text = row_text.split('\n')[0] if '\n' in row_text else row_text
                        text_to_fullname_map[link_text] = row_text
                except Exception:
                    continue
            
            all_links = driver.find_elements(By.TAG_NAME, 'a')
            
            for link in all_links:
                try:
                    text = link.text.strip()
                    href = link.get_attribute('href')
                    
                    # 1. 首先检查基本条件：必须是详情页链接
                    if not (href and '/new/disclosure/detail' in href
                            and f'stockCode={stock_code}' in href):
                        continue
                        
                    # 2. 使用完整的文件名进行关键词匹配（如果可用）
                    full_text = text_to_fullname_map.get(text, text)
                    
                    # 3. 然后检查关键词过滤
                    if allowed_keywords:
                        # 检查文件名是否包含允许的关键词
                        keyword_match = any(keyword in full_text for keyword in allowed_keywords)
                        if not keyword_match:
                            logger.debug(f"[跳过] 文件名不包含关键词: {full_text}")
                            continue
                    
                    # 4. 立即生成文件名并检查文件是否已存在
                    file_name = f"{self.clean_filename(full_text)}.pdf"
                    save_path = os.path.join(stock_dir, file_name)
                    
                    # 尽早检查文件存在性，避免不必要的处理
                    # 检查股票子目录和根目录（兼容旧版本文件位置）
                    file_exists = False
                    
                    # 首先检查股票子目录
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 10 * 1024:
                        file_exists = True
                    else:
                        # 然后检查根目录（兼容旧版本文件位置）
                        root_save_path = os.path.join(self.save_dir, file_name)
                        if os.path.exists(root_save_path) and os.path.getsize(root_save_path) > 10 * 1024:
                            file_exists = True
                    
                    if file_exists:
                        logger.info(f"[跳过] 文件已存在: {file_name}")
                        continue
                    
                    # 5. 只有需要下载的文件才构建详细信息
                    detail_infos.append({
                        'href': href,
                        'file_name': file_name,
                        'save_path': save_path
                    })
                except Exception as e:
                    logger.debug(f"处理链接时发生错误: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"查找下载链接时发生错误: {e}")
        
        return detail_infos
    
    def _download_page_files(self, driver, detail_infos, headless=True, max_retries=3):
        """下载当前页面的所有文件"""
        downloaded_count = 0
        
        for idx, info in enumerate(detail_infos, 1):
            detail_url = info['href']
            file_name = info['file_name']
            save_path = info['save_path']
            
            logger.info(f"正在下载 {idx}/{len(detail_infos)}: {file_name}")
            
            # 尝试下载文件，带重试机制
            success = False
            for retry in range(max_retries):
                try:
                    if retry > 0:
                        logger.info(f"第 {retry + 1} 次重试下载: {file_name}")
                        # 重试前重启浏览器
                        if not self.restart_driver(headless):
                            logger.error("重启WebDriver失败")
                            break
                        driver = self.driver
                    
                    # 清理可能存在的pdf.txt文件
                    self._cleanup_pdf_txt()
                    
                    # 访问详情页
                    driver.get(detail_url)
                    self.dynamic_delay(3, 8)
                    
                    # 模拟人类行为
                    self.simulate_human_behavior()
                    
                    # 查找并点击下载按钮
                    download_btn = WebDriverWait(driver, 30).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., '公告下载')]"))
                    )
                    
                    before_files = set(os.listdir(self.save_dir))
                    
                    # 模拟人类点击
                    actions = ActionChains(driver)
                    actions.move_to_element(download_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                    logger.info(f"已点击下载按钮，等待文件下载...")
                    
                    # 等待下载完成
                    download_timeout = self.config_manager.get('timeout.download', 30)
                    if self._wait_for_download(before_files, save_path, timeout=download_timeout):
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
                    self.dynamic_delay(5, 15)
            
            if not success:
                logger.error(f"下载失败（已重试{max_retries}次）: {file_name}")
            
            # 下载间隔
            self.dynamic_delay(2, 6)
        
        return downloaded_count
    
    def _wait_for_download(self, before_files, target_path, timeout=None):
        if timeout is None:
            timeout = self.config_manager.get('timeout.download', 30)
        """等待文件下载完成（优化版本：渐进式退避）"""
        start_time = time.time()
        check_interval = 0.5  # 开始时使用0.5秒间隔
        
        while time.time() - start_time < timeout:
            time.sleep(check_interval)
            # 渐进式增加检查间隔，最大2秒
            check_interval = min(check_interval * 1.2, 2.0)
            
            # 清理pdf.txt文件
            self._cleanup_pdf_txt()
            
            # 检查新文件
            try:
                after_files = set(os.listdir(self.save_dir))
                new_files = after_files - before_files
                
                for file in new_files:
                    file_path = os.path.join(self.save_dir, file)
                    
                    if file.lower().endswith('.pdf') and os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        
                        if file_size > 10 * 1024:  # 文件大于10KB
                            # 移动文件到目标位置
                            if file_path != target_path:
                                try:
                                    shutil.move(file_path, target_path)
                                except Exception:
                                    pass
                            return True
                        else:
                            # 删除过小的文件
                            try:
                                os.remove(file_path)
                            except Exception:
                                pass
                
                # 检查目标文件是否已存在且大小合适
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
            # 模拟人类行为
            self.simulate_human_behavior()
            
            # 方法1: 查找下一页按钮
            next_btn = driver.find_element(By.XPATH, "//button[contains(@class, 'el-pagination__next') and not(@disabled)]")
            if next_btn.is_enabled():
                actions = ActionChains(driver)
                actions.move_to_element(next_btn).pause(random.uniform(0.5, 1.5)).click().perform()
                self.dynamic_delay(3, 6)
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
                self.dynamic_delay(3, 6)
                return True
        except Exception:
            pass
        
        try:
            # 方法3: 查找快速翻页按钮
            quick_next = driver.find_element(By.CSS_SELECTOR, ".btn-quicknext")
            if quick_next.is_displayed() and quick_next.is_enabled():
                actions = ActionChains(driver)
                actions.move_to_element(quick_next).pause(random.uniform(0.5, 1.5)).click().perform()
                self.dynamic_delay(3, 6)
                return True
        except Exception:
            pass
        
        return False

def main():
    """主函数"""
    # 读取配置文件
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        sys.exit(1)
    
    stock_code = config.get('stock_code')
    save_dir = config.get('save_dir', 'downloads')
    headless = config.get('headless', True)
    max_retries = config.get('max_retries', 3)
    use_dynamic_delay = config.get('use_dynamic_delay', True)
    
    if not stock_code:
        logger.error("配置文件中未指定股票代码")
        sys.exit(1)
    
    logger.info(f"开始处理股票代码: {stock_code}")
    logger.info(f"配置参数: 最大重试次数={max_retries}, 动态延迟={use_dynamic_delay}")
    
    # 创建下载器
    downloader = CninfoDownloader(save_dir=save_dir)
    
    # 设置动态延迟标志
    if use_dynamic_delay:
        logger.info("启用动态延迟机制")
    
    # 处理多个页面配置
    pages = config.get('pages', [])
    total_success = False
    
    if pages:
        logger.info(f"发现 {len(pages)} 个页面配置，开始逐个处理")
        for page_config in pages:
            page_name = page_config.get('name', '未知页面')
            suffix = page_config.get('suffix', '')
            allowed_keywords = page_config.get('allowed_keywords')
            
            logger.info(f"开始处理页面: {page_name} (suffix: {suffix})")
            if allowed_keywords:
                logger.info(f"关键词过滤: {allowed_keywords}")
            
            success = downloader.download_activity_records(
                stock_code, 
                headless=headless, 
                max_retries=max_retries,
                suffix=suffix,
                allowed_keywords=allowed_keywords
            )
            total_success = total_success or success
            
            # 页面间延迟
            downloader.random_delay(3, 8)
    else:
        # 向后兼容：如果没有页面配置，使用默认行为
        logger.info("使用默认下载行为")
        total_success = downloader.download_activity_records(stock_code, headless=headless, max_retries=max_retries)
    
    if total_success:
        logger.info("所有下载任务完成")
    else:
        logger.error("部分或全部下载任务失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
