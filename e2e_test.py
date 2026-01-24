#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
端到端测试最终版本
严格按照测试要求.txt实现的所有功能
测试新旧两个下载器的完整功能
"""

# 在导入任何其他模块之前设置事件循环策略
import sys
import asyncio
if sys.platform == 'win32':
    # 设置控制台编码为UTF-8，防止乱码
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

    # Windows上Playwright需要ProactorEventLoop，但sync_playwright会自动处理
    # 为避免事件循环冲突，确保每次测试都有干净的事件循环
    try:
        # 尝试获取并关闭现有事件循环（如果存在且未运行）
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                # 如果循环存在但未运行，关闭它
                loop.close()
        except RuntimeError:
            # 没有事件循环，这是正常的
            pass
        except:
            # 其他错误，忽略
            pass

        # 创建新的事件循环并设置为当前循环
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
    except Exception as e:
        print(f"设置事件循环策略时发生错误: {e}")

def get_real_stock_name(stock_code):
    """获取真实的股票名称，不硬编码"""
    try:
        from get_stock_name import get_stock_name
        stock_name = get_stock_name(stock_code)
        if not stock_name or stock_name.startswith('错误') or stock_name.startswith('网络'):
            log(f"警告: 股票名称获取失败，使用备选名称: {stock_name}")
            return f"股票{stock_code}"
        return stock_name
    except Exception as e:
        log(f"错误: 获取股票名称时发生异常: {e}")
        return f"股票{stock_code}"

import sys
import locale
import os
import json
import time
import shutil
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime

# 导入测试报告生成器
sys.path.insert(0, str(Path(__file__).parent))
# from tests.unit.test_report_generator import TestReportGenerator  # 暂时注释掉，避免导入错误

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def log(message):
    """简单的日志输出，处理编码问题"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{timestamp}] {message}")
    except UnicodeEncodeError:
        # 如果无法编码（例如在GBK终端打印特殊符号），则尝试用替换方式打印
        try:
            print(f"[{timestamp}] {message.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)}")
        except:
            # 最后的退路：只打印ASCII部分
            print(f"[{timestamp}] {message.encode('ascii', errors='replace').decode('ascii')}")

def calculate_file_hash(file_path):
    """计算文件MD5"""
    if not os.path.exists(file_path):
        return ""
    
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def compare_files(file1, file2, max_retries=3):
    """比较两个文件是否相同，支持重试"""
    for attempt in range(max_retries):
        try:
            if not os.path.exists(file1) or not os.path.exists(file2):
                time.sleep(0.1 * (attempt + 1))  # 指数退避
                continue

            # 比较大小
            if os.path.getsize(file1) != os.path.getsize(file2):
                return False

            # 比较MD5
            return calculate_file_hash(file1) == calculate_file_hash(file2)
        except (PermissionError, OSError) as e:
            if attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))
            else:
                log(f"文件比较失败 {file1} vs {file2}: {e}")
                return False
    return False

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
    
    # 修复：只复制当前测试股票代码对应的文件，而不是所有文件
    save_dir = Path(config["save_dir"])
    files_copied = 0
    
    # 获取当前测试用例的股票代码和公司名称
    current_stock_code = test_case["stock_code"]
    current_company_name = None
    
    # 查找当前测试用例对应的预期公司目录
    target_expected_dir = None
    for expected_company_dir in expected_company_dirs:
        dir_name = expected_company_dir.name
        
        # 从配置文件中获取股票代码到公司名称的映射
        # 检查这个目录中的文件是否包含当前测试用例的股票代码
        for expected_file in expected_company_dir.glob("*.pdf"):
            if current_stock_code in expected_file.name:
                target_expected_dir = expected_company_dir
                current_company_name = dir_name
                break
        if target_expected_dir:
            break
    
    if not target_expected_dir:
        log(f"警告: 未找到股票代码 {current_stock_code} 对应的预期结果目录")
        return None
    
    # 获取标准公司名称
    try:
        from get_stock_name import get_stock_name
        standard_name = get_stock_name(current_stock_code)
        if standard_name and not standard_name.startswith('错误'):
            current_company_name = standard_name
    except Exception:
        pass  # 使用目录名
    
    # 创建对应的公司目录
    target_company_dir = save_dir / current_company_name
    target_company_dir.mkdir(parents=True, exist_ok=True)
    
    # 只复制当前测试用例对应的文件
    for expected_file in target_expected_dir.glob("*.pdf"):
        target_file = target_company_dir / expected_file.name
        if not target_file.exists():
            shutil.copy2(expected_file, target_file)
            log(f"复制文件以测试跳过逻辑: {expected_file.name} -> {current_company_name}")
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
        # 使用统一下载器工厂创建旧下载器（向后兼容）
        from src.factory.downloader_factory import downloader_factory

        # 创建下载器（通过适配器保证完全兼容）
        downloader = downloader_factory.create_legacy_adapter(
            'cninfo',
            save_dir=config["save_dir"]
        )
        
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
        if success:
            # 检查超时
            if duration > timeout:
                error_msg = f"下载过慢: {duration:.1f}s"
                success = False
            else:
                log(f"下载成功，耗时 {duration:.1f}s，找到 {len(downloaded_files)} 个文件")
                
                # 与预期结果比较（严格验证文件目录结构）
                # 让下载器自己处理目录结构，测试程序只验证结果
                if success:
                    # 查找预期结果目录中的实际公司目录
                    expected_base_dir = Path(config["expected_result_dir"])
                    if expected_base_dir.exists():
                        expected_company_dirs = [d for d in expected_base_dir.iterdir() if d.is_dir()]
                        
                        if not expected_company_dirs:
                            success = False
                            error_msg = "预期结果目录中没有找到公司目录"
                        else:
                            # 严格验证：检查每个预期文件是否在正确的公司目录中
                            all_matched = True
                            matched_files = 0
                            total_expected_files = 0
                            
                            for expected_company_dir in expected_company_dirs:
                                expected_files = list(expected_company_dir.glob("*.pdf"))
                                total_expected_files += len(expected_files)
                                
                                for expected_file in expected_files:
                                    file_matched = False
                                    
                                    # 在下载的文件中查找同名文件且在同名的公司目录中
                                    for downloaded_file in downloaded_files:
                                        if (downloaded_file.name == expected_file.name and 
                                            downloaded_file.parent.name == expected_company_dir.name and
                                            compare_files(downloaded_file, expected_file)):
                                            log(f"文件匹配: {expected_company_dir.name}/{expected_file.name}")
                                            matched_files += 1
                                            file_matched = True
                                            break
                                    
                                    if not file_matched:
                                        log(f"文件不匹配: {expected_company_dir.name}/{expected_file.name}")
                                        all_matched = False
                            
                            # 检查是否有多余的下载文件
                            if len(downloaded_files) > matched_files:
                                log(f"警告: 发现 {len(downloaded_files) - matched_files} 个多余的下载文件")
                                for downloaded_file in downloaded_files:
                                    # 检查这个文件是否是预期的
                                    is_expected = False
                                    for expected_company_dir in expected_company_dirs:
                                        for expected_file in expected_company_dir.glob("*.pdf"):
                                            if downloaded_file.name == expected_file.name:
                                                is_expected = True
                                                break
                                        if is_expected:
                                            break
                                    
                                    if not is_expected:
                                        log(f"多余文件: {downloaded_file.parent.name}/{downloaded_file.name}")
                                        all_matched = False
                            
                            # 检查是否缺少预期的文件
                            if matched_files < total_expected_files:
                                error_msg = f"缺少 {total_expected_files - matched_files} 个预期文件"
                                all_matched = False
                            
                            if all_matched and matched_files > 0:
                                log(f"所有文件匹配成功: {matched_files}/{total_expected_files}")
                            else:
                                success = False
                                error_msg = f"文件匹配失败: {matched_files}/{total_expected_files}"
                    else:
                        success = False
                        error_msg = "预期结果目录不存在"
                
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
    
    # 获取真实的股票名称
    stock_name = get_real_stock_name(stock_code)
    
    return {
        "downloader": "old",
        "stock_code": stock_code,
        "stock_name": stock_name,
        "success": success,
        "error": error_msg,
        "duration": duration,
        "downloaded_files": len(downloaded_files)
    }

def run_test_with_new_downloader(test_case, config, browser_strategy="playwright"):
    """使用新下载器运行测试"""
    stock_code = test_case["stock_code"]
    log(f"\n使用新下载器测试: {stock_code} (策略: {browser_strategy})")
    
    # 让下载器自己处理目录结构，测试程序不干预
    allowed_keywords = test_case.get("allowed_keywords")
    delete_later = test_case.get("delete_later", True)
    max_pages = test_case.get("max_pages", 5)
    timeout = test_case.get("timeout_seconds", 180)
    suffix = test_case.get("suffix", "research")
    
    start_time = time.time()
    success = False
    error_msg = ""
    downloaded_files = []
    duration = 0
    
    try:
        # 创建临时配置文件
        temp_config_dir = Path(config["save_dir"]) / "temp_config"
        temp_config_dir.mkdir(exist_ok=True)
        
        # 创建临时映射文件 - 使用实际映射数据而不是硬编码
        temp_mapping_file = temp_config_dir / "temp_mapping.json"
        
        # 从主映射文件复制相关股票的映射数据
        from src.data.mapping import MappingManager
        main_mapping = MappingManager("stock_orgid_mapping.json")
        
        test_mapping = {}
        # 只包含当前测试用例的股票代码
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
                "max_downloads_per_session": 5,
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
        
        # 使用统一下载器工厂API（向后兼容）
        from src.factory.downloader_factory import downloader_factory
        from src.interfaces.downloader_interface import DownloadRequest

        # 创建下载器实例，使用指定的浏览器策略（通过适配器保证兼容性）
        downloader = downloader_factory.create_legacy_adapter(
            'download_service_v2',
            save_dir=config["save_dir"],
            mapping_file=str(temp_mapping_file),
            browser_strategy=browser_strategy
        )

        # 获取股票名称
        stock_name = get_real_stock_name(stock_code)

        # 创建DownloadRequest对象（关键修复）
        request = DownloadRequest(
            stock_code=stock_code,
            stock_name=stock_name,
            suffix=suffix,
            allowed_keywords=allowed_keywords,
            max_pages=max_pages,
            delete_later=delete_later,
            timeout_seconds=timeout,
            save_dir=config["save_dir"]
        )

        # 执行下载 - 适配器需要单独参数，而不是DownloadRequest对象
        # 注意：这里强制传入 delete_later=False，因为我们需要保留文件进行最终的目录比对。
        # 清理工作将由 e2e_test.py 在比对完成后，根据 test_case 的配置统一执行。
        download_records = downloader.download_stock_pdfs(
            stock_code=request.stock_code,
            stock_name=request.stock_name,
            suffix=request.suffix,
            allowed_keywords=request.allowed_keywords,
            max_pages=request.max_pages,
            timeout_seconds=request.timeout_seconds,
            save_dir=request.save_dir,
            delete_later=False  # 强制不删除，等待测试脚本统一清理
        )

        # 诊断信息：打印返回值类型
        print(f"[DEBUG] download_stock_pdfs() 返回值类型: {type(download_records)}")
        print(f"[DEBUG] download_stock_pdfs() 返回值: {download_records}")

        duration = time.time() - start_time

        # 检查返回值类型，处理兼容性问题
        if hasattr(download_records, 'downloaded_files'):
            # 如果是 DownloadResult 对象
            actual_files = download_records.downloaded_files
            success = len(actual_files) > 0
        elif isinstance(download_records, dict) and 'downloaded_files' in download_records:
            # 如果是字典格式
            actual_files = download_records['downloaded_files']
            success = len(actual_files) > 0
        elif isinstance(download_records, list):
            # 如果是列表格式
            actual_files = download_records
            success = len(actual_files) > 0
        else:
            # 未知类型，假设是旧的列表格式
            actual_files = download_records
            success = len(actual_files) > 0
        if success:
            log(f"下载成功，获得 {len(actual_files)} 个文件")
        else:
            error_msg = "未下载到任何文件"
            log(error_msg)
        
        # 检查下载的文件（使用从下载器返回的实际文件列表）
        save_dir = Path(config["save_dir"])

        # 使用 actual_files 而不是重新搜索，因为下载器可能使用了不同的保存逻辑
        if success and actual_files:
            # 验证文件是否真实存在
            existing_files = [f for f in actual_files if Path(f).exists()]
            downloaded_files = existing_files  # 更新 downloaded_files 变量
            log(f"找到 {len(existing_files)} 个实际下载文件")

            # 验证结果
            # 检查超时
            if duration > timeout:
                error_msg = f"下载过慢: {duration:.1f}s"
                success = False
            else:
                # 检查文件是否在公司目录（如果不删除）
                if not delete_later:
                    # 查找实际的公司目录（下载器创建的目录）
                    company_dirs = [d for d in save_dir.iterdir() if d.is_dir() and d.name != '.tmp']

                    if not company_dirs:
                        # 检查是否有文件在根目录（兼容旧版本）
                        root_files = [f for f in save_dir.glob("*.pdf")]
                        if root_files:
                            log(f"警告: 未找到公司目录，但在根目录发现 {len(root_files)} 个文件")
                        else:
                            if len(existing_files) == 0:
                                error_msg = "下载器未创建任何公司目录且未找到文件"
                            else:
                                log(f"信息: 下载器报告下载了 {len(existing_files)} 个文件，但未找到对应的目录结构")
                    else:
                        # 检查是否有文件在公司子目录中
                        company_files = []
                        for company_dir in company_dirs:
                            company_files.extend([f for f in company_dir.glob("*.pdf")])

                        if not company_files:
                            root_files = [f for f in save_dir.glob("*.pdf")]
                            if root_files:
                                log(f"警告: 公司目录为空，但在根目录发现 {len(root_files)} 个文件")
                            else:
                                if len(existing_files) == 0:
                                    error_msg = "公司子目录中没有找到PDF文件"
                                else:
                                    log(f"信息: 下载器报告下载了 {len(existing_files)} 个文件，但公司目录为空")
                        else:
                            log(f"发现 {len(company_files)} 个文件在公司目录: {[f.parent.name for f in company_files]}")
        else:
            # 如果没有实际文件，但success为True，说明actual_files为空
            if success and not actual_files:
                error_msg = "下载器报告成功但未返回文件路径"
                success = False

        # 修复：不要覆盖之前的成功判断逻辑
        # success = not error_msg  # 这行代码会覆盖之前所有的成功判断，是错误的
        
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

    # 清理下载器资源（特别是浏览器实例）
    try:
        if 'downloader' in locals() and hasattr(downloader, 'cleanup'):
            downloader.cleanup()
            log(f"下载器资源已清理")
    except Exception as e:
        log(f"清理下载器资源失败: {e}")

    # 读取调试标记（在清理之前）
    debug_markers = []
    debug_summary = {}
    try:
        if 'downloader' in locals():
            # 尝试获取调试标记
            if hasattr(downloader, 'get_debug_markers'):
                debug_markers = downloader.get_debug_markers()
                log(f"获取到 {len(debug_markers)} 个调试标记")

            if hasattr(downloader, 'get_debug_summary'):
                debug_summary = downloader.get_debug_summary()
                log(f"调试标记摘要: 成功={debug_summary.get('successful', 0)}, 失败={debug_summary.get('failed', 0)}")

                # 输出每个步骤的统计
                if 'steps' in debug_summary:
                    for step_name, step_stats in debug_summary['steps'].items():
                        log(f"  - {step_name}: {step_stats['successful']}/{step_stats['total']} 成功")
    except Exception as e:
        log(f"读取调试标记失败: {e}")

    # 确保清理所有临时文件（包括可能残留的临时目录）
    try:
        save_path = Path(save_dir)
        # 清理临时配置目录
        temp_config_path = save_path / "temp_config"
        if temp_config_path.exists():
            shutil.rmtree(temp_config_path, ignore_errors=True)

        # 清理可能残留的Playwright临时目录
        for item in save_path.iterdir():
            if item.is_dir() and (item.name.startswith('playwright_user_') or
                                (len(item.name) == 36 and '-' in item.name)):  # UUID格式
                try:
                    shutil.rmtree(item, ignore_errors=True)
                    log(f"清理残留临时目录: {item.name}")
                except:
                    pass
    except Exception as e:
        log(f"清理残留临时文件失败: {e}")

    log(f"测试完成 (delete_later={delete_later})")

    # 输出结果
    log(f"结果: {'成功' if success else '失败'}")
    if error_msg:
        log(f"错误: {error_msg}")
    log(f"耗时: {duration:.1f}s")

    # 获取真实的股票名称
    stock_name = get_real_stock_name(stock_code)

    # 输出详细的调试信息
    log(f"调试信息:")
    log(f"  - 股票代码: {stock_code}")
    log(f"  - 股票名称: {stock_name}")
    log(f"  - 浏览器策略: {browser_strategy}")
    log(f"  - 下载成功: {success}")
    log(f"  - 下载文件数: {len(downloaded_files)}")
    log(f"  - 错误信息: {error_msg}")
    log(f"  - 耗时: {duration:.1f}s")
    log(f"  - 调试标记数: {len(debug_markers)}")

    return {
        "downloader": "new",
        "browser_strategy": browser_strategy,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "success": success,
        "error": error_msg,
        "duration": duration,
        "downloaded_files": len(downloaded_files),
        "debug_markers": debug_markers,
        "debug_summary": debug_summary
    }

def compare_directories(actual_dir, expected_dir):
    """比较两个目录结构和内容是否完全一致（100%严格模式，不进行任何过滤）"""
    actual_path = Path(actual_dir)
    expected_path = Path(expected_dir)

    if not actual_path.exists() or not expected_path.exists():
        return False, "目录不存在"

    # 创建文件锁防止清理
    lock_files = []
    try:
        # 为所有实际目录中的公司目录加锁
        companies_to_lock = [d.name for d in actual_path.iterdir() if d.is_dir()]

        log(f"开始严格文件比较，为 {len(companies_to_lock)} 个公司目录加锁防止清理...")
        for company_name in companies_to_lock:
            company_dir = actual_path / company_name
            if company_dir.exists():
                lock_file = company_dir / ".lock"
                try:
                    lock_file.touch(exist_ok=True)
                    lock_files.append(lock_file)
                except Exception as e:
                    log(f"警告: 无法为目录 {company_dir} 创建锁文件: {e}")

        # 比较目录结构（100%严格，不进行任何过滤）
        actual_dirs = sorted([p.relative_to(actual_path) for p in actual_path.rglob('*') if p.is_dir()])
        expected_dirs = sorted([p.relative_to(expected_path) for p in expected_path.rglob('*') if p.is_dir()])

        if actual_dirs != expected_dirs:
            return False, f"目录结构不一致:\n  实际: {actual_dirs}\n  预期: {expected_dirs}"

        # 比较文件（100%严格，不进行任何过滤）
        actual_files = sorted([p.relative_to(actual_path) for p in actual_path.rglob('*.pdf')])
        expected_files = sorted([p.relative_to(expected_path) for p in expected_path.rglob('*.pdf')])

        if actual_files != expected_files:
            return False, f"文件列表不一致:\n  实际: {actual_files}\n  预期: {expected_files}"

        # 比较文件内容
        for file_path in expected_files:
            actual_file = actual_path / file_path
            expected_file = expected_path / file_path

            if not compare_files(actual_file, expected_file):
                return False, f"文件内容不一致: {file_path}"

        return True, "所有文件和目录完全匹配"
    finally:
        # 清理锁文件
        log(f"文件比较完成，清理 {len(lock_files)} 个锁文件...")
        for lock_file in lock_files:
            try:
                if lock_file.exists():
                    lock_file.unlink()
            except Exception as e:
                log(f"警告: 无法删除锁文件 {lock_file}: {e}")

def main():
    """主函数"""
    log("开始端到端测试（最终版本）")
    log("严格按照测试说明.md实现")

    # 加载配置（只支持config_end2end_test.json）
    import argparse
    import json
    parser = argparse.ArgumentParser(description='端到端测试')
    parser.add_argument('--test-old-downloader', action='store_true', help='测试旧下载器')
    parser.add_argument('--browser-strategy', choices=['selenium', 'playwright', 'both'],
                       default='playwright', help='浏览器策略模式 (默认: playwright)')
    args = parser.parse_args()
    
    # 始终使用config_end2end_test.json配置文件
    config_file = 'config_end2end_test.json'
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        log(f"加载配置失败: {e}")
        return 1
    
    log(f"使用配置: {config_file}")
    log(f"保存目录: {config['save_dir']}")
    log(f"预期结果目录: {config['expected_result_dir']}")
    log(f"浏览器策略: {args.browser_strategy}")
    
    # 创建必要目录
    save_dir = Path(config["save_dir"])
    Path("logs").mkdir(exist_ok=True)

    # 获取测试用例列表（用于智能清理）
    test_cases = config.get("test_cases", [])

    # === 关键修改：强制重置测试目录 ===
    # 痛点解决：确保每次测试前环境绝对干净，移除所有上一次测试的残留文件（包括.crdownload等垃圾文件）
    log("正在初始化测试环境...")
    try:
        if save_dir.exists():
            log(f"清理旧测试目录: {save_dir}")
            # 使用 shutil.rmtree 彻底删除目录及其所有内容
            shutil.rmtree(save_dir)
            # 稍微等待一下文件系统释放锁（Windows系统特有）
            time.sleep(0.5)
        
        # 重新创建干净的空目录
        save_dir.mkdir(parents=True, exist_ok=True)
        log(f"已创建全新的测试结果目录: {save_dir}")
    except Exception as e:
        log(f"严重错误: 无法重置测试目录: {e}")
        # 如果无法清理目录，测试无法继续，必须报错退出
        return 1
    
    # 验证测试设置
    log("\n验证测试设置...")
    expected_dir = Path(config["expected_result_dir"])
    if not expected_dir.exists():
        log(f"警告: 预期结果目录不存在: {expected_dir}")
    else:
        company_dirs = [d for d in expected_dir.iterdir() if d.is_dir()]
        log(f"发现 {len(company_dirs)} 个预期结果公司目录")
        
        # 检查预期文件总数
        expected_files = list(expected_dir.rglob('*.pdf'))
        log(f"预期文件总数: {len(expected_files)} 个")
        for file in expected_files:
            log(f"  - {file.relative_to(expected_dir)}")
    
    # 运行所有测试用例
    all_results = []
    max_test_retries = 1  # 每个测试用例最大重试次数
    companies_to_compare = []  # 用于存储测试涉及的公司名称

    for i, test_case in enumerate(test_cases, 1):
        log(f"\n{'='*80}")
        log(f"测试用例 {i}/{len(test_cases)}: {test_case['stock_code']}")
        log(f"类型: {test_case.get('suffix', 'research')}")
        log(f"delete_later: {test_case.get('delete_later', True)}")
        log(f"max_pages: {test_case.get('max_pages', 5)}")
        log(f"{'='*80}")
        
        # 测试新下载器（带重试机制）- 根据命令行参数选择策略
        if args.browser_strategy == 'both':
            strategies_to_test = ["playwright", "selenium"]
        else:
            strategies_to_test = [args.browser_strategy]
        
        for strategy in strategies_to_test:
            new_result = None
            for retry in range(max_test_retries + 1):
                try:
                    log(f"测试新下载器({strategy})... (尝试 {retry + 1}/{max_test_retries + 1})")
                    new_result = run_test_with_new_downloader(test_case, config, strategy)
                    
                    # 如果下载成功（无论文件匹配与否），跳出重试循环
                    if new_result.get("downloaded_files", 0) > 0:
                        log(f"下载成功，获得 {new_result['downloaded_files']} 个文件")
                        break
                    else:
                        log(f"下载失败，错误: {new_result.get('error', '未知错误')}")
                        if retry < max_test_retries:
                            log(f"等待 {10 + retry * 5} 秒后重试...")
                            time.sleep(10 + retry * 5)
                        else:
                            log(f"新下载器({strategy})测试达到最大重试次数")
                except Exception as e:
                    log(f"新下载器({strategy})测试异常: {e}")
                    if retry < max_test_retries:
                        log(f"等待 {10 + retry * 5} 秒后重试...")
                        time.sleep(10 + retry * 5)
                    else:
                        log(f"新下载器({strategy})测试达到最大重试次数")
                        new_result = {
                            "downloader": "new",
                            "browser_strategy": strategy,
                            "stock_code": test_case["stock_code"],
                            "stock_name": get_real_stock_name(test_case['stock_code']),
                            "success": False,
                            "error": f"测试异常: {str(e)}",
                            "duration": 0,
                            "downloaded_files": 0
                        }
            
            if new_result:
                all_results.append(new_result)
            
            # DEBUG CHECK
            debug_file = Path(config["save_dir"]) / "中密控股" / "中密控股：2025年一季度报告.pdf"
            log(f"DEBUG: After {strategy}, file exists: {debug_file.exists()}")

        # 测试旧下载器（如果启用）
        if args.test_old_downloader:
            log(f"\n{'='*80}")
            log(f"测试旧下载器: {test_case['stock_code']}")
            log(f"{'='*80}")
            try:
                old_result = run_test_with_old_downloader(test_case, config)
                all_results.append(old_result)
                log(f"旧下载器测试完成: {old_result.get('success', False)}")
                time.sleep(2)  # 旧下载器测试后间隔
            except Exception as e:
                log(f"旧下载器测试异常: {e}")
                old_result = {
                    "downloader": "old",
                    "stock_code": test_case["stock_code"],
                    "success": False,
                    "error": f"旧下载器测试异常: {e}",
                    "duration": 0,
                    "downloaded_files": 0
                }
                all_results.append(old_result)

        # 策略间隔（如果测试多种策略）
        if len(strategies_to_test) > 1:
            time.sleep(5)  # 策略间间隔5秒
        else:
            time.sleep(2)  # 单策略间隔2秒
    
    # 执行最终目录比较
    log(f"\n{'='*80}")
    log("最终目录比较")
    log(f"{'='*80}")

    save_dir = Path(config["save_dir"])
    expected_dir = Path(config["expected_result_dir"])

    # 检查下载的文件总数
    downloaded_files = list(save_dir.rglob('*.pdf'))
    log(f"下载文件总数: {len(downloaded_files)} 个")
    for file in downloaded_files:
        log(f"  - {file.relative_to(save_dir)}")

    # 执行目录比较（100%严格模式，不进行任何过滤）
    log(f"开始100%严格目录比较...")
    comparison_success, comparison_message = compare_directories(save_dir, expected_dir)

    log(f"目录比较结果: {'成功' if comparison_success else '失败'}")
    log(f"比较详情: {comparison_message}")

    # 验证目录结构（严格模式）- 在最终清理前验证
    log(f"\n目录结构验证（严格模式）:")
    from src.utils.directory_manager import DirectoryManager
    directory_manager = DirectoryManager()

    # 获取预期的公司名称列表（只包含测试用例涉及的公司）
    expected_companies = companies_to_compare if companies_to_compare else []
    if not expected_companies and expected_dir.exists():
        # 如果未获取到公司名称，回退到所有目录
        expected_companies = [d.name for d in expected_dir.iterdir() if d.is_dir()]
    log(f"验证目录结构，预期公司: {expected_companies}")

    structure_valid, structure_issues = directory_manager.validate_directory_structure(
        save_dir, expected_companies
    )

    log(f"目录结构验证: {'通过' if structure_valid else '失败'}")
    if not structure_valid:
        for issue in structure_issues:
            log(f"  - {issue}")

    # 在目录验证后，进行最终清理（只删除需要删除的文件）
    log("\n执行最终清理...")
    try:
        from tools.debug.test_helper_cleaner import clean_test_files
        preserve_cases = [case for case in test_cases if not case.get("delete_later", True)]
        clean_result = clean_test_files(config["save_dir"], preserve_cases)
        log(f"清理完成:")
        log(f"  - 删除临时文件: {clean_result.get('cleaned_temp_files', 0)} 个")
        log(f"  - 删除临时目录: {clean_result.get('cleaned_temp_dirs', 0)} 个")
        log(f"  - 删除公司文件: {clean_result['cleaned_files']} 个")
        log(f"  - 删除公司目录: {clean_result['cleaned_dirs']} 个")
        log(f"  - 保留文件: {clean_result['preserved_files']} 个")
        log(f"  - 保留目录: {clean_result['preserved_dirs']} 个")
    except Exception as e:
        log(f"清理失败: {e}")

    # 生成报告
    total_tests = len(all_results)
    successful_downloads = sum(1 for r in all_results if r.get("downloaded_files", 0) > 0)

    # 更新整体测试结果 - 必须100%精确匹配目录结构和文件内容
    # comparison_success已经包含了严格的目录和文件匹配检查
    overall_success = comparison_success
    
    log(f"\n测试总结:")
    log(f"总测试用例: {total_tests}")
    log(f"成功下载: {successful_downloads}")
    log(f"成功率: {successful_downloads/total_tests*100:.1f}%")
    log(f"目录比较: {'通过' if comparison_success else '失败'}")
    log(f"目录结构: {'通过' if structure_valid else '失败'}")
    log(f"整体测试: {'通过' if overall_success else '失败'}")
    
    # 输出详细结果
    log(f"\n详细结果:")
    for result in all_results:
        status = "成功" if result.get("downloaded_files", 0) > 0 else "失败"
        strategy = result.get("browser_strategy", "unknown")
        log(f"  - {result['stock_code']} [{strategy}]: {status} ({result.get('downloaded_files', 0)} 个文件, {result.get('duration', 0):.1f}s)")
    
    # 比较浏览器策略性能
    log(f"\n浏览器策略性能比较:")
    strategy_results = {}
    for result in all_results:
        strategy = result.get("browser_strategy", "selenium")
        if strategy not in strategy_results:
            strategy_results[strategy] = {
                "total_tests": 0,
                "successful_tests": 0,
                "total_duration": 0,
                "total_files": 0,
                "total_errors": 0,
                "error_messages": []
            }
        
        strategy_results[strategy]["total_tests"] += 1
        if result.get("downloaded_files", 0) > 0:
            strategy_results[strategy]["successful_tests"] += 1
            strategy_results[strategy]["total_files"] += result.get("downloaded_files", 0)
        else:
            strategy_results[strategy]["total_errors"] += 1
            if result.get("error"):
                strategy_results[strategy]["error_messages"].append(result["error"])
        strategy_results[strategy]["total_duration"] += result.get("duration", 0)
    
    for strategy, stats in strategy_results.items():
        success_rate = (stats["successful_tests"] / stats["total_tests"] * 100) if stats["total_tests"] > 0 else 0
        avg_duration = stats["total_duration"] / stats["total_tests"] if stats["total_tests"] > 0 else 0
        avg_files = stats["total_files"] / stats["successful_tests"] if stats["successful_tests"] > 0 else 0
        error_rate = (stats["total_errors"] / stats["total_tests"] * 100) if stats["total_tests"] > 0 else 0
        
        log(f"  - {strategy.upper()}:")
        log(f"     成功率: {success_rate:.1f}% ({stats['successful_tests']}/{stats['total_tests']})")
        log(f"     失败率: {error_rate:.1f}% ({stats['total_errors']}/{stats['total_tests']})")
        log(f"     平均耗时: {avg_duration:.1f}s")
        log(f"     平均文件数: {avg_files:.1f} 个/成功测试")
        
        # 显示常见错误信息
        if stats["error_messages"]:
            from collections import Counter
            error_counter = Counter(stats["error_messages"])
            log(f"     常见错误:")
            for error_msg, count in error_counter.most_common(3):
                log(f"        - {count}次: {error_msg}")

    # 生成测试报告
    log("\n生成测试报告...")
    try:
        import json
        from datetime import datetime

        report_data = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "test_type": "e2e",
                "description": "端到端测试报告",
                "config_file": config_file
            },
            "test_cases": test_cases,
            "results": strategy_results,
            "summary": {
                "overall_success": overall_success,
                "total_tests": sum(stats["total_tests"] for stats in strategy_results.values()),
                "successful_tests": sum(stats["successful_tests"] for stats in strategy_results.values()),
                "total_errors": sum(stats["total_errors"] for stats in strategy_results.values()),
                "total_duration": sum(stats["total_duration"] for stats in strategy_results.values()),
                "total_files": sum(stats["total_files"] for stats in strategy_results.values())
            }
        }

        report_file = "e2e_test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        log(f"测试报告已保存到: {report_file}")

    except Exception as e:
        log(f"生成测试报告失败: {e}")

    return 0 if overall_success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)