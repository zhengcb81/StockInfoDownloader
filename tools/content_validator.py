#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
内容真实性验证工具
用于验证网页翻页后内容是否真正更新
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logger import get_logger
from src.web.driver import WebDriverManager
from src.web.scraper import WebScraper
from selenium.webdriver.common.by import By

logger = get_logger(__name__)

class ContentValidator:
    """内容真实性验证器"""
    
    def __init__(self, headless: bool = True, timeout: int = 30):
        """
        初始化验证器
        
        Args:
            headless: 是否无头模式
            timeout: 超时时间
        """
        self.headless = headless
        self.timeout = timeout
        self.results = []
        
    def validate_pagination_content(self, 
                                  stock_code: str,
                                  org_id: str,
                                  max_pages: int = 3,
                                  save_report: bool = True) -> Dict:
        """
        验证分页内容真实性
        
        Args:
            stock_code: 股票代码
            org_id: 组织ID
            max_pages: 最大验证页数
            save_report: 是否保存报告
            
        Returns:
            Dict: 验证结果
        """
        logger.info(f"开始验证股票 {stock_code} 的分页内容真实性...")
        
        driver_manager = WebDriverManager(
            headless=self.headless,
            download_dir=f"content_validation_{stock_code}",
            page_load_timeout=self.timeout,
            implicit_wait=10
        )
        
        validation_result = {
            "stock_code": stock_code,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "max_pages": max_pages,
            "pages_analyzed": [],
            "content_differences": [],
            "overall_status": "unknown",
            "recommendations": []
        }
        
        try:
            with driver_manager as driver:
                url = f"https://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#research"
                
                logger.info(f"访问页面: {url}")
                driver.get(url)
                time.sleep(8)  # 充分等待初始加载
                
                scraper = WebScraper(driver)
                
                # 存储每页的内容用于对比
                page_contents = {}
                
                # 验证前max_pages页
                for page_num in range(1, max_pages + 1):
                    logger.info(f"\n{'='*60}")
                    logger.info(f"=== 验证第{page_num}页内容 ===")
                    logger.info(f"{'='*60}")
                    
                    if page_num > 1:
                        logger.info(f"正在导航到第{page_num}页...")
                        
                        success = scraper.go_to_page(page_num, timeout=15)
                        if not success:
                            logger.error(f"❌ 无法跳转到第{page_num}页")
                            validation_result["recommendations"].append(f"第{page_num}页导航失败")
                            break
                        
                        # 等待页面加载
                        logger.info("等待页面内容完全加载...")
                        time.sleep(5)
                    
                    # 获取当前页面的详细内容
                    content = self._get_page_content(driver, page_num)
                    page_contents[page_num] = content
                    
                    validation_result["pages_analyzed"].append({
                        "page_num": page_num,
                        "document_count": len(content["documents"]),
                        "date_range": content["date_range"],
                        "sample_titles": content["sample_titles"]
                    })
                    
                    logger.info(f"第{page_num}页分析结果:")
                    logger.info(f"  文档数量: {len(content['documents'])}")
                    logger.info(f"  日期范围: {content['date_range']}")
                    logger.info(f"  前3个标题: {content['sample_titles']}")
                
                # 进行内容对比分析
                content_analysis = self._analyze_content_differences(page_contents)
                validation_result["content_differences"] = content_analysis["differences"]
                validation_result["overall_status"] = content_analysis["status"]
                validation_result["recommendations"].extend(content_analysis["recommendations"])
                
                # 生成最终报告
                self._generate_validation_report(validation_result, save_report)
                
                return validation_result
                
        except Exception as e:
            logger.error(f"验证失败: {e}")
            validation_result["overall_status"] = "error"
            validation_result["recommendations"].append(f"验证过程中发生错误: {str(e)}")
            return validation_result
        
        finally:
            logger.info("验证完成")
    
    def _get_page_content(self, driver, page_num: int) -> Dict:
        """获取页面内容"""
        try:
            documents = []
            
            # 尝试多种选择器找到文档表格
            table_selectors = [
                ".el-table__row",
                ".table-row", 
                "tbody tr",
                ".el-table tbody tr",
                "tr[data-row-key]"
            ]
            
            all_rows = []
            for selector in table_selectors:
                try:
                    found_rows = driver.find_elements(By.CSS_SELECTOR, selector)
                    if found_rows:
                        all_rows = found_rows
                        break
                except:
                    continue
            
            # 解析每个文档
            for i, row in enumerate(all_rows):
                try:
                    cells = row.find_elements(By.CSS_SELECTOR, "td, .el-table__cell")
                    
                    if len(cells) >= 2:
                        title_text = cells[0].text.strip()
                        date_text = cells[1].text.strip() if len(cells) > 1 else ''
                        
                        documents.append({
                            "title": title_text,
                            "date": date_text,
                            "full_text": row.text.strip()
                        })
                except Exception as e:
                    logger.debug(f"解析第{i+1}行失败: {e}")
                    continue
            
            # 提取日期范围和样本标题
            dates = [doc["date"] for doc in documents if doc["date"]]
            titles = [doc["title"] for doc in documents]
            
            date_range = "未知"
            if dates:
                try:
                    # 提取年份信息
                    years = []
                    for date in dates:
                        if len(date) >= 4 and date[:4].isdigit():
                            years.append(date[:4])
                    
                    if years:
                        date_range = f"{min(years)}-{max(years)}"
                except:
                    pass
            
            return {
                "page_num": page_num,
                "document_count": len(documents),
                "date_range": date_range,
                "sample_titles": titles[:3] if titles else [],
                "documents": documents
            }
            
        except Exception as e:
            logger.error(f"获取第{page_num}页内容失败: {e}")
            return {
                "page_num": page_num,
                "document_count": 0,
                "date_range": "error",
                "sample_titles": [],
                "documents": []
            }
    
    def _analyze_content_differences(self, page_contents: Dict) -> Dict:
        """分析内容差异"""
        analysis = {
            "differences": [],
            "status": "unknown",
            "recommendations": []
        }
        
        if len(page_contents) < 2:
            analysis["status"] = "insufficient_data"
            analysis["recommendations"].append("需要至少2页数据进行对比")
            return analysis
        
        # 对比相邻页面
        has_differences = False
        for page_num in range(1, len(page_contents)):
            if page_num in page_contents and (page_num + 1) in page_contents:
                current_docs = page_contents[page_num]["documents"]
                next_docs = page_contents[page_num + 1]["documents"]
                
                # 提取标题进行对比
                current_titles = [doc["title"] for doc in current_docs]
                next_titles = [doc["title"] for doc in next_docs]
                
                if current_titles != next_titles:
                    has_differences = True
                    analysis["differences"].append({
                        "page_pair": f"{page_num} vs {page_num + 1}",
                        "different": True,
                        "current_count": len(current_titles),
                        "next_count": len(next_titles)
                    })
                else:
                    analysis["differences"].append({
                        "page_pair": f"{page_num} vs {page_num + 1}",
                        "different": False,
                        "current_count": len(current_titles),
                        "next_count": len(next_titles)
                    })
        
        # 确定整体状态
        if has_differences:
            analysis["status"] = "healthy"
            analysis["recommendations"].append("✅ 分页功能正常 - 各页内容有差异")
        else:
            analysis["status"] = "suspicious"
            analysis["recommendations"].append("⚠️  分页功能异常 - 各页内容相同")
            analysis["recommendations"].append("建议检查分页导航逻辑或等待机制")
        
        return analysis
    
    def _generate_validation_report(self, result: Dict, save_report: bool):
        """生成验证报告"""
        logger.info(f"\n{'='*80}")
        logger.info("=== 内容真实性验证报告 ===")
        logger.info(f"{'='*80}")
        
        logger.info(f"股票代码: {result['stock_code']}")
        logger.info(f"验证时间: {result['timestamp']}")
        logger.info(f"验证页数: {result['max_pages']}")
        logger.info(f"整体状态: {result['overall_status']}")
        
        logger.info(f"\n📊 页面分析结果:")
        for page in result["pages_analyzed"]:
            logger.info(f"  第{page['page_num']}页: {page['document_count']}个文档, 日期范围: {page['date_range']}")
            logger.info(f"    样本: {page['sample_titles']}")
        
        logger.info(f"\n🔍 内容差异分析:")
        for diff in result["content_differences"]:
            status = "✅ 不同" if diff["different"] else "❌ 相同"
            logger.info(f"  {diff['page_pair']}: {status}")
        
        logger.info(f"\n💡 建议:")
        for rec in result["recommendations"]:
            logger.info(f"  - {rec}")
        
        if save_report:
            report_file = f"content_validation_report_{result['stock_code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"\n📄 报告已保存: {report_file}")
        
        logger.info(f"{'='*80}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='内容真实性验证工具')
    parser.add_argument('--stock-code', required=True, help='股票代码')
    parser.add_argument('--org-id', required=True, help='组织ID')
    parser.add_argument('--max-pages', type=int, default=3, help='最大验证页数')
    parser.add_argument('--headless', action='store_true', help='无头模式')
    parser.add_argument('--no-report', action='store_true', help='不保存报告')
    parser.add_argument('--timeout', type=int, default=30, help='超时时间')
    
    args = parser.parse_args()
    
    validator = ContentValidator(headless=args.headless, timeout=args.timeout)
    result = validator.validate_pagination_content(
        stock_code=args.stock_code,
        org_id=args.org_id,
        max_pages=args.max_pages,
        save_report=not args.no_report
    )
    
    # 返回适当的退出码
    if result["overall_status"] == "healthy":
        logger.info("🎉 内容真实性验证通过！")
        sys.exit(0)
    elif result["overall_status"] == "suspicious":
        logger.info("⚠️  内容真实性验证发现异常")
        sys.exit(1)
    else:
        logger.info("❌ 内容真实性验证失败")
        sys.exit(2)

if __name__ == "__main__":
    main()