#!/usr/bin/env python3
"""
保护expected_results目录，防止被其他程序污染。

基于config_e2e_official.json配置文件，验证目录结构并设置保护措施。

设计原则：
1. 无硬编码 - 所有数据来自配置文件
2. 配置驱动 - 使用项目的映射系统和配置文件
3. 可重复执行 - 可以定期运行作为维护任务

用法：
python tools/protect_expected_results.py [--config CONFIG_FILE] [--dry-run] [--lock]

参数：
--config: 配置文件路径，默认为config_e2e_official.json
--dry-run: 只显示将要进行的操作，不实际执行
--lock: 设置目录只读权限（如果支持）
"""

import os
import sys
import json
import argparse
import shutil
import stat
from pathlib import Path
from typing import Set, Dict, List, Optional

def parse_arguments():
    parser = argparse.ArgumentParser(description="保护expected_results目录")
    parser.add_argument('--config', default='config_e2e_official.json',
                       help='配置文件路径（默认：config_e2e_official.json）')
    parser.add_argument('--dry-run', action='store_true',
                       help='只显示将要进行的操作，不实际执行')
    parser.add_argument('--lock', action='store_true',
                       help='设置目录只读权限')
    return parser.parse_args()

def load_config(config_path: Path) -> dict:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"错误：加载配置文件失败: {e}")
        raise

def get_stock_name_from_code(stock_code: str, mapping_manager=None) -> Optional[str]:
    """
    获取股票代码对应的公司名称。

    优先使用MappingManager，如果不可用则尝试从映射文件直接读取。
    """
    try:
        # 尝试使用MappingManager
        if mapping_manager:
            name = mapping_manager.get_stock_name(stock_code)
            if name:
                return name
    except:
        pass

    # 备选方案：直接读取映射文件
    mapping_files = [
        Path("configs/stock_orgid_mapping.json"),
        Path("src/data/stock_orgid_mapping.json"),
        Path("stock_orgid_mapping.json")
    ]

    for mapping_file in mapping_files:
        if mapping_file.exists():
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                    if stock_code in mapping_data:
                        item = mapping_data[stock_code]
                        # 兼容不同字段名
                        return item.get('name') or item.get('stock_name') or stock_code
            except:
                continue

    # 如果找不到映射，返回股票代码作为备用
    print(f"警告：找不到股票代码 {stock_code} 的映射，使用代码作为目录名")
    return stock_code

def analyze_configuration(config: dict) -> dict:
    """
    分析配置文件，获取预期的目录结构。

    返回:
        expected_result_dir: Path - 预期结果目录路径
        expected_structure: Dict[str, List[str]] - 预期目录结构和文件模式
    """
    expected_result_dir = Path(config.get('expected_result_dir', 'end2end_test/expected_results'))
    test_cases = config.get('test_cases', [])

    # 尝试导入MappingManager（可选）
    mapping_manager = None
    try:
        sys.path.insert(0, str(Path.cwd()))
        from src.data.mapping import MappingManager
        mapping_manager = MappingManager()
        print("[OK] 已加载映射管理器")
    except ImportError as e:
        print(f"信息：无法导入MappingManager，使用备用方法: {e}")

    # 构建预期结构
    expected_structure = {}

    for test_case in test_cases:
        stock_code = test_case.get('stock_code')
        if not stock_code:
            print("警告：测试用例缺少stock_code字段")
            continue

        # 获取公司名称
        company_name = get_stock_name_from_code(stock_code, mapping_manager)
        if not company_name:
            company_name = stock_code

        # 获取允许的关键词
        allowed_keywords = test_case.get('allowed_keywords', [])

        # 添加到预期结构
        if company_name not in expected_structure:
            expected_structure[company_name] = []

        # 添加关键词作为文件匹配模式
        for keyword in allowed_keywords:
            expected_structure[company_name].append(keyword)

    return {
        'expected_result_dir': expected_result_dir,
        'expected_structure': expected_structure
    }

def validate_directory_structure(expected_dir: Path, expected_structure: Dict[str, List[str]],
                                dry_run: bool = False) -> bool:
    """
    验证目录结构是否符合预期。

    返回:
        bool: 验证是否成功（True表示结构正确或已修复）
    """
    if not expected_dir.exists():
        print(f"错误：预期结果目录不存在: {expected_dir}")
        return False

    all_valid = True

    # 检查预期目录是否存在
    for expected_company, patterns in expected_structure.items():
        company_dir = expected_dir / expected_company

        if not company_dir.exists():
            print(f"错误：缺少预期目录: {expected_company}")
            all_valid = False
            continue

        if not company_dir.is_dir():
            print(f"错误：{expected_company} 不是目录")
            all_valid = False
            continue

    # 检查多余目录
    expected_companies = set(expected_structure.keys())
    actual_dirs = [d for d in expected_dir.iterdir() if d.is_dir()]

    extra_dirs = []
    for actual_dir in actual_dirs:
        if actual_dir.name not in expected_companies:
            extra_dirs.append(actual_dir)

    if extra_dirs:
        print(f"发现 {len(extra_dirs)} 个多余目录:")
        for d in extra_dirs:
            print(f"  - {d}")
        all_valid = False

        if not dry_run:
            print("正在删除多余目录...")
            for d in extra_dirs:
                try:
                    shutil.rmtree(d)
                    print(f"  已删除: {d}")
                except Exception as e:
                    print(f"  删除失败 {d}: {e}")
                    all_valid = False
        else:
            print("  (dry-run) 将删除这些目录")

    # 检查每个公司目录中的文件
    for expected_company, patterns in expected_structure.items():
        company_dir = expected_dir / expected_company
        if not company_dir.exists():
            continue

        # 获取目录中所有文件
        try:
            all_files = [f for f in company_dir.iterdir() if f.is_file()]
        except:
            print(f"警告：无法读取目录 {company_dir}")
            continue

        # 检查是否有文件不匹配任何模式
        extra_files = []
        for file_path in all_files:
            matched = False
            for pattern in patterns:
                if pattern in file_path.name:
                    matched = True
                    break

            if not matched:
                extra_files.append(file_path)

        if extra_files:
            print(f"在目录 {expected_company} 中发现 {len(extra_files)} 个不匹配的文件:")
            for f in extra_files:
                print(f"  - {f.name}")
            all_valid = False

            if not dry_run:
                print(f"正在删除不匹配的文件...")
                for f in extra_files:
                    try:
                        f.unlink()
                        print(f"  已删除: {f.name}")
                    except Exception as e:
                        print(f"  删除失败 {f.name}: {e}")
                        all_valid = False
            else:
                print("  (dry-run) 将删除这些文件")

    return all_valid

def set_directory_lock(directory: Path, dry_run: bool = False) -> bool:
    """
    设置目录为只读（如果平台支持）。

    注意：Windows的只读权限可能不如Unix-like系统严格。
    """
    if not directory.exists():
        print(f"错误：目录不存在: {directory}")
        return False

    if dry_run:
        print(f"(dry-run) 将设置目录只读: {directory}")
        return True

    try:
        # 在Unix-like系统上设置只读权限
        if hasattr(os, 'chmod'):
            # 移除所有写权限
            current_mode = directory.stat().st_mode
            new_mode = current_mode & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH
            os.chmod(str(directory), new_mode)

            # 递归设置子目录和文件
            for root, dirs, files in os.walk(str(directory)):
                for name in dirs:
                    dirpath = Path(root) / name
                    dir_mode = dirpath.stat().st_mode
                    dir_new_mode = dir_mode & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH
                    os.chmod(str(dirpath), dir_new_mode)

                for name in files:
                    filepath = Path(root) / name
                    file_mode = filepath.stat().st_mode
                    file_new_mode = file_mode & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH
                    os.chmod(str(filepath), file_new_mode)

            print(f"[OK] 已设置目录只读权限: {directory}")
            return True
        else:
            print(f"警告：当前平台不支持chmod，无法设置只读权限")
            return False

    except Exception as e:
        print(f"[ERROR] 设置只读权限失败: {e}")
        return False

def main():
    args = parse_arguments()

    # 加载配置文件
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"错误：配置文件不存在: {config_path}")
        return 1

    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"错误：无法处理配置文件: {e}")
        return 1

    # 分析配置
    try:
        analysis = analyze_configuration(config)
        expected_dir = analysis['expected_result_dir']
        expected_structure = analysis['expected_structure']
    except Exception as e:
        print(f"错误：分析配置失败: {e}")
        return 1

    print(f"配置文件: {config_path}")
    print(f"预期结果目录: {expected_dir}")
    print(f"预期目录结构:")
    for company, patterns in expected_structure.items():
        print(f"  - {company}: {patterns}")

    # 验证目录结构
    print(f"\n验证目录结构...")
    if not validate_directory_structure(expected_dir, expected_structure, args.dry_run):
        print("[ERROR] 目录验证失败")
        return 1

    print("[OK] 目录结构验证通过")

    # 设置目录锁定
    if args.lock:
        print(f"\n设置目录锁定...")
        if set_directory_lock(expected_dir, args.dry_run):
            print("[OK] 目录锁定成功")
        else:
            print("[WARNING] 目录锁定失败或部分失败")

    # 提供后续建议
    print(f"\n建议:")
    print(f"1. 定期运行此脚本以维护目录完整性")
    print(f"2. 可以将此脚本添加到git pre-commit钩子")
    print(f"3. 或设置为定时任务定期执行")
    print(f"4. 使用 --lock 参数保护目录不被修改")

    return 0

if __name__ == '__main__':
    sys.exit(main())