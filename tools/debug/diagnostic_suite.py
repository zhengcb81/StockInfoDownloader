#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
综合诊断套件 - 系统化故障分析工具
集成网络连接、浏览器初始化、页面导航、文件下载、系统资源诊断
"""

import os
import sys
import time
import json
import socket
import subprocess
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class DiagnosticSuite:
    """综合诊断套件"""

    def __init__(self, config_path: Optional[str] = None):
        """初始化诊断套件"""
        self.config_path = config_path
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "diagnostics": {}
        }

    def run_all_diagnostics(self) -> Dict[str, Any]:
        """运行所有诊断"""
        print("=" * 60)
        print("运行综合诊断套件")
        print("=" * 60)

        # 1. 网络连接诊断
        print("\n1. 网络连接诊断...")
        self.results["diagnostics"]["network"] = self.diagnose_network()

        # 2. 浏览器环境诊断
        print("\n2. 浏览器环境诊断...")
        self.results["diagnostics"]["browser"] = self.diagnose_browser_environment()

        # 3. Python环境诊断
        print("\n3. Python环境诊断...")
        self.results["diagnostics"]["python"] = self.diagnose_python_environment()

        # 4. 文件系统诊断
        print("\n4. 文件系统诊断...")
        self.results["diagnostics"]["filesystem"] = self.diagnose_filesystem()

        # 5. 配置文件诊断
        print("\n5. 配置文件诊断...")
        self.results["diagnostics"]["config"] = self.diagnose_configuration()

        # 6. 外部服务诊断
        print("\n6. 外部服务诊断...")
        self.results["diagnostics"]["external_services"] = self.diagnose_external_services()

        # 生成总结
        self.results["summary"] = self.generate_summary()

        print("\n" + "=" * 60)
        print("诊断完成")
        print("=" * 60)

        return self.results

    def diagnose_network(self) -> Dict[str, Any]:
        """诊断网络连接"""
        result = {
            "connectivity": {},
            "dns": {},
            "latency": {}
        }

        # 测试目标网站连接
        test_hosts = [
            ("www.cninfo.com.cn", "巨潮资讯网"),
            ("www.baidu.com", "百度（参考）"),
            ("8.8.8.8", "Google DNS")
        ]

        for host, description in test_hosts:
            try:
                # DNS解析
                start = time.time()
                ip = socket.gethostbyname(host)
                dns_time = (time.time() - start) * 1000

                # TCP连接测试
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                start = time.time()
                sock.connect((ip, 80))
                connect_time = (time.time() - start) * 1000
                sock.close()

                result["connectivity"][host] = {
                    "status": "success",
                    "ip": ip,
                    "dns_time_ms": round(dns_time, 2),
                    "connect_time_ms": round(connect_time, 2),
                    "description": description
                }

                print(f"  [OK] {description} ({host}) - IP: {ip}, DNS: {dns_time:.1f}ms, 连接: {connect_time:.1f}ms")

            except socket.gaierror as e:
                result["connectivity"][host] = {
                    "status": "dns_error",
                    "error": str(e),
                    "description": description
                }
                print(f"  [FAIL] {description} ({host}) - DNS错误: {e}")
            except socket.timeout as e:
                result["connectivity"][host] = {
                    "status": "timeout",
                    "error": str(e),
                    "description": description
                }
                print(f"  [FAIL] {description} ({host}) - 连接超时")
            except Exception as e:
                result["connectivity"][host] = {
                    "status": "error",
                    "error": str(e),
                    "description": description
                }
                print(f"  [FAIL] {description} ({host}) - 错误: {e}")

        return result

    def diagnose_browser_environment(self) -> Dict[str, Any]:
        """诊断浏览器环境"""
        result = {
            "selenium": {},
            "playwright": {},
            "chrome": {},
            "chromedriver": {}
        }

        # 检查Selenium
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            result["selenium"]["status"] = "available"
            result["selenium"]["version"] = webdriver.__version__
            print(f"  [OK] Selenium: {webdriver.__version__}")
        except ImportError as e:
            result["selenium"]["status"] = "not_available"
            result["selenium"]["error"] = str(e)
            print(f"  [FAIL] Selenium: 未安装 ({e})")

        # 检查Playwright
        try:
            import playwright
            result["playwright"]["status"] = "available"
            result["playwright"]["version"] = playwright.__version__
            print(f"  [OK] Playwright: {playwright.__version__}")
        except ImportError as e:
            result["playwright"]["status"] = "not_available"
            result["playwright"]["error"] = str(e)
            print(f"  [FAIL] Playwright: 未安装 ({e})")

        # 检查Chrome
        try:
            if platform.system() == "Windows":
                # Windows上查找Chrome
                chrome_paths = [
                    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
                ]
                for path in chrome_paths:
                    if os.path.exists(path):
                        result["chrome"]["status"] = "available"
                        result["chrome"]["path"] = path
                        # 尝试获取版本
                        try:
                            version_output = subprocess.check_output(
                                [path, "--version"], stderr=subprocess.STDOUT, text=True
                            )
                            result["chrome"]["version"] = version_output.strip()
                        except:
                            result["chrome"]["version"] = "unknown"
                        break
                else:
                    result["chrome"]["status"] = "not_found"
            else:
                # 其他系统
                try:
                    version_output = subprocess.check_output(
                        ["google-chrome", "--version"], stderr=subprocess.STDOUT, text=True
                    )
                    result["chrome"]["status"] = "available"
                    result["chrome"]["version"] = version_output.strip()
                except:
                    result["chrome"]["status"] = "not_found"

            if result["chrome"].get("status") == "available":
                print(f"  [OK] Chrome: {result['chrome'].get('version', '未知版本')}")
            else:
                print("  [FAIL] Chrome: 未找到")

        except Exception as e:
            result["chrome"]["status"] = "error"
            result["chrome"]["error"] = str(e)
            print(f"  [FAIL] Chrome检查错误: {e}")

        # 检查ChromeDriver
        try:
            if platform.system() == "Windows":
                chromedriver_paths = [
                    "chromedriver.exe",
                    "C:\\Windows\\chromedriver.exe",
                    str(project_root / "chromedriver.exe")
                ]
                for path in chromedriver_paths:
                    if os.path.exists(path):
                        result["chromedriver"]["status"] = "available"
                        result["chromedriver"]["path"] = path
                        break
                else:
                    # 尝试通过PATH查找
                    try:
                        subprocess.run(["chromedriver", "--version"],
                                     capture_output=True, check=True)
                        result["chromedriver"]["status"] = "available_in_path"
                    except:
                        result["chromedriver"]["status"] = "not_found"
            else:
                try:
                    subprocess.run(["chromedriver", "--version"],
                                 capture_output=True, check=True)
                    result["chromedriver"]["status"] = "available"
                except:
                    result["chromedriver"]["status"] = "not_found"

            if result["chromedriver"].get("status") in ["available", "available_in_path"]:
                print("  [OK] ChromeDriver: 可用")
            else:
                print("  [FAIL] ChromeDriver: 未找到")

        except Exception as e:
            result["chromedriver"]["status"] = "error"
            result["chromedriver"]["error"] = str(e)
            print(f"  [FAIL] ChromeDriver检查错误: {e}")

        return result

    def diagnose_python_environment(self) -> Dict[str, Any]:
        """诊断Python环境"""
        result = {
            "packages": {},
            "paths": sys.path[:10],  # 只显示前10个路径
            "environment_vars": {}
        }

        # 检查关键包
        key_packages = [
            "requests", "selenium", "playwright", "pytest",
            "pandas", "numpy", "beautifulsoup4"
        ]

        for package in key_packages:
            try:
                module = __import__(package)
                result["packages"][package] = {
                    "status": "available",
                    "version": getattr(module, "__version__", "unknown")
                }
                print(f"  [OK] {package}: {result['packages'][package]['version']}")
            except ImportError:
                result["packages"][package] = {
                    "status": "not_available"
                }
                print(f"  [FAIL] {package}: 未安装")

        # 检查环境变量
        env_vars = ["PATH", "PYTHONPATH", "TEST_ENV"]
        for var in env_vars:
            value = os.environ.get(var)
            if value:
                result["environment_vars"][var] = "set"
            else:
                result["environment_vars"][var] = "not_set"

        return result

    def diagnose_filesystem(self) -> Dict[str, Any]:
        """诊断文件系统"""
        result = {
            "directories": {},
            "permissions": {},
            "disk_space": {}
        }

        # 检查关键目录
        key_dirs = [
            ("项目根目录", str(project_root)),
            ("测试目录", str(project_root / "end2end_test")),
            ("测试结果目录", str(project_root / "end2end_test" / "test_results")),
            ("预期结果目录", str(project_root / "end2end_test" / "expected_results")),
            ("日志目录", str(project_root / "logs")),
            ("调试标记目录", str(project_root / "logs" / "debug_markers"))
        ]

        for name, path in key_dirs:
            dir_info = {}
            try:
                if os.path.exists(path):
                    dir_info["exists"] = True
                    dir_info["is_dir"] = os.path.isdir(path)
                    dir_info["writable"] = os.access(path, os.W_OK)

                    if dir_info["is_dir"]:
                        # 列出文件数量（最多10个）
                        files = list(Path(path).iterdir())
                        dir_info["file_count"] = len(files)
                        dir_info["sample_files"] = [f.name for f in files[:5]]

                    status = "[OK]" if dir_info["writable"] else "[FAIL]"
                    print(f"  {status} {name}: {path}")
                    if not dir_info["writable"]:
                        print(f"    警告: 目录不可写")
                else:
                    dir_info["exists"] = False
                    print(f"  [FAIL] {name}: 不存在 ({path})")

            except Exception as e:
                dir_info["error"] = str(e)
                print(f"  [FAIL] {name}: 检查错误 ({e})")

            result["directories"][name] = dir_info

        # 检查磁盘空间
        try:
            import shutil
            disk_usage = shutil.disk_usage(project_root)
            result["disk_space"] = {
                "total_gb": round(disk_usage.total / (1024**3), 2),
                "used_gb": round(disk_usage.used / (1024**3), 2),
                "free_gb": round(disk_usage.free / (1024**3), 2),
                "free_percent": round(disk_usage.free / disk_usage.total * 100, 2)
            }
            print(f"  磁盘空间: 总共 {result['disk_space']['total_gb']}GB, "
                  f"可用 {result['disk_space']['free_gb']}GB ({result['disk_space']['free_percent']}%)")
        except Exception as e:
            result["disk_space"]["error"] = str(e)
            print(f"  磁盘空间检查错误: {e}")

        return result

    def diagnose_configuration(self) -> Dict[str, Any]:
        """诊断配置文件"""
        result = {
            "files": {},
            "validation": {}
        }

        # 检查配置文件
        config_files = [
            ("端到端测试配置", "config_end2end_test.json"),
            ("项目配置", "config.json"),
            ("调试配置", "config_debug.json")
        ]

        for name, filename in config_files:
            filepath = project_root / filename
            file_info = {}

            try:
                if filepath.exists():
                    file_info["exists"] = True
                    file_info["size_bytes"] = filepath.stat().st_size
                    file_info["readable"] = os.access(filepath, os.R_OK)

                    # 尝试解析JSON
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = json.load(f)
                        file_info["valid_json"] = True
                        file_info["keys"] = list(content.keys())[:10]  # 只显示前10个键

                        # 特定配置验证
                        if filename == "config_end2end_test.json":
                            if "test_cases" in content:
                                file_info["test_case_count"] = len(content["test_cases"])
                            if "save_dir" in content:
                                file_info["save_dir"] = content["save_dir"]

                    except json.JSONDecodeError as e:
                        file_info["valid_json"] = False
                        file_info["json_error"] = str(e)

                    status = "[OK]" if file_info.get("valid_json", False) else "[FAIL]"
                    print(f"  {status} {name}: {filename} ({file_info['size_bytes']} bytes)")
                    if "test_case_count" in file_info:
                        print(f"    测试用例数: {file_info['test_case_count']}")

                else:
                    file_info["exists"] = False
                    print(f"  [FAIL] {name}: 不存在 ({filename})")

            except Exception as e:
                file_info["error"] = str(e)
                print(f"  [FAIL] {name}: 检查错误 ({e})")

            result["files"][name] = file_info

        return result

    def diagnose_external_services(self) -> Dict[str, Any]:
        """诊断外部服务"""
        result = {
            "services": {}
        }

        # 检查本地服务
        services = [
            ("Chrome浏览器进程", "chrome.exe" if platform.system() == "Windows" else "chrome"),
            ("ChromeDriver进程", "chromedriver.exe" if platform.system() == "Windows" else "chromedriver")
        ]

        for name, process_name in services:
            service_info = {}
            try:
                if platform.system() == "Windows":
                    output = subprocess.run(
                        ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
                        capture_output=True, text=True, check=False
                    )
                    running = process_name in output.stdout
                else:
                    output = subprocess.run(
                        ["pgrep", "-f", process_name],
                        capture_output=True, text=True, check=False
                    )
                    running = output.returncode == 0

                service_info["running"] = running
                if running:
                    print(f"  [WARN] {name}: 正在运行 (可能影响测试)")
                else:
                    print(f"  [OK] {name}: 未运行")

            except Exception as e:
                service_info["error"] = str(e)
                print(f"  [FAIL] {name}: 检查错误 ({e})")

            result["services"][name] = service_info

        return result

    def generate_summary(self) -> Dict[str, Any]:
        """生成诊断总结"""
        summary = {
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "warnings": [],
            "critical_issues": [],
            "recommendations": []
        }

        # 分析网络诊断
        network = self.results["diagnostics"]["network"]["connectivity"]
        for host, info in network.items():
            summary["total_checks"] += 1
            if info.get("status") == "success":
                summary["passed_checks"] += 1
            else:
                summary["failed_checks"] += 1
                if host == "www.cninfo.com.cn":
                    summary["critical_issues"].append(f"无法连接巨潮资讯网: {info.get('error', '未知错误')}")

        # 分析浏览器诊断
        browser = self.results["diagnostics"]["browser"]
        if browser.get("selenium", {}).get("status") != "available":
            summary["critical_issues"].append("Selenium未安装")
        if browser.get("playwright", {}).get("status") != "available":
            summary["warnings"].append("Playwright未安装")
        if browser.get("chrome", {}).get("status") != "available":
            summary["critical_issues"].append("Chrome浏览器未找到")
        if browser.get("chromedriver", {}).get("status") not in ["available", "available_in_path"]:
            summary["critical_issues"].append("ChromeDriver未找到")

        # 分析文件系统诊断
        filesystem = self.results["diagnostics"]["filesystem"]["directories"]
        for name, info in filesystem.items():
            if not info.get("exists", False):
                summary["warnings"].append(f"目录不存在: {name}")
            elif not info.get("writable", False):
                summary["critical_issues"].append(f"目录不可写: {name}")

        # 分析配置诊断
        config = self.results["diagnostics"]["configuration"]["files"]
        for name, info in config.items():
            if not info.get("exists", False) and name == "端到端测试配置":
                summary["critical_issues"].append(f"配置文件不存在: {name}")
            elif not info.get("valid_json", False) and info.get("exists", False):
                summary["critical_issues"].append(f"配置文件格式错误: {name}")

        # 生成建议
        if summary["critical_issues"]:
            summary["recommendations"].append("请先解决关键问题再运行测试")
        elif summary["warnings"]:
            summary["recommendations"].append("建议处理警告问题")
        else:
            summary["recommendations"].append("环境正常，可以运行测试")

        return summary

    def save_report(self, output_path: Optional[str] = None):
        """保存诊断报告"""
        if output_path is None:
            output_path = project_root / "logs" / "diagnostic_reports" / f"diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n诊断报告已保存: {output_path}")

        # 同时生成简版报告
        txt_path = output_path.with_suffix('.txt')
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("综合诊断报告\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"时间: {self.results['timestamp']}\n")
            f.write(f"平台: {self.results['platform']}\n")
            f.write(f"Python版本: {self.results['python_version']}\n\n")

            # 总结部分
            summary = self.results['summary']
            f.write("=" * 60 + "\n")
            f.write("诊断总结\n")
            f.write("=" * 60 + "\n")
            f.write(f"总检查数: {summary['total_checks']}\n")
            f.write(f"通过检查: {summary['passed_checks']}\n")
            f.write(f"失败检查: {summary['failed_checks']}\n\n")

            if summary['critical_issues']:
                f.write("关键问题:\n")
                for issue in summary['critical_issues']:
                    f.write(f"  [FAIL] {issue}\n")
                f.write("\n")

            if summary['warnings']:
                f.write("警告:\n")
                for warning in summary['warnings']:
                    f.write(f"  [WARN] {warning}\n")
                f.write("\n")

            if summary['recommendations']:
                f.write("建议:\n")
                for rec in summary['recommendations']:
                    f.write(f"  → {rec}\n")

        print(f"文本报告已保存: {txt_path}")
        return str(output_path)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='运行综合诊断套件')
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--output', type=str, help='输出报告路径')
    parser.add_argument('--quick', action='store_true', help='快速模式（跳过部分检查）')

    args = parser.parse_args()

    try:
        diagnostic = DiagnosticSuite(config_path=args.config)
        results = diagnostic.run_all_diagnostics()
        diagnostic.save_report(args.output)

        # 根据总结提供建议
        summary = results['summary']
        if summary['critical_issues']:
            print("\n[CRITICAL] 存在关键问题，请先解决:")
            for issue in summary['critical_issues']:
                print(f"   - {issue}")
            sys.exit(1)
        elif summary['warnings']:
            print("\n[WARN] 存在警告问题，建议处理:")
            for warning in summary['warnings']:
                print(f"   - {warning}")
            print("\n[SUCCESS] 环境基本正常，可以运行测试")
            sys.exit(0)
        else:
            print("\n[SUCCESS] 环境检查通过，可以运行测试")
            sys.exit(0)

    except Exception as e:
        print(f"诊断过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()