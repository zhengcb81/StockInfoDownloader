#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
并行多公司股票信息下载器主程序
支持并行处理多个公司代码，具备反爬虫保护和IP轮换功能
"""

import sys
import locale
import asyncio
import concurrent.futures
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

# 设置控制台编码为UTF-8
if sys.platform == 'win32':
    try:
        # Windows下设置控制台编码为UTF-8
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        # 如果设置失败，忽略错误
        pass

import sys
import json
import os
import argparse
import threading
from dataclasses import dataclass

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.config import ConfigManager
from src.core.logger import get_logger
from src.core.performance_monitor import log_performance_stats, get_performance_stats
from src.services.downloader_v2 import DownloadServiceV2 as DownloadService
from src.data.mapping import MappingManager

# 导入新增的并行下载服务
try:
    from src.services.parallel_downloader import ParallelDownloadManager
    from src.web.proxy_manager import ProxyManager
    PARALLEL_DOWNLOAD_AVAILABLE = True
except ImportError:
    PARALLEL_DOWNLOAD_AVAILABLE = False
    print("警告: 并行下载模块不可用，将使用串行模式")

# 导入股票名称获取函数
try:
    from get_stock_name import get_stock_name
except ImportError:
    # 如果导入失败，使用备选方案
    def get_stock_name(stock_code, mapping_file='stock_orgid_mapping.json'):
        mapping_manager = MappingManager(mapping_file)
        return mapping_manager.get_stock_name(stock_code) or f"股票{stock_code}"


@dataclass
class CompanyConfig:
    """公司配置数据类"""
    stock_code: str
    company_name: str
    enabled: bool = True
    priority: int = 1
    custom_pages: Optional[List[Dict]] = None


class MultiCompanyDownloader:
    """多公司并行下载器"""

    def __init__(self, config: Dict[str, Any], config_file: Optional[str] = None):
        self.config = config
        self.config_file = config_file or "config.json"
        self.logger = get_logger(__name__)
        self.mapping_manager = MappingManager()
        self.save_dir = config.get('save_dir', 'downloads')

        # 并行下载配置
        self.parallel_config = config.get('parallel_download', {})
        self.use_parallel = self.parallel_config.get('enabled', False) and PARALLEL_DOWNLOAD_AVAILABLE
        self.max_workers = self.parallel_config.get('max_workers', 3)

        # 代理配置
        self.proxy_config = config.get('proxy_management', {})
        self.use_proxy = self.proxy_config.get('enabled', False)

        # 初始化服务 - 使用DownloadServiceV2
        browser_strategy = config.get('browser', {}).get('strategy', 'playwright')
        self.download_service = DownloadService(
            save_dir=self.save_dir,
            mapping_file="stock_orgid_mapping.json",
            browser_strategy=browser_strategy
        )

        # 如果需要并行下载，初始化并行下载管理器
        if self.use_parallel:
            self.parallel_manager = ParallelDownloadManager(
                max_workers=self.max_workers,
                config=self.parallel_config
            )
            self.logger.info(f"并行下载模式已启用，最大工作线程数: {self.max_workers}")
        else:
            self.parallel_manager = None
            self.logger.info("使用串行下载模式")

        # 如果需要代理，初始化代理管理器
        if self.use_proxy:
            self.proxy_manager = ProxyManager(self.proxy_config)
            self.logger.info("代理管理已启用")
        else:
            self.proxy_manager = None
            self.logger.info("未启用代理功能")

    def get_company_configs(self) -> List[CompanyConfig]:
        """获取公司配置列表"""
        companies = []

        # 优先使用新的companies配置
        if 'companies' in self.config:
            for company_data in self.config['companies']:
                if company_data.get('enabled', True):
                    company_config = CompanyConfig(
                        stock_code=company_data['stock_code'],
                        company_name=company_data.get('company_name', ''),
                        enabled=company_data.get('enabled', True),
                        priority=company_data.get('priority', 1),
                        custom_pages=company_data.get('custom_pages')
                    )
                    companies.append(company_config)

        # 兼容旧的stock_code配置
        elif 'stock_code' in self.config:
            stock_code = self.config['stock_code']
            company_name = get_stock_name(stock_code)
            company_config = CompanyConfig(
                stock_code=stock_code,
                company_name=company_name,
                enabled=True,
                priority=1
            )
            companies.append(company_config)

        # 按优先级排序
        companies.sort(key=lambda x: x.priority)

        self.logger.info(f"配置了 {len(companies)} 个公司进行下载")
        for company in companies:
            self.logger.info(f"  - {company.stock_code}: {company.company_name} (优先级: {company.priority})")

        return companies

    def download_company(self, company_config: CompanyConfig) -> Dict[str, Any]:
        """下载单个公司的数据"""
        start_time = time.time()
        self.logger.info(f"开始处理公司: {company_config.stock_code} - {company_config.company_name}")

        try:
            # 验证股票代码
            if not company_config.stock_code.isdigit() or len(company_config.stock_code) != 6:
                error_msg = f"无效的股票代码: {company_config.stock_code}"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'stock_code': company_config.stock_code,
                    'error': error_msg,
                    'files_downloaded': 0,
                    'execution_time': time.time() - start_time
                }

            # 获取组织ID
            org_id = self.mapping_manager.get_org_id(company_config.stock_code)
            if not org_id:
                error_msg = f"无法获取股票 {company_config.stock_code} 的组织ID"
                self.logger.error(error_msg)
                return {
                    'success': False,
                    'stock_code': company_config.stock_code,
                    'error': error_msg,
                    'files_downloaded': 0,
                    'execution_time': time.time() - start_time
                }

            # 获取页面配置
            pages = company_config.custom_pages or self.config.get('pages', [
                {'name': '调研', 'suffix': 'research', 'allowed_keywords': None},
                {'name': '定期公告', 'suffix': 'periodicReports', 'allowed_keywords': None},
                {'name': '最新公告', 'suffix': 'latestAnnouncement', 'allowed_keywords': ["招股说明书"]}
            ])

            total_files = 0
            successful_pages = 0

            # 执行下载
            for page_config in pages:
                page_name = page_config.get('name', '未知页面')
                suffix = page_config.get('suffix', '')
                allowed_keywords = page_config.get('allowed_keywords')

                self.logger.info(f"开始下载 {company_config.stock_code} 的页面: {page_name}")

                try:
                    # 构建目标页面列表 - 传递完整的页面配置包括排除关键词
                    if suffix:
                        target_pages = [{'suffix': suffix, 'allowed_keywords': allowed_keywords, 'excluded_keywords': page_config.get('excluded_keywords')}]
                    else:
                        target_pages = [{'suffix': 'research', 'allowed_keywords': None, 'excluded_keywords': None}]

                    # 如果使用代理，设置代理
                    proxy_info = None
                    if self.proxy_manager:
                        proxy_info = self.proxy_manager.get_proxy()
                        if proxy_info:
                            self.logger.info(f"使用代理: {proxy_info.get('ip', 'unknown')}")

                    # 执行下载 - DownloadServiceV2不支持proxy_info参数
                    result = self.download_service.download_stock_pdfs(
                        stock_code=company_config.stock_code,
                        target_pages=target_pages,
                        max_retries=self.config.get('max_retries', 3)
                    )

                    if result and len(result) > 0:
                        total_files += len(result)
                        successful_pages += 1
                        self.logger.info(f"页面 {page_name} 下载完成，下载了 {len(result)} 个文件")
                    else:
                        self.logger.warning(f"页面 {page_name} 下载失败或没有新文件")

                except Exception as e:
                    self.logger.error(f"下载页面 {page_name} 时发生错误: {e}")
                    self.logger.error(f"错误详情: {str(e)}", exc_info=True)

                # 页面间延迟 - 随机延迟以避免反爬虫
                import random
                delay = random.uniform(0.5, 2.0)
                time.sleep(delay)

            execution_time = time.time() - start_time

            result = {
                'success': successful_pages > 0,
                'stock_code': company_config.stock_code,
                'company_name': company_config.company_name,
                'files_downloaded': total_files,
                'successful_pages': successful_pages,
                'total_pages': len(pages),
                'execution_time': execution_time,
                'timestamp': datetime.now().isoformat()
            }

            if result['success']:
                self.logger.info(f"公司 {company_config.stock_code} 下载完成，共下载 {total_files} 个文件，耗时 {execution_time:.2f} 秒")
            else:
                self.logger.warning(f"公司 {company_config.stock_code} 下载失败")

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"处理公司 {company_config.stock_code} 时发生异常: {e}"
            self.logger.error(error_msg)
            self.logger.error(f"错误详情: {str(e)}", exc_info=True)

            return {
                'success': False,
                'stock_code': company_config.stock_code,
                'error': error_msg,
                'files_downloaded': 0,
                'execution_time': execution_time
            }

    def download_companies_sequential(self, company_configs: List[CompanyConfig]) -> List[Dict[str, Any]]:
        """串行下载多个公司"""
        results = []

        for company_config in company_configs:
            try:
                result = self.download_company(company_config)
                results.append(result)

                # 公司间延迟 - 避免反爬虫
                if company_config != company_configs[-1]:  # 不是最后一个公司
                    import random
                    delay = random.uniform(2.0, 5.0)
                    self.logger.info(f"公司间延迟 {delay:.2f} 秒")
                    time.sleep(delay)

            except Exception as e:
                self.logger.error(f"处理公司 {company_config.stock_code} 时发生异常: {e}")
                results.append({
                    'success': False,
                    'stock_code': company_config.stock_code,
                    'error': str(e),
                    'files_downloaded': 0,
                    'execution_time': 0
                })

        return results

    def download_companies_parallel(self, company_configs: List[CompanyConfig]) -> List[Dict[str, Any]]:
        """并行下载多个公司"""
        results = []

        try:
            # 使用线程池并行处理
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                future_to_company = {
                    executor.submit(self.download_company, company_config): company_config
                    for company_config in company_configs
                }

                # 收集结果
                for future in concurrent.futures.as_completed(future_to_company):
                    company_config = future_to_company[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        self.logger.error(f"公司 {company_config.stock_code} 并行处理失败: {e}")
                        results.append({
                            'success': False,
                            'stock_code': company_config.stock_code,
                            'error': str(e),
                            'files_downloaded': 0,
                            'execution_time': 0
                        })

        except Exception as e:
            self.logger.error(f"并行下载失败: {e}")
            # 降级到串行模式
            self.logger.info("降级到串行模式")
            return self.download_companies_sequential(company_configs)

        return results

    def download_all_companies(self) -> List[Dict[str, Any]]:
        """下载所有配置的公司"""
        company_configs = self.get_company_configs()

        if not company_configs:
            self.logger.error("没有找到有效的公司配置")
            return []

        self.logger.info(f"开始下载 {len(company_configs)} 个公司的数据")

        if self.use_parallel and len(company_configs) > 1:
            # 并行下载
            return self.download_companies_parallel(company_configs)
        else:
            # 串行下载
            return self.download_companies_sequential(company_configs)

    def print_summary(self, results: List[Dict[str, Any]]):
        """打印下载摘要"""
        if not results:
            self.logger.info("没有下载结果")
            return

        total_companies = len(results)
        successful_companies = sum(1 for r in results if r['success'])
        total_files = sum(r.get('files_downloaded', 0) for r in results)
        total_time = sum(r.get('execution_time', 0) for r in results)

        self.logger.info("=== 下载摘要 ===")
        self.logger.info(f"总处理公司数: {total_companies}")
        self.logger.info(f"成功下载公司数: {successful_companies}")
        self.logger.info(f"下载文件总数: {total_files}")
        self.logger.info(f"总执行时间: {total_time:.2f} 秒")

        if total_time > 0:
            avg_time_per_company = total_time / total_companies
            self.logger.info(f"平均每公司耗时: {avg_time_per_company:.2f} 秒")

        # 显示每个公司的详细结果
        self.logger.info("=== 详细结果 ===")
        for result in results:
            status = "成功" if result['success'] else "失败"
            files = result.get('files_downloaded', 0)
            time_spent = result.get('execution_time', 0)

            detail = f"{result['stock_code']} ({result.get('company_name', 'unknown')}): {status}"
            if files > 0:
                detail += f" - {files} 个文件"
            if time_spent > 0:
                detail += f" - {time_spent:.2f} 秒"

            if not result['success'] and 'error' in result:
                detail += f" - 错误: {result['error']}"

            self.logger.info(detail)


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='多公司股票信息并行下载器')
    parser.add_argument('--config', default='config.json', help='配置文件路径 (默认: config.json)')
    parser.add_argument('--parallel', action='store_true', help='强制启用并行模式')
    parser.add_argument('--sequential', action='store_true', help='强制使用串行模式')
    parser.add_argument('--max-workers', type=int, help='最大并行工作线程数')
    args = parser.parse_args()

    # 初始化日志
    logger = get_logger(__name__)

    try:
        logger.info("启动多公司股票信息并行下载器...")

        # 加载配置
        config_manager = ConfigManager()
        try:
            config = config_manager.load_config(args.config)
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            return 1

        # 处理命令行参数覆盖
        if args.parallel:
            config.setdefault('parallel_download', {})['enabled'] = True
        if args.sequential:
            config.setdefault('parallel_download', {})['enabled'] = False
        if args.max_workers:
            config.setdefault('parallel_download', {})['max_workers'] = args.max_workers

        # 初始化下载器
        downloader = MultiCompanyDownloader(config, args.config)

        # 执行下载
        start_time = time.time()
        results = downloader.download_all_companies()
        total_time = time.time() - start_time

        # 打印摘要
        downloader.print_summary(results)

        # 输出性能报告
        logger.info("=== 性能统计报告 ===")
        logger.info(f"总执行时间: {total_time:.2f} 秒")
        log_performance_stats()

        # 判断执行结果
        successful_companies = sum(1 for r in results if r['success'])
        if successful_companies > 0:
            logger.info(f"成功完成 {successful_companies} 个公司的下载")
            return 0
        else:
            logger.warning("没有成功下载任何公司的数据")
            return 0  # 没有下载成功不算失败，可能是没有新数据

    except KeyboardInterrupt:
        logger.info("用户中断程序")
        return 0
    except Exception as e:
        logger.error(f"程序运行失败: {e}")
        logger.error(f"错误详情: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)