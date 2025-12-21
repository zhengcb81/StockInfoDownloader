#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试目录结构问题的脚本
详细分析Playwright测试中的目录结构问题
"""

from pathlib import Path
import os

def debug_directory_structure():
    """详细分析目录结构问题"""

    actual_dir = Path("end2end_test/test_results")
    expected_dir = Path("end2end_test/expected_results")

    print("=" * 80)
    print("目录结构问题详细分析")
    print("=" * 80)

    # 1. 检查目录是否存在
    print(f"\n1. 目录存在性检查:")
    print(f"   实际目录存在: {actual_dir.exists()}")
    print(f"   预期目录存在: {expected_dir.exists()}")

    if not actual_dir.exists():
        print("   ❌ 实际目录不存在，无法继续分析")
        return

    if not expected_dir.exists():
        print("   [WARNING] 预期目录不存在，无法进行比较")
        print("   这可能是导致测试失败的根本原因")

    # 2. 显示实际目录内容
    print(f"\n2. 实际目录内容:")
    print(f"   路径: {actual_dir}")

    # 列出所有文件和目录
    all_items = list(actual_dir.iterdir())
    print(f"   根目录项目数: {len(all_items)}")
    for item in all_items:
        if item.is_file():
            print(f"   [FILE] 文件: {item.name}")
        elif item.is_dir():
            print(f"   [DIR] 目录: {item.name}")
            # 显示目录内容
            for subitem in item.iterdir():
                if subitem.is_file():
                    print(f"      [FILE] {subitem.name}")
                elif subitem.is_dir():
                    print(f"      [DIR] {subitem.name}")

    # 3. 分析PDF文件分布
    print(f"\n3. PDF文件分布分析:")
    pdf_files = list(actual_dir.rglob("*.pdf"))
    print(f"   总PDF文件数: {len(pdf_files)}")

    root_pdfs = [f for f in pdf_files if f.parent == actual_dir]
    subdir_pdfs = [f for f in pdf_files if f.parent != actual_dir]

    print(f"   根目录PDF: {len(root_pdfs)}")
    for pdf in root_pdfs:
        print(f"      [PDF] {pdf.name}")

    print(f"   子目录PDF: {len(subdir_pdfs)}")
    for pdf in subdir_pdfs:
        print(f"      [PDF] {pdf.relative_to(actual_dir)}")

    # 4. 分析目录结构问题
    print(f"\n4. 目录结构问题诊断:")

    # 检查是否有文件在根目录
    if root_pdfs:
        print(f"   [ERROR] 发现 {len(root_pdfs)} 个文件在根目录，应该在公司子目录中")
        print("   这是导致目录比较失败的主要原因")

    # 检查公司目录
    company_dirs = [d for d in actual_dir.iterdir() if d.is_dir()]
    print(f"   公司目录数: {len(company_dirs)}")
    for dir_name in company_dirs:
        print(f"      [DIR] {dir_name.name}")

    # 5. 检查预期的公司名称
    print(f"\n5. 预期的公司目录:")
    expected_companies = ["珂玛科技", "中密控股"]
    for company in expected_companies:
        company_path = actual_dir / company
        exists = company_path.exists()
        status = "[OK]" if exists else "[MISSING]"
        print(f"   {status} {company}: {exists}")

    # 6. 分析文件命名问题
    print(f"\n6. 文件命名分析:")
    for pdf in pdf_files:
        relative_path = pdf.relative_to(actual_dir)
        parts = relative_path.parts
        if len(parts) == 1:
            print(f"   [WARNING] 根目录文件: {pdf.name}")
        elif len(parts) == 2:
            company, filename = parts
            print(f"   [OK] 公司目录文件: {company}/{filename}")
        else:
            print(f"   [ERROR] 深层嵌套: {relative_path}")

    # 7. 检查配置文件
    print(f"\n7. 配置文件检查:")
    config_file = Path("config_end2end_test.json")
    if config_file.exists():
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"   配置文件: {config_file.name}")
        print(f"   保存目录: {config.get('save_dir', 'N/A')}")
        print(f"   预期结果目录: {config.get('expected_result_dir', 'N/A')}")
    else:
        print(f"   [ERROR] 配置文件不存在: {config_file}")

    print(f"\n8. 问题总结:")
    print(f"   根目录文件数: {len(root_pdfs)} (应该为0)")
    print(f"   子目录文件数: {len(subdir_pdfs)}")
    print(f"   公司目录数: {len(company_dirs)}")

    if len(root_pdfs) > 0:
        print(f"\n   [ROOT_CAUSE] 根本原因: 下载器将文件保存到了根目录而不是公司子目录")
        print(f"   [ACTION] 需要检查下载器的目录创建逻辑")
    else:
        print(f"\n   [SUCCESS] 目录结构正常")

    return len(root_pdfs) > 0

if __name__ == "__main__":
    has_issue = debug_directory_structure()
    exit(1 if has_issue else 0)