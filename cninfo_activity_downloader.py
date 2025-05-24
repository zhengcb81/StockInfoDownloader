#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
巨潮资讯网投资者关系活动记录表下载器

本程序用于自动下载巨潮资讯网上的投资者关系活动记录表PDF文件。
支持通过股票代码查询，自动从映射表中查找组织ID，构造正确的API请求参数，
下载并保存PDF格式的投资者关系活动记录表。

作者: Manus
日期: 2025-05-17
"""

import os
import re
import sys
import json
import time
import logging
import datetime
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
from orgid_utils import get_org_id_by_code  #, get_stock_name_by_code  # 新增导入
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import shutil
from get_stock_name import get_stock_name

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cninfo_downloader.log')
    ]
)
logger = logging.getLogger('cninfo_downloader')

class CninfoDownloader:
    """巨潮资讯网投资者关系活动记录表下载器"""
    
    def __init__(self, save_dir='downloads', mapping_file='stock_orgid_mapping.json'):
        """
        初始化下载器
        
        参数:
            save_dir: 保存文件的目录
            mapping_file: 股票代码与组织ID的映射文件
        """
        self.base_url = "https://www.cninfo.com.cn"
        self.query_url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
        self.save_dir = save_dir
        self.mapping_file = mapping_file
        self.mapping = {}
        self.session = requests.Session()
        
        # 设置请求头
        self.headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://www.cninfo.com.cn',
            'Referer': 'https://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        # 创建保存目录
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # 加载映射文件
        self.load_mapping()
        
        # 预设的组织ID映射表（用于映射文件不存在或查找失败时的备用）
        self.org_id_cache = {
            "000001": "9900000001",  # 平安银行
            "000002": "9900000002",  # 万科A
            "000063": "9900000063",  # 中兴通讯
            "000333": "9900000333",  # 美的集团
            "000651": "9900000651",  # 格力电器
            "000858": "9900000858",  # 五粮液
            "002714": "9900008369",  # 牧原股份
            "300010": "9900008267",  # 豆神教育
            "300059": "9900008316",  # 东方财富
            "300750": "9900009007",  # 宁德时代
            "600000": "9900010000",  # 浦发银行
            "600009": "9900010009",  # 上海机场
            "600016": "9900010016",  # 民生银行
            "600036": "9900010036",  # 招商银行
            "600276": "9900010276",  # 恒瑞医药
            "600519": "9900010519",  # 贵州茅台
            "600887": "9900010887",  # 伊利股份
            "601318": "9900011318",  # 中国平安
            "601398": "9900011398",  # 工商银行
            "603288": "9900013288"   # 海天味业
        }
    
    def load_mapping(self):
        """加载股票代码与组织ID的映射文件"""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    self.mapping = json.load(f)
                logger.info(f"已加载 {len(self.mapping)} 条映射记录")
            except Exception as e:
                logger.error(f"加载映射文件时发生错误: {e}")
                self.mapping = {}
        else:
            logger.warning(f"映射文件 {self.mapping_file} 不存在")
    
    def get_org_id(self, stock_code, force_run=False):
        """
        获取股票代码对应的组织ID，统一调用orgid_utils.get_org_id_by_code
        参数：
            stock_code: 股票代码
            force_run: 是否强制重新爬取org id
        返回：
            str: 组织ID，如果获取失败则返回None
        """
        return get_org_id_by_code(stock_code, force_run=force_run, mapping_file=self.mapping_file)
    
    def query_announcements(self, stock_code, org_id, page=1, page_size=30, start_date=None, end_date=None):
        """
        查询公告
        
        参数:
            stock_code: 股票代码
            org_id: 组织ID
            page: 页码
            page_size: 每页条数
            start_date: 开始日期，格式为yyyy-MM-dd
            end_date: 结束日期，格式为yyyy-MM-dd
            
        返回:
            dict: 查询结果
        """
        # 设置日期范围
        if not start_date:
            # 默认查询最近6个月的公告
            start_date = (datetime.datetime.now() - datetime.timedelta(days=180)).strftime('%Y-%m-%d')
        
        if not end_date:
            end_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 构造请求参数
        data = {
            'pageNum': page,
            'pageSize': page_size,
            'column': 'szse' if stock_code.startswith(('000', '002', '300', '301')) else 'sse',
            'tabName': 'fulltext',
            'plate': '',
            'stock': f"{stock_code},{org_id}",
            'searchkey': '',
            'secid': '',
            'category': '',
            'trade': '',
            'seDate': f"{start_date}~{end_date}",
            'sortName': '',
            'sortType': '',
            'isHLtitle': 'true'
        }
        
        # 发送请求
        try:
            response = self.session.post(self.query_url, headers=self.headers, data=data)
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            logger.debug(f"查询结果: {result}")
            
            if 'announcements' in result and result['announcements']:
                logger.info(f"查询到 {len(result['announcements'])} 条公告")
                return result
            else:
                logger.warning(f"未查询到 {stock_code} 的公告")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"查询公告时发生错误: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"解析响应时发生错误: {e}")
            return None
    
    def filter_activity_records(self, announcements):
        """
        过滤投资者关系活动记录表
        
        参数:
            announcements: 公告列表
            
        返回:
            list: 投资者关系活动记录表列表
        """
        if not announcements:
            return []
        
        # 关键词列表
        keywords = [
            '投资者关系活动记录表',
            '投资者关系活动',
            '调研活动',
            '投资者关系管理'
        ]
        
        # 过滤公告
        activity_records = []
        for announcement in announcements:
            title = announcement.get('announcementTitle', '')
            
            # 检查标题是否包含关键词
            if any(keyword in title for keyword in keywords):
                logger.info(f"找到投资者关系活动记录表: {title}")
                activity_records.append(announcement)
        
        return activity_records
    
    def download_pdf(self, announcement, stock_code):
        """
        下载PDF文件
        
        参数:
            announcement: 公告信息
            stock_code: 股票代码
            
        返回:
            str: 保存的文件路径，如果下载失败则返回None
        """
        # 提取PDF下载链接
        adjunct_url = announcement.get('adjunctUrl')
        if not adjunct_url:
            logger.error(f"未找到PDF下载链接")
            return None
        
        # 构造完整的下载链接
        download_url = f"{self.base_url}/new/announcement/download?bulletinId={announcement.get('announcementId')}&announceTime={quote(announcement.get('announcementTime', ''))}"
        
        # 提取文件名
        file_name = os.path.basename(adjunct_url)
        if not file_name.endswith('.pdf'):
            file_name = f"{file_name}.pdf"
        
        # 创建股票代码目录
        stock_dir = os.path.join(self.save_dir, stock_code)
        if not os.path.exists(stock_dir):
            os.makedirs(stock_dir)
        
        # 保存路径
        save_path = os.path.join(stock_dir, file_name)
        
        # 下载文件
        try:
            response = self.session.get(download_url, headers=self.headers, stream=True)
            response.raise_for_status()
            
            # 检查是否是PDF文件
            content_type = response.headers.get('Content-Type', '')
            if 'application/pdf' not in content_type and not file_name.endswith('.pdf'):
                logger.warning(f"下载的文件可能不是PDF文件: {content_type}")
            
            # 保存文件
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"已下载: {save_path}")
            return save_path
        except requests.exceptions.RequestException as e:
            logger.error(f"下载PDF文件时发生错误: {e}")
            return None
    
    def download_activity_records(self, stock_code, org_id=None, max_pages=10, start_date=None, end_date=None):
        """
        下载投资者关系活动记录表
        
        参数:
            stock_code: 股票代码
            org_id: 组织ID，如果为None则自动获取
            max_pages: 最大查询页数
            start_date: 开始日期，格式为yyyy-MM-dd
            end_date: 结束日期，格式为yyyy-MM-dd
            
        返回:
            list: 下载的文件路径列表
        """
        # 获取组织ID
        if not org_id:
            org_id = self.get_org_id(stock_code)
            if not org_id:
                logger.error(f"无法获取 {stock_code} 的组织ID")
                return []
        
        # 下载的文件路径列表
        downloaded_files = []
        
        # 分页查询
        for page in range(1, max_pages + 1):
            logger.info(f"正在查询第 {page} 页")
            
            # 查询公告
            result = self.query_announcements(
                stock_code=stock_code,
                org_id=org_id,
                page=page,
                start_date=start_date,
                end_date=end_date
            )
            
            if not result:
                logger.warning(f"第 {page} 页查询失败或无数据")
                break
            
            # 提取公告列表
            announcements = result.get('announcements', [])
            if not announcements:
                logger.info(f"第 {page} 页无公告数据")
                break
            
            # 过滤投资者关系活动记录表
            activity_records = self.filter_activity_records(announcements)
            if not activity_records:
                logger.info(f"第 {page} 页无投资者关系活动记录表")
                continue
            
            # 下载PDF文件
            for record in activity_records:
                file_path = self.download_pdf(record, stock_code)
                if file_path:
                    downloaded_files.append(file_path)
            
            # 检查是否有下一页
            has_more = result.get('hasMore', False)
            if not has_more:
                logger.info("已到达最后一页")
                break
            
            # 添加延迟，避免请求过于频繁
            time.sleep(1 + (time.time() % 2))
        
        return downloaded_files

def clean_filename(s):
    # 去除文件名中的非法字符
    return re.sub(r'[\\/:*?"<>|]', '_', s)

def download_pdfs_by_selenium(stock_code, org_id, save_dir='downloads', headless=False):
    url = f"https://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#research"
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    prefs = {
        "download.default_directory": os.path.abspath(save_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    driver = uc.Chrome(options=chrome_options)
    driver.set_page_load_timeout(120)
    try:
        driver.get(url)
        time.sleep(5)
        logger.info('页面加载完成')
    except Exception as e:
        logger.error(f"页面加载异常: {e}")
        driver.quit()
        return

    stock_name = get_stock_name(stock_code, mapping_file='stock_orgid_mapping.json')
    if not stock_name:
        stock_name = stock_code
    stock_dir = os.path.join(save_dir, clean_filename(stock_name))
    logger.info(f"当前子文件夹名: {stock_dir}")
    os.makedirs(stock_dir, exist_ok=True)

    logger.info(f"开始采集所有调研页内容")
    page_num = 1
    while True:
        logger.info(f"采集第{page_num}页...")
        all_a = driver.find_elements(By.TAG_NAME, 'a')
        detail_infos = []
        for a in all_a:
            text = a.text.strip()
            href = a.get_attribute('href')
            if (
                text and '投资者关系活动记录表' in text
                and href and '/new/disclosure/detail' in href
                and f'stockCode={stock_code}' in href
            ):
                file_name = f"{clean_filename(text)}.pdf"
                save_path = os.path.join(stock_dir, file_name)
                if os.path.exists(save_path) and os.path.getsize(save_path) > 10 * 1024:
                    logger.info(f"[跳过] 文件已存在: {file_name}")
                    continue
                detail_infos.append({'a': a, 'href': href, 'file_name': file_name, 'save_path': save_path})

        logger.info(f"共发现{len(detail_infos)}个待下载详情页链接。")
        if not detail_infos:
            logger.info('未找到目标详情页链接。')

        for idx, info in enumerate(detail_infos, 1):
            detail_url = info['href']
            file_name = info['file_name']
            save_path = info['save_path']
            logger.info(f"正在处理{idx}/{len(detail_infos)}: {detail_url}")
            try:
                for f in os.listdir(save_dir):
                    if f.lower() == 'pdf.txt':
                        try:
                            os.remove(os.path.join(save_dir, f))
                            logger.info(f"[清理] 已删除pdf.txt文件: {f}")
                        except Exception:
                            pass
                driver.get(detail_url)
                try:
                    download_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., '公告下载')]") )
                    )
                    before_files = set(os.listdir(save_dir))
                    driver.execute_script("arguments[0].click();", download_btn)
                    logger.info(f"已点击'公告下载'按钮，等待下载...")
                    download_wait_time = 0
                    max_wait = 180
                    while download_wait_time < max_wait:
                        time.sleep(1)
                        for f in os.listdir(save_dir):
                            if f.lower() == 'pdf.txt':
                                try:
                                    os.remove(os.path.join(save_dir, f))
                                    logger.info(f"[清理] 已删除pdf.txt文件: {f}")
                                except Exception:
                                    pass
                        after_files = set(os.listdir(save_dir))
                        new_files = after_files - before_files
                        for f in new_files:
                            file_path = os.path.join(save_dir, f)
                            if f.lower().endswith('.pdf'):
                                if os.path.exists(file_path) and os.path.getsize(file_path) > 10 * 1024:
                                    if file_path != save_path:
                                        try:
                                            shutil.move(file_path, save_path)
                                            logger.info(f"PDF已下载并移动到: {save_path}")
                                        except Exception:
                                            logger.info(f"PDF已下载: {file_path}")
                                    else:
                                        logger.info(f"PDF已下载: {file_path}")
                                else:
                                    logger.warning(f"文件过小或异常，已删除: {f}")
                                    try:
                                        os.remove(file_path)
                                    except Exception:
                                        pass
                        if os.path.exists(save_path) and os.path.getsize(save_path) > 10 * 1024:
                            break
                        download_wait_time += 1
                    else:
                        logger.warning(f"等待下载超时: {detail_url}")
                except Exception as e:
                    logger.warning(f"未找到或无法点击'公告下载'按钮: {detail_url}，原因: {e}")
            except Exception as e:
                logger.error(f"处理详情页失败: {detail_url}，原因: {e}")

        # 翻页逻辑
        next_page_clicked = False
        try:
            next_btn = driver.find_element(By.XPATH, "//button[contains(@class, 'el-pagination__next') and not(@disabled)]")
            if next_btn.is_enabled():
                logger.info(f"点击下一页按钮，准备采集下一页...")
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(3)
                page_num += 1
                next_page_clicked = True
        except Exception:
            pass
        if not next_page_clicked:
            try:
                arrow_icon = driver.find_element(By.CSS_SELECTOR, "i.el-icon.el-icon-arrow-right")
                parent_btn = arrow_icon.find_element(By.XPATH, "./ancestor::button[not(@disabled)]")
                if parent_btn.is_enabled():
                    logger.info(f"点击右箭头下一页按钮，准备采集下一页...")
                    driver.execute_script("arguments[0].click();", parent_btn)
                    time.sleep(3)
                    page_num += 1
                    next_page_clicked = True
            except Exception:
                pass
        if not next_page_clicked:
            try:
                quick_next = driver.find_element(By.CSS_SELECTOR, ".btn-quicknext")
                if quick_next.is_displayed() and quick_next.is_enabled():
                    logger.info(f"点击快速翻页按钮...")
                    driver.execute_script("arguments[0].click();", quick_next)
                    time.sleep(3)
                    page_num += 1
                    next_page_clicked = True
            except Exception:
                pass
        if not next_page_clicked:
            logger.info(f"未找到可用的下一页或快速翻页按钮，采集结束。")
            break
    driver.quit()
    logger.info("全部下载完成！")

def main():
    # 读取配置文件
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    stock_code = config.get('stock_code')
    save_dir = config.get('save_dir', 'downloads')
    headless = config.get('headless', True)

    logger.info(f"开始处理股票代码: {stock_code}")
    org_id = get_org_id_by_code(stock_code)
    if not org_id:
        logger.error(f"未能获取{stock_code}的org id，无法下载。")
        sys.exit(1)
    logger.info(f"已获取org id: {org_id}")

    # 先用requests方式批量下载
    downloader = CninfoDownloader(save_dir=save_dir)
    files = downloader.download_activity_records(stock_code, org_id=org_id)
    logger.info(f"requests方式共下载{len(files)}个PDF文件。")

    # 再用selenium方式补充下载
    download_pdfs_by_selenium(stock_code, org_id, save_dir, headless=headless)
    logger.info("selenium方式补充下载完成。")

if __name__ == "__main__":
    main()
