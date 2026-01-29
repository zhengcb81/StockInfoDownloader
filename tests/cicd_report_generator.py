#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CI/CD测试报告扩展
为GitHub Actions工作流提供专门的报告生成功能
"""

import glob
import json
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from tests.unit.test_report_generator import TestReportGenerator


class CICDReportGenerator(TestReportGenerator):
    """CI/CD专用报告生成器"""

    def __init__(self, base_dir: str = "test_reports"):
        super().__init__(base_dir)
        # 确保CI/CD特定的目录存在
        for subdir in ["ci_cd", "release", "comprehensive"]:
            (self.base_dir / subdir).mkdir(parents=True, exist_ok=True)

    def create_comprehensive_report(
        self, reports: List[str], description: str = "综合测试报告"
    ) -> str:
        """创建综合测试报告"""
        timestamp = self.get_timestamp()
        report_data = {
            "report_info": {
                "timestamp": datetime.now().isoformat(),
                "report_type": "comprehensive",
                "description": description,
                "generated_by": "CICDReportGenerator",
            },
            "environment": self.get_environment_info(),
            "reports_summary": [],
            "combined_summary": {
                "total_reports": len(reports),
                "total_tests": 0,
                "total_passed": 0,
                "total_failed": 0,
                "overall_success_rate": 0.0,
            },
        }

        total_tests = 0
        total_passed = 0
        total_failed = 0

        # 分析所有报告
        for report_file in reports:
            try:
                with open(report_file, "r", encoding="utf-8") as f:
                    report_content = json.load(f)

                summary = report_content.get("summary", {})
                report_summary = {
                    "report_file": report_file,
                    "test_type": report_content.get("test_info", {}).get(
                        "test_type", "Unknown"
                    ),
                    "total_tests": summary.get("total_tests", 0),
                    "passed_tests": summary.get("passed_tests", 0),
                    "failed_tests": summary.get("failed_tests", 0),
                    "success_rate": summary.get("success_rate", 0),
                    "execution_time": summary.get("execution_time", 0),
                }

                report_data["reports_summary"].append(report_summary)
                total_tests += summary.get("total_tests", 0)
                total_passed += summary.get("passed_tests", 0)
                total_failed += summary.get("failed_tests", 0)

            except Exception as e:
                print(f"读取报告失败 {report_file}: {e}")

        # 计算总体统计
        report_data["combined_summary"]["total_tests"] = total_tests
        report_data["combined_summary"]["total_passed"] = total_passed
        report_data["combined_summary"]["total_failed"] = total_failed
        report_data["combined_summary"]["overall_success_rate"] = (
            (total_passed / total_tests * 100) if total_tests > 0 else 0
        )

        # 保存综合报告
        report_file = (
            self.base_dir / "comprehensive" / f"comprehensive_report_{timestamp}.json"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        return str(report_file)

    def create_release_report(
        self,
        test_results: str,
        coverage_data: str,
        security_data: str,
        quality_data: str,
        description: str = "发布测试报告",
    ) -> str:
        """创建发布测试报告"""
        timestamp = self.get_timestamp()
        report_data = {
            "release_info": {
                "timestamp": datetime.now().isoformat(),
                "report_type": "release",
                "description": description,
                "version": "1.0.0",  # 可以从配置或版本文件获取
            },
            "environment": self.get_environment_info(),
            "test_results": self._load_json_files(test_results),
            "coverage": self._load_coverage_data(coverage_data),
            "security": self._load_security_data(security_data),
            "quality": self._load_quality_data(quality_data),
            "release_readiness": {
                "tests_passing": False,
                "coverage adequate": False,
                "security_passing": False,
                "quality_passing": False,
                "overall_ready": False,
            },
        }

        # 评估发布就绪状态
        self._evaluate_release_readiness(report_data)

        # 保存发布报告
        report_file = self.base_dir / "release" / f"release_report_{timestamp}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        return str(report_file)

    def generate_test_summary(
        self, workflow_name: str, run_id: str, run_number: str
    ) -> str:
        """生成测试汇总报告（HTML格式）"""
        timestamp = self.get_timestamp()

        # 收集所有测试结果
        all_reports = glob.glob(str(self.base_dir / "**" / "*.json"), recursive=True)

        # 生成HTML报告
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>测试汇总报告 - {workflow_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; }}
                .test-results {{ margin: 20px 0; }}
                .test-result {{ margin: 10px 0; padding: 10px; border-radius: 3px; }}
                .pass {{ background-color: #d4edda; }}
                .fail {{ background-color: #f8d7da; }}
                .metrics {{ display: flex; gap: 20px; }}
                .metric {{ background-color: #e9ecef; padding: 10px; border-radius: 3px; }}
                .report-section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>测试汇总报告</h1>
                <p>工作流: {workflow_name}</p>
                <p>运行ID: {run_id}</p>
                <p>运行编号: {run_number}</p>
                <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <h2>测试概览</h2>
                <div class="metrics">
                    <div class="metric">
                        <h3>报告文件数</h3>
                        <p>{len(all_reports)}</p>
                    </div>
                    <div class="metric">
                        <h3>测试类型</h3>
                        <p>单元测试、集成测试、端到端测试、回归测试</p>
                    </div>
                    <div class="metric">
                        <h3>环境</h3>
                        <p>{platform.system()} {platform.release()}</p>
                    </div>
                    <div class="metric">
                        <h3>Python版本</h3>
                        <p>{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}</p>
                    </div>
                </div>
            </div>
            
            <div class="report-section">
                <h2>测试报告文件</h2>
                <ul>
        """

        # 添加报告文件列表
        for report_file in sorted(all_reports):
            relative_path = Path(report_file).relative_to(self.base_dir)
            html_content += f'<li><a href="{relative_path}">{relative_path}</a></li>'

        html_content += """
                </ul>
            </div>
            
            <div class="test-results">
                <h2>测试结果详情</h2>
                <div id="test-results-list">
                    <!-- 测试结果将在这里动态生成 -->
                </div>
            </div>
        </body>
        </html>
        """

        # 保存HTML报告
        report_file = self.base_dir / "ci_cd" / f"test_summary_{timestamp}.html"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(report_file)

    def _load_json_files(self, pattern: str) -> List[Dict]:
        """加载匹配模式的JSON文件"""
        results = []
        for file_path in glob.glob(pattern):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    results.append(json.load(f))
            except Exception as e:
                print(f"加载文件失败 {file_path}: {e}")
        return results

    def _load_coverage_data(self, coverage_file: str) -> Dict:
        """加载覆盖率数据"""
        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(coverage_file)
            root = tree.getroot()

            # 解析覆盖率数据
            coverage_data = {
                "line_coverage": 0.0,
                "branch_coverage": 0.0,
                "total_lines": 0,
                "covered_lines": 0,
            }

            # 这里需要根据实际的coverage XML格式进行解析
            # 简化的解析逻辑
            for counter in root.findall(".//counter"):
                if counter.get("type") == "LINE":
                    coverage_data["covered_lines"] = int(counter.get("covered", 0))
                    coverage_data["total_lines"] = (
                        int(counter.get("missed", 0)) + coverage_data["covered_lines"]
                    )
                    coverage_data["line_coverage"] = (
                        coverage_data["covered_lines"]
                        / coverage_data["total_lines"]
                        * 100
                        if coverage_data["total_lines"] > 0
                        else 0
                    )

            return coverage_data
        except Exception as e:
            print(f"加载覆盖率数据失败: {e}")
            return {"error": str(e)}

    def _load_security_data(self, security_file: str) -> Dict:
        """加载安全扫描数据"""
        try:
            with open(security_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载安全数据失败: {e}")
            return {"error": str(e)}

    def _load_quality_data(self, quality_file: str) -> Dict:
        """加载代码质量数据"""
        try:
            with open(quality_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载质量数据失败: {e}")
            return {"error": str(e)}

    def _evaluate_release_readiness(self, report_data: Dict):
        """评估发布就绪状态"""
        readiness = report_data["release_readiness"]

        # 测试通过率检查
        test_summary = report_data.get("combined_summary", {})
        if test_summary.get("overall_success_rate", 0) >= 95:
            readiness["tests_passing"] = True

        # 覆盖率检查
        coverage = report_data.get("coverage", {})
        if coverage.get("line_coverage", 0) >= 80:
            readiness["coverage adequate"] = True

        # 安全检查
        security = report_data.get("security", {})
        if isinstance(security, dict) and not security.get("errors", []):
            readiness["security_passing"] = True

        # 质量检查
        quality = report_data.get("quality", {})
        if isinstance(quality, dict) and not quality.get("errors", []):
            readiness["quality_passing"] = True

        # 总体评估
        readiness["overall_ready"] = all(
            [
                readiness["tests_passing"],
                readiness["coverage adequate"],
                readiness["security_passing"],
                readiness["quality_passing"],
            ]
        )


def main():
    """CI/CD报告生成器测试"""
    print("测试CI/CD报告生成器...")

    generator = CICDReportGenerator()

    # 测试综合报告
    sample_reports = [
        "test_reports/e2e/sample_e2e_report.json",
        "test_reports/unit/sample_unit_report.json",
    ]

    comprehensive_report = generator.create_comprehensive_report(
        reports=sample_reports, description="CI/CD综合测试报告"
    )
    print(f"综合报告: {comprehensive_report}")

    # 测试发布报告
    release_report = generator.create_release_report(
        test_results="test_reports/**/*.json",
        coverage_data="coverage.xml",
        security_data="security-scan.json",
        quality_data="flake8-report.json",
        description="发布测试报告",
    )
    print(f"发布报告: {release_report}")

    # 测试HTML汇总报告
    html_summary = generator.generate_test_summary(
        workflow_name="CI/CD Pipeline", run_id="12345", run_number="678"
    )
    print(f"HTML汇总报告: {html_summary}")


if __name__ == "__main__":
    main()
