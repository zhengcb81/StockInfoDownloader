#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
真实场景测试用例生成器
基于真实文档和分类体系生成测试用例
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from real_document_manager import RealDocumentManager
from document_classification_system import DocumentClassificationSystem


@dataclass
class RealScenarioTestCase:
    """真实场景测试用例"""
    test_id: str
    scenario_name: str
    description: str
    stock_code: str
    stock_name: str
    document_type: str
    keywords: List[str]
    expected_documents: List[str]
    delete_later: bool
    max_pages: int
    timeout_seconds: int
    difficulty_level: str
    business_scenario: str
    test_priority: str
    coverage_dimension: str
    dependencies: List[str]


class RealScenarioTestGenerator:
    """真实场景测试用例生成器"""

    def __init__(self, base_dir: str = "end2end_test"):
        """
        初始化测试用例生成器

        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
        self.document_manager = RealDocumentManager(base_dir)
        self.classification_system = DocumentClassificationSystem(base_dir)

        # 定义业务场景
        self.business_scenarios = {
            "投资者关系活动": {
                "description": "投资者关系部门组织的投资者调研、路演等活动",
                "typical_frequency": "每月1-2次",
                "typical_participants": "机构投资者、分析师",
                "document_types": ["research"]
            },
            "定期报告披露": {
                "description": "公司按照监管要求定期披露的财务和经营报告",
                "typical_frequency": "季度、半年度、年度",
                "typical_participants": "全体投资者",
                "document_types": ["quarterly_report", "semi_annual_report", "annual_report"]
            },
            "重大事项公告": {
                "description": "公司发生的重大事项需要及时向市场公告",
                "typical_frequency": "不定期",
                "typical_participants": "全体投资者",
                "document_types": ["announcement"]
            },
            "业绩预告发布": {
                "description": "公司对未来业绩的预测和预告",
                "typical_frequency": "季度末",
                "typical_participants": "全体投资者",
                "document_types": ["announcement"]
            },
            "股东大会材料": {
                "description": "股东大会相关的议案和材料",
                "typical_frequency": "年度及临时股东大会",
                "typical_participants": "全体股东",
                "document_types": ["announcement", "research"]
            }
        }

        # 定义测试优先级
        self.test_priorities = {
            "P0": "关键业务场景，必须保证",
            "P1": "重要业务场景，优先保证",
            "P2": "一般业务场景，正常保证",
            "P3": "边缘业务场景，有时间保证"
        }

        # 定义覆盖维度
        self.coverage_dimensions = {
            "functional": "功能覆盖 - 验证下载功能正确性",
            "performance": "性能覆盖 - 验证下载速度和稳定性",
            "compatibility": "兼容性覆盖 - 验证不同环境下的表现",
            "reliability": "可靠性覆盖 - 验证异常情况处理",
            "usability": "易用性覆盖 - 验证配置和操作便利性"
        }

    def generate_real_scenario_test_cases(self) -> List[RealScenarioTestCase]:
        """生成真实场景测试用例"""
        print("开始生成真实场景测试用例...")

        # 获取文档分类信息
        try:
            classification = self.classification_system.classify_documents()
        except Exception as e:
            print(f"分类系统运行失败: {e}")
            classification = self._get_fallback_classification()

        print(f"基于 {classification['total_documents']} 个文档生成测试用例")

        test_cases = []

        # 生成核心业务场景测试用例
        core_cases = self._generate_core_business_scenarios(classification)
        test_cases.extend(core_cases)

        # 生成跨分类测试用例
        cross_cases = self._generate_cross_classification_scenarios(classification)
        test_cases.extend(cross_cases)

        # 生成边界情况测试用例
        boundary_cases = self._generate_boundary_scenarios(classification)
        test_cases.extend(boundary_cases)

        # 生成性能测试用例
        performance_cases = self._generate_performance_scenarios(classification)
        test_cases.extend(performance_cases)

        # 去重和优先级排序
        test_cases = self._deduplicate_and_prioritize(test_cases)

        print(f"生成了 {len(test_cases)} 个真实场景测试用例")
        return test_cases

    def _get_fallback_classification(self) -> Dict[str, Any]:
        """获取备用分类信息（当分类系统失败时）"""
        return {
            "total_documents": 3,
            "by_company_category": {
                "中盘股": {
                    "document_count": 3,
                    "companies": ["珂玛科技", "中密控股"],
                    "documents": []
                }
            },
            "by_document_type": {
                "research": {"document_count": 2},
                "quarterly_report": {"document_count": 1}
            },
            "by_size_category": {
                "small": {"document_count": 1},
                "medium": {"document_count": 2}
            }
        }

    def _generate_core_business_scenarios(self, classification: Dict[str, Any]) -> List[RealScenarioTestCase]:
        """生成核心业务场景测试用例"""
        test_cases = []

        # 场景1: 投资者关系活动 - 珂玛科技
        test_cases.append(RealScenarioTestCase(
            test_id="RS001",
            scenario_name="珂玛科技投资者关系活动记录",
            description="测试珂玛科技投资者关系活动记录表的下载和验证",
            stock_code="301611",
            stock_name="珂玛科技",
            document_type="research",
            keywords=["投资者关系管理信息20250725"],
            expected_documents=["珂玛科技：301611珂玛科技投资者关系管理信息20250725.pdf"],
            delete_later=False,
            max_pages=1,
            timeout_seconds=180,
            difficulty_level="容易",
            business_scenario="投资者关系活动",
            test_priority="P0",
            coverage_dimension="functional",
            dependencies=[]
        ))

        # 场景2: 定期报告 - 中密控股季度报告
        test_cases.append(RealScenarioTestCase(
            test_id="RS002",
            scenario_name="中密控股季度报告下载",
            description="测试中密控股季度报告的下载和验证",
            stock_code="300470",
            stock_name="中密控股",
            document_type="quarterly_report",
            keywords=["2025年一季度报告"],
            expected_documents=["中密控股：2025年一季度报告.pdf"],
            delete_later=True,
            max_pages=5,
            timeout_seconds=240,
            difficulty_level="中等",
            business_scenario="定期报告披露",
            test_priority="P0",
            coverage_dimension="functional",
            dependencies=[]
        ))

        # 场景3: 调研活动 - 中密控股历史调研
        test_cases.append(RealScenarioTestCase(
            test_id="RS003",
            scenario_name="中密控股投资者关系活动历史记录",
            description="测试中密控股历史投资者关系活动记录的下载",
            stock_code="300470",
            stock_name="中密控股",
            document_type="research",
            keywords=["2023年1月31日投资者关系活动记录表"],
            expected_documents=["中密控股：2023年1月31日投资者关系活动记录表.pdf"],
            delete_later=True,
            max_pages=3,
            timeout_seconds=300,
            difficulty_level="中等",
            business_scenario="投资者关系活动",
            test_priority="P1",
            coverage_dimension="functional",
            dependencies=[]
        ))

        # 场景4: 大盘股测试 - 平安银行年度报告
        test_cases.append(RealScenarioTestCase(
            test_id="RS004",
            scenario_name="平安银行年度报告下载测试",
            description="测试大盘股平安银行年度报告的下载性能和稳定性",
            stock_code="000001",
            stock_name="平安银行",
            document_type="annual_report",
            keywords=["2023年年度报告"],
            expected_documents=["平安银行：2023年年度报告.pdf"],
            delete_later=True,
            max_pages=2,
            timeout_seconds=360,
            difficulty_level="中等",
            business_scenario="定期报告披露",
            test_priority="P1",
            coverage_dimension="performance",
            dependencies=["RS001"]
        ))

        # 场景5: 房地产公司测试 - 万科A投资者关系
        test_cases.append(RealScenarioTestCase(
            test_id="RS005",
            scenario_name="万科A投资者关系管理信息测试",
            description="测试房地产龙头企业万科A的投资者关系信息下载",
            stock_code="000002",
            stock_name="万科A",
            document_type="research",
            keywords=["投资者关系管理信息20240815"],
            expected_documents=["万科A：投资者关系管理信息20240815.pdf"],
            delete_later=False,
            max_pages=3,
            timeout_seconds=240,
            difficulty_level="中等",
            business_scenario="投资者关系活动",
            test_priority="P1",
            coverage_dimension="compatibility",
            dependencies=[]
        ))

        # 场景6: 半年度报告测试 - 万科A半年度报告
        test_cases.append(RealScenarioTestCase(
            test_id="RS006",
            scenario_name="万科A半年度报告下载测试",
            description="测试万科A半年度报告的下载和内容验证",
            stock_code="000002",
            stock_name="万科A",
            document_type="semi_annual_report",
            keywords=["2024年半年度报告"],
            expected_documents=["万科A：2024年半年度报告.pdf"],
            delete_later=True,
            max_pages=3,
            timeout_seconds=300,
            difficulty_level="中等",
            business_scenario="定期报告披露",
            test_priority="P1",
            coverage_dimension="functional",
            dependencies=["RS005"]
        ))

        return test_cases

    def _generate_cross_classification_scenarios(self, classification: Dict[str, Any]) -> List[RealScenarioTestCase]:
        """生成跨分类测试用例"""
        test_cases = []

        # 场景7: 科技股调研 - 海康威视投资者调研
        test_cases.append(RealScenarioTestCase(
            test_id="RS007",
            scenario_name="海康威视投资者调研纪要下载",
            description="测试安防龙头企业海康威视的投资者调研纪要下载",
            stock_code="002415",
            stock_name="海康威视",
            document_type="research",
            keywords=["2024年8月投资者调研纪要"],
            expected_documents=["海康威视：2024年8月投资者调研纪要.pdf"],
            delete_later=False,
            max_pages=3,
            timeout_seconds=240,
            difficulty_level="中等",
            business_scenario="投资者关系活动",
            test_priority="P1",
            coverage_dimension="functional",
            dependencies=[]
        ))

        # 场景8: 科技股公告 - 海康威视重大事项公告
        test_cases.append(RealScenarioTestCase(
            test_id="RS008",
            scenario_name="海康威视重大事项公告下载",
            description="测试海康威视重大事项公告的及时下载",
            stock_code="002415",
            stock_name="海康威视",
            document_type="announcement",
            keywords=["重大事项"],
            expected_documents=["海康威视：关于重大事项的公告.pdf"],
            delete_later=True,
            max_pages=2,
            timeout_seconds=180,
            difficulty_level="容易",
            business_scenario="重大事项公告",
            test_priority="P2",
            coverage_dimension="reliability",
            dependencies=["RS007"]
        ))

        # 场景9: 小盘股测试 - 诺瓦星云投资者关系
        test_cases.append(RealScenarioTestCase(
            test_id="RS009",
            scenario_name="诺瓦星云投资者关系活动记录",
            description="测试小盘股诺瓦星云投资者关系活动记录下载",
            stock_code="301589",
            stock_name="诺瓦星云",
            document_type="research",
            keywords=["投资者关系活动记录202407"],
            expected_documents=["诺瓦星云：投资者关系活动记录202407.pdf"],
            delete_later=False,
            max_pages=2,
            timeout_seconds=200,
            difficulty_level="中等",
            business_scenario="投资者关系活动",
            test_priority="P2",
            coverage_dimension="compatibility",
            dependencies=[]
        ))

        # 场景10: 小盘股季度报告 - 诺瓦星云季度报告
        test_cases.append(RealScenarioTestCase(
            test_id="RS010",
            scenario_name="诺瓦星云第三季度报告下载",
            description="测试小盘股诺瓦星云季度报告下载",
            stock_code="301589",
            stock_name="诺瓦星云",
            document_type="quarterly_report",
            keywords=["2024年第三季度报告"],
            expected_documents=["诺瓦星云：2024年第三季度报告.pdf"],
            delete_later=True,
            max_pages=3,
            timeout_seconds=280,
            difficulty_level="中等",
            business_scenario="定期报告披露",
            test_priority="P2",
            coverage_dimension="functional",
            dependencies=["RS009"]
        ))

        return test_cases

    def _generate_boundary_scenarios(self, classification: Dict[str, Any]) -> List[RealScenarioTestCase]:
        """生成边界情况测试用例"""
        test_cases = []

        # 场景11: 业绩预告测试 - 平安银行业绩预告
        test_cases.append(RealScenarioTestCase(
            test_id="RS011",
            scenario_name="平安银行业绩预告下载测试",
            description="测试平安银行第一季度业绩预告的及时下载",
            stock_code="000001",
            stock_name="平安银行",
            document_type="announcement",
            keywords=["2024年第一季度业绩预告"],
            expected_documents=["平安银行：2024年第一季度业绩预告.pdf"],
            delete_later=True,
            max_pages=1,
            timeout_seconds=150,
            difficulty_level="容易",
            business_scenario="业绩预告发布",
            test_priority="P2",
            coverage_dimension="reliability",
            dependencies=[]
        ))

        # 场景12: 白酒行业测试 - 五粮液经销商调研
        test_cases.append(RealScenarioTestCase(
            test_id="RS012",
            scenario_name="五粮液经销商调研活动记录",
            description="测试白酒行业龙头五粮液经销商调研活动记录下载",
            stock_code="000858",
            stock_name="五粮液",
            document_type="research",
            keywords=["经销商调研活动记录"],
            expected_documents=["五粮液：经销商调研活动记录.pdf"],
            delete_later=False,
            max_pages=2,
            timeout_seconds=220,
            difficulty_level="中等",
            business_scenario="投资者关系活动",
            test_priority="P2",
            coverage_dimension="usability",
            dependencies=[]
        ))

        # 场景13: 新能源汽车测试 - 比亚迪投资者关系
        test_cases.append(RealScenarioTestCase(
            test_id="RS013",
            scenario_name="比亚迪投资者关系活动记录表",
            description="测试新能源汽车龙头比亚迪投资者关系活动记录",
            stock_code="002594",
            stock_name="比亚迪",
            document_type="research",
            keywords=["2024年投资者关系活动记录表"],
            expected_documents=["比亚迪：2024年投资者关系活动记录表.pdf"],
            delete_later=False,
            max_pages=3,
            timeout_seconds=260,
            difficulty_level="中等",
            business_scenario="投资者关系活动",
            test_priority="P1",
            coverage_dimension="performance",
            dependencies=[]
        ))

        return test_cases

    def _generate_performance_scenarios(self, classification: Dict[str, Any]) -> List[RealScenarioTestCase]:
        """生成性能测试用例"""
        test_cases = []

        # 场景14: 大文件下载测试 - 比亚迪季度报告
        test_cases.append(RealScenarioTestCase(
            test_id="RS014",
            scenario_name="比亚迪第二季度报告大文件下载",
            description="测试大文件(>4MB)的下载性能和稳定性",
            stock_code="002594",
            stock_name="比亚迪",
            document_type="quarterly_report",
            keywords=["2024年第二季度报告"],
            expected_documents=["比亚迪：2024年第二季度报告.pdf"],
            delete_later=True,
            max_pages=4,
            timeout_seconds=400,
            difficulty_level="困难",
            business_scenario="定期报告披露",
            test_priority="P1",
            coverage_dimension="performance",
            dependencies=["RS013"]
        ))

        # 场景15: 多页下载测试 - 平安银行年度报告
        test_cases.append(RealScenarioTestCase(
            test_id="RS015",
            scenario_name="平安银行年度报告多页下载",
            description="测试多页文档的完整下载性能",
            stock_code="000001",
            stock_name="平安银行",
            document_type="annual_report",
            keywords=["2023年年度报告"],
            expected_documents=["平安银行：2023年年度报告.pdf"],
            delete_later=False,
            max_pages=5,
            timeout_seconds=450,
            difficulty_level="困难",
            business_scenario="定期报告披露",
            test_priority="P1",
            coverage_dimension="performance",
            dependencies=["RS004"]
        ))

        return test_cases

    def _deduplicate_and_prioritize(self, test_cases: List[RealScenarioTestCase]) -> List[RealScenarioTestCase]:
        """去重和优先级排序"""
        # 去重（基于stock_code + document_type + keywords）
        seen = set()
        unique_cases = []
        for case in test_cases:
            key = (case.stock_code, case.document_type, tuple(case.keywords))
            if key not in seen:
                seen.add(key)
                unique_cases.append(case)

        # 按优先级排序
        priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        unique_cases.sort(key=lambda x: (priority_order.get(x.test_priority, 4), x.test_id))

        return unique_cases

    def generate_test_config(self, test_cases: List[RealScenarioTestCase]) -> Dict[str, Any]:
        """生成测试配置文件"""
        config = {
            "save_dir": "end2end_test/test_results",
            "expected_result_dir": "end2end_test/expected_results",
            "headless": True,
            "max_retries": 3,
            "use_dynamic_delay": True,
            "download": {
                "human_behavior_delay": 0.5,
                "element_wait": 2,
                "max_retries": 3,
                "max_downloads_per_session": 15
            },
            "max_pages": 5,
            "pagination_wait": 2,
            "timeout_seconds": 600,
            "test_cases": []
        }

        for case in test_cases:
            config_case = {
                "test_id": case.test_id,
                "scenario_name": case.scenario_name,
                "description": case.description,
                "stock_code": case.stock_code,
                "stock_name": case.stock_name,
                "suffix": case.document_type,
                "allowed_keywords": case.keywords,
                "expected_documents": case.expected_documents,
                "max_pages": case.max_pages,
                "delete_later": case.delete_later,
                "timeout_seconds": case.timeout_seconds,
                "difficulty_level": case.difficulty_level,
                "business_scenario": case.business_scenario,
                "test_priority": case.test_priority,
                "coverage_dimension": case.coverage_dimension,
                "dependencies": case.dependencies
            }
            config["test_cases"].append(config_case)

        return config

    def save_test_cases(self, test_cases: List[RealScenarioTestCase], output_dir: str = None):
        """保存测试用例"""
        if not output_dir:
            output_dir = self.base_dir / "real_scenario_tests"

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 保存JSON格式的测试用例
        test_cases_data = [asdict(case) for case in test_cases]
        json_file = output_path / "real_scenario_test_cases.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(test_cases_data, f, ensure_ascii=False, indent=2)

        # 保存测试配置文件
        config = self.generate_test_config(test_cases)
        config_file = output_path / "real_scenario_test_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        # 生成测试用例报告
        report = self._generate_test_cases_report(test_cases)
        report_file = output_path / "real_scenario_test_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"测试用例已保存到: {output_path}")
        print(f"  - 测试用例文件: {json_file}")
        print(f"  - 测试配置文件: {config_file}")
        print(f"  - 测试报告文件: {report_file}")

        return {
            "test_cases_file": str(json_file),
            "config_file": str(config_file),
            "report_file": str(report_file)
        }

    def _generate_test_cases_report(self, test_cases: List[RealScenarioTestCase]) -> str:
        """生成测试用例报告"""
        report_lines = [
            "# 真实场景测试用例报告",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"测试用例总数: {len(test_cases)}",
            "",
            "## 测试用例概述",
            "",
            "### 按优先级分布",
            "",
            "### 按业务场景分布",
            "",
            "### 按覆盖维度分布",
            "",
            "## 详细测试用例",
            ""
        ]

        # 统计分布
        priority_stats = {}
        scenario_stats = {}
        dimension_stats = {}

        for case in test_cases:
            # 优先级统计
            priority_stats[case.test_priority] = priority_stats.get(case.test_priority, 0) + 1
            # 业务场景统计
            scenario_stats[case.business_scenario] = scenario_stats.get(case.business_scenario, 0) + 1
            # 覆盖维度统计
            dimension_stats[case.coverage_dimension] = dimension_stats.get(case.coverage_dimension, 0) + 1

        # 添加统计信息
        report_lines.extend([
            "#### 按优先级分布",
            ""
        ])
        for priority, count in sorted(priority_stats.items()):
            report_lines.append(f"- **{priority}**: {count} 个测试用例")

        report_lines.extend([
            "",
            "#### 按业务场景分布",
            ""
        ])
        for scenario, count in sorted(scenario_stats.items()):
            report_lines.append(f"- **{scenario}**: {count} 个测试用例")

        report_lines.extend([
            "",
            "#### 按覆盖维度分布",
            ""
        ])
        for dimension, count in sorted(dimension_stats.items()):
            report_lines.append(f"- **{dimension}**: {count} 个测试用例")

        # 添加详细测试用例
        report_lines.extend([
            "",
            "## 详细测试用例",
            ""
        ])

        for i, case in enumerate(test_cases, 1):
            report_lines.extend([
                f"### {case.test_id} - {case.scenario_name}",
                f"**描述**: {case.description}",
                f"**股票代码**: {case.stock_code}",
                f"**股票名称**: {case.stock_name}",
                f"**文档类型**: {case.document_type}",
                f"**关键词**: {', '.join(case.keywords)}",
                f"**预期文档**: {', '.join(case.expected_documents)}",
                f"**下载后删除**: {'是' if case.delete_later else '否'}",
                f"**最大页数**: {case.max_pages}",
                f"**超时时间**: {case.timeout_seconds}秒",
                f"**难度等级**: {case.difficulty_level}",
                f"**业务场景**: {case.business_scenario}",
                f"**测试优先级**: {case.test_priority}",
                f"**覆盖维度**: {case.coverage_dimension}",
                f"**依赖关系**: {', '.join(case.dependencies) if case.dependencies else '无'}",
                ""
            ])

        return "\n".join(report_lines)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='真实场景测试用例生成器')
    parser.add_argument('--base-dir', default='end2end_test', help='基础目录路径')
    parser.add_argument('--output-dir', help='输出目录路径')
    parser.add_argument('--count', type=int, default=15, help='目标测试用例数量')

    args = parser.parse_args()

    generator = RealScenarioTestGenerator(args.base_dir)
    test_cases = generator.generate_real_scenario_test_cases()

    # 限制测试用例数量
    if args.count < len(test_cases):
        test_cases = test_cases[:args.count]
        print(f"限制测试用例数量为: {args.count}")

    # 保存测试用例
    result_files = generator.save_test_cases(test_cases, args.output_dir)

    print(f"\n=== 测试用例生成完成 ===")
    print(f"生成了 {len(test_cases)} 个真实场景测试用例")
    print(f"P0级测试用例: {len([c for c in test_cases if c.test_priority == 'P0'])} 个")
    print(f"P1级测试用例: {len([c for c in test_cases if c.test_priority == 'P1'])} 个")
    print(f"P2级测试用例: {len([c for c in test_cases if c.test_priority == 'P2'])} 个")

    return 0


if __name__ == "__main__":
    sys.exit(main())