#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文档分类系统
建立基于真实场景的文档分类体系
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass, asdict

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from real_document_manager import RealDocumentManager, DocumentInfo


@dataclass
class CompanyCategory:
    """公司分类"""
    category_name: str
    description: str
    criteria: Dict[str, Any]
    examples: List[str]


@dataclass
class DocumentType:
    """文档类型"""
    type_name: str
    description: str
    suffix: str
    typical_keywords: List[str]
    typical_size_range: Tuple[int, int]  # (min_bytes, max_bytes)


@dataclass
class DifficultyLevel:
    """难度等级"""
    level: str
    description: str
    criteria: Dict[str, Any]
    typical_challenges: List[str]


class DocumentClassificationSystem:
    """文档分类系统"""

    def __init__(self, base_dir: str = "end2end_test"):
        """
        初始化文档分类系统

        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
        self.expected_results_dir = self.base_dir / "expected_results"
        self.document_manager = RealDocumentManager(base_dir)

        # 定义分类标准
        self.company_categories = self._define_company_categories()
        self.document_types = self._define_document_types()
        self.difficulty_levels = self._define_difficulty_levels()

        # 分类结果
        self.classification_result = {}

    def _define_company_categories(self) -> Dict[str, CompanyCategory]:
        """定义公司分类标准"""
        return {
            "大盘股": CompanyCategory(
                category_name="大盘股",
                description="市值超过1000亿的大型公司，通常具有稳定的业务和广泛的投资者关注",
                criteria={
                    "market_cap_min": 100000000000,  # 1000亿
                    "industries": ["银行", "保险", "房地产", "白酒", "汽车", "电池"],
                    "stock_exchange": ["深交所主板", "上交所主板"]
                },
                examples=["平安银行", "万科A", "五粮液", "比亚迪", "宁德时代"]
            ),
            "中盘股": CompanyCategory(
                category_name="中盘股",
                description="市值在100-1000亿之间的中型公司，具有良好的成长性",
                criteria={
                    "market_cap_min": 10000000000,   # 100亿
                    "market_cap_max": 100000000000,  # 1000亿
                    "industries": ["机械制造", "半导体", "化工", "医药"],
                    "stock_exchange": ["深交所主板", "上交所主板", "创业板"]
                },
                examples=["中密控股", "珂玛科技", "海康威视"]
            ),
            "小盘股": CompanyCategory(
                category_name="小盘股",
                description="市值小于100亿的小型公司，通常具有较高的成长潜力",
                criteria={
                    "market_cap_max": 10000000000,   # 100亿
                    "industries": ["半导体", "科技", "新材料", "生物医药"],
                    "stock_exchange": ["创业板", "科创板", "北交所"]
                },
                examples=["诺瓦星云", "铖昌科技"]
            )
        }

    def _define_document_types(self) -> Dict[str, DocumentType]:
        """定义文档类型标准"""
        return {
            "research": DocumentType(
                type_name="投资者关系活动",
                description="记录投资者关系活动、调研、路演等活动的文档",
                suffix="research",
                typical_keywords=["投资者关系", "调研", "投资者活动", "路演", "纪要"],
                typical_size_range=(50000, 500000)  # 50KB - 500KB
            ),
            "annual_report": DocumentType(
                type_name="年度报告",
                description="公司年度财务和经营报告",
                suffix="periodicReports",
                typical_keywords=["年度报告", "年报", "股东大会"],
                typical_size_range=(1000000, 10000000)  # 1MB - 10MB
            ),
            "semi_annual_report": DocumentType(
                type_name="半年度报告",
                description="公司半年度财务和经营报告",
                suffix="periodicReports",
                typical_keywords=["半年度报告", "半年报", "中期报告"],
                typical_size_range=(500000, 5000000)  # 500KB - 5MB
            ),
            "quarterly_report": DocumentType(
                type_name="季度报告",
                description="公司季度财务和经营报告",
                suffix="periodicReports",
                typical_keywords=["季度报告", "一季度报告", "二季度报告", "三季度报告", "四季度报告"],
                typical_size_range=(200000, 2000000)  # 200KB - 2MB
            ),
            "announcement": DocumentType(
                type_name="临时公告",
                description="公司临时发布的各类公告信息",
                suffix="announcement",
                typical_keywords=["公告", "通知", "重大事项", "业绩预告", "股价异动"],
                typical_size_range=(30000, 300000)  # 30KB - 300KB
            )
        }

    def _define_difficulty_levels(self) -> Dict[str, DifficultyLevel]:
        """定义难度等级标准"""
        return {
            "容易": DifficultyLevel(
                level="容易",
                description="文档下载相对容易，网络连接稳定，网站响应正常",
                criteria={
                    "download_time_max": 60,  # 60秒内
                    "retry_times_max": 2,     # 最多重试2次
                    "file_size_max": 1000000, # 小于1MB
                    "success_rate_min": 0.9   # 成功率90%以上
                },
                typical_challenges=["基本网络延迟", "页面加载时间"]
            ),
            "中等": DifficultyLevel(
                level="中等",
                description="文档下载需要一定时间，可能遇到网络波动或页面复杂的情况",
                criteria={
                    "download_time_max": 300, # 5分钟内
                    "retry_times_max": 3,     # 最多重试3次
                    "file_size_max": 5000000, # 小于5MB
                    "success_rate_min": 0.7   # 成功率70%以上
                },
                typical_challenges=["网络波动", "页面结构复杂", "反爬虫机制", "文件较大"]
            ),
            "困难": DifficultyLevel(
                level="困难",
                description="文档下载困难，可能遇到多种技术挑战",
                criteria={
                    "download_time_max": 900, # 15分钟内
                    "retry_times_max": 5,     # 最多重试5次
                    "file_size_max": 10000000, # 小于10MB
                    "success_rate_min": 0.5   # 成功率50%以上
                },
                typical_challenges=["强反爬虫机制", "网络不稳定", "大文件下载", "网站结构频繁变化"]
            )
        }

    def classify_documents(self) -> Dict[str, Any]:
        """对所有文档进行分类"""
        print("开始文档分类...")

        # 获取所有文档
        documents = self.document_manager.scan_existing_documents()
        print(f"找到 {len(documents)} 个文档")

        classification = {
            "total_documents": len(documents),
            "by_company_category": {},
            "by_document_type": {},
            "by_size_category": {},
            "by_difficulty": {},
            "by_industry": {},
            "cross_classification": {},
            "classification_metadata": {
                "classification_time": datetime.now().isoformat(),
                "system_version": "1.0",
                "total_categories": len(self.company_categories),
                "total_document_types": len(self.document_types),
                "total_difficulty_levels": len(self.difficulty_levels)
            }
        }

        # 初始化分类统计
        for category in self.company_categories.keys():
            classification["by_company_category"][category] = {
                "document_count": 0,
                "companies": set(),
                "documents": []
            }

        for doc_type in self.document_types.keys():
            classification["by_document_type"][doc_type] = {
                "document_count": 0,
                "total_size": 0,
                "documents": []
            }

        size_categories = {
            "small": (100000, "小文件 < 100KB"),
            "medium": (1000000, "中文件 100KB-1MB"),
            "large": (10000000, "大文件 1MB-10MB"),
            "xlarge": (float('inf'), "超大文件 > 10MB")
        }

        for size_cat in size_categories.keys():
            classification["by_size_category"][size_cat] = {
                "document_count": 0,
                "total_size": 0,
                "documents": []
            }

        for difficulty in self.difficulty_levels.keys():
            classification["by_difficulty"][difficulty] = {
                "document_count": 0,
                "estimated_download_time": 0,
                "documents": []
            }

        # 对每个文档进行分类
        for doc in documents:
            doc_classification = self._classify_single_document(doc)

            # 更新分类统计
            self._update_classification_stats(classification, doc, doc_classification)

        # 转换set为list以便JSON序列化
        for category_data in classification["by_company_category"].values():
            category_data["companies"] = list(category_data["companies"])

        # 生成交叉分类统计
        classification["cross_classification"] = self._generate_cross_classification(classification)

        self.classification_result = classification
        print(f"分类完成: {len(documents)} 个文档已分类")

        return classification

    def _classify_single_document(self, doc: DocumentInfo) -> Dict[str, str]:
        """对单个文档进行分类"""
        classification = {
            "company_category": self._classify_company(doc.stock_name),
            "document_type": doc.document_type,
            "size_category": self._classify_by_size(doc.file_size),
            "difficulty": self._estimate_difficulty(doc),
            "industry": self._classify_industry(doc.stock_name)
        }

        return classification

    def _classify_company(self, stock_name: str) -> str:
        """根据公司名称分类"""
        # 简单的基于已知公司名称的分类
        if stock_name in ["平安银行", "万科A", "五粮液", "比亚迪", "宁德时代"]:
            return "大盘股"
        elif stock_name in ["中密控股", "珂玛科技", "海康威视"]:
            return "中盘股"
        elif stock_name in ["诺瓦星云", "铖昌科技"]:
            return "小盘股"
        else:
            # 默认分类
            return "中盘股"

    def _classify_by_size(self, file_size: int) -> str:
        """根据文件大小分类"""
        if file_size < 100000:  # < 100KB
            return "small"
        elif file_size < 1000000:  # < 1MB
            return "medium"
        elif file_size < 10000000:  # < 10MB
            return "large"
        else:
            return "xlarge"

    def _estimate_difficulty(self, doc: DocumentInfo) -> str:
        """估算下载难度"""
        # 基于文档类型和大小的简单难度估算
        if doc.document_type == "announcement":
            return "容易"  # 公告通常较小且容易下载
        elif doc.document_type == "research":
            return "中等"  # 调研报告中等难度
        elif doc.document_type in ["annual_report", "semi_annual_report"]:
            return "中等"  # 定期报告中等难度
        elif doc.document_type == "quarterly_report":
            return "容易"  # 季度报告相对容易
        else:
            return "中等"

    def _classify_industry(self, stock_name: str) -> str:
        """根据公司名称分类行业"""
        if "银行" in stock_name:
            return "银行"
        elif "保险" in stock_name:
            return "保险"
        elif "地产" in stock_name or "万科" in stock_name:
            return "房地产"
        elif "酒" in stock_name or "五粮液" in stock_name:
            return "白酒"
        elif "汽车" in stock_name or "比亚迪" in stock_name:
            return "汽车"
        elif "电池" in stock_name or "宁德" in stock_name:
            return "电池"
        elif "科技" in stock_name or "半导体" in stock_name or "海康" in stock_name:
            return "科技"
        elif "机械" in stock_name or "中密" in stock_name:
            return "机械制造"
        else:
            return "其他"

    def _update_classification_stats(self, classification: Dict[str, Any], doc: DocumentInfo, doc_classification: Dict[str, str]):
        """更新分类统计"""
        # 公司分类统计
        company_cat = doc_classification["company_category"]
        if company_cat in classification["by_company_category"]:
            classification["by_company_category"][company_cat]["document_count"] += 1
            classification["by_company_category"][company_cat]["companies"].add(doc.stock_name)
            classification["by_company_category"][company_cat]["documents"].append({
                "stock_name": doc.stock_name,
                "stock_code": doc.stock_code,
                "document_name": doc.document_name,
                "file_size": doc.file_size,
                "document_type": doc.document_type
            })

        # 文档类型统计
        doc_type = doc_classification["document_type"]
        if doc_type in classification["by_document_type"]:
            classification["by_document_type"][doc_type]["document_count"] += 1
            classification["by_document_type"][doc_type]["total_size"] += doc.file_size
            classification["by_document_type"][doc_type]["documents"].append({
                "stock_name": doc.stock_name,
                "document_name": doc.document_name,
                "file_size": doc.file_size
            })

        # 大小分类统计
        size_cat = doc_classification["size_category"]
        if size_cat in classification["by_size_category"]:
            classification["by_size_category"][size_cat]["document_count"] += 1
            classification["by_size_category"][size_cat]["total_size"] += doc.file_size
            classification["by_size_category"][size_cat]["documents"].append({
                "stock_name": doc.stock_name,
                "document_name": doc.document_name,
                "file_size": doc.file_size
            })

        # 难度统计
        difficulty = doc_classification["difficulty"]
        if difficulty in classification["by_difficulty"]:
            classification["by_difficulty"][difficulty]["document_count"] += 1
            # 估算下载时间（简单估算）
            estimated_time = self._estimate_download_time(doc)
            classification["by_difficulty"][difficulty]["estimated_download_time"] += estimated_time
            classification["by_difficulty"][difficulty]["documents"].append({
                "stock_name": doc.stock_name,
                "document_name": doc.document_name,
                "estimated_time": estimated_time
            })

        # 行业统计
        industry = doc_classification["industry"]
        if industry not in classification["by_industry"]:
            classification["by_industry"][industry] = {
                "document_count": 0,
                "companies": set(),
                "documents": []
            }
        classification["by_industry"][industry]["document_count"] += 1
        classification["by_industry"][industry]["companies"].add(doc.stock_name)
        classification["by_industry"][industry]["documents"].append({
            "stock_name": doc.stock_name,
            "document_name": doc.document_name,
            "document_type": doc.document_type
        })

    def _estimate_download_time(self, doc: DocumentInfo) -> int:
        """估算下载时间（秒）"""
        # 简单的基于文件大小的下载时间估算
        base_time = 10  # 基础时间10秒
        size_factor = doc.file_size / 100000  # 每100KB增加的时间因子

        if doc.document_type == "announcement":
            return base_time + int(size_factor * 0.5)
        elif doc.document_type == "research":
            return base_time + int(size_factor * 1.0)
        elif doc.document_type in ["annual_report", "semi_annual_report"]:
            return base_time + int(size_factor * 1.5)
        else:
            return base_time + int(size_factor * 1.0)

    def _generate_cross_classification(self, classification: Dict[str, Any]) -> Dict[str, Any]:
        """生成交叉分类统计"""
        cross_stats = {
            "company_category_vs_document_type": {},
            "document_type_vs_size": {},
            "industry_vs_difficulty": {}
        }

        # 公司分类 vs 文档类型
        for company_cat in self.company_categories.keys():
            cross_stats["company_category_vs_document_type"][company_cat] = {}
            for doc_type in self.document_types.keys():
                count = 0
                for doc in classification["by_company_category"][company_cat]["documents"]:
                    if doc["document_type"] == doc_type:
                        count += 1
                cross_stats["company_category_vs_document_type"][company_cat][doc_type] = count

        # 文档类型 vs 大小分类
        for doc_type in self.document_types.keys():
            cross_stats["document_type_vs_size"][doc_type] = {}
            for size_cat in ["small", "medium", "large", "xlarge"]:
                count = 0
                for doc in classification["by_document_type"][doc_type]["documents"]:
                    if self._classify_by_size(doc["file_size"]) == size_cat:
                        count += 1
                cross_stats["document_type_vs_size"][doc_type][size_cat] = count

        # 行业 vs 难度
        for industry in classification["by_industry"].keys():
            cross_stats["industry_vs_difficulty"][industry] = {}
            for difficulty in self.difficulty_levels.keys():
                count = 0
                # 这里需要更复杂的逻辑来交叉统计，简化处理
                cross_stats["industry_vs_difficulty"][industry][difficulty] = 0

        return cross_stats

    def generate_classification_report(self) -> str:
        """生成分类报告"""
        if not self.classification_result:
            self.classify_documents()

        report_lines = [
            "# 文档分类体系报告",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 总体统计",
            f"- 总文档数: {self.classification_result['total_documents']}",
            f"- 公司分类数: {len(self.classification_result['by_company_category'])}",
            f"- 文档类型数: {len(self.classification_result['by_document_type'])}",
            "",
            "## 按公司规模分类",
        ]

        for category, data in self.classification_result["by_company_category"].items():
            report_lines.append(f"### {category}")
            report_lines.append(f"- 文档数量: {data['document_count']}")
            report_lines.append(f"- 覆盖公司: {', '.join(data['companies'])}")
            report_lines.append("")

        report_lines.extend([
            "## 按文档类型分类",
        ])

        for doc_type, data in self.classification_result["by_document_type"].items():
            type_info = self.document_types.get(doc_type)
            if type_info:
                type_name = type_info.type_name
            else:
                type_name = doc_type
            report_lines.append(f"### {type_name}")
            report_lines.append(f"- 文档数量: {data['document_count']}")
            report_lines.append(f"- 总大小: {data['total_size'] / 1024:.1f} KB")
            report_lines.append("")

        report_lines.extend([
            "## 按文件大小分类",
        ])

        size_names = {"small": "小文件", "medium": "中文件", "large": "大文件", "xlarge": "超大文件"}
        for size_cat, data in self.classification_result["by_size_category"].items():
            size_name = size_names.get(size_cat, size_cat)
            report_lines.append(f"### {size_name}")
            report_lines.append(f"- 文档数量: {data['document_count']}")
            report_lines.append(f"- 总大小: {data['total_size'] / 1024:.1f} KB")
            report_lines.append("")

        return "\n".join(report_lines)

    def save_classification_result(self, output_file: str = None):
        """保存分类结果"""
        if not self.classification_result:
            self.classify_documents()

        if not output_file:
            output_file = self.base_dir / "document_classification_result.json"

        # 准备可序列化的数据
        serializable_result = self.classification_result.copy()

        # 转换sets为lists
        for industry_data in serializable_result["by_industry"].values():
            if "companies" in industry_data:
                industry_data["companies"] = list(industry_data["companies"])

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_result, f, ensure_ascii=False, indent=2)

        print(f"分类结果已保存到: {output_file}")

        return str(output_file)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='文档分类系统')
    parser.add_argument('--base-dir', default='end2end_test', help='基础目录路径')
    parser.add_argument('--report-only', action='store_true', help='仅生成报告')
    parser.add_argument('--output-file', help='输出文件路径')

    args = parser.parse_args()

    classifier = DocumentClassificationSystem(args.base_dir)

    if args.report_only:
        # 仅生成报告
        report = classifier.generate_classification_report()
        print(report)
        return 0

    # 执行完整分类
    classification = classifier.classify_documents()

    # 保存结果
    output_file = args.output_file or classifier.save_classification_result()

    # 生成报告
    report_file = Path(args.base_dir) / "document_classification_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(classifier.generate_classification_report())

    print(f"分类报告已保存到: {report_file}")

    # 打印简要统计
    print(f"\n=== 分类统计 ===")
    print(f"总文档数: {classification['total_documents']}")
    print(f"公司分类:")
    for category, data in classification["by_company_category"].items():
        print(f"  {category}: {data['document_count']} 个文档")

    print(f"文档类型:")
    for doc_type, data in classification["by_document_type"].items():
        print(f"  {doc_type}: {data['document_count']} 个文档")

    return 0


if __name__ == "__main__":
    sys.exit(main())