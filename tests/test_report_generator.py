#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一测试报告生成器
按照TESTING_PROTOCOL.md规范生成各种类型的测试报告
"""

import json
import os
import sys
import platform
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


class TestReportGenerator:
    """统一测试报告生成器"""
    
    def __init__(self, base_dir: str = "test_reports"):
        self.base_dir = Path(base_dir)
        self.ensure_directories()
    
    def ensure_directories(self):
        """确保报告目录存在"""
        for subdir in ["e2e", "unit", "integration", "regression", "summary"]:
            (self.base_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    def get_timestamp(self) -> str:
        """获取标准时间戳"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def get_system_info(self) -> Dict[str, str]:
        """获取系统信息"""
        return {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.platform(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor()
        }
    
    def get_environment_info(self) -> Dict[str, Any]:
        """获取测试环境信息"""
        env_info = self.get_system_info()
        
        # 尝试获取Chrome版本
        try:
            import selenium.webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            service = Service()
            driver = selenium.webdriver.Chrome(service=service, options=options)
            chrome_version = driver.capabilities.get('browserVersion', 'Unknown')
            driver.quit()
            env_info["chrome_version"] = chrome_version
        except Exception:
            env_info["chrome_version"] = "Not available"
        
        # 检查网络连接
        try:
            import requests
            response = requests.get("https://www.cninfo.com.cn", timeout=5)
            env_info["network_status"] = "Connected" if response.status_code == 200 else "Issue"
        except Exception:
            env_info["network_status"] = "Disconnected"
        
        return env_info
    
    def generate_report_filename(self, test_type: str, timestamp: str = None) -> str:
        """生成报告文件名"""
        if timestamp is None:
            timestamp = self.get_timestamp()
        
        return f"{self.base_dir}/{test_type}/{test_type}_report_{timestamp}.json"
    
    def create_e2e_report(self, 
                         test_cases: List[Dict[str, Any]], 
                         results: List[Dict[str, Any]],
                         config_file: str = None,
                         description: str = "端到端测试") -> str:
        """创建端到端测试报告"""
        
        timestamp = self.get_timestamp()
        report_data = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "test_type": "e2e",
                "description": description,
                "config_file": config_file
            },
            "test_environment": self.get_environment_info(),
            "test_data": {
                "test_cases_count": len(test_cases),
                "stock_codes": list(set([case.get("stock_code", "") for case in test_cases])),
                "config_used": config_file is not None
            },
            "results": results,
            "summary": self._calculate_summary(results)
        }
        
        filename = self.generate_report_filename("e2e", timestamp)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def create_unit_report(self,
                         test_results: List[Dict[str, Any]],
                         modules_tested: List[str],
                         description: str = "单元测试") -> str:
        """创建单元测试报告"""
        
        timestamp = self.get_timestamp()
        report_data = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "test_type": "unit",
                "description": description
            },
            "test_environment": self.get_environment_info(),
            "test_data": {
                "modules_tested": modules_tested,
                "total_tests": len(test_results)
            },
            "results": test_results,
            "summary": self._calculate_summary(test_results)
        }
        
        filename = self.generate_report_filename("unit", timestamp)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def create_integration_report(self,
                               test_results: List[Dict[str, Any]],
                               components_tested: List[str],
                               description: str = "集成测试") -> str:
        """创建集成测试报告"""
        
        timestamp = self.get_timestamp()
        report_data = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "test_type": "integration",
                "description": description
            },
            "test_environment": self.get_environment_info(),
            "test_data": {
                "components_tested": components_tested,
                "total_tests": len(test_results)
            },
            "results": test_results,
            "summary": self._calculate_summary(test_results)
        }
        
        filename = self.generate_report_filename("integration", timestamp)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def create_regression_report(self,
                               test_results: List[Dict[str, Any]],
                               bugs_tested: List[str],
                               description: str = "回归测试") -> str:
        """创建回归测试报告"""
        
        timestamp = self.get_timestamp()
        report_data = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "test_type": "regression",
                "description": description
            },
            "test_environment": self.get_environment_info(),
            "test_data": {
                "bugs_tested": bugs_tested,
                "total_tests": len(test_results)
            },
            "results": test_results,
            "summary": self._calculate_summary(test_results)
        }
        
        filename = self.generate_report_filename("regression", timestamp)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def create_summary_report(self,
                            report_files: List[str],
                            description: str = "综合测试报告") -> str:
        """创建综合测试报告"""
        
        timestamp = self.get_timestamp()
        
        # 收集所有报告的数据
        all_results = []
        total_tests = 0
        total_passed = 0
        test_types = set()
        
        for report_file in report_files:
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                
                test_type = report_data.get("test_info", {}).get("test_type", "unknown")
                test_types.add(test_type)
                
                results = report_data.get("results", [])
                all_results.extend(results)
                
                summary = report_data.get("summary", {})
                total_tests += summary.get("total", 0)
                total_passed += summary.get("passed", 0)
                
            except Exception as e:
                print(f"Warning: Could not read report file {report_file}: {e}")
        
        summary_data = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "test_type": "summary",
                "description": description
            },
            "test_environment": self.get_environment_info(),
            "coverage": {
                "test_types": list(test_types),
                "reports_included": len(report_files),
                "report_files": report_files
            },
            "summary": {
                "total": total_tests,
                "passed": total_passed,
                "failed": total_tests - total_passed,
                "success_rate": f"{total_passed/total_tests*100:.1f}%" if total_tests > 0 else "0%"
            }
        }
        
        filename = self.generate_report_filename("summary", timestamp)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def _calculate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算测试结果摘要"""
        total = len(results)
        passed = sum(1 for r in results if r.get("success", False))
        failed = total - passed
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": f"{passed/total*100:.1f}%" if total > 0 else "0%"
        }
    
    def print_report_summary(self, report_file: str):
        """打印报告摘要"""
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            test_info = report_data.get("test_info", {})
            summary = report_data.get("summary", {})
            
            print(f"\n{'='*60}")
            print(f"测试报告摘要")
            print(f"{'='*60}")
            print(f"测试类型: {test_info.get('test_type', 'Unknown')}")
            print(f"测试时间: {test_info.get('timestamp', 'Unknown')}")
            print(f"测试描述: {test_info.get('description', 'No description')}")
            print(f"{'='*60}")
            print(f"总测试数: {summary.get('total', 0)}")
            print(f"通过: {summary.get('passed', 0)}")
            print(f"失败: {summary.get('failed', 0)}")
            print(f"成功率: {summary.get('success_rate', '0%')}")
            print(f"{'='*60}")
            print(f"报告文件: {report_file}")
            
        except Exception as e:
            print(f"无法读取报告文件: {e}")


def main():
    """测试报告生成器示例用法"""
    generator = TestReportGenerator()
    
    # 示例：创建端到端测试报告
    sample_results = [
        {"downloader": "new", "stock_code": "300470", "success": True, "duration": 45.2},
        {"downloader": "old", "stock_code": "300470", "success": True, "duration": 52.1},
        {"downloader": "new", "stock_code": "301611", "success": False, "duration": 30.5, "error": "Network timeout"}
    ]
    
    sample_test_cases = [
        {"stock_code": "300470", "suffix": "research", "delete_later": True},
        {"stock_code": "301611", "suffix": "periodicReports", "delete_later": False}
    ]
    
    print("生成示例测试报告...")
    
    # 生成端到端测试报告
    e2e_report = generator.create_e2e_report(
        test_cases=sample_test_cases,
        results=sample_results,
        config_file="config_end2end_test.json",
        description="示例端到端测试"
    )
    
    # 生成单元测试报告
    unit_report = generator.create_unit_report(
        test_results=[
            {"module": "mapping", "test": "org_id_mapping", "success": True},
            {"module": "file_utils", "test": "filename_cleaning", "success": True},
            {"module": "config", "test": "config_parsing", "success": False, "error": "Invalid JSON"}
        ],
        modules_tested=["mapping", "file_utils", "config"],
        description="示例单元测试"
    )
    
    # 生成综合报告
    summary_report = generator.create_summary_report(
        report_files=[e2e_report, unit_report],
        description="示例综合测试报告"
    )
    
    # 打印报告摘要
    generator.print_report_summary(summary_report)
    
    print(f"\n生成的报告文件:")
    print(f"- 端到端测试报告: {e2e_report}")
    print(f"- 单元测试报告: {unit_report}")
    print(f"- 综合测试报告: {summary_report}")
    
    # 测试新的CI/CD报告方法
    print("\n测试CI/CD报告生成...")
    
    # 测试综合报告
    comprehensive_report = generator.create_comprehensive_report(
        reports=[e2e_report, unit_report],
        description="CI/CD综合测试报告"
    )
    print(f"- 综合报告: {comprehensive_report}")
    
    # 测试发布报告
    release_report = generator.create_release_report(
        test_results="reports/*.json",
        coverage_data="coverage.xml",
        security_data="security-scan.json",
        quality_data="flake8-report.json",
        description="发布测试报告"
    )
    print(f"- 发布报告: {release_report}")
    
    # 测试HTML汇总报告
    html_summary = generator.generate_test_summary(
        workflow_name="CI/CD Pipeline",
        run_id="12345",
        run_number="678"
    )
    print(f"- HTML汇总报告: {html_summary}")


if __name__ == "__main__":
    main()