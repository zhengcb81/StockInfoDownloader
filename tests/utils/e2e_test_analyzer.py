#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
端到端测试结果分析器
分析真实环境下的测试结果，区分网络问题、网站变更和代码缺陷
"""

import json
import logging
import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """失败类型枚举"""

    NETWORK_ERROR = "network_error"  # 网络问题
    WEBSITE_CHANGE = "website_change"  # 网站变更
    CODE_DEFECT = "code_defect"  # 代码缺陷
    TIMEOUT = "timeout"  # 超时
    EXTERNAL_SERVICE = "external_service"  # 外部服务问题
    UNKNOWN = "unknown"  # 未知原因


class E2EResultCategory:
    """测试结果分类"""

    def __init__(
        self,
        test_name: str,
        success: bool,
        duration: float,
        error: Optional[str] = None,
    ):
        self.test_name = test_name
        self.success = success
        self.duration = duration
        self.error = error
        self.failure_type = FailureType.UNKNOWN if not success else None
        self.timestamp = datetime.now().isoformat()
        self.stock_code = self._extract_stock_code(test_name)
        self.suggested_fix = None
        self.confidence = 0.0  # 分类置信度

    def _extract_stock_code(self, test_name: str) -> Optional[str]:
        """从测试名称中提取股票代码"""
        match = re.search(r"(\d{6})", test_name)
        return match.group(1) if match else None


class E2ETestAnalyzer:
    """端到端测试结果分析器"""

    def __init__(self):
        self.failure_patterns = self._initialize_failure_patterns()
        self.website_change_indicators = self._initialize_website_patterns()
        self.network_error_patterns = self._initialize_network_patterns()
        self.results = []

    def generate_report(self) -> str:
        """生成并保存报告，返回报告路径"""
        analysis = self.analyze_batch(self.results)
        report_path = (
            f"e2e_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        self.export_report(analysis, report_path)
        return report_path

    def get_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        analysis = self.analyze_batch(self.results)
        return analysis.get(
            "summary", {"total_tests": 0, "successful_tests": 0, "failed_tests": 0}
        )

    def add_result(
        self,
        test_name: str,
        success: bool,
        duration: float,
        error: Optional[str] = None,
    ):
        """添加测试结果"""
        self.results.append(
            {
                "test_name": test_name,
                "success": success,
                "duration": duration,
                "error": error,
            }
        )

    def _initialize_failure_patterns(self) -> Dict[str, FailureType]:
        """初始化失败模式识别规则"""
        return {
            # 网络相关错误
            r".*timeout.*": FailureType.TIMEOUT,
            r".*connection.*refused.*": FailureType.NETWORK_ERROR,
            r".*connection.*reset.*": FailureType.NETWORK_ERROR,
            r".*network.*unreachable.*": FailureType.NETWORK_ERROR,
            r".*dns.*": FailureType.NETWORK_ERROR,
            r".*ssl.*error.*": FailureType.NETWORK_ERROR,
            r".*certificate.*": FailureType.NETWORK_ERROR,
            r".*proxy.*error.*": FailureType.NETWORK_ERROR,
            # 网站变更相关错误
            r".*element.*not.*found.*": FailureType.WEBSITE_CHANGE,
            r".*no.*such.*element.*": FailureType.WEBSITE_CHANGE,
            r".*xpath.*not.*found.*": FailureType.WEBSITE_CHANGE,
            r".*selector.*not.*found.*": FailureType.WEBSITE_CHANGE,
            r".*stale.*element.*reference.*": FailureType.WEBSITE_CHANGE,
            r".*unable.*to.*locate.*": FailureType.WEBSITE_CHANGE,
            r".*page.*structure.*": FailureType.WEBSITE_CHANGE,
            r".*404.*not.*found.*": FailureType.WEBSITE_CHANGE,
            r".*503.*service.*unavailable.*": FailureType.WEBSITE_CHANGE,
            r".*url.*not.*found.*": FailureType.WEBSITE_CHANGE,
            # 代码缺陷相关错误
            r".*index.*out.*of.*range.*": FailureType.CODE_DEFECT,
            r".*key.*error.*": FailureType.CODE_DEFECT,
            r".*attribute.*error.*": FailureType.CODE_DEFECT,
            r".*type.*error.*": FailureType.CODE_DEFECT,
            r".*value.*error.*": FailureType.CODE_DEFECT,
            r".*none.*type.*": FailureType.CODE_DEFECT,
            r".*assertion.*error.*": FailureType.CODE_DEFECT,
            r".*logic.*error.*": FailureType.CODE_DEFECT,
            # 超时
            r".*time.*out.*": FailureType.TIMEOUT,
            r".*exceeded.*max.*time.*": FailureType.TIMEOUT,
            r".*wait.*timeout.*": FailureType.TIMEOUT,
            # 外部服务
            r".*external.*service.*": FailureType.EXTERNAL_SERVICE,
            r".*third.*party.*": FailureType.EXTERNAL_SERVICE,
            r".*api.*error.*": FailureType.EXTERNAL_SERVICE,
        }

    def _initialize_website_patterns(self) -> List[str]:
        """初始化网站变更指示器"""
        return [
            "element not found",
            "no such element",
            "xpath not found",
            "selector not found",
            "stale element reference",
            "unable to locate",
            "page structure",
            "404 not found",
            "page not found",
            "url changed",
            "redirected",
            "structure changed",
        ]

    def _initialize_network_patterns(self) -> List[str]:
        """初始化网络错误指示器"""
        return [
            "timeout",
            "connection refused",
            "connection reset",
            "network unreachable",
            "dns error",
            "ssl error",
            "certificate error",
            "proxy error",
            "connection error",
        ]

    def analyze_result(
        self,
        test_name: str,
        success: bool,
        duration: float,
        error_message: Optional[str] = None,
        stack_trace: Optional[str] = None,
    ) -> E2EResultCategory:
        """分析单个测试结果"""
        result = E2EResultCategory(test_name, success, duration, error_message)

        if not success and error_message:
            self._classify_failure(result, error_message, stack_trace)

        return result

    def _classify_failure(
        self,
        result: E2EResultCategory,
        error_message: str,
        stack_trace: Optional[str] = None,
    ):
        """分类失败原因"""
        error_lower = error_message.lower()
        stack_lower = stack_trace.lower() if stack_trace else ""
        combined_text = f"{error_lower} {stack_lower}"

        max_confidence = 0.0
        best_match = FailureType.UNKNOWN

        # 使用模式匹配
        for pattern, failure_type in self.failure_patterns.items():
            if re.search(pattern, combined_text, re.IGNORECASE):
                # 计算置信度（基于匹配长度）
                match = re.search(pattern, combined_text, re.IGNORECASE)
                if match:
                    confidence = (
                        len(match.group(0)) / len(error_lower)
                        if len(error_lower) > 0
                        else 0.5
                    )
                    if confidence > max_confidence:
                        max_confidence = confidence
                        best_match = failure_type

        result.failure_type = best_match
        result.confidence = max_confidence

        # 生成修复建议
        result.suggested_fix = self._generate_fix_suggestion(result)

    def _generate_fix_suggestion(self, result: E2EResultCategory) -> Optional[str]:
        """生成修复建议"""
        suggestions = {
            FailureType.NETWORK_ERROR: "检查网络连接，考虑使用重试机制或代理",
            FailureType.WEBSITE_CHANGE: "检查网站页面结构，更新XPath或选择器",
            FailureType.CODE_DEFECT: "检查代码逻辑，添加错误处理和边界检查",
            FailureType.TIMEOUT: "增加超时时间或优化等待逻辑",
            FailureType.EXTERNAL_SERVICE: "检查外部服务状态，考虑降级方案",
            FailureType.UNKNOWN: "需要进一步调查失败原因",
        }
        return suggestions.get(result.failure_type, "未知原因，需要调查")

    def analyze_batch(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量分析测试结果"""
        analyzed_results = []
        failure_stats = {failure_type: 0 for failure_type in FailureType}

        for result_data in test_results:
            test_name = result_data.get("test_name", "unknown")
            success = result_data.get("success", False)
            duration = result_data.get("duration", 0.0)
            error = result_data.get("error")
            stack_trace = result_data.get("stack_trace")

            analyzed = self.analyze_result(
                test_name, success, duration, error, stack_trace
            )
            analyzed_results.append(analyzed)

            if not success:
                failure_stats[analyzed.failure_type] += 1

        return {
            "analyzed_results": analyzed_results,
            "failure_statistics": failure_stats,
            "summary": self._generate_summary(analyzed_results, failure_stats),
        }

    def _generate_summary(
        self, results: List[E2EResultCategory], failure_stats: Dict[FailureType, int]
    ) -> Dict[str, Any]:
        """生成分析摘要"""
        total = len(results)
        passed = sum(1 for r in results if r.success)
        failed = total - passed

        # 按失败类型统计
        failure_by_type = {
            failure_type.value: count
            for failure_type, count in failure_stats.items()
            if count > 0
        }

        # 计算成功率
        success_rate = (passed / total * 100) if total > 0 else 0

        # 识别问题股票代码
        problematic_stocks = {}
        for result in results:
            if not result.success and result.stock_code:
                if result.stock_code not in problematic_stocks:
                    problematic_stocks[result.stock_code] = {
                        "failure_count": 0,
                        "failure_types": set(),
                    }
                problematic_stocks[result.stock_code]["failure_count"] += 1
                if result.failure_type:
                    problematic_stocks[result.stock_code]["failure_types"].add(
                        result.failure_type.value
                    )

        # 转换为可序列化的格式
        for stock in problematic_stocks.values():
            stock["failure_types"] = list(stock["failure_types"])

        return {
            "total_tests": total,
            "passed_tests": passed,
            "successful_tests": passed,
            "failed_tests": failed,
            "success_rate": round(success_rate, 2),
            "failure_by_type": failure_by_type,
            "problematic_stocks": problematic_stocks,
            "analysis_timestamp": datetime.now().isoformat(),
        }

    def generate_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        summary = analysis_results.get("summary", {})
        failure_stats = analysis_results.get("failure_statistics", {})

        total_failures = summary.get("failed_tests", 0)

        if total_failures == 0:
            recommendations.append("✅ 所有测试通过，无需改进")
            return recommendations

        # 按失败类型给出建议
        for failure_type, count in failure_stats.items():
            if count == 0:
                continue

            percentage = (count / total_failures) * 100

            if failure_type == FailureType.NETWORK_ERROR:
                recommendations.append(
                    f"🔧 网络错误 ({percentage:.1f}%): 考虑实现重试机制、使用代理或优化网络配置"
                )
            elif failure_type == FailureType.WEBSITE_CHANGE:
                recommendations.append(
                    f"🔧 网站变更 ({percentage:.1f}%): 需要更新页面元素选择器，建议定期检查网站结构"
                )
            elif failure_type == FailureType.CODE_DEFECT:
                recommendations.append(
                    f"🐛 代码缺陷 ({percentage:.1f}%): 需要修复代码逻辑错误，添加更多的边界检查"
                )
            elif failure_type == FailureType.TIMEOUT:
                recommendations.append(
                    f"⏱️ 超时问题 ({percentage:.1f}%): 增加超时时间或优化等待策略"
                )
            elif failure_type == FailureType.EXTERNAL_SERVICE:
                recommendations.append(
                    f"🌐 外部服务问题 ({percentage:.1f}%): 检查外部服务状态，实现降级方案"
                )

        # 一般性建议
        if total_failures > 0:
            recommendations.append("📊 建议定期运行这些测试以监控稳定性")
            recommendations.append("📝 记录常见问题及其解决方案")

        return recommendations

    def export_report(self, analysis_results: Dict[str, Any], output_file: str):
        """导出分析报告"""
        # 转换E2EResultCategory对象为可序列化的字典
        results_data = []
        for result in analysis_results["analyzed_results"]:
            results_data.append(
                {
                    "test_name": result.test_name,
                    "success": result.success,
                    "duration": result.duration,
                    "error": result.error,
                    "failure_type": (
                        result.failure_type.value if result.failure_type else None
                    ),
                    "stock_code": result.stock_code,
                    "suggested_fix": result.suggested_fix,
                    "confidence": result.confidence,
                    "timestamp": result.timestamp,
                }
            )

        report_data = {
            "analysis_info": {
                "timestamp": datetime.now().isoformat(),
                "analyzer_version": "1.0.0",
            },
            "summary": analysis_results["summary"],
            "failure_statistics": {
                failure_type.value: count
                for failure_type, count in analysis_results[
                    "failure_statistics"
                ].items()
            },
            "detailed_results": results_data,
            "recommendations": self.generate_recommendations(analysis_results),
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        logger.info(f"分析报告已保存到: {output_file}")


def create_sample_analysis():
    """创建示例分析数据"""
    analyzer = E2ETestAnalyzer()

    # 模拟测试结果
    sample_results = [
        {
            "test_name": "test_download_stock_000001",
            "success": True,
            "duration": 45.2,
            "error": None,
        },
        {
            "test_name": "test_download_stock_300470",
            "success": False,
            "duration": 30.5,
            "error": "TimeoutException: Connection timeout after 30 seconds",
        },
        {
            "test_name": "test_download_stock_600000",
            "success": False,
            "duration": 15.3,
            "error": "NoSuchElementException: Unable to locate element: //div[@class='content']",
        },
        {
            "test_name": "test_download_stock_000002",
            "success": False,
            "duration": 2.1,
            "error": "IndexError: list index out of range",
        },
        {
            "test_name": "test_download_stock_601398",
            "success": False,
            "duration": 60.0,
            "error": "TimeoutException: Page load timeout",
        },
    ]

    analysis_results = analyzer.analyze_batch(sample_results)

    # 打印摘要
    summary = analysis_results["summary"]
    print(f"\n{'='*60}")
    print("端到端测试结果分析")
    print(f"{'='*60}")
    print(f"总测试数: {summary['total_tests']}")
    print(f"通过: {summary['passed_tests']}")
    print(f"失败: {summary['failed_tests']}")
    print(f"成功率: {summary['success_rate']:.1f}%")
    print(f"{'='*60}")

    if summary["failed_tests"] > 0:
        print("\n失败类型分布:")
        for failure_type, count in summary["failure_by_type"].items():
            percentage = (count / summary["failed_tests"]) * 100
            print(f"  {failure_type}: {count} ({percentage:.1f}%)")

        print(f"\n{'='*60}")
        print("改进建议:")
        for rec in analysis_results.get("recommendations", []):
            print(f"  {rec}")

    print(f"{'='*60}\n")

    return analysis_results


if __name__ == "__main__":
    print("测试端到端测试结果分析器...")
    create_sample_analysis()
