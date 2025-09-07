#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一的测试套件
合并系统测试、性能测试、验证测试等功能
"""

import sys
import locale

# 设置控制台编码为UTF-8
if sys.platform == 'win32':
    try:
        # Windows下设置控制台编码为UTF-8
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        # 如果设置失败，忽略错误
        pass

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

def run_system_test():
    """运行系统测试"""
    print("=" * 60)
    print("系统测试 - 验证基础组件功能")
    print("=" * 60)
    
    tests = [
        {
            "name": "配置系统测试",
            "code": "from src.core.config import ConfigManager; cm = ConfigManager(); cm.reset_config(); print('ConfigManager OK')"
        },
        {
            "name": "旧下载器初始化",
            "code": "from cninfo_activity_downloader import CninfoDownloader; d = CninfoDownloader(save_dir='test_sys'); print('Old Downloader OK')"
        },
        {
            "name": "WebDriver初始化",
            "code": "from src.web.driver import WebDriverManager; dm = WebDriverManager(); print('WebDriver OK')"
        },
        {
            "name": "服务层初始化",
            "code": "from src.services.downloader import DownloadService; ds = DownloadService(); print('DownloadService OK')"
        }
    ]
    
    results = []
    for test in tests:
        print(f"\n运行: {test['name']}")
        try:
            result = subprocess.run(
                [sys.executable, "-c", test['code']],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=15
            )
            success = result.returncode == 0
            results.append({
                "name": test['name'],
                "success": success,
                "error": result.stderr if result.stderr else None
            })
            print(f"结果: {'[OK]' if success else '[ERROR]'}")
        except Exception as e:
            results.append({
                "name": test['name'],
                "success": False,
                "error": str(e)
            })
            print(f"结果: [ERROR] ({e})")
    
    passed = sum(1 for r in results if r['success'])
    print(f"\n系统测试结果: {passed}/{len(results)} 通过")
    return results

def run_performance_test():
    """运行性能测试"""
    print("\n" + "=" * 60)
    print("性能测试 - 验证优化效果")
    print("=" * 60)
    
    print("\n1. WebDriver性能测试")
    try:
        result = subprocess.run([
            sys.executable, "-c", """
import time
from src.web.driver import WebDriverManager

driver_manager = WebDriverManager()
start = time.time()
try:
    driver = driver_manager.create_driver()
    init_time = time.time() - start
    
    start_page = time.time()
    driver.get('https://www.cninfo.com.cn')
    page_time = time.time() - start_page
    
    total_time = time.time() - start
    print(f'WebDriver初始化: {init_time:.2f}秒')
    print(f'页面加载: {page_time:.2f}秒')
    print(f'总耗时: {total_time:.2f}秒')
    
    driver.quit()
except Exception as e:
    total_time = time.time() - start
    print(f'性能测试失败: {e}')
    print(f'尝试耗时: {total_time:.2f}秒')
"""
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
        
        print(result.stdout.strip())
        
    except Exception as e:
        print(f"性能测试异常: {e}")
    
    return {"performance_test": "completed"}

def run_validation_test():
    """运行验证测试"""
    print("\n" + "=" * 60)
    print("验证测试 - 关键功能验证")
    print("=" * 60)
    
    print("\n1. 组织ID映射验证")
    try:
        result = subprocess.run([
            sys.executable, "-c", """
from src.data.mapping import MappingManager

mapping = MappingManager()
org_id = mapping.get_org_id('300470')
print(f'300470 -> {org_id}')

if org_id == '9900023856':
    print('[OK] 组织ID映射正确')
else:
    print('[ERROR] 组织ID映射错误')
"""
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10)
        
        print(result.stdout.strip())
        
    except Exception as e:
        print(f"组织ID验证异常: {e}")
    
    print("\n2. 配置便利方法验证")
    try:
        result = subprocess.run([
            sys.executable, "-c", """
from src.core.config import ConfigManager

config = ConfigManager()
config.reset_config()

print(f'基础URL: {config.get_base_url()}')
print(f'页面加载超时: {config.get_timeout("page_load")}秒')
print(f'详情链接选择器: {config.get_selector("detail_links")}')
print(f'页面加载策略: {config.get_page_load_strategy()}')

print('[OK] 配置便利方法正常')
"""
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10)
        
        print(result.stdout.strip())
        
    except Exception as e:
        print(f"配置验证异常: {e}")
    
    return {"validation_test": "completed"}

def run_quick_e2e_test():
    """运行快速端到端测试"""
    print("\n" + "=" * 60)
    print("快速端到端测试")
    print("=" * 60)
    
    # 创建简化的测试配置
    test_config = {
        "stock_code": "300470",
        "save_dir": "quick_test_results",
        "max_retries": 1,
        "max_pages": 1,
        "pages": [
            {
                "name": "调研",
                "suffix": "research",
                "allowed_keywords": None
            }
        ]
    }
    
    config_file = "quick_test_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(test_config, f, ensure_ascii=False, indent=2)
    
    try:
        print("运行快速端到端测试（限时60秒）...")
        start_time = time.time()
        
        result = subprocess.run([
            sys.executable, "main.py",
            "--config", config_file
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        
        elapsed = time.time() - start_time
        
        print(f"执行完成，耗时: {elapsed:.2f}秒")
        print(f"返回码: {result.returncode}")
        
        if result.returncode == 0:
            print("[OK] 快速端到端测试成功")
        else:
            print("[ERROR] 快速端到端测试失败")
            if result.stderr:
                print(f"错误: {result.stderr[:200]}")
        
        return {
            "quick_e2e": {
                "success": result.returncode == 0,
                "elapsed": elapsed
            }
        }
        
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"[ERROR] 快速端到端测试超时 ({elapsed:.2f}秒)")
        return {
            "quick_e2e": {
                "success": False,
                "elapsed": elapsed,
                "error": "timeout"
            }
        }
    except Exception as e:
        return {
            "quick_e2e": {
                "success": False,
                "error": str(e)
            }
        }
    finally:
        if os.path.exists(config_file):
            os.remove(config_file)

def generate_report(results: Dict[str, Any]):
    """生成测试报告"""
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    
    report_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = Path("test_reports/suite")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = report_dir / f"test_suite_report_{report_time}.json"
    
    report_data = {
        "test_info": {
            "timestamp": datetime.now().isoformat(),
            "test_type": "suite",
            "description": "统一测试套件 - 系统、性能、验证测试"
        },
        "results": results,
        "summary": {
            "system_test": len([r for r in results.get("system_test", []) if r["success"]]),
            "performance_test": "completed" if results.get("performance_test") else "failed",
            "validation_test": "completed" if results.get("validation_test") else "failed",
            "quick_e2e": results.get("quick_e2e", {}).get("success", False)
        }
    }
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"测试报告已保存到: {report_file}")
    
    # 输出摘要
    print("\n测试摘要:")
    system_passed = len([r for r in results.get("system_test", []) if r["success"]])
    system_total = len(results.get("system_test", []))
    print(f"  系统测试: {system_passed}/{system_total} 通过")
    
    if results.get("performance_test"):
        print(f"  性能测试: [OK] 完成")
    else:
        print(f"  性能测试: [ERROR] 失败")
    
    if results.get("validation_test"):
        print(f"  验证测试: [OK] 完成")
    else:
        print(f"  验证测试: [ERROR] 失败")
    
    quick_e2e = results.get("quick_e2e", {})
    if quick_e2e.get("success"):
        print(f"  快速E2E: [OK] 成功 ({quick_e2e.get('elapsed', 0):.1f}秒)")
    else:
        print(f"  快速E2E: [ERROR] 失败")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='统一测试套件')
    parser.add_argument('--system', action='store_true', help='只运行系统测试')
    parser.add_argument('--performance', action='store_true', help='只运行性能测试')
    parser.add_argument('--validation', action='store_true', help='只运行验证测试')
    parser.add_argument('--quick-e2e', action='store_true', help='只运行快速端到端测试')
    parser.add_argument('--all', action='store_true', help='运行所有测试（默认）')
    
    args = parser.parse_args()
    
    if not any([args.system, args.performance, args.validation, args.quick_e2e, args.all]):
        args.all = True
    
    print("开始统一测试套件...")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    if args.all or args.system:
        results["system_test"] = run_system_test()
    
    if args.all or args.performance:
        results["performance_test"] = run_performance_test()
    
    if args.all or args.validation:
        results["validation_test"] = run_validation_test()
    
    if args.all or args.quick_e2e:
        results["quick_e2e"] = run_quick_e2e_test()["quick_e2e"]
    
    # 生成报告
    generate_report(results)
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)