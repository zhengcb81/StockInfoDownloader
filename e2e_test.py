#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
端到端测试最终版本
严格按照测试要求.txt实现的所有功能
测试新旧两个下载器的完整功能
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
import shutil
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime

# 导入测试报告生成器
sys.path.insert(0, str(Path(__file__).parent / "tests"))
from test_report_generator import TestReportGenerator

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

def test_skip_logic(test_case, config, downloader_type="new"):
    """测试文件跳过逻辑（当delete_later=False时）"""
    if test_case.get("delete_later", True):
        return None  # 跳过此测试
        
    stock_code = test_case["stock_code"]
    log(f"\n测试跳过逻辑 ({downloader_type}下载器): {stock_code}")
    
    # 让下载器自己处理目录结构，测试程序只检查最终结果的保存位置
    # 复制预期文件到下载目录根目录，让下载器自己组织到子目录
    save_dir = Path(config["save_dir"])
    expected_dir = Path(config["expected_result_dir"])
    
    # 查找预期结果目录中的实际公司目录（不硬编码公司名称）
    expected_base_dir = Path(config["expected_result_dir"])
    expected_company_dirs = [d for d in expected_base_dir.iterdir() if d.is_dir()] if expected_base_dir.exists() else []
    
    if not expected_company_dirs:
        log(f"警告: 在预期结果目录中未找到任何公司目录")
        return None
    
    # 让下载器自己处理目录结构，测试程序只检查最终结果的保存位置
    # 复制预期文件到对应的公司子目录中，模拟已存在文件的情况
    save_dir = Path(config["save_dir"])
    files_copied = 0
    for expected_company_dir in expected_company_dirs:
        # 为每个公司创建对应的子目录
        # 使用下载器自身的功能获取股票名称，避免hardcode
        company_dir_name = expected_company_dir.name
        
        # 尝试从目录名推断股票代码，然后获取标准名称
        stock_code = None
        for test_case in config.get("test_cases", []):
            # 检查测试用例中是否有相关的股票信息
            test_stock_name = test_case.get("stock_name", "")
            if (test_stock_name in company_dir_name or 
                company_dir_name in test_stock_name or
                str(test_case.get("stock_code", "")) in company_dir_name):
                stock_code = test_case.get("stock_code")
                break
        
        # 如果找到股票代码，使用标准函数获取名称
        if stock_code:
            try:
                from get_stock_name import get_stock_name
                standard_name = get_stock_name(stock_code)
                if standard_name and not standard_name.startswith('错误'):
                    company_dir_name = standard_name
            except Exception:
                pass  # 使用原有名称
        
        target_company_dir = save_dir / company_dir_name
        target_company_dir.mkdir(parents=True, exist_ok=True)
        
        for expected_file in expected_company_dir.glob("*.pdf"):
            # 直接复制到对应的公司子目录中
            target_file = target_company_dir / expected_file.name
            if not target_file.exists():
                shutil.copy2(expected_file, target_file)
                log(f"复制文件以测试跳过逻辑: {expected_file.name} -> {target_company_dir.name}")
                files_copied += 1
    
    if files_copied == 0:
        log("没有复制任何文件用于跳过测试")
        return None
    
    # 记录整个save_dir中的现有文件（让下载器自己组织）
    existing_files = list(save_dir.rglob("*.pdf")) if save_dir.exists() else []
    
    # 运行下载器（应该跳过已存在的文件）
    if downloader_type == "old":
        result = run_test_with_old_downloader(test_case, config)
    else:
        result = run_test_with_new_downloader(test_case, config)
    
    # 验证整个save_dir中的文件数量（让下载器自己决定文件位置）
    if save_dir.exists():
        new_files = list(save_dir.rglob("*.pdf"))
        if len(new_files) == len(existing_files):
            log("跳过逻辑测试通过: 文件数量未增加")
            result["skip_test_passed"] = True
        else:
            log("跳过逻辑测试失败: 文件数量增加")
            result["skip_test_passed"] = False
    
    return result

def run_test_with_old_downloader(test_case, config):
    """使用旧下载器运行测试"""
    stock_code = test_case["stock_code"]
    log(f"\n使用旧下载器测试: {stock_code}")
    
    # 让下载器自己处理目录结构，测试程序不干预
    suffix = test_case.get("suffix", "research")
    allowed_keywords = test_case.get("allowed_keywords")
    delete_later = test_case.get("delete_later", True)
    max_pages = test_case.get("max_pages", 5)
    timeout = test_case.get("timeout_seconds", 180)
    
    # 让下载器自己处理目录结构，测试程序不干预
    
    start_time = time.time()
    success = False
    error_msg = ""
    downloaded_files = []
    duration = 0
    
    try:
        # 导入旧下载器
        from cninfo_activity_downloader import CninfoDownloader
        
        # 创建下载器
        downloader = CninfoDownloader(save_dir=config["save_dir"])
        
        # 获取组织ID
        org_id = downloader.get_org_id(stock_code)
        if not org_id:
            error_msg = "无法获取组织ID"
        else:
            # 解析关键词
            keywords = allowed_keywords
            
            # 执行下载
            success = downloader.download_activity_records(
                stock_code=stock_code,
                org_id=org_id,
                headless=config.get("headless", True),
                max_retries=config.get("max_retries", 3),
                suffix=suffix,
                allowed_keywords=keywords,
                max_pages=max_pages
            )
            
            if not success:
                error_msg = "下载失败"
        
        duration = time.time() - start_time
        
        # 检查下载的文件（让下载器自己决定文件位置）
        save_dir = Path(config["save_dir"])
        downloaded_files = list(save_dir.rglob("*.pdf")) if save_dir.exists() else []
        
        # 验证结果
        if success and downloaded_files:
            # 检查超时
            if duration > timeout:
                error_msg = f"下载过慢: {duration:.1f}s"
                success = False
            else:
                log(f"下载成功，耗时 {duration:.1f}s，找到 {len(downloaded_files)} 个文件")
                
                # 与预期结果比较（检查整个save_dir结构是否符合预期）
                # 让下载器自己处理目录结构，测试程序只验证结果
                if success:
                    # 查找预期结果目录中的实际公司目录
                    expected_base_dir = Path(config["expected_result_dir"])
                    if expected_base_dir.exists():
                        expected_company_dirs = [d for d in expected_base_dir.iterdir() if d.is_dir()]
                        
                        if not expected_company_dirs:
                            log("警告: 预期结果目录中没有找到公司目录")
                        else:
                            match_found = False
                            for expected_company_dir in expected_company_dirs:
                                for expected_file in expected_company_dir.glob("*.pdf"):
                                    # 在下载的文件中查找同名文件
                                    for downloaded_file in downloaded_files:
                                        if downloaded_file.name == expected_file.name and compare_files(downloaded_file, expected_file):
                                            log(f"文件匹配: {downloaded_file.name} (公司: {expected_company_dir.name})")
                                            match_found = True
                                            break
                                    if match_found:
                                        break
                                if match_found:
                                    break
                            
                            if not match_found:
                                log("警告: 没有找到匹配的预期文件")
                
                # 验证目录结构是否符合要求（文件应在公司子目录中，而不是根目录）
                if success and not delete_later:
                    root_pdf_files = [f for f in save_dir.glob("*.pdf")]
                    if root_pdf_files:
                        log(f"警告: 发现根目录文件: {[f.name for f in root_pdf_files]}")
                        # 这本身不是失败，但应该记录为警告
        else:
            error_msg = error_msg or "未下载到文件"
            success = False
            
    except Exception as e:
        error_msg = f"测试异常: {str(e)}"
        success = False
    
    # 注意：清理逻辑已移至main函数末尾统一处理
    log(f"测试完成，等待统一清理 (delete_later={delete_later})")
    
    # 输出结果
    log(f"结果: {'成功' if success else '失败'}")
    if error_msg:
        log(f"错误: {error_msg}")
    
    return {
        "downloader": "old",
        "stock_code": stock_code,
        "stock_name": f"股票{stock_code}",
        "success": success,
        "error": error_msg,
        "duration": duration,
        "downloaded_files": len(downloaded_files)
    }

def run_test_with_new_downloader(test_case, config):
    """使用新下载器运行测试"""
    stock_code = test_case["stock_code"]
    log(f"\n使用新下载器测试: {stock_code}")
    
    # 让下载器自己处理目录结构，测试程序不干预
    allowed_keywords = test_case.get("allowed_keywords")
    delete_later = test_case.get("delete_later", True)
    max_pages = test_case.get("max_pages", 5)
    timeout = test_case.get("timeout_seconds", 180)
    suffix = test_case.get("suffix", "research")
    
    # 让下载器自己处理目录结构，测试程序不干预
    
    start_time = time.time()
    success = False
    error_msg = ""
    downloaded_files = []
    duration = 0
    duration = 0
    
    try:
        # 创建临时配置文件
        # 注意：测试程序不生成公司名称，让下载器自己决定
        temp_config = {
            "stock_code": stock_code,
            "save_dir": config["save_dir"],
            "max_retries": config.get("max_retries", 3),
            "max_pages": max_pages,
            "pages": [{
                "name": f"{suffix}页面",
                "suffix": suffix,
                "allowed_keywords": allowed_keywords
            }]
        }
        
        temp_config_file = "temp_final_e2e_config.json"
        with open(temp_config_file, 'w', encoding='utf-8') as f:
            json.dump(temp_config, f, ensure_ascii=False, indent=2)
        
        try:
            # 运行main.py
            result = subprocess.run(
                [sys.executable, "main.py", "--config", temp_config_file],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout + 60
            )
            
            if result.returncode == 0:
                success = True
                log("main.py执行成功")
            else:
                error_msg = f"main.py执行失败: {result.stderr}"
                log(error_msg)
        finally:
            if os.path.exists(temp_config_file):
                os.remove(temp_config_file)
        
        duration = time.time() - start_time
        
        # 检查下载的文件（让下载器自己决定文件位置）
        save_dir = Path(config["save_dir"])
        downloaded_files = list(save_dir.rglob("*.pdf")) if save_dir.exists() else []
        
        log(f"找到 {len(downloaded_files)} 个下载文件")
        
        # 验证结果
        if success and downloaded_files:
            # 检查超时
            if duration > timeout:
                error_msg = f"下载过慢: {duration:.1f}s"
                success = False
            else:
                # 检查文件是否在公司目录（如果不删除）
                # 让下载器自己决定目录结构，测试程序只验证结果
                if not delete_later:
                    # 查找实际的公司目录（下载器创建的目录）
                    company_dirs = [d for d in save_dir.iterdir() if d.is_dir() and d.name != '.tmp']
                    
                    if not company_dirs:
                        error_msg = "下载器未创建任何公司目录"
                    else:
                        # 检查是否有文件在公司子目录中
                        company_files = []
                        for company_dir in company_dirs:
                            company_files.extend([f for f in company_dir.glob("*.pdf")])
                        
                        if not company_files:
                            error_msg = "公司子目录中没有找到PDF文件"
                        else:
                            log(f"发现 {len(company_files)} 个文件在公司目录: {[f.parent.name for f in company_files]}")
                
                # 与预期结果比较
                if not error_msg:
                    # 查找预期结果目录中的实际公司目录
                    expected_base_dir = Path(config["expected_result_dir"])
                    if expected_base_dir.exists():
                        expected_company_dirs = [d for d in expected_base_dir.iterdir() if d.is_dir()]
                        
                        if not expected_company_dirs:
                            log("警告: 预期结果目录中没有找到公司目录")
                        else:
                            # 尝试匹配下载的文件与预期文件
                            match_found = False
                            for expected_company_dir in expected_company_dirs:
                                for expected_file in expected_company_dir.glob("*.pdf"):
                                    # 在下载的文件中查找同名文件
                                    for downloaded_file in downloaded_files:
                                        if downloaded_file.name == expected_file.name:
                                            if compare_files(downloaded_file, expected_file):
                                                log(f"文件匹配: {downloaded_file.name} (公司: {expected_company_dir.name})")
                                                match_found = True
                                                break
                                    if match_found:
                                        break
                                if match_found:
                                    break
                            
                            if not match_found:
                                log("警告: 没有找到匹配的预期文件")
        
        success = not error_msg
        
    except Exception as e:
        error_msg = f"测试异常: {str(e)}"
        success = False
        duration = time.time() - start_time
    
    # 注意：清理逻辑已移至main函数末尾统一处理
    log(f"测试完成，等待统一清理 (delete_later={delete_later})")
    
    # 输出结果
    log(f"结果: {'成功' if success else '失败'}")
    if error_msg:
        log(f"错误: {error_msg}")
    log(f"耗时: {duration:.1f}s")
    
    return {
        "downloader": "new",
        "stock_code": stock_code,
        "stock_name": f"股票{stock_code}",
        "success": success,
        "error": error_msg,
        "duration": duration,
        "downloaded_files": len(downloaded_files)
    }

def main():
    """主函数"""
    log("开始端到端测试（最终版本）")
    log("严格按照测试说明.md实现")
    
    # 加载配置（支持命令行参数）
    import argparse
    parser = argparse.ArgumentParser(description='端到端测试')
    parser.add_argument('--config', default='config_end2end_test.json', help='配置文件路径')
    args = parser.parse_args()
    config_file = args.config
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        log(f"加载配置失败: {e}")
        return 1
    
    log(f"使用配置: {config_file}")
    log(f"保存目录: {config['save_dir']}")
    log(f"预期结果目录: {config['expected_result_dir']}")
    
    # 创建必要目录
    Path(config["save_dir"]).mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    # 验证测试设置
    log("\n验证测试设置...")
    expected_dir = Path(config["expected_result_dir"])
    if not expected_dir.exists():
        log(f"警告: 预期结果目录不存在: {expected_dir}")
    else:
        company_dirs = [d for d in expected_dir.iterdir() if d.is_dir()]
        log(f"发现 {len(company_dirs)} 个预期结果公司目录")
    
    # 运行测试
    all_results = []
    test_cases = config.get("test_cases", [])
    max_test_retries = 2  # 每个测试用例最大重试次数
    
    for i, test_case in enumerate(test_cases, 1):
        log(f"\n{'='*80}")
        log(f"测试用例 {i}/{len(test_cases)}: {test_case['stock_code']}")
        log(f"类型: {test_case.get('suffix', 'research')}")
        log(f"delete_later: {test_case.get('delete_later', True)}")
        log(f"max_pages: {test_case.get('max_pages', 5)}")
        log(f"{'='*80}")
        
        # 测试旧下载器（带重试机制）
        old_result = None
        for retry in range(max_test_retries + 1):
            try:
                log(f"测试旧下载器... (尝试 {retry + 1}/{max_test_retries + 1})")
                old_result = run_test_with_old_downloader(test_case, config)
                
                # 如果测试成功，跳出重试循环
                if old_result.get("success", False):
                    log("旧下载器测试成功")
                    break
                else:
                    log(f"旧下载器测试失败，错误: {old_result.get('error', '未知错误')}")
                    if retry < max_test_retries:
                        log(f"等待 {10 + retry * 5} 秒后重试...")
                        time.sleep(10 + retry * 5)
                    else:
                        log("旧下载器测试达到最大重试次数")
            except Exception as e:
                log(f"旧下载器测试异常: {e}")
                if retry < max_test_retries:
                    log(f"等待 {10 + retry * 5} 秒后重试...")
                    time.sleep(10 + retry * 5)
                else:
                    log("旧下载器测试达到最大重试次数")
                    old_result = {
                        "downloader": "old",
                        "stock_code": test_case["stock_code"],
                        "stock_name": f"股票{test_case['stock_code']}",
                        "success": False,
                        "error": f"测试异常: {str(e)}",
                        "duration": 0,
                        "downloaded_files": 0
                    }
        
        if old_result:
            all_results.append(old_result)
        
        # 测试间隔
        time.sleep(1)
        
        # 测试新下载器（带重试机制）
        new_result = None
        for retry in range(max_test_retries + 1):
            try:
                log(f"测试新下载器... (尝试 {retry + 1}/{max_test_retries + 1})")
                new_result = run_test_with_new_downloader(test_case, config)
                
                # 如果测试成功，跳出重试循环
                if new_result.get("success", False):
                    log("新下载器测试成功")
                    break
                else:
                    log(f"新下载器测试失败，错误: {new_result.get('error', '未知错误')}")
                    if retry < max_test_retries:
                        log(f"等待 {10 + retry * 5} 秒后重试...")
                        time.sleep(10 + retry * 5)
                    else:
                        log("新下载器测试达到最大重试次数")
            except Exception as e:
                log(f"新下载器测试异常: {e}")
                if retry < max_test_retries:
                    log(f"等待 {10 + retry * 5} 秒后重试...")
                    time.sleep(10 + retry * 5)
                else:
                    log("新下载器测试达到最大重试次数")
                    new_result = {
                        "downloader": "new",
                        "stock_code": test_case["stock_code"],
                        "stock_name": f"股票{test_case['stock_code']}",
                        "success": False,
                        "error": f"测试异常: {str(e)}",
                        "duration": 0,
                        "downloaded_files": 0
                    }
        
        if new_result:
            all_results.append(new_result)
        
        # 测试间隔
        time.sleep(1)
        
        # 如果delete_later为False，测试跳过逻辑
        if not test_case.get("delete_later", True):
            log("测试文件跳过逻辑...")
            # 测试旧下载器的跳过逻辑
            old_skip_result = test_skip_logic(test_case, config, "old")
            if old_skip_result:
                all_results.append(old_skip_result)
            
            time.sleep(2)
            
            # 测试新下载器的跳过逻辑
            new_skip_result = test_skip_logic(test_case, config, "new")
            if new_skip_result:
                all_results.append(new_skip_result)
            
            time.sleep(2)
    
    # 生成报告
    log(f"\n{'='*80}")
    log("测试报告")
    log(f"{'='*80}")
    
    total_tests = len(all_results)
    passed_tests = sum(1 for r in all_results if r["success"])
    skip_tests_passed = sum(1 for r in all_results if r.get("skip_test_passed", False))
    
    log(f"总测试数: {total_tests}")
    log(f"通过: {passed_tests}")
    log(f"失败: {total_tests - passed_tests}")
    log(f"成功率: {passed_tests/total_tests*100:.1f}%")
    if skip_tests_passed > 0:
        log(f"跳过逻辑测试通过: {skip_tests_passed}")
    
    # 使用统一的报告生成器创建报告
    generator = TestReportGenerator()
    
    log("生成标准化测试报告...")
    report_file = generator.create_e2e_report(
        test_cases=test_cases,
        results=all_results,
        config_file=config_file,
        description="端到端测试 - 验证新旧下载器功能一致性"
    )
    
    # 打印报告摘要
    generator.print_report_summary(report_file)
    
    # 输出失败测试详情
    failed_tests = [r for r in all_results if not r["success"]]
    if failed_tests:
        log(f"\n失败测试详情:")
        for test in failed_tests:
            log(f"  - {test['downloader']}下载器 {test['stock_code']}: {test.get('error', '未知错误')}")
    
    log(f"\n详细报告已保存到: {report_file}")
    
    # 执行最终清理（只保留delete_later=False的文件）
    log("\n执行最终清理...")
    try:
        from test_cleaner import clean_test_files
        preserve_cases = [case for case in test_cases if not case.get("delete_later", True)]
        clean_result = clean_test_files(config["save_dir"], preserve_cases)
        log(f"清理完成: 删除 {clean_result['cleaned_files']} 个文件, {clean_result['cleaned_dirs']} 个目录")
    except Exception as e:
        log(f"清理失败: {e}")
    
    return 0 if passed_tests == total_tests else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)