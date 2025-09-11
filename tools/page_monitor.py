#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
页面监控工具
用于持续监控网页每页的所有文档内容
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logger import get_logger
from src.web.driver import WebDriverManager
from src.web.scraper import WebScraper
from selenium.webdriver.common.by import By

logger = get_logger(__name__)

class PageMonitor:
    """页面监控器"""
    
    def __init__(self, headless: bool = True, timeout: int = 30):
        """
        初始化监控器
        
        Args:
            headless: 是否无头模式
            timeout: 超时时间
        """
        self.headless = headless
        self.timeout = timeout
        
    def monitor_all_pages(self,
                         stock_code: str,
                         org_id: str,
                         max_pages: int = 5,
                         save_results: bool = True,
                         export_format: str = "json") -> Dict:
        """
        监控所有页面的文档内容
        
        Args:
            stock_code: 股票代码
            org_id: 组织ID  
            max_pages: 最大监控页数
            save_results: 是否保存结果
            export_format: 导出格式 (json/csv)
            
        Returns:
            Dict: 监控结果
        """
        logger.info(f"开始监控股票 {stock_code} 的所有页面文档...")
        
        driver_manager = WebDriverManager(
            headless=self.headless,
            download_dir=f"page_monitor_{stock_code}",
            page_load_timeout=self.timeout,
            implicit_wait=10
        )
        
        monitor_result = {
            "stock_code": stock_code,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "max_pages": max_pages,
            "pages_data": {},
            "summary": {},
            "recommendations": []
        }
        
        try:
            with driver_manager as driver:
                url = f"https://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#research"
                
                logger.info(f"访问页面: {url}")
                driver.get(url)
                time.sleep(8)  # 充分等待初始加载
                
                scraper = WebScraper(driver)
                
                # 存储每页的完整文档列表
                all_pages_data = {}
                
                # 监控前max_pages页的所有文档
                for page_num in range(1, max_pages + 1):
                    logger.info(f"\n{'='*80}")
                    logger.info(f"=== 完整监控第{page_num}页所有文档 ===")
                    logger.info(f"{'='*80}")
                    
                    if page_num > 1:
                        logger.info(f"正在导航到第{page_num}页...")
                        
                        # 记录导航前的状态
                        before_state = {
                            'url': driver.current_url,
                            'title': driver.title,
                            'document_count': len(driver.find_elements(By.CSS_SELECTOR, ".el-table__row, .table-row"))
                        }
                        
                        success = scraper.go_to_page(page_num, timeout=15)
                        if not success:
                            logger.error(f"❌ 无法跳转到第{page_num}页")
                            monitor_result["recommendations"].append(f"第{page_num}页导航失败")
                            break
                        
                        # 等待页面完全加载
                        logger.info("等待页面内容完全加载...")
                        time.sleep(5)
                        
                        # 验证状态变化
                        after_state = {
                            'url': driver.current_url,
                            'title': driver.title,
                            'document_count': len(driver.find_elements(By.CSS_SELECTOR, ".el-table__row, .table-row"))
                        }
                        
                        logger.info(f"导航前后对比:")
                        logger.info(f"  URL: {before_state['url']} -> {after_state['url']}")
                        logger.info(f"  标题: {before_state['title']} -> {after_state['title']}")
                        logger.info(f"  文档数量: {before_state['document_count']} -> {after_state['document_count']}")
                    
                    # 获取第{page_num}页的完整文档列表
                    page_data = self._get_complete_page_content(driver, page_num)
                    all_pages_data[page_num] = page_data
                    
                    logger.info(f"第{page_num}页完整分析:")
                    logger.info(f"  总文档数量: {len(page_data['documents'])}")
                    logger.info(f"  分页信息: {page_data['page_info']}")
                    
                    # 详细列出所有文档
                    if page_data['documents']:
                        logger.info(f"\n--- 第{page_num}页所有文档详细列表 ---")
                        
                        # 按日期排序显示
                        sorted_docs = sorted(page_data['documents'], key=lambda x: x.get('date', ''), reverse=True)
                        
                        for i, doc in enumerate(sorted_docs, 1):
                            logger.info(f"  {i:2d}. {doc['title']}")
                            logger.info(f"      日期: {doc['date']}")
                            logger.info(f"      完整文本: {doc['full_text'][:100]}...")
                            logger.info(f"      ---")
                    
                    # 分析本页日期分布
                    self._analyze_date_distribution(page_data['documents'], page_num)
                
                # 最终跨页面对比分析
                logger.info(f"\n{'='*80}")
                logger.info("=== 最终跨页面完整对比分析 ===")
                logger.info(f"{'='*80}")
                
                comparison_result = self._perform_complete_comparison(all_pages_data)
                
                # 生成总结
                logger.info(f"\n{'='*80}")
                logger.info("=== 完整监控总结报告 ===")
                logger.info(f"{'='*80}")
                
                monitor_result["pages_data"] = all_pages_data
                monitor_result["summary"] = self._generate_monitor_summary(all_pages_data)
                monitor_result["recommendations"] = comparison_result["recommendations"]
                
                # 保存结果
                if save_results:
                    self._save_monitor_results(monitor_result, stock_code, export_format)
                
                return monitor_result
                
        except Exception as e:
            logger.error(f"完整监控失败: {e}")
            monitor_result["recommendations"].append(f"监控过程中发生错误: {str(e)}")
            return monitor_result
        
        finally:
            logger.info("完整监控完成")
    
    def _get_complete_page_content(self, driver, page_num: int) -> Dict:
        """获取页面的完整内容"""
        try:
            # 获取页面基本信息
            page_info = {
                'page_num': page_num,
                'url': driver.current_url,
                'title': driver.title,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 获取分页信息
            try:
                pagination_elements = driver.find_elements(By.CSS_SELECTOR, ".el-pagination, .pagination")
                for elem in pagination_elements:
                    if elem.is_displayed():
                        page_info['pagination_text'] = elem.text
                        break
            except:
                page_info['pagination_text'] = '未找到'
            
            # 获取所有文档行
            documents = []
            
            # 尝试多种选择器确保找到所有文档
            table_selectors = [
                ".el-table__row",
                ".table-row", 
                "tbody tr",
                ".el-table tbody tr",
                "tr[data-row-key]",
                ".el-table__body-wrapper tbody tr"
            ]
            
            all_rows = []
            for selector in table_selectors:
                try:
                    found_rows = driver.find_elements(By.CSS_SELECTOR, selector)
                    if found_rows:
                        all_rows = found_rows
                        logger.info(f"使用选择器 '{selector}' 找到 {len(found_rows)} 个文档行")
                        break
                except:
                    continue
            
            # 解析每个文档的详细信息
            for i, row in enumerate(all_rows):
                try:
                    # 获取行内所有单元格
                    cells = row.find_elements(By.CSS_SELECTOR, "td, .el-table__cell")
                    
                    doc = {
                        'row_index': i + 1,
                        'cells_count': len(cells),
                        'full_text': row.text.strip(),
                        'title': '',
                        'date': '',
                        'keywords_matched': []
                    }
                    
                    # 提取标题和日期
                    if len(cells) >= 2:
                        # 通常第一列是标题，第二列是日期
                        title_text = cells[0].text.strip()
                        date_text = cells[1].text.strip() if len(cells) > 1 else ''
                        
                        doc['title'] = title_text
                        doc['date'] = date_text
                        
                        # 提取关键词用于后续分析
                        if '2023' in title_text:
                            doc['keywords_matched'].append('2023')
                        if '2024' in title_text:
                            doc['keywords_matched'].append('2024')
                        if '2025' in title_text:
                            doc['keywords_matched'].append('2025')
                        if '投资者' in title_text or '关系' in title_text:
                            doc['keywords_matched'].append('投资者关系')
                    else:
                        # 如果没有表格结构，使用整行文本
                        full_text = row.text.strip()
                        doc['title'] = full_text[:80]  # 限制长度
                        doc['date'] = ''
                        doc['full_text'] = full_text
                    
                    documents.append(doc)
                    
                except Exception as e:
                    logger.debug(f"解析第{i+1}行失败: {e}")
                    continue
            
            return {
                'page_num': page_num,
                'page_info': page_info,
                'documents': documents,
                'document_count': len(documents),
                'analysis_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            logger.error(f"获取第{page_num}页完整内容失败: {e}")
            return {
                'page_num': page_num,
                'page_info': {},
                'documents': [],
                'document_count': 0,
                'error': str(e)
            }
    
    def _analyze_date_distribution(self, documents: List[Dict], page_num: int):
        """分析日期分布"""
        if not documents:
            return
        
        dates = [doc.get('date', '') for doc in documents if doc.get('date', '')]
        
        if not dates:
            logger.info(f"第{page_num}页: 未找到有效日期")
            return
        
        # 提取年份
        years = []
        for date in dates:
            if len(date) >= 4 and date[:4].isdigit():
                years.append(date[:4])
        
        if years:
            year_counts = {}
            for year in years:
                year_counts[year] = year_counts.get(year, 0) + 1
            
            logger.info(f"第{page_num}页日期分布:")
            for year, count in sorted(year_counts.items(), reverse=True):
                logger.info(f"  {year}年: {count} 个文档")
            
            # 高亮显示重要年份
            important_years = ['2023', '2024', '2025']
            for year in important_years:
                if year in year_counts:
                    logger.info(f"  🎯 第{page_num}页找到 {year_counts[year]} 个{year}年文档！")
    
    def _perform_complete_comparison(self, all_pages_data: Dict) -> Dict:
        """执行完整的跨页面对比"""
        result = {
            "differences": [],
            "recommendations": []
        }
        
        if len(all_pages_data) < 2:
            logger.info("不足2页，无法进行对比")
            result["recommendations"].append("需要至少2页数据进行有效对比")
            return result
        
        logger.info("执行完整跨页面对比分析...")
        
        # 对比相邻页面
        has_differences = False
        for page_num in range(1, len(all_pages_data)):
            if page_num in all_pages_data and (page_num + 1) in all_pages_data:
                current_page = all_pages_data[page_num]
                next_page = all_pages_data[page_num + 1]
                
                current_docs = current_page['documents']
                next_docs = next_page['documents']
                
                logger.info(f"\n--- 第{page_num}页 vs 第{page_num + 1}页对比 ---")
                logger.info(f"第{page_num}页: {len(current_docs)} 个文档")
                logger.info(f"第{page_num + 1}页: {len(next_docs)} 个文档")
                
                if current_docs and next_docs:
                    # 提取标题进行对比
                    current_titles = [doc['title'] for doc in current_docs]
                    next_titles = [doc['title'] for doc in next_docs]
                    
                    if current_titles == next_titles:
                        logger.error(f"❌ 第{page_num}页和第{page_num + 1}页文档完全相同！")
                        result["differences"].append({
                            "pages": f"{page_num}-{page_num + 1}",
                            "same_content": True,
                            "issue": "页面内容完全相同"
                        })
                    else:
                        has_differences = True
                        logger.info(f"✅ 第{page_num}页和第{page_num + 1}页文档不同")
                        
                        # 显示具体差异
                        unique_current = set(current_titles) - set(next_titles)
                        unique_next = set(next_titles) - set(current_titles)
                        
                        logger.info(f"第{page_num}页独有: {len(unique_current)} 个")
                        logger.info(f"第{page_num + 1}页独有: {len(unique_next)} 个")
                        
                        if unique_current:
                            logger.info(f"第{page_num}页独有文档:")
                            for title in list(unique_current)[:3]:
                                logger.info(f"  - {title}")
                        
                        if unique_next:
                            logger.info(f"第{page_num + 1}页独有文档:")
                            for title in list(unique_next)[:3]:
                                logger.info(f"  - {title}")
                        
                        result["differences"].append({
                            "pages": f"{page_num}-{page_num + 1}",
                            "same_content": False,
                            "unique_to_first": len(unique_current),
                            "unique_to_second": len(unique_next)
                        })
                else:
                    logger.warning(f"某些页面内容为空，无法进行有效对比")
                    result["differences"].append({
                        "pages": f"{page_num}-{page_num + 1}",
                        "same_content": False,
                        "issue": "某些页面内容为空"
                    })
        
        # 生成建议
        if has_differences:
            result["recommendations"].append("✅ 翻页功能正常 - 各页内容有差异")
        else:
            result["recommendations"].append("❌ 翻页功能异常 - 各页内容相同")
            result["recommendations"].append("建议检查分页导航逻辑或等待机制")
        
        return result
    
    def _generate_monitor_summary(self, all_pages_data: Dict) -> Dict:
        """生成监控总结"""
        summary = {
            "total_pages": len(all_pages_data),
            "total_documents": 0,
            "page_statistics": []
        }
        
        total_docs = 0
        for page_num, page_data in all_pages_data.items():
            doc_count = page_data['document_count']
            total_docs += doc_count
            
            summary["page_statistics"].append({
                "page": page_num,
                "documents": doc_count,
                "date_range": self._extract_date_range(page_data['documents'])
            })
        
        summary["total_documents"] = total_docs
        
        # 翻页功能结论
        if len(all_pages_data) >= 2:
            # 检查是否有内容变化
            has_differences = False
            for diff in self._perform_complete_comparison(all_pages_data)["differences"]:
                if not diff.get("same_content", True):
                    has_differences = True
                    break
            
            if has_differences:
                summary["pagination_status"] = "正常"
                summary["pagination_message"] = "✅ 翻页功能正常 - 各页内容有差异"
            else:
                summary["pagination_status"] = "异常"
                summary["pagination_message"] = "❌ 翻页功能异常 - 各页内容相同"
        else:
            summary["pagination_status"] = "未知"
            summary["pagination_message"] = "⚠️  数据不足，无法进行有效对比"
        
        return summary
    
    def _extract_date_range(self, documents: List[Dict]) -> str:
        """提取日期范围"""
        if not documents:
            return "无数据"
        
        dates = [doc.get('date', '') for doc in documents if doc.get('date', '')]
        if not dates:
            return "无日期"
        
        # 提取年份
        years = []
        for date in dates:
            if len(date) >= 4 and date[:4].isdigit():
                years.append(date[:4])
        
        if years:
            return f"{min(years)}-{max(years)}"
        return "未知"
    
    def _save_monitor_results(self, result: Dict, stock_code: str, format: str = "json"):
        """保存监控结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format.lower() == "json":
            filename = f"page_monitor_{stock_code}_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        elif format.lower() == "csv":
            filename = f"page_monitor_{stock_code}_{timestamp}.csv"
            self._export_to_csv(result, filename)
        
        logger.info(f"📄 监控结果已保存: {filename}")
    
    def _export_to_csv(self, result: Dict, filename: str):
        """导出为CSV格式"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 写入标题行
            writer.writerow(['页面', '文档标题', '日期', '完整文本', '关键词匹配'])
            
            # 写入数据
            for page_num, page_data in result["pages_data"].items():
                for doc in page_data["documents"]:
                    writer.writerow([
                        page_num,
                        doc.get("title", ""),
                        doc.get("date", ""),
                        doc.get("full_text", "")[:200],  # 限制长度
                        ", ".join(doc.get("keywords_matched", []))
                    ])

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='页面监控工具')
    parser.add_argument('--stock-code', required=True, help='股票代码')
    parser.add_argument('--org-id', required=True, help='组织ID')
    parser.add_argument('--max-pages', type=int, default=5, help='最大监控页数')
    parser.add_argument('--headless', action='store_true', help='无头模式')
    parser.add_argument('--no-save', action='store_true', help='不保存结果')
    parser.add_argument('--export-format', choices=['json', 'csv'], default='json', help='导出格式')
    parser.add_argument('--timeout', type=int, default=30, help='超时时间')
    
    args = parser.parse_args()
    
    monitor = PageMonitor(headless=args.headless, timeout=args.timeout)
    result = monitor.monitor_all_pages(
        stock_code=args.stock_code,
        org_id=args.org_id,
        max_pages=args.max_pages,
        save_results=not args.no_save,
        export_format=args.export_format
    )
    
    # 输出总结
    logger.info(f"\n{'='*80}")
    logger.info("=== 监控完成总结 ===")
    logger.info(f"{'='*80}")
    logger.info(f"股票代码: {result['stock_code']}")
    logger.info(f"监控页数: {len(result['pages_data'])}")
    logger.info(f"总文档数: {result['summary']['total_documents']}")
    logger.info(f"翻页状态: {result['summary']['pagination_message']}")
    
    sys.exit(0)

if __name__ == "__main__":
    main()