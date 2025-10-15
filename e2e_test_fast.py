#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速端到端测试 - 优化性能版本
"""

import os
import sys
import json
import time
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def log(message):
    """记录日志"""
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {message}")
    except UnicodeEncodeError:
        # 处理编码问题
        safe_message = message.encode('gbk', errors='replace').decode('gbk')
        print(f"[{time.strftime('%H:%M:%S')}] {safe_message}")

def run_fast_e2e_test():
    """运行快速端到端测试"""
    log("开始快速端到端测试...")

    # 加载配置文件
    config_path = "config_end2end_test.json"
    if not os.path.exists(config_path):
        log(f"配置文件不存在: {config_path}")
        return False

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 创建测试目录
    save_dir = Path(config.get('save_dir', 'end2end_test/test_results'))
    save_dir.mkdir(parents=True, exist_ok=True)

    # 清理之前的测试结果
    if save_dir.exists():
        shutil.rmtree(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    test_cases = config.get('test_cases', [])
    total_cases = len(test_cases)
    successful_cases = 0

    log(f"共有 {total_cases} 个测试案例")

    for i, test_case in enumerate(test_cases, 1):
        log(f"\n=== 测试案例 {i}/{total_cases} ===")
        log(f"股票代码: {test_case.get('stock_code')}")
        log(f"类型: {test_case.get('suffix')}")
        log(f"目标文件: {test_case.get('allowed_keywords')}")

        try:
            from src.services.downloader_v2 import DownloadServiceV2

            # 创建下载器 - 使用优化配置
            downloader = DownloadServiceV2(
                save_dir=str(save_dir),
                browser_strategy="playwright"
            )

            log("下载器创建成功")

            # 准备目标页面配置
            target_pages = [{
                "suffix": test_case.get('suffix'),
                "allowed_keywords": test_case.get('allowed_keywords'),
                "max_pages": test_case.get('max_pages', 1)
            }]

            # 下载文件
            start_time = time.time()
            result = downloader.download_stock_pdfs(
                stock_code=test_case.get('stock_code'),
                target_pages=target_pages,
                max_retries=test_case.get('max_retries', 1)  # 减少重试次数
            )
            end_time = time.time()
            duration = end_time - start_time

            if result:
                log(f"✅ 下载成功! 耗时: {duration:.2f}秒")

                # 检查下载的文件
                stock_name = downloader.mapping_manager.get_stock_name(test_case.get('stock_code'))
                test_dir = save_dir / stock_name

                if test_dir.exists():
                    files = list(test_dir.glob("*.pdf"))
                    if files:
                        log(f"找到 {len(files)} 个文件:")
                        for file in files:
                            log(f"  - {file.name} ({file.stat().st_size} bytes)")

                        # 检查是否下载了目标文件
                        target_keywords = test_case.get('allowed_keywords', [])
                        target_files = []
                        for keyword in target_keywords:
                            target_files.extend([f for f in files if keyword in f.name])

                        if target_files:
                            log(f"✅ 成功下载目标文件: {target_files[0].name}")
                            successful_cases += 1
                        else:
                            log("❌ 未找到目标文件")
                    else:
                        log("❌ 下载目录为空")
                else:
                    log("❌ 下载目录不存在")
            else:
                log("❌ 下载失败")

        except Exception as e:
            log(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()

    # 总体结果
    log(f"\n=== 总体结果 ===")
    log(f"成功案例: {successful_cases}/{total_cases}")

    if successful_cases == total_cases:
        log("🎉 所有测试案例全部通过！")
        return True
    else:
        log("❌ 有测试案例失败")
        return False

if __name__ == "__main__":
    success = run_fast_e2e_test()
    log(f"\n测试结果: {'成功' if success else '失败'}")
    sys.exit(0 if success else 1)