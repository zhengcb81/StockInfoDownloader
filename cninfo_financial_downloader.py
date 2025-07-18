#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
巨潮资讯网财务报告下载器

本程序用于自动下载巨潮资讯网上的财务报告，包括：
- 年度报告
- 半年度报告  
- 季度报告（一季报、三季报）

作者: Claude Code
日期: 2025-07-16
"""

import os
import re
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from cninfo_activity_downloader import CninfoDownloader
from orgid_utils import get_org_id_by_code
from get_stock_name import get_stock_name
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cninfo_financial_downloader.log')
    ]
)
logger = logging.getLogger('cninfo_financial_downloader')

class FinancialReportType:
    """财务报告类型枚举"""
    ANNUAL = "annual"          # 年度报告
    SEMI_ANNUAL = "semi_annual"  # 半年度报告
    QUARTERLY_Q1 = "q1"        # 一季度报告
    QUARTERLY_Q3 = "q3"        # 三季度报告
    ALL = "all"               # 所有类型

class CninfoFinancialDownloader(CninfoDownloader):
    """巨潮资讯网财务报告下载器"""
    
    def __init__(self, save_dir='downloads', mapping_file='stock_orgid_mapping.json'):
        """
        初始化财务报告下载器
        
        参数:
            save_dir: 保存文件的目录
            mapping_file: 股票代码与组织ID的映射文件
        """
        super().__init__(save_dir, mapping_file)
        self.base_financial_url = "http://www.cninfo.com.cn/new/information/topSearch/query"
        self.config = {'headless': True}
        
    def get_financial_reports(self, stock_code: str, report_types: List[str] = None, 
                            years: List[int] = None, max_reports: int = None) -> List[Dict]:
        """
        获取财务报告列表
        
        参数:
            stock_code: 股票代码
            report_types: 报告类型列表，如['annual', 'semi_annual', 'q1', 'q3']
            years: 年份列表，如[2023, 2024]
            max_reports: 最大报告数量
            
        返回:
            List[Dict]: 报告信息列表
        """
        if report_types is None:
            report_types = [FinancialReportType.ALL]
            
        if FinancialReportType.ALL in report_types:
            report_types = [FinancialReportType.ANNUAL, FinancialReportType.SEMI_ANNUAL, 
                          FinancialReportType.QUARTERLY_Q1, FinancialReportType.QUARTERLY_Q3]
        
        org_id = self.get_org_id(stock_code)
        if not org_id:
            logger.error(f"无法获取股票 {stock_code} 的组织ID")
            return []
            
        stock_name = get_stock_name(stock_code)
        if not stock_name:
            stock_name = stock_code
            
        reports = []
        
        try:
            # 构建搜索URL
            search_url = f"http://www.cninfo.com.cn/new/information/topSearch/query"
            
            # 设置Chrome选项
            self.setup_driver(headless=self.config.get('headless', True))
            
            # 访问定期报告页面
            financial_url = f"http://www.cninfo.com.cn/new/disclosure/stock?stockCode={stock_code}&orgId={org_id}#periodicReports"
            
            logger.info(f"访问股票 {stock_code} 的定期报告页面: {financial_url}")
            self.driver.get(financial_url)
            
            # 等待页面加载
            self.random_delay(2, 4)
            
            # 模拟人类行为
            self.simulate_human_behavior()
            
            # 查找报告列表
            reports = self._extract_financial_reports(stock_code, stock_name, report_types, years, max_reports)
            
        except Exception as e:
            logger.error(f"获取财务报告时出错: {str(e)}")
            
        return reports
    
    def _extract_financial_reports(self, stock_code: str, stock_name: str, 
                                 report_types: List[str], years: List[int], 
                                 max_reports: int = None) -> List[Dict]:
        """提取财务报告列表"""
        reports = []
        
        try:
            # 等待报告列表加载
            wait = WebDriverWait(self.driver, 10)
            
            # 查找定期报告标签 - 更健壮的选择器
            try:
                # 尝试多种方式找到定期报告标签
                periodic_tab = None
                
                # 方法1: 查找包含“定期报告”的元素
                for xpath in [
                    "//div[contains(text(), '定期报告')]",
                    "//span[contains(text(), '定期报告')]",
                    "//a[contains(text(), '定期报告')]",
                    "//*[contains(text(), '定期报告')]"
                ]:
                    try:
                        periodic_tab = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                        break
                    except:
                        continue
                
                if not periodic_tab:
                    # 方法2: 查找定期报告相关的class或ID
                    for selector in [
                        "#periodicReports",
                        "[data-tab='periodic']",
                        ".periodic-reports",
                        "[href*='periodic']"
                    ]:
                        try:
                            periodic_tab = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                            break
                        except:
                            continue
                
                if periodic_tab:
                    # 滚动到元素位置再点击
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", periodic_tab)
                    self.random_delay(1, 2)
                    periodic_tab.click()
                else:
                    logger.warning("未找到定期报告标签，尝试直接访问页面")
                    
            except Exception as e:
                logger.warning(f"无法点击定期报告标签: {str(e)}")
            
            self.random_delay(1, 3)
            
            # 查找报告表格
            report_table = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "el-table__body"))
            )
            
            # 获取所有报告行
            report_rows = report_table.find_elements(By.TAG_NAME, "tr")
            
            for row in report_rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 4:
                        # 提取报告信息
                        title = cells[1].text.strip()
                        date = cells[2].text.strip()
                        file_type = cells[3].text.strip()
                        
                        # 检查报告类型（跳过英文版报告）
                        report_type = self._classify_report_type(title, file_type)
                        if report_type is None or report_type not in report_types:
                            continue
                            
                        # 检查年份
                        if years:
                            report_year = self._extract_year_from_date(date)
                            if report_year and report_year not in years:
                                continue
                        
                        # 查找下载链接
                        download_link = None
                        try:
                            link_element = cells[1].find_element(By.TAG_NAME, "a")
                            download_link = link_element.get_attribute("href")
                        except:
                            pass
                        
                        if download_link and download_link.endswith('.pdf'):
                            report = {
                                'stock_code': stock_code,
                                'stock_name': stock_name,
                                'title': title,
                                'date': date,
                                'report_type': report_type,
                                'file_type': file_type,
                                'download_url': download_link,
                                'filename': f"{stock_name}_{title}_{date}.pdf"
                            }
                            reports.append(report)
                            
                            if max_reports and len(reports) >= max_reports:
                                break
                                
                except Exception as e:
                    logger.warning(f"解析报告行时出错: {str(e)}")
                    continue
                    
        except TimeoutException:
            logger.error("页面加载超时，无法找到报告列表")
            
        return reports
    
    def _classify_report_type(self, title: str, file_type: str) -> str:
        """根据标题和文件类型分类报告"""
        title = title.lower()
        file_type = file_type.lower()
        
        # 跳过英文版报告
        english_keywords = ['英文版', 'english', '英文', 'english version', 'english edition']
        for keyword in english_keywords:
            if keyword in title or keyword in file_type:
                return None  # 返回None表示跳过此报告
        
        if '年度报告' in title or '年报' in title:
            return FinancialReportType.ANNUAL
        elif '半年度' in title or '中报' in title:
            return FinancialReportType.SEMI_ANNUAL
        elif '第一季度' in title or '一季报' in title:
            return FinancialReportType.QUARTERLY_Q1
        elif '第三季度' in title or '三季报' in title:
            return FinancialReportType.QUARTERLY_Q3
        else:
            # 根据文件类型判断
            if '年度报告' in file_type:
                return FinancialReportType.ANNUAL
            elif '半年度报告' in file_type:
                return FinancialReportType.SEMI_ANNUAL
            elif '第一季度报告' in file_type:
                return FinancialReportType.QUARTERLY_Q1
            elif '第三季度报告' in file_type:
                return FinancialReportType.QUARTERLY_Q3
                
        return FinancialReportType.ANNUAL  # 默认
    
    def _extract_year_from_date(self, date_str: str) -> Optional[int]:
        """从日期字符串中提取年份"""
        try:
            # 处理格式如 "2023-12-31" 或 "2023年12月31日"
            year_match = re.search(r'(\d{4})', date_str)
            if year_match:
                return int(year_match.group(1))
        except:
            pass
        return None
    
    def download_financial_reports(self, reports: List[Dict], overwrite: bool = False) -> Dict[str, int]:
        """
        下载财务报告
        
        参数:
            reports: 报告信息列表
            overwrite: 是否覆盖已存在的文件
            
        返回:
            Dict[str, int]: 下载统计信息
        """
        if not reports:
            logger.warning("没有需要下载的报告")
            return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0}
            
        stats = {'total': len(reports), 'success': 0, 'failed': 0, 'skipped': 0}
        
        for i, report in enumerate(reports, 1):
            try:
                logger.info(f"[{i}/{len(reports)}] 下载报告: {report['title']}")
                
                # 创建保存目录（与投资者关系下载器一致，直接在公司目录下）
                save_path = os.path.join(self.save_dir, report['stock_name'])
                if not os.path.exists(save_path):
                    os.makedirs(save_path)
                
                # 清理文件名
                filename = self.clean_filename(report['filename'])
                file_path = os.path.join(save_path, filename)
                
                # 检查文件是否已存在
                if os.path.exists(file_path) and not overwrite:
                    logger.info(f"文件已存在，跳过: {filename}")
                    stats['skipped'] += 1
                    continue
                
                # 下载文件
                success = self._download_single_report(report['download_url'], file_path)
                if success:
                    stats['success'] += 1
                    logger.info(f"下载成功: {filename}")
                else:
                    stats['failed'] += 1
                    logger.error(f"下载失败: {filename}")
                
                # 会话管理
                self.download_count += 1
                if self.download_count >= self.max_downloads_per_session:
                    self.restart_driver()
                    self.download_count = 0
                else:
                    self.random_delay(2, 5)  # 下载间隔
                    
            except Exception as e:
                logger.error(f"下载报告 {report['title']} 时出错: {str(e)}")
                stats['failed'] += 1
                continue
        
        return stats
    
    def _download_single_report(self, url: str, file_path: str) -> bool:
        """下载单个报告"""
        try:
            self.driver.get(url)
            self.random_delay(1, 3)
            
            # 这里可以添加实际的PDF下载逻辑
            # 由于cninfo.com.cn的PDF通常直接通过URL下载
            # 我们可以使用requests或者直接通过浏览器下载
            
            # 对于直接PDF链接，使用浏览器下载
            if url.endswith('.pdf'):
                # 触发下载（具体实现取决于网站结构）
                return self._handle_pdf_download(url, file_path)
            
            return True
            
        except Exception as e:
            logger.error(f"下载PDF失败: {str(e)}")
            return False
    
    def _handle_pdf_download(self, url: str, file_path: str) -> bool:
        """处理PDF下载"""
        try:
            import requests
            headers = {
                'User-Agent': random.choice(self.user_agents)
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                return True
                
        except Exception as e:
            logger.error(f"PDF下载失败: {str(e)}")
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='巨潮资讯网财务报告下载器')
    parser.add_argument('--stock-code', required=True, help='股票代码')
    parser.add_argument('--report-types', nargs='+', 
                       choices=['annual', 'semi_annual', 'q1', 'q3', 'all'],
                       default=['all'], help='报告类型')
    parser.add_argument('--years', nargs='+', type=int, help='年份列表')
    parser.add_argument('--max-reports', type=int, help='最大报告数量')
    parser.add_argument('--save-dir', default='downloads', help='保存目录')
    parser.add_argument('--headless', action='store_true', help='无头模式')
    parser.add_argument('--overwrite', action='store_true', help='覆盖已存在文件')
    
    args = parser.parse_args()
    
    # 创建下载器
    downloader = CninfoFinancialDownloader(save_dir=args.save_dir)
    downloader.config = {'headless': args.headless}
    
    try:
        # 获取报告列表
        reports = downloader.get_financial_reports(
            stock_code=args.stock_code,
            report_types=args.report_types,
            years=args.years,
            max_reports=args.max_reports
        )
        
        if not reports:
            print("未找到符合条件的财务报告")
            return
            
        print(f"找到 {len(reports)} 个财务报告")
        
        # 下载报告
        stats = downloader.download_financial_reports(reports, overwrite=args.overwrite)
        
        print(f"\n下载完成:")
        print(f"总计: {stats['total']}")
        print(f"成功: {stats['success']}")
        print(f"失败: {stats['failed']}")
        print(f"跳过: {stats['skipped']}")
        
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")
    finally:
        if hasattr(downloader, 'driver') and downloader.driver:
            downloader.driver.quit()

if __name__ == "__main__":
    main()