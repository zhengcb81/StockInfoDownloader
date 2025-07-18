#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
巨潮资讯网统一下载器

支持下载：
1. 投资者关系活动记录表
2. 财务报告（年报、半年报、季报）

作者: Claude Code
日期: 2025-07-16
"""

import os
import json
import argparse
import logging
from typing import Dict, List, Optional
from cninfo_activity_downloader import CninfoDownloader
from cninfo_financial_downloader import CninfoFinancialDownloader, FinancialReportType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('unified_downloader.log')
    ]
)
logger = logging.getLogger('unified_downloader')

class UnifiedDownloader:
    """统一下载器，支持投资者关系和财务报告"""
    
    def __init__(self, config_file: str = 'config.json'):
        """
        初始化统一下载器
        
        参数:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            
        # 默认配置
        return {
            "stock_code": "",
            "save_dir": "downloads",
            "headless": True,
            "download_type": "investor_relations",
            "report_types": ["annual"],
            "years": [2023, 2024],
            "max_reports": 10,
            "overwrite_existing": False
        }
    
    def download_investor_relations(self, stock_code: str = None) -> bool:
        """下载投资者关系活动记录表"""
        stock_code = stock_code or self.config.get('stock_code')
        if not stock_code:
            logger.error("未指定股票代码")
            return False
            
        try:
            downloader = CninfoDownloader(
                save_dir=self.config.get('save_dir', 'downloads')
            )
            
            logger.info(f"开始下载股票 {stock_code} 的投资者关系活动记录表")
            
            org_id = downloader.get_org_id(stock_code)
            if not org_id:
                logger.error(f"无法获取股票 {stock_code} 的组织ID")
                return False
                
            success = downloader.download_activity_records(stock_code)
            
            if success:
                logger.info(f"股票 {stock_code} 的投资者关系活动记录表下载完成")
            else:
                logger.error(f"股票 {stock_code} 的投资者关系活动记录表下载失败")
                
            return success
            
        except Exception as e:
            logger.error(f"下载投资者关系记录表时出错: {str(e)}")
            return False
        finally:
            if hasattr(downloader, 'driver') and downloader.driver:
                downloader.driver.quit()
    
    def download_financial_reports(self, stock_code: str = None, 
                                 report_types: List[str] = None,
                                 years: List[int] = None,
                                 max_reports: int = None) -> bool:
        """下载财务报告"""
        stock_code = stock_code or self.config.get('stock_code')
        report_types = report_types or self.config.get('report_types', ['annual'])
        years = years or self.config.get('years', [2023, 2024])
        max_reports = max_reports or self.config.get('max_reports', 10)
        
        if not stock_code:
            logger.error("未指定股票代码")
            return False
            
        try:
            downloader = CninfoFinancialDownloader(
                save_dir=self.config.get('save_dir', 'downloads')
            )
            downloader.config = {'headless': self.config.get('headless', True)}
            
            logger.info(f"开始下载股票 {stock_code} 的财务报告")
            
            # 获取报告列表
            reports = downloader.get_financial_reports(
                stock_code=stock_code,
                report_types=report_types,
                years=years,
                max_reports=max_reports
            )
            
            if not reports:
                logger.warning("未找到符合条件的财务报告")
                return False
                
            logger.info(f"找到 {len(reports)} 个财务报告，开始下载...")
            
            # 下载报告
            stats = downloader.download_financial_reports(
                reports, 
                overwrite=self.config.get('overwrite_existing', False)
            )
            
            logger.info(f"财务报告下载完成 - 成功: {stats['success']}, 失败: {stats['failed']}, 跳过: {stats['skipped']}")
            
            return stats['success'] > 0
            
        except Exception as e:
            logger.error(f"下载财务报告时出错: {str(e)}")
            return False
        finally:
            if hasattr(downloader, 'driver') and downloader.driver:
                downloader.driver.quit()
    
    def interactive_mode(self):
        """交互模式"""
        print("=" * 50)
        print("巨潮资讯网统一下载器")
        print("=" * 50)
        
        # 输入股票代码
        stock_code = input("请输入股票代码 (如: 002415): ").strip()
        if not stock_code:
            print("股票代码不能为空")
            return
            
        # 选择下载类型
        print("\n选择下载类型:")
        print("1. 投资者关系活动记录表")
        print("2. 财务报告")
        
        choice = input("请选择 (1/2): ").strip()
        
        if choice == "1":
            self.download_investor_relations(stock_code)
            
        elif choice == "2":
            print("\n选择报告类型 (可多选，用空格分隔):")
            print("annual - 年度报告")
            print("semi_annual - 半年度报告")
            print("q1 - 第一季度报告")
            print("q3 - 第三季度报告")
            print("all - 所有类型")
            
            report_types_input = input("报告类型: ").strip().split()
            if not report_types_input:
                report_types = ["annual"]
            else:
                report_types = [t for t in report_types_input if t in 
                              ["annual", "semi_annual", "q1", "q3", "all"]]
            
            years_input = input("年份 (如: 2023 2024，留空默认最近两年): ").strip()
            if years_input:
                try:
                    years = [int(y) for y in years_input.split()]
                except:
                    years = [2023, 2024]
            else:
                years = [2023, 2024]
                
            max_reports_input = input("最大报告数量 (留空无限制): ").strip()
            max_reports = int(max_reports_input) if max_reports_input.isdigit() else None
            
            self.download_financial_reports(
                stock_code=stock_code,
                report_types=report_types,
                years=years,
                max_reports=max_reports
            )
            
        else:
            print("无效的选择")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='巨潮资讯网统一下载器')
    parser.add_argument('--stock-code', help='股票代码')
    parser.add_argument('--type', choices=['investor_relations', 'financial'], 
                       default='investor_relations', help='下载类型')
    parser.add_argument('--report-types', nargs='+', 
                       choices=['annual', 'semi_annual', 'q1', 'q3', 'all'],
                       default=['annual'], help='财务报告类型')
    parser.add_argument('--years', nargs='+', type=int, help='年份')
    parser.add_argument('--max-reports', type=int, help='最大报告数量')
    parser.add_argument('--save-dir', default='downloads', help='保存目录')
    parser.add_argument('--headless', action='store_true', help='无头模式')
    parser.add_argument('--overwrite', action='store_true', help='覆盖已存在文件')
    parser.add_argument('--interactive', action='store_true', help='交互模式')
    parser.add_argument('--config', default='config.json', help='配置文件')
    
    args = parser.parse_args()
    
    downloader = UnifiedDownloader(config_file=args.config)
    
    if args.interactive:
        downloader.interactive_mode()
        return
    
    # 更新配置
    if args.save_dir:
        downloader.config['save_dir'] = args.save_dir
    if args.headless:
        downloader.config['headless'] = args.headless
    if args.overwrite:
        downloader.config['overwrite_existing'] = args.overwrite
    if args.report_types:
        downloader.config['report_types'] = args.report_types
    if args.years:
        downloader.config['years'] = args.years
    if args.max_reports:
        downloader.config['max_reports'] = args.max_reports
    
    stock_code = args.stock_code or downloader.config.get('stock_code')
    if not stock_code:
        print("错误: 必须指定股票代码")
        return
    
    # 执行下载
    if args.type == 'investor_relations':
        success = downloader.download_investor_relations(stock_code)
    else:
        success = downloader.download_financial_reports(
            stock_code=stock_code,
            report_types=args.report_types,
            years=args.years,
            max_reports=args.max_reports
        )
    
    if success:
        print("下载完成！")
    else:
        print("下载失败！")

if __name__ == "__main__":
    main()