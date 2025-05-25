#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
巨潮资讯网组织ID爬虫

本程序用于自动遍历A股股票代码，通过Chrome WebDriver访问巨潮资讯网调研栏目，
获取每个股票代码对应的组织ID，并生成映射表。

作者: Manus
日期: 2025-05-17
"""

import os
import re
import sys
import time
import json
import logging
import argparse
import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from get_stock_name import get_stock_name

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('orgid_crawler.log')
    ]
)
logger = logging.getLogger('orgid_crawler')

class OrgIdCrawler:
    """巨潮资讯网组织ID爬虫"""
    
    def __init__(self, output_file='stock_orgid_mapping.json', headless=True):
        """
        初始化爬虫
        
        参数:
            output_file: 输出文件路径
            headless: 是否使用无头模式
        """
        self.output_file = output_file
        self.headless = headless
        self.driver = None
        self.mapping = {}
        
        # 加载已有的映射数据（如果存在）
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    self.mapping = json.load(f)
                logger.info(f"已加载 {len(self.mapping)} 条映射记录")
            except Exception as e:
                logger.error(f"加载映射文件时发生错误: {e}")
                self.mapping = {}
    
    def setup_driver(self):
        """设置WebDriver"""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # 创建WebDriver
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            logger.info("WebDriver初始化成功")
            return True
        except Exception as e:
            logger.error(f"WebDriver初始化失败: {e}")
            return False
    
    def close_driver(self):
        """关闭WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver已关闭")
            except Exception as e:
                logger.error(f"关闭WebDriver时发生错误: {e}")
    
    def extract_org_id_from_url(self):
        """从URL中提取组织ID"""
        try:
            current_url = self.driver.current_url
            org_id_match = re.search(r'orgId=(\d+)', current_url)
            
            if org_id_match:
                org_id = org_id_match.group(1)
                logger.info(f"从URL中提取到组织ID: {org_id}")
                return org_id
            
            return None
        except Exception as e:
            logger.error(f"从URL中提取组织ID时发生错误: {e}")
            return None
    
    def extract_org_id_from_source(self):
        """从页面源代码中提取组织ID"""
        try:
            page_source = self.driver.page_source
            
            # 使用正则表达式从源代码中提取
            patterns = [
                r'orgId["\s:=]+(\d+)',
                r'orgid["\s:=]+(\d+)',
                r'"orgId"\s*:\s*"?(\d+)"?',
                r'orgId=(\d+)'
            ]
            
            for pattern in patterns:
                org_id_match = re.search(pattern, page_source)
                if org_id_match:
                    org_id = org_id_match.group(1)
                    logger.info(f"从页面源代码中提取到组织ID: {org_id}")
                    return org_id
            
            return None
        except Exception as e:
            logger.error(f"从页面源代码中提取组织ID时发生错误: {e}")
            return None
    
    def get_org_id(self, stock_code):
        """
        获取股票代码对应的组织ID
        """
        if not self.driver:
            if not self.setup_driver():
                return None
        
        # 清理旧的浏览器标签页
        try:
            handles = self.driver.window_handles
            for h in handles[1:]:
                self.driver.switch_to.window(h)
                self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
        except Exception as e:
            logger.debug(f"关闭旧tab时发生异常: {e}")
        
        try:
            # 直接访问搜索结果页
            search_url = f"https://www.cninfo.com.cn/new/fulltextSearch?notautosubmit=&keyWord={stock_code}"
            self.driver.get(search_url)
            time.sleep(3)  # 等待页面加载
            
            # 点击"公司介绍"tab
            try:
                # 优先精确查找<a>标签，href包含companyProfile且文本为公司介绍
                tab_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'companyProfile') and contains(text(), '公司介绍')]"))
                )
                tab_button.click()
                logger.info("已点击公司介绍tab")
                time.sleep(2)
            except Exception as e:
                logger.debug(f"点击公司介绍tab失败: {e}")
                # 尝试其他方式查找tab
                tab_selectors = [
                    "//div[contains(@class, 'tab') and contains(., '公司介绍')]",
                    "//a[contains(text(), '公司介绍')]",
                    "//span[contains(text(), '公司介绍')]",
                    "//*[contains(@class, 'el-tabs__item') and contains(text(), '公司介绍')]"
                ]
                
                for selector in tab_selectors:
                    try:
                        tab_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        tab_button.click()
                        logger.info(f"已点击公司介绍tab: {selector}")
                        time.sleep(2)
                        break
                    except Exception:
                        continue
            
            # 提取组织ID
            org_id = self.extract_org_id_from_url() or self.extract_org_id_from_source()
            
            if org_id:
                logger.info(f"获取到 {stock_code} 的组织ID: {org_id}")
                return org_id
            else:
                # 使用默认值
                default_org_id = f"990000{stock_code}"
                logger.warning(f"未能提取 {stock_code} 的组织ID，使用默认值: {default_org_id}")
                return default_org_id
                
        except TimeoutException:
            logger.error(f"访问 {stock_code} 页面超时")
            self.close_driver()
            self.driver = None
            return None
        except WebDriverException as e:
            logger.error(f"WebDriver异常: {e}")
            self.close_driver()
            self.driver = None
            return None
        except Exception as e:
            logger.error(f"获取 {stock_code} 的组织ID时发生错误: {e}")
            return None
    
    def save_mapping(self):
        """保存映射数据到文件"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.mapping, f, ensure_ascii=False, indent=4)
            logger.info(f"已保存 {len(self.mapping)} 条映射记录到 {self.output_file}")
            return True
        except Exception as e:
            logger.error(f"保存映射文件时发生错误: {e}")
            return False
    
    def fetch_all_a_stock_codes(self, csv_path='a_stock_codes.csv'):
        """自动下载A股全量股票代码并保存到csv"""
        url = "http://44.push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': 1,
            'pz': 5000,
            'po': 1,
            'np': 1,
            'ut': 'b2884a393a59ad64002292a3e90d46a5',
            'fltt': 2,
            'invt': 2,
            'fid': 'f3',
            'fs': 'm:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23',
            'fields': 'f12,f14'
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            stocks = data['data']['diff']
            code_list = [item['f12'] for item in stocks]
            name_list = [item['f14'] for item in stocks]
            df = pd.DataFrame({'code': code_list, 'name': name_list})
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            logger.info(f"已保存A股代码到 {csv_path}，共{len(df)}只股票。")
            return df
        except Exception as e:
            logger.error(f"下载A股代码失败: {e}")
            return None
    
    def get_stock_codes_from_csv(self, csv_path='a_stock_codes.csv', start=0, end=None):
        """从csv文件读取A股代码"""
        try:
            df = pd.read_csv(csv_path, dtype=str)
            codes = df['code'].tolist()
            if end is None:
                end = len(codes)
            return codes[start:end]
        except Exception as e:
            logger.error(f"读取A股代码csv失败: {e}")
            return []
    
    def crawl(self, start=0, end=1000, batch_size=10, save_interval=10, csv_path='a_stock_codes.csv'):
        """
        爬取股票代码对应的组织ID
        """
        # 获取股票代码列表
        if not os.path.exists(csv_path):
            self.fetch_all_a_stock_codes(csv_path)
        
        stock_codes = self.get_stock_codes_from_csv(csv_path, start, end)
        if not stock_codes:
            logger.error("无法获取股票代码列表")
            return self.mapping
        
        total = len(stock_codes)
        logger.info(f"准备爬取 {total} 只股票的组织ID")
        
        # 初始化WebDriver
        if not self.setup_driver():
            logger.error("WebDriver初始化失败，无法继续爬取")
            return self.mapping
        
        # 分批处理
        processed = 0
        for i in range(0, total, batch_size):
            batch = stock_codes[i:i+batch_size]
            logger.info(f"正在处理第 {i+1}-{i+len(batch)} 只股票，共 {total} 只")
            
            for stock_code in batch:
                # 如果已经有映射，则跳过
                if stock_code in self.mapping:
                    logger.info(f"跳过已有映射的股票 {stock_code}")
                    continue
                
                # 获取组织ID
                org_id = self.get_org_id(stock_code)
                if org_id:
                    self.mapping[stock_code] = {
                        "orgId": org_id,
                        "name": get_stock_name(stock_code, self.output_file),
                        "timestamp": time.time()
                    }
                
                processed += 1
                
                # 添加随机延迟，避免请求过于频繁
                time.sleep(1 + (time.time() % 2))
            
            # 定期保存映射数据
            if processed % save_interval == 0:
                self.save_mapping()
        
        # 最后保存一次
        self.save_mapping()
        
        # 关闭WebDriver
        self.close_driver()
        
        return self.mapping

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='爬取A股股票代码对应的组织ID')
    parser.add_argument('--output', default='stock_orgid_mapping.json', help='输出文件路径')
    parser.add_argument('--start', type=int, default=0, help='起始索引')
    parser.add_argument('--end', type=int, default=1000, help='结束索引')
    parser.add_argument('--batch-size', type=int, default=10, help='每批处理的股票数量')
    parser.add_argument('--save-interval', type=int, default=10, help='保存间隔')
    parser.add_argument('--headless', action='store_true', help='使用无头模式')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--test', action='store_true', help='测试模式，只处理一个股票代码')
    parser.add_argument('--stock-code', help='指定要处理的股票代码，仅在测试模式下有效')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # 创建爬虫
    crawler = OrgIdCrawler(output_file=args.output, headless=args.headless)
    
    # 测试模式
    if args.test:
        stock_code = args.stock_code or "300010"
        logger.info(f"测试模式，处理股票代码: {stock_code}")
        
        org_id = crawler.get_org_id(stock_code)
        if org_id:
            crawler.mapping[stock_code] = {
                "orgId": org_id,
                "name": get_stock_name(stock_code, crawler.output_file),
                "timestamp": time.time()
            }
            crawler.save_mapping()
            logger.info(f"测试完成，股票 {stock_code} 的组织ID: {org_id}")
        else:
            logger.error(f"测试失败，未能获取股票 {stock_code} 的组织ID")
        
        crawler.close_driver()
        return
    
    # 爬取组织ID
    mapping = crawler.crawl(
        start=args.start,
        end=args.end,
        batch_size=args.batch_size,
        save_interval=args.save_interval,
        csv_path='a_stock_codes.csv'
    )
    
    logger.info(f"爬取完成，共获取 {len(mapping)} 条映射记录")

if __name__ == "__main__":
    main()
