#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
真实文档扩展工具
用于下载更多真实文档来扩展测试文档库
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from real_document_manager import RealDocumentManager


class RealDocumentExpander:
    """真实文档扩展器"""

    def __init__(self, base_dir: str = "end2end_test"):
        """
        初始化文档扩展器

        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
        self.expected_results_dir = self.base_dir / "expected_results"
        self.document_manager = RealDocumentManager(base_dir)

        # 定义要扩展的股票代码和公司信息
        self.target_stocks = [
            # 大盘股
            {"stock_code": "000001", "stock_name": "平安银行", "category": "大盘股", "industry": "银行"},
            {"stock_code": "000002", "stock_name": "万科A", "category": "大盘股", "industry": "房地产"},
            {"stock_code": "002415", "stock_name": "海康威视", "category": "大盘股", "industry": "安防"},

            # 中盘股
            {"stock_code": "300470", "stock_name": "中密控股", "category": "中盘股", "industry": "机械制造"},
            {"stock_code": "301611", "stock_name": "珂玛科技", "category": "中盘股", "industry": "半导体"},

            # 小盘股
            {"stock_code": "301589", "stock_name": "诺瓦星云", "category": "小盘股", "industry": "半导体"},
            {"stock_code": "301628", "stock_name": "铖昌科技", "category": "小盘股", "industry": "半导体"},

            # 不同行业的代表
            {"stock_code": "000858", "stock_name": "五粮液", "category": "大盘股", "industry": "白酒"},
            {"stock_code": "002594", "stock_name": "比亚迪", "category": "大盘股", "industry": "新能源汽车"},
            {"stock_code": "300750", "stock_name": "宁德时代", "category": "大盘股", "industry": "电池"},
        ]

        # 定义要下载的文档类型和关键词
        self.document_types = {
            "research": {
                "suffix": "research",
                "keywords": ["投资者关系", "调研", "投资者活动", "路演"],
                "max_pages": 3,
                "description": "投资者关系活动记录"
            },
            "periodicReports": {
                "suffix": "periodicReports",
                "keywords": ["年度报告", "半年报", "一季度报告", "三季度报告"],
                "max_pages": 5,
                "description": "定期报告"
            },
            "announcement": {
                "suffix": "announcement",
                "keywords": ["公告", "通知", "重大事项", "业绩预告"],
                "max_pages": 2,
                "description": "临时公告"
            }
        }

    def analyze_current_documents(self) -> Dict[str, Any]:
        """分析当前文档库状态"""
        existing_docs = self.document_manager.scan_existing_documents()

        analysis = {
            "total_documents": len(existing_docs),
            "stock_coverage": set(),
            "document_types": set(),
            "companies": set(),
            "size_distribution": {"small": 0, "medium": 0, "large": 0}
        }

        for doc in existing_docs:
            analysis["stock_coverage"].add(doc.stock_code)
            analysis["document_types"].add(doc.document_type)
            analysis["companies"].add(doc.stock_name)

            # 按大小分类
            if doc.file_size < 100 * 1024:  # < 100KB
                analysis["size_distribution"]["small"] += 1
            elif doc.file_size < 1024 * 1024:  # < 1MB
                analysis["size_distribution"]["medium"] += 1
            else:
                analysis["size_distribution"]["large"] += 1

        return analysis

    def create_expansion_plan(self, target_count: int = 20) -> Dict[str, Any]:
        """创建文档扩展计划"""
        current_analysis = self.analyze_current_documents()

        plan = {
            "current_status": current_analysis,
            "target_count": target_count,
            "needed_documents": target_count - current_analysis["total_documents"],
            "expansion_targets": []
        }

        # 根据当前缺口制定扩展计划
        missing_stocks = set()
        for stock in self.target_stocks:
            if stock["stock_code"] not in current_analysis["stock_coverage"]:
                missing_stocks.add(stock["stock_code"])

        # 为每个缺失的股票制定下载计划
        for stock in self.target_stocks:
            if stock["stock_code"] in missing_stocks or len(plan["expansion_targets"]) < plan["needed_documents"]:
                for doc_type, config in self.document_types.items():
                    if len(plan["expansion_targets"]) >= plan["needed_documents"]:
                        break

                    plan["expansion_targets"].append({
                        "stock_code": stock["stock_code"],
                        "stock_name": stock["stock_name"],
                        "category": stock["category"],
                        "industry": stock["industry"],
                        "document_type": doc_type,
                        "suffix": config["suffix"],
                        "keywords": config["keywords"][:1],  # 每次只下载一个关键词
                        "max_pages": config["max_pages"],
                        "description": config["description"],
                        "priority": self._calculate_priority(stock, current_analysis)
                    })

        # 按优先级排序
        plan["expansion_targets"].sort(key=lambda x: x["priority"], reverse=True)

        return plan

    def _calculate_priority(self, stock: Dict[str, Any], current_analysis: Dict[str, Any]) -> int:
        """计算下载优先级"""
        priority = 0

        # 大盘股优先级更高
        if stock["category"] == "大盘股":
            priority += 3
        elif stock["category"] == "中盘股":
            priority += 2
        else:
            priority += 1

        # 覆盖不足的行业优先级更高
        current_industries = set()
        for doc in self.document_manager.scan_existing_documents():
            # 简单的行业映射
            if "银行" in doc.stock_name:
                current_industries.add("银行")
            elif "地产" in doc.stock_name or "万科" in doc.stock_name:
                current_industries.add("房地产")
            elif "科技" in doc.stock_name or "半导体" in doc.stock_name:
                current_industries.add("科技")

        if stock["industry"] not in current_industries:
            priority += 2

        return priority

    def download_documents_for_expansion(self, plan: Dict[str, Any], max_downloads: int = 5) -> Dict[str, Any]:
        """执行文档下载扩展"""
        print("开始执行文档扩展...")
        print(f"当前文档数: {plan['current_status']['total_documents']}")
        print(f"目标文档数: {plan['target_count']}")
        print(f"需要下载: {plan['needed_documents']}")

        results = {
            "successful_downloads": [],
            "failed_downloads": [],
            "skipped_downloads": [],
            "total_attempted": 0,
            "total_successful": 0
        }

        # 尝试下载高优先级的文档
        high_priority_targets = [t for t in plan["expansion_targets"] if t["priority"] >= 3]

        for i, target in enumerate(high_priority_targets[:max_downloads]):
            print(f"\n下载目标 {i+1}/{min(len(high_priority_targets), max_downloads)}:")
            print(f"  股票: {target['stock_name']} ({target['stock_code']})")
            print(f"  类型: {target['description']}")
            print(f"  关键词: {target['keywords']}")

            results["total_attempted"] += 1

            try:
                success = self._download_single_document(target)
                if success:
                    results["successful_downloads"].append(target)
                    results["total_successful"] += 1
                    print(f"  [成功] 下载成功")
                else:
                    results["failed_downloads"].append(target)
                    print(f"  [失败] 下载失败")
            except Exception as e:
                results["failed_downloads"].append(target)
                print(f"  [异常] 下载异常: {e}")

            # 下载间隔
            time.sleep(2)

        # 更新文档目录
        print("\n重新扫描文档库...")
        updated_docs = self.document_manager.scan_existing_documents()
        self.document_manager.register_documents(updated_docs)

        results["final_document_count"] = len(updated_docs)
        results["expansion_success"] = results["final_document_count"] > plan["current_status"]["total_documents"]

        return results

    def _download_single_document(self, target: Dict[str, Any]) -> bool:
        """下载单个文档"""
        try:
            # 设置路径
            project_root = Path(__file__).parent.parent
            sys.path.insert(0, str(project_root))

            # 使用DownloadServiceV2进行下载
            from src.services.downloader_v2 import DownloadServiceV2
            from src.data.mapping import MappingManager

            # 创建临时映射文件
            temp_mapping_file = self.base_dir / "temp_expansion_mapping.json"
            mapping_data = {
                target["stock_code"]: {
                    "orgId": "9900056250",  # 使用一个通用的orgId
                    "name": target["stock_name"]
                }
            }

            with open(temp_mapping_file, 'w', encoding='utf-8') as f:
                json.dump(mapping_data, f, ensure_ascii=False, indent=2)

            # 创建下载器
            downloader = DownloadServiceV2(
                save_dir=str(self.expected_results_dir),
                mapping_file=str(temp_mapping_file),
                browser_strategy="playwright"  # 使用更稳定的Playwright
            )

            # 构建目标页面配置
            target_pages = [{
                "suffix": target["suffix"],
                "allowed_keywords": target["keywords"]
            }]

            # 执行下载
            download_records = downloader.download_stock_pdfs(
                stock_code=target["stock_code"],
                target_pages=target_pages,
                max_retries=1  # 减少重试次数，加快速度
            )

            # 清理临时文件
            if temp_mapping_file.exists():
                temp_mapping_file.unlink()

            return len(download_records) > 0

        except Exception as e:
            print(f"下载过程中发生错误: {e}")
            return False

    def create_document_classification_report(self) -> Dict[str, Any]:
        """创建文档分类报告"""
        existing_docs = self.document_manager.scan_existing_documents()

        classification = {
            "by_company": {},
            "by_document_type": {},
            "by_size": {"small": [], "medium": [], "large": []},
            "by_industry": {},
            "summary": {
                "total_documents": len(existing_docs),
                "total_companies": 0,
                "total_document_types": 0,
                "coverage_score": 0.0
            }
        }

        industries = {}

        for doc in existing_docs:
            # 按公司分类
            if doc.stock_name not in classification["by_company"]:
                classification["by_company"][doc.stock_name] = {
                    "stock_code": doc.stock_code,
                    "documents": [],
                    "document_count": 0,
                    "total_size": 0
                }

            classification["by_company"][doc.stock_name]["documents"].append({
                "document_name": doc.document_name,
                "document_type": doc.document_type,
                "file_size": doc.file_size,
                "file_hash": doc.file_hash[:8] + "..."
            })
            classification["by_company"][doc.stock_name]["document_count"] += 1
            classification["by_company"][doc.stock_name]["total_size"] += doc.file_size

            # 按文档类型分类
            if doc.document_type not in classification["by_document_type"]:
                classification["by_document_type"][doc.document_type] = {
                    "documents": [],
                    "count": 0,
                    "total_size": 0
                }

            classification["by_document_type"][doc.document_type]["documents"].append({
                "stock_name": doc.stock_name,
                "document_name": doc.document_name,
                "file_size": doc.file_size
            })
            classification["by_document_type"][doc.document_type]["count"] += 1
            classification["by_document_type"][doc.document_type]["total_size"] += doc.file_size

            # 按大小分类
            if doc.file_size < 100 * 1024:
                classification["by_size"]["small"].append(doc)
            elif doc.file_size < 1024 * 1024:
                classification["by_size"]["medium"].append(doc)
            else:
                classification["by_size"]["large"].append(doc)

            # 简单的行业分类
            industry = "其他"
            if "银行" in doc.stock_name:
                industry = "银行"
            elif "地产" in doc.stock_name or "万科" in doc.stock_name:
                industry = "房地产"
            elif "科技" in doc.stock_name or "半导体" in doc.stock_name:
                industry = "科技"
            elif "汽车" in doc.stock_name or "比亚迪" in doc.stock_name:
                industry = "汽车"

            if industry not in classification["by_industry"]:
                classification["by_industry"][industry] = {
                    "companies": set(),
                    "document_count": 0
                }

            classification["by_industry"][industry]["companies"].add(doc.stock_name)
            classification["by_industry"][industry]["document_count"] += 1

        # 计算汇总信息
        classification["summary"]["total_companies"] = len(classification["by_company"])
        classification["summary"]["total_document_types"] = len(classification["by_document_type"])

        # 转换set为list以便JSON序列化
        for industry_data in classification["by_industry"].values():
            industry_data["companies"] = list(industry_data["companies"])

        # 计算覆盖评分
        target_companies = len(self.target_stocks)
        covered_companies = classification["summary"]["total_companies"]
        classification["summary"]["coverage_score"] = (covered_companies / target_companies * 100) if target_companies > 0 else 0

        return classification


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='真实文档扩展工具')
    parser.add_argument('--base-dir', default='end2end_test', help='基础目录路径')
    parser.add_argument('--target-count', type=int, default=20, help='目标文档数量')
    parser.add_argument('--max-downloads', type=int, default=5, help='最大下载数量')
    parser.add_argument('--analyze-only', action='store_true', help='仅分析，不下载')
    parser.add_argument('--classify-only', action='store_true', help='仅分类统计')

    args = parser.parse_args()

    expander = RealDocumentExpander(args.base_dir)

    if args.classify_only:
        # 仅进行分类统计
        print("生成文档分类报告...")
        classification = expander.create_document_classification_report()

        print(f"\n=== 文档分类报告 ===")
        print(f"总文档数: {classification['summary']['total_documents']}")
        print(f"覆盖公司数: {classification['summary']['total_companies']}")
        print(f"文档类型数: {classification['summary']['total_document_types']}")
        print(f"覆盖评分: {classification['summary']['coverage_score']:.1f}%")

        print(f"\n按公司分类:")
        for company, data in classification["by_company"].items():
            print(f"  {company} ({data['stock_code']}): {data['document_count']} 个文档, {data['total_size']/1024:.1f} KB")

        print(f"\n按文档类型分类:")
        for doc_type, data in classification["by_document_type"].items():
            print(f"  {doc_type}: {data['count']} 个文档, {data['total_size']/1024:.1f} KB")

        print(f"\n按大小分类:")
        for size_category, docs in classification["by_size"].items():
            print(f"  {size_category}: {len(docs)} 个文档")

        return 0

    # 分析当前状态
    print("分析当前文档库状态...")
    current_analysis = expander.analyze_current_documents()

    print(f"当前状态:")
    print(f"  文档总数: {current_analysis['total_documents']}")
    print(f"  覆盖股票: {', '.join(current_analysis['stock_coverage'])}")
    print(f"  文档类型: {', '.join(current_analysis['document_types'])}")
    print(f"  公司数量: {len(current_analysis['companies'])}")
    print(f"  大小分布: 小文件({current_analysis['size_distribution']['small']}), "
          f"中文件({current_analysis['size_distribution']['medium']}), "
          f"大文件({current_analysis['size_distribution']['large']})")

    if args.analyze_only:
        return 0

    # 创建扩展计划
    print(f"\n创建扩展计划 (目标: {args.target_count} 个文档)...")
    expansion_plan = expander.create_expansion_plan(args.target_count)

    print(f"扩展计划:")
    print(f"  需要下载: {expansion_plan['needed_documents']} 个文档")
    print(f"  扩展目标: {len(expansion_plan['expansion_targets'])} 个")

    if expansion_plan['expansion_targets']:
        print(f"\n高优先级扩展目标:")
        for i, target in enumerate(expansion_plan['expansion_targets'][:5]):
            print(f"  {i+1}. {target['stock_name']} ({target['stock_code']}) - {target['description']}")

    # 执行扩展
    if expansion_plan['needed_documents'] > 0:
        print(f"\n开始执行文档扩展 (最多下载 {args.max_downloads} 个)...")
        results = expander.download_documents_for_expansion(expansion_plan, args.max_downloads)

        print(f"\n扩展结果:")
        print(f"  尝试下载: {results['total_attempted']} 个")
        print(f"  成功下载: {results['total_successful']} 个")
        print(f"  最终文档数: {results['final_document_count']}")
        print(f"  扩展成功: {'是' if results['expansion_success'] else '否'}")

        if results['successful_downloads']:
            print(f"\n成功下载的文档:")
            for doc in results['successful_downloads']:
                print(f"  [成功] {doc['stock_name']} ({doc['stock_code']}) - {doc['description']}")

        if results['failed_downloads']:
            print(f"\n下载失败的文档:")
            for doc in results['failed_downloads']:
                print(f"  [失败] {doc['stock_name']} ({doc['stock_code']}) - {doc['description']}")
    else:
        print("文档库已达到目标数量，无需扩展。")

    # 生成最终的分类报告
    print(f"\n生成最终分类报告...")
    final_classification = expander.create_document_classification_report()

    # 保存分类报告
    report_file = Path(args.base_dir) / "document_classification_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(final_classification, f, ensure_ascii=False, indent=2)

    print(f"分类报告已保存到: {report_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())