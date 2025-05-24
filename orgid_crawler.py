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
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
#from orgid_utils import get_stock_name_by_code  # 新增导入
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
        self.base_url = "http://www.cninfo.com.cn"
        self.research_url = "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search&keywords=#/3"
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
    
    def inject_monitoring_scripts(self):
        """注入监控脚本，用于捕获XHR请求和DOM变化"""
        try:
            # 注入XHR监听脚本
            xhr_script = """
            // 监听XHR请求，捕获调研栏目的API请求参数
            window.xhrRequests = [];
            const originalXHROpen = XMLHttpRequest.prototype.open;
            const originalXHRSend = XMLHttpRequest.prototype.send;

            // 重写open方法
            XMLHttpRequest.prototype.open = function(method, url) {
                this._method = method;
                this._url = url;
                return originalXHROpen.apply(this, arguments);
            };

            // 重写send方法
            XMLHttpRequest.prototype.send = function(body) {
                const xhr = this;
                
                // 存储请求信息
                const requestInfo = {
                    method: xhr._method,
                    url: xhr._url,
                    body: body ? body.toString() : null,
                    timestamp: new Date().toISOString()
                };
                
                window.xhrRequests.push(requestInfo);
                
                // 添加响应监听
                this.addEventListener('load', function() {
                    try {
                        const responseData = xhr.responseText;
                        const responseInfo = {
                            url: xhr._url,
                            status: xhr.status,
                            response: responseData
                        };
                        
                        // 将响应信息添加到请求信息中
                        for (let i = 0; i < window.xhrRequests.length; i++) {
                            if (window.xhrRequests[i].url === xhr._url) {
                                window.xhrRequests[i].response = responseInfo;
                                break;
                            }
                        }
                    } catch (e) {
                        console.error('Error logging XHR response:', e);
                    }
                });
                
                return originalXHRSend.apply(this, arguments);
            };
            
            // 监听fetch请求
            window.fetchRequests = [];
            const originalFetch = window.fetch;
            window.fetch = async function(...args) {
                const url = args[0];
                const options = args[1] || {};
                
                const requestInfo = {
                    url: typeof url === 'string' ? url : url.url,
                    method: options.method || 'GET',
                    headers: options.headers,
                    body: options.body,
                    timestamp: new Date().toISOString()
                };
                
                window.fetchRequests.push(requestInfo);
                
                try {
                    const response = await originalFetch.apply(this, args);
                    const clone = response.clone();
                    
                    clone.text().then(text => {
                        try {
                            const responseInfo = {
                                url: requestInfo.url,
                                status: clone.status,
                                response: text
                            };
                            
                            // 将响应信息添加到请求信息中
                            for (let i = 0; i < window.fetchRequests.length; i++) {
                                if (window.fetchRequests[i].url === requestInfo.url) {
                                    window.fetchRequests[i].response = responseInfo;
                                    break;
                                }
                            }
                        } catch (e) {
                            console.error('Error logging fetch response:', e);
                        }
                    }).catch(e => console.error('Error reading fetch response:', e));
                    
                    return response;
                } catch (error) {
                    console.error('Fetch error:', error);
                    throw error;
                }
            };
            """
            
            # 注入DOM监控脚本
            dom_script = """
            // 存储自动完成下拉框信息
            window.autocompleteItems = [];
            
            // 监控DOM变化，捕获自动完成下拉框
            const observer = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                        // 检查是否添加了自动完成下拉框
                        const dropdown = document.querySelector('.el-autocomplete-suggestion');
                        if (dropdown && dropdown.offsetParent !== null) { // 检查是否可见
                            // 查找下拉项
                            const items = dropdown.querySelectorAll('li');
                            
                            if (items.length > 0) {
                                window.autocompleteItems = [];
                                
                                Array.from(items).forEach((item) => {
                                    const itemInfo = {
                                        text: item.textContent,
                                        html: item.innerHTML,
                                        attributes: {}
                                    };
                                    
                                    // 收集所有属性
                                    for (let attr of item.attributes) {
                                        itemInfo.attributes[attr.name] = attr.value;
                                    }
                                    
                                    window.autocompleteItems.push(itemInfo);
                                });
                            }
                        }
                    }
                }
            });
            
            // 开始观察文档变化
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
            """
            
            # 执行脚本
            self.driver.execute_script(xhr_script)
            self.driver.execute_script(dom_script)
            logger.info("监控脚本注入成功")
            return True
        except Exception as e:
            logger.error(f"注入监控脚本时发生错误: {e}")
            return False
    
    def extract_org_id_from_xhr(self):
        """从XHR请求中提取组织ID"""
        try:
            # 获取XHR请求列表
            xhr_requests = self.driver.execute_script("return window.xhrRequests;")
            
            if not xhr_requests:
                logger.warning("未捕获到XHR请求")
                return None
            
            # 查找包含组织ID的请求
            for request in xhr_requests:
                url = request.get('url', '')
                body = request.get('body', '')
                response = request.get('response', {}).get('response', '')
                
                # 从请求体中提取组织ID
                if body and isinstance(body, str):
                    # 检查是否是查询请求
                    if 'query' in url.lower() and body.find('orgId') > -1:
                        org_id_match = re.search(r'orgId=(\d+)', body)
                        if org_id_match:
                            org_id = org_id_match.group(1)
                            logger.info(f"从XHR请求体中提取到组织ID: {org_id}")
                            return org_id
                
                # 从响应中提取组织ID
                if response and isinstance(response, str):
                    # 尝试解析JSON响应
                    try:
                        if response.startswith('{') and response.endswith('}'):
                            json_response = json.loads(response)
                            
                            # 检查是否包含组织ID
                            if 'orgId' in response:
                                # 递归查找orgId字段
                                def find_org_id(obj):
                                    if isinstance(obj, dict):
                                        if 'orgId' in obj:
                                            return obj['orgId']
                                        for key, value in obj.items():
                                            result = find_org_id(value)
                                            if result:
                                                return result
                                    elif isinstance(obj, list):
                                        for item in obj:
                                            result = find_org_id(item)
                                            if result:
                                                return result
                                    return None
                                
                                org_id = find_org_id(json_response)
                                if org_id:
                                    logger.info(f"从XHR响应中提取到组织ID: {org_id}")
                                    return org_id
                    except:
                        pass
                    
                    # 使用正则表达式从响应中提取
                    org_id_match = re.search(r'"orgId"\s*:\s*"?(\d+)"?', response)
                    if org_id_match:
                        org_id = org_id_match.group(1)
                        logger.info(f"从XHR响应中提取到组织ID: {org_id}")
                        return org_id
            
            logger.warning("未从XHR请求中找到组织ID")
            return None
        except Exception as e:
            logger.error(f"从XHR请求中提取组织ID时发生错误: {e}")
            return None
    
    def extract_org_id_from_autocomplete(self):
        """从自动完成下拉框中提取组织ID"""
        try:
            # 获取自动完成下拉项
            autocomplete_items = self.driver.execute_script("return window.autocompleteItems;")
            
            if not autocomplete_items:
                logger.warning("未捕获到自动完成下拉项")
                return None
            
            # 查找包含组织ID的下拉项
            for item in autocomplete_items:
                html = item.get('html', '')
                text = item.get('text', '')
                attributes = item.get('attributes', {})
                
                # 从属性中提取组织ID
                for attr_name, attr_value in attributes.items():
                    if 'orgid' in attr_name.lower() and attr_value:
                        logger.info(f"从自动完成下拉项属性中提取到组织ID: {attr_value}")
                        return attr_value
                
                # 从HTML中提取组织ID
                org_id_match = re.search(r'data-orgid="?(\d+)"?', html) or re.search(r'orgId=(\d+)', html)
                if org_id_match:
                    org_id = org_id_match.group(1)
                    logger.info(f"从自动完成下拉项HTML中提取到组织ID: {org_id}")
                    return org_id
            
            logger.warning("未从自动完成下拉项中找到组织ID")
            return None
        except Exception as e:
            logger.error(f"从自动完成下拉项中提取组织ID时发生错误: {e}")
            return None
    
    def extract_org_id_from_url(self):
        """从URL中提取组织ID"""
        try:
            current_url = self.driver.current_url
            org_id_match = re.search(r'orgId=(\d+)', current_url)
            
            if org_id_match:
                org_id = org_id_match.group(1)
                logger.info(f"从URL中提取到组织ID: {org_id}")
                return org_id
            
            logger.warning("未从URL中找到组织ID")
            return None
        except Exception as e:
            logger.error(f"从URL中提取组织ID时发生错误: {e}")
            return None
    
    def extract_org_id_from_dom(self):
        """从DOM结构中提取组织ID"""
        try:
            # 尝试从表格行中提取
            script = """
            // 查找可能包含组织ID的元素
            const elements = document.querySelectorAll('*');
            let orgIdElement = null;
            
            for (const el of elements) {
                // 检查元素属性
                for (const attr of el.attributes) {
                    if ((attr.name.includes('orgid') || attr.name.includes('orgId')) && attr.value) {
                        orgIdElement = {
                            tagName: el.tagName,
                            attribute: attr.name,
                            value: attr.value
                        };
                        break;
                    }
                    
                    if (attr.value.includes('orgId=')) {
                        const match = attr.value.match(/orgId=(\\d+)/);
                        if (match) {
                            orgIdElement = {
                                tagName: el.tagName,
                                attribute: attr.name,
                                value: match[1]
                            };
                            break;
                        }
                    }
                }
                
                if (orgIdElement) break;
                
                // 检查元素内容
                if (el.textContent && el.textContent.includes('orgId=')) {
                    const match = el.textContent.match(/orgId=(\\d+)/);
                    if (match) {
                        orgIdElement = {
                            tagName: el.tagName,
                            textContent: el.textContent.substring(0, 50),
                            value: match[1]
                        };
                        break;
                    }
                }
            }
            
            return orgIdElement;
            """
            
            result = self.driver.execute_script(script)
            
            if result and 'value' in result:
                org_id = result['value']
                logger.info(f"从DOM结构中提取到组织ID: {org_id}")
                return org_id
            
            logger.warning("未从DOM结构中找到组织ID")
            return None
        except Exception as e:
            logger.error(f"从DOM结构中提取组织ID时发生错误: {e}")
            return None
    
    def extract_org_id_from_source(self):
        """从页面源代码中提取组织ID"""
        try:
            page_source = self.driver.page_source
            
            # 使用正则表达式从源代码中提取
            org_id_match = re.search(r'orgId["\s:=]+(\d+)', page_source) or re.search(r'orgid["\s:=]+(\d+)', page_source)
            
            if org_id_match:
                org_id = org_id_match.group(1)
                logger.info(f"从页面源代码中提取到组织ID: {org_id}")
                return org_id
            
            logger.warning("未从页面源代码中找到组织ID")
            return None
        except Exception as e:
            logger.error(f"从页面源代码中提取组织ID时发生错误: {e}")
            return None
    
    def extract_company_name(self):
        """提取公司名称，优先用<div class='name' title>的title属性，需等待元素出现"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            # 等待公司介绍页的div.name[title]出现
            try:
                name_div = WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.name[title]"))
                )
                title = name_div.get_attribute("title")
                if title:
                    logger.info(f"通过<div class='name' title>提取到公司名称: {title}")
                    return title
            except Exception as e:
                logger.debug(f"等待<div class='name' title>时异常: {e}")
            # 其次用原有多选择器逻辑
            def is_valid_company_name(name):
                if not name:
                    return False
                if name.isdigit():
                    return False
                if any(x in name for x in [":", "_", "-", "年", "月", "日", "/", " "]):
                    # 包含明显时间特征或分隔符
                    return False
                if len(name) < 2 or len(name) > 20:
                    return False
                return True
            selectors = [
                ".company-name",
                ".companyName",
                ".el-table__row td:nth-child(2)",
                "h1",
                "h2",
                "span"
            ]
            for sel in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for element in elements:
                    txt = element.text.strip()
                    if is_valid_company_name(txt):
                        logger.info(f"提取到公司名称: {txt}")
                        return txt
            # 再尝试从自动完成下拉项中提取
            autocomplete_items = self.driver.execute_script("return window.autocompleteItems;")
            if autocomplete_items and len(autocomplete_items) > 0:
                for item in autocomplete_items:
                    text = item.get('text', '')
                    parts = text.split()
                    for part in parts:
                        if is_valid_company_name(part):
                            logger.info(f"从自动完成下拉项中提取到公司名称: {part}")
                            return part
            logger.warning("未提取到公司名称")
            return "未知"
        except Exception as e:
            logger.error(f"提取公司名称时发生错误: {e}")
            return "未知"
    
    def get_org_id(self, stock_code):
        """
        获取股票代码对应的组织ID
        """
        if not self.driver:
            if not self.setup_driver():
                return None
        # 每次新股票前关闭所有旧tab，仅保留一个新tab
        try:
            handles = self.driver.window_handles
            for h in handles[1:]:
                self.driver.switch_to.window(h)
                self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
        except Exception as e:
            logger.debug(f"关闭旧tab时发生异常: {e}")
        try:
            # 直接访问搜索结果页，无需输入和点击
            search_url = f"https://www.cninfo.com.cn/new/fulltextSearch?notautosubmit=&keyWord={stock_code}"
            self.driver.get(search_url)
            time.sleep(3)  # 等待页面加载
            # 注入监控脚本
            self.inject_monitoring_scripts()
            # 跳转后点击"公司介绍"tab
            try:
                tab_button = None
                # 优先精确查找<a>标签，href包含companyProfile且文本为公司介绍
                try:
                    tab_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'companyProfile') and contains(text(), '公司介绍')]"))
                    )
                    tab_button.click()
                    logger.info("已精确点击<a>公司介绍</a>tab")
                    time.sleep(2)
                except Exception as e:
                    logger.debug(f"精确<a>查找公司介绍tab失败: {e}")
                    # 多种方式尝试查找tab
                    tab_selectors = [
                        "//div[contains(@class, 'tab') and contains(., '公司介绍')]",
                        "//a[contains(text(), '公司介绍')]",
                        "//span[contains(text(), '公司介绍')]",
                        "//*[contains(@class, 'el-tabs__item') and contains(text(), '公司介绍')]",
                        "//*[contains(text(), '公司介绍') and (self::a or self::span or self::div)]"
                    ]
                    for selector in tab_selectors:
                        try:
                            tab_button = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            if tab_button:
                                tab_button.click()
                                logger.info(f"已点击公司介绍tab: {selector}")
                                time.sleep(2)
                                break
                        except Exception as e2:
                            logger.debug(f"未通过{selector}找到公司介绍tab: {e2}")
                if not tab_button:
                    logger.warning("未能自动点击'公司介绍'tab，请检查页面结构")
            except Exception as e:
                logger.warning(f"点击'公司介绍'tab时发生异常: {e}")
            # 优先从新页面URL中提取orgId
            org_id = self.extract_org_id_from_url() or \
                self.extract_org_id_from_xhr() or \
                self.extract_org_id_from_dom() or \
                self.extract_org_id_from_source()
            if org_id:
                logger.info(f"获取到 {stock_code} 的组织ID: {org_id}")
                return org_id
            else:
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
        # 优先尝试从csv获取A股代码
        if not os.path.exists(csv_path):
            self.fetch_all_a_stock_codes(csv_path)
        stock_codes = self.get_stock_codes_from_csv(csv_path, start, end)
        if not stock_codes:
            logger.warning("未能从csv获取A股代码，回退到generate_stock_codes")
            stock_codes = self.generate_stock_codes(start, end)
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
