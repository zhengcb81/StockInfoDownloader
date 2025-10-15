#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
扩展端到端测试
支持更多测试场景和功能验证
"""

import sys
import os
import json
import time
import shutil
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

# 设置控制台编码为UTF-8
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def log(message):
    """简单的日志输出"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def calculate_file_hash(file_path):
    """计算文件MD5"""
    if not os.path.exists(file_path):
        return ""

    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def compare_files(file1, file2):
    """比较两个文件是否相同"""
    if not os.path.exists(file1) or not os.path.exists(file2):
        return False

    # 比较大小
    if os.path.getsize(file1) != os.path.getsize(file2):
        return False

    # 比较MD5
    return calculate_file_hash(file1) == calculate_file_hash(file2)

def get_real_stock_name(stock_code):
    """获取真实的股票名称"""
    try:
        from get_stock_name import get_stock_name
        stock_name = get_stock_name(stock_code)
        if not stock_name or stock_name.startswith('错误') or stock_name.startswith('网络'):
            return f"股票{stock_code}"
        return stock_name
    except Exception as e:
        log(f"错误: 获取股票名称时发生异常: {e}")
        return f"股票{stock_code}"

def validate_test_environment(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """验证测试环境"""
    issues = []

    # 检查目录
    save_dir = Path(config["save_dir"])
    expected_dir = Path(config["expected_result_dir"])

    if not save_dir.exists():
        save_dir.mkdir(parents=True, exist_ok=True)
        log(f"创建保存目录: {save_dir}")

    if not expected_dir.exists():
        issues.append(f"预期结果目录不存在: {expected_dir}")

    # 检查文档管理工具
    try:
        from tools.real_document_manager import RealDocumentManager
        doc_manager = RealDocumentManager()

        # 验证测试配置
        valid, config_issues = doc_manager.validate_test_configuration("config_end2end_test_extended.json")
        if not valid:
            issues.extend(config_issues)

    except Exception as e:
        issues.append(f"文档管理工具初始化失败: {e}")

    return len(issues) == 0, issues

def prepare_test_environment(config: Dict[str, Any]) -> bool:
    """准备测试环境"""
    try:
        # 使用智能清理工具准备环境
        from tools.smart_directory_cleaner import SmartDirectoryCleaner
        cleaner = SmartDirectoryCleaner()

        # 清空测试结果目录（保留配置中指定的文件）
        log("准备测试环境...")
        result = cleaner.smart_cleanup("config_end2end_test_extended.json", dry_run=False)

        if result.errors:
            log(f"环境准备警告: {len(result.errors)} 个错误")
            for error in result.errors:
                log(f"  - {error}")

        # 从预期结果恢复文档
        restored_files, restore_errors = cleaner.restore_expected_documents(dry_run=False)
        log(f"从预期结果恢复 {restored_files} 个文档")

        if restore_errors:
            log(f"文档恢复警告: {len(restore_errors)} 个错误")
            for error in restore_errors:
                log(f"  - {error}")

        return True

    except Exception as e:
        log(f"环境准备失败: {e}")
        return False

def run_comprehensive_test(test_case: Dict[str, Any], config: Dict[str, Any],
                          browser_strategy: str = "playwright") -> Dict[str, Any]:
    """运行综合测试"""
    stock_code = test_case["stock_code"]
    description = test_case.get("description", "")

    log(f"\n运行测试: {stock_code} - {description}")
    log(f"浏览器策略: {browser_strategy}")

    start_time = time.time()
    success = False
    error_msg = ""
    downloaded_files = []
    duration = 0

    try:
        # 创建临时配置文件
        temp_config_dir = Path(config["save_dir"]) / "temp_config"
        temp_config_dir.mkdir(exist_ok=True)

        # 创建临时映射文件
        temp_mapping_file = temp_config_dir / "temp_mapping.json"

        from src.data.mapping import MappingManager
        main_mapping = MappingManager("stock_orgid_mapping.json")

        test_mapping = {}
        test_stock_code = test_case["stock_code"]
        org_id = main_mapping.get_org_id(test_stock_code)
        stock_name = main_mapping.get_stock_name(test_stock_code) or f"测试公司{test_stock_code}"

        if org_id:
            test_mapping[test_stock_code] = {"orgId": org_id, "name": stock_name}
        else:
            # 如果找不到orgId，使用一个有效的测试orgId
            test_mapping[test_stock_code] = {"orgId": "9900056250", "name": stock_name}

        with open(temp_mapping_file, 'w', encoding='utf-8') as f:
            json.dump(test_mapping, f, ensure_ascii=False, indent=2)

        # 创建临时配置文件
        temp_config_file = temp_config_dir / "temp_config.json"
        temp_config_data = {
            "browser": {
                "strategy": browser_strategy,
                "headless": True
            },
            "download": {
                "max_retries": config.get("max_retries", 3),
                "max_downloads_per_session": 10,
                "human_behavior_delay": 3
            },
            "webdriver": {
                "window_size": "1920,1080",
                "user_agents": [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ]
            },
            "timeout": {
                "page_load": 15,
                "element_wait": 3
            }
        }
        with open(temp_config_file, 'w', encoding='utf-8') as f:
            json.dump(temp_config_data, f, ensure_ascii=False, indent=2)

        # 使用DownloadServiceV2 API
        from src.services.downloader_v2 import DownloadServiceV2

        # 创建下载器实例
        downloader = DownloadServiceV2(
            save_dir=config["save_dir"],
            mapping_file=str(temp_mapping_file),
            browser_strategy=browser_strategy
        )

        # 构建目标页面配置
        target_pages = [{
            "suffix": test_case.get("suffix", "research"),
            "allowed_keywords": test_case.get("allowed_keywords", [])
        }]

        # 执行下载
        download_records = downloader.download_stock_pdfs(
            stock_code=stock_code,
            target_pages=target_pages,
            max_retries=config.get("max_retries", 3)
        )

        duration = time.time() - start_time

        success = len(download_records) > 0
        if success:
            log(f"下载成功，获得 {len(download_records)} 个文件")
        else:
            error_msg = "未下载到任何文件"
            log(error_msg)

        # 检查下载的文件
        save_dir = Path(config["save_dir"])
        downloaded_files = list(save_dir.rglob("*.pdf")) if save_dir.exists() else []

        log(f"找到 {len(downloaded_files)} 个下载文件")

        # 验证结果
        if success:
            # 检查超时
            timeout = test_case.get("timeout_seconds", 180)
            if duration > timeout:
                error_msg = f"下载过慢: {duration:.1f}s (超时: {timeout}s)"
                success = False

        success = not error_msg

        # 清理临时配置文件
        try:
            shutil.rmtree(temp_config_dir)
        except Exception as e:
            log(f"清理临时配置文件失败: {e}")

    except Exception as e:
        error_msg = f"测试异常: {str(e)}"
        success = False
        duration = time.time() - start_time

        # 确保清理临时配置文件
        try:
            if 'temp_config_dir' in locals():
                shutil.rmtree(temp_config_dir)
        except Exception:
            pass

    # 获取真实的股票名称
    stock_name = get_real_stock_name(stock_code)

    return {
        "downloader": "new",
        "browser_strategy": browser_strategy,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "description": description,
        "success": success,
        "error": error_msg,
        "duration": duration,
        "downloaded_files": len(downloaded_files),
        "timeout": test_case.get("timeout_seconds", 180)
    }

def analyze_test_results(all_results: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """分析测试结果"""
    analysis = {
        "total_tests": len(all_results),
        "successful_downloads": sum(1 for r in all_results if r.get("downloaded_files", 0) > 0),
        "failed_downloads": sum(1 for r in all_results if r.get("downloaded_files", 0) == 0),
        "total_duration": sum(r.get("duration", 0) for r in all_results),
        "total_files": sum(r.get("downloaded_files", 0) for r in all_results),
        "strategy_performance": {},
        "stock_performance": {},
        "test_type_performance": {}
    }

    # 按浏览器策略分析
    for result in all_results:
        strategy = result.get("browser_strategy", "selenium")
        if strategy not in analysis["strategy_performance"]:
            analysis["strategy_performance"][strategy] = {
                "total_tests": 0,
                "successful_tests": 0,
                "total_files": 0,
                "total_duration": 0
            }

        analysis["strategy_performance"][strategy]["total_tests"] += 1
        if result.get("downloaded_files", 0) > 0:
            analysis["strategy_performance"][strategy]["successful_tests"] += 1
            analysis["strategy_performance"][strategy]["total_files"] += result.get("downloaded_files", 0)
        analysis["strategy_performance"][strategy]["total_duration"] += result.get("duration", 0)

    # 按股票代码分析
    for result in all_results:
        stock_code = result["stock_code"]
        if stock_code not in analysis["stock_performance"]:
            analysis["stock_performance"][stock_code] = {
                "stock_name": result["stock_name"],
                "total_tests": 0,
                "successful_tests": 0,
                "total_files": 0
            }

        analysis["stock_performance"][stock_code]["total_tests"] += 1
        if result.get("downloaded_files", 0) > 0:
            analysis["stock_performance"][stock_code]["successful_tests"] += 1
            analysis["stock_performance"][stock_code]["total_files"] += result.get("downloaded_files", 0)

    # 计算成功率
    analysis["success_rate"] = (analysis["successful_downloads"] / analysis["total_tests"] * 100) if analysis["total_tests"] > 0 else 0
    analysis["average_duration"] = analysis["total_duration"] / analysis["total_tests"] if analysis["total_tests"] > 0 else 0
    analysis["average_files_per_test"] = analysis["total_files"] / analysis["successful_downloads"] if analysis["successful_downloads"] > 0 else 0

    return analysis

def main():
    """主函数"""
    log("开始扩展端到端测试")
    log("支持更多测试场景和功能验证")

    # 加载扩展配置
    config_file = 'config_end2end_test_extended.json'
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        log(f"加载配置失败: {e}")
        return 1

    log(f"使用配置: {config_file}")
    log(f"测试用例数: {len(config.get('test_cases', []))}")

    # 验证测试环境
    log("\n验证测试环境...")
    env_valid, env_issues = validate_test_environment(config)
    if not env_valid:
        log("测试环境验证失败:")
        for issue in env_issues:
            log(f"  - {issue}")
        return 1
    log("测试环境验证通过")

    # 准备测试环境
    if not prepare_test_environment(config):
        log("测试环境准备失败")
        return 1
    log("测试环境准备完成")

    # 运行所有测试用例
    all_results = []
    test_cases = config.get("test_cases", [])
    max_test_retries = 2  # 每个测试用例最大重试次数

    # 浏览器策略配置
    browser_strategies = ["playwright", "selenium"]

    for i, test_case in enumerate(test_cases, 1):
        log(f"\n{'='*80}")
        log(f"测试用例 {i}/{len(test_cases)}: {test_case['stock_code']}")
        log(f"描述: {test_case.get('description', '无描述')}")
        log(f"类型: {test_case.get('suffix', 'research')}")
        log(f"delete_later: {test_case.get('delete_later', True)}")
        log(f"max_pages: {test_case.get('max_pages', 5)}")
        log(f"{'='*80}")

        # 测试多种浏览器策略
        for strategy in browser_strategies:
            result = None
            for retry in range(max_test_retries + 1):
                try:
                    log(f"测试浏览器策略({strategy})... (尝试 {retry + 1}/{max_test_retries + 1})")
                    result = run_comprehensive_test(test_case, config, strategy)

                    # 如果下载成功，跳出重试循环
                    if result.get("downloaded_files", 0) > 0:
                        log(f"下载成功，获得 {result['downloaded_files']} 个文件")
                        break
                    else:
                        log(f"下载失败，错误: {result.get('error', '未知错误')}")
                        if retry < max_test_retries:
                            log(f"等待 {10 + retry * 5} 秒后重试...")
                            time.sleep(10 + retry * 5)
                        else:
                            log(f"浏览器策略({strategy})测试达到最大重试次数")
                except Exception as e:
                    log(f"浏览器策略({strategy})测试异常: {e}")
                    if retry < max_test_retries:
                        log(f"等待 {10 + retry * 5} 秒后重试...")
                        time.sleep(10 + retry * 5)
                    else:
                        log(f"浏览器策略({strategy})测试达到最大重试次数")
                        result = {
                            "downloader": "new",
                            "browser_strategy": strategy,
                            "stock_code": test_case["stock_code"],
                            "stock_name": get_real_stock_name(test_case['stock_code']),
                            "description": test_case.get('description', ''),
                            "success": False,
                            "error": f"测试异常: {str(e)}",
                            "duration": 0,
                            "downloaded_files": 0,
                            "timeout": test_case.get("timeout_seconds", 180)
                        }

            if result:
                all_results.append(result)

        # 测试用例间间隔
        time.sleep(5)

    # 分析测试结果
    log(f"\n{'='*80}")
    log("测试结果分析")
    log(f"{'='*80}")

    analysis = analyze_test_results(all_results, config)

    log(f"总测试数: {analysis['total_tests']}")
    log(f"成功下载: {analysis['successful_downloads']}")
    log(f"失败下载: {analysis['failed_downloads']}")
    log(f"成功率: {analysis['success_rate']:.1f}%")
    log(f"总耗时: {analysis['total_duration']:.1f}s")
    log(f"平均耗时: {analysis['average_duration']:.1f}s")
    log(f"总文件数: {analysis['total_files']}")
    log(f"平均文件数/成功测试: {analysis['average_files_per_test']:.1f}")

    # 浏览器策略性能比较
    log(f"\n浏览器策略性能:")
    for strategy, stats in analysis["strategy_performance"].items():
        success_rate = (stats["successful_tests"] / stats["total_tests"] * 100) if stats["total_tests"] > 0 else 0
        avg_duration = stats["total_duration"] / stats["total_tests"] if stats["total_tests"] > 0 else 0
        avg_files = stats["total_files"] / stats["successful_tests"] if stats["successful_tests"] > 0 else 0

        log(f"  - {strategy.upper()}:")
        log(f"     成功率: {success_rate:.1f}% ({stats['successful_tests']}/{stats['total_tests']})")
        log(f"     平均耗时: {avg_duration:.1f}s")
        log(f"     平均文件数: {avg_files:.1f} 个/成功测试")

    # 股票性能分析
    log(f"\n股票性能分析:")
    for stock_code, stats in analysis["stock_performance"].items():
        success_rate = (stats["successful_tests"] / stats["total_tests"] * 100) if stats["total_tests"] > 0 else 0
        log(f"  - {stock_code} ({stats['stock_name']}): {success_rate:.1f}% ({stats['successful_tests']}/{stats['total_tests']})")

    # 详细结果
    log(f"\n详细测试结果:")
    for result in all_results:
        status = "成功" if result.get("downloaded_files", 0) > 0 else "失败"
        strategy = result.get("browser_strategy", "unknown")
        log(f"  - {result['stock_code']} [{strategy}]: {status} ({result.get('downloaded_files', 0)} 个文件, {result.get('duration', 0):.1f}s)")
        if result.get("error"):
            log(f"     错误: {result['error']}")

    # 执行最终清理
    log("\n执行最终清理...")
    try:
        from tools.smart_directory_cleaner import SmartDirectoryCleaner
        cleaner = SmartDirectoryCleaner()
        result = cleaner.smart_cleanup("config_end2end_test_extended.json", dry_run=False)
        log(f"清理完成: 删除 {result.cleaned_files} 个文件, {result.cleaned_dirs} 个目录")
    except Exception as e:
        log(f"清理失败: {e}")

    # 总体测试结果
    overall_success = analysis["success_rate"] >= 50.0  # 成功率超过50%就算通过

    log(f"\n总体测试结果: {'通过' if overall_success else '失败'}")

    return 0 if overall_success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)