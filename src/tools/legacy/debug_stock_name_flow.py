#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
追踪stock_name参数传递链路的调试脚本
详细分析Playwright测试中stock_name参数从创建到使用的完整流程
"""

from pathlib import Path
import sys
import os

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def analyze_stock_name_flow():
    """分析stock_name参数的完整传递链路"""

    print("=" * 80)
    print("STOCK_NAME参数传递链路详细分析")
    print("=" * 80)

    # 1. 检查配置文件
    print("\n1. 配置文件分析:")
    config_file = Path("config_end2end_test.json")
    if config_file.exists():
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"   配置文件: {config_file.name}")
        print(f"   保存目录: {config.get('save_dir', 'N/A')}")
        print(f"   预期结果目录: {config.get('expected_result_dir', 'N/A')}")

        # 检查测试用例
        test_cases = config.get('test_cases', [])
        print(f"\n   测试用例数: {len(test_cases)}")
        for i, case in enumerate(test_cases):
            print(f"   用例{i+1}: 股票代码={case['stock_code']}, 后缀={case['suffix']}")
    else:
        print(f"   [ERROR] 配置文件不存在: {config_file}")
        return False

    # 2. 检查MappingManager是否能正确获取stock_name
    print("\n2. 股票名称映射检查:")
    try:
        from src.data.mapping import MappingManager
        mapping_manager = MappingManager("stock_orgid_mapping.json")

        test_stocks = ["301611", "300470"]
        for stock_code in test_stocks:
            stock_name = mapping_manager.get_stock_name(stock_code)
            org_id = mapping_manager.get_org_id(stock_code)
            print(f"   {stock_code}: stock_name={stock_name}, org_id={org_id}")

            if not stock_name:
                print(f"   [WARNING] 无法获取{stock_code}的股票名称")
    except Exception as e:
        print(f"   [ERROR] MappingManager初始化失败: {e}")

    # 3. 检查DownloadRequest的stock_name属性设置
    print("\n3. DownloadRequest对象分析:")
    try:
        from src.interfaces.downloader_interface import DownloadRequest

        # 模拟创建请求
        request = DownloadRequest(
            stock_code="301611",
            suffix="research",
            allowed_keywords=["投资者关系管理信息20250725"],
            max_pages=1,
            save_dir="end2end_test/test_results"
        )

        # 模拟添加stock_name属性（如download_activity_records函数中所做的）
        request.org_id = "org_301611"
        request.stock_name = "珂玛科技"

        print(f"   创建的请求对象:")
        print(f"     stock_code: {request.stock_code}")
        print(f"     suffix: {request.suffix}")
        print(f"     save_dir: {request.save_dir}")
        print(f"     org_id: {getattr(request, 'org_id', 'NOT_SET')}")
        print(f"     stock_name: {getattr(request, 'stock_name', 'NOT_SET')}")

        # 检查hasattr和getattr
        print(f"\n   属性检查:")
        print(f"     hasattr(request, 'stock_name'): {hasattr(request, 'stock_name')}")
        print(f"     hasattr(request, 'org_id'): {hasattr(request, 'org_id')}")

    except Exception as e:
        print(f"   [ERROR] DownloadRequest测试失败: {e}")

    # 4. 检查_real_download_file函数的逻辑
    print("\n4. _real_download_file函数逻辑分析:")
    print("   关键代码段:")
    print("   ```python")
    print("   stock_name = None")
    print("   if request and hasattr(request, 'stock_name'):")
    print("       stock_name = request.stock_name")
    print("   elif self.current_request and hasattr(self.current_request, 'stock_name'):")
    print("       stock_name = self.current_request.stock_name")
    print("   ")
    print("   if stock_name:")
    print("       save_path = Path(save_dir) / stock_name / filename")
    print("   else:")
    print("       save_path = Path(save_dir) / filename  # 保存到根目录!")
    print("   ```")

    # 5. 模拟执行路径分析
    print("\n5. 执行路径模拟:")
    print("   下载流程:")
    print("   download_activity_records()")
    print("   → 创建DownloadRequest，设置stock_name属性")
    print("   → download_stock_pdfs(request)")
    print("   → _perform_download(request)")
    print("   → _download_with_pagination(request)")
    print("   → _process_download_links(links, request)")
    print("   → _download_file(url, filename, save_dir, request)")
    print("   → _real_download_file(url, filename, save_dir, request)")
    print("   → 检查request.stock_name是否存在")
    print("   → 决定保存路径")

    # 6. 潜在问题分析
    print("\n6. 潜在问题分析:")
    print("   [可能问题1] request参数在传递过程中可能被修改或丢失")
    print("   [可能问题2] stock_name属性可能未被正确设置")
    print("   [可能问题3] request可能为None或不包含stock_name属性")
    print("   [可能问题4] current_request可能未正确保存请求信息")

    # 7. 建议的debug检查点
    print("\n7. 建议的Debug检查点:")
    print("   在以下位置添加print语句:")
    print("   1) download_activity_records() - 设置stock_name后")
    print("   2) download_stock_pdfs() - 接收request后")
    print("   3) _perform_download() - 接收request后")
    print("   4) _download_with_pagination() - 接收request后")
    print("   5) _process_download_links() - 接收request后")
    print("   6) _download_file() - 接收request后")
    print("   7) _real_download_file() - 检查request和stock_name")

    return True

def check_current_debug_markers():
    """检查现有的debug标记文件"""
    print("\n" + "=" * 80)
    print("现有Debug标记文件分析")
    print("=" * 80)

    debug_dir = Path("logs/debug_markers")
    if debug_dir.exists():
        jsonl_files = list(debug_dir.glob("*.jsonl"))
        print(f"发现 {len(jsonl_files)} 个debug标记文件:")

        for file in jsonl_files[-3:]:  # 只显示最近的3个
            print(f"\n文件: {file.name}")
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    print(f"  标记数量: {len(lines)}")
                    if lines:
                        # 显示最后几个标记
                        for line in lines[-3:]:
                            import json
                            data = json.loads(line.strip())
                            print(f"    - {data['step']}: {data['success']}")
            except Exception as e:
                print(f"    读取失败: {e}")
    else:
        print("Debug标记目录不存在")

def check_actual_vs_expected_structure():
    """检查实际vs预期的目录结构"""
    print("\n" + "=" * 80)
    print("目录结构对比分析")
    print("=" * 80)

    actual_dir = Path("end2end_test/test_results")
    expected_dir = Path("end2end_test/expected_results")

    print(f"\n实际目录: {actual_dir}")
    print(f"存在性: {actual_dir.exists()}")

    if actual_dir.exists():
        # 列出所有文件和目录
        items = list(actual_dir.iterdir())
        print(f"项目数: {len(items)}")

        for item in items:
            if item.is_file():
                print(f"  [文件] {item.name}")
            elif item.is_dir():
                print(f"  [目录] {item.name}/")
                # 显示目录内容
                for subitem in item.iterdir():
                    if subitem.is_file():
                        print(f"        [文件] {subitem.name}")

    print(f"\n预期目录: {expected_dir}")
    print(f"存在性: {expected_dir.exists()}")

    if not expected_dir.exists():
        print("  [ERROR] 预期目录不存在，无法进行比较")
        print("  [建议] 需要先创建预期结果目录结构")

    # 检查PDF文件分布
    print(f"\nPDF文件分布分析:")
    if actual_dir.exists():
        all_pdfs = list(actual_dir.rglob("*.pdf"))
        root_pdfs = [f for f in all_pdfs if f.parent == actual_dir]
        subdir_pdfs = [f for f in all_pdfs if f.parent != actual_dir]

        print(f"  总PDF数: {len(all_pdfs)}")
        print(f"  根目录PDF: {len(root_pdfs)}")
        print(f"  子目录PDF: {len(subdir_pdfs)}")

        if root_pdfs:
            print(f"\n  [问题] 发现 {len(root_pdfs)} 个文件在根目录:")
            for pdf in root_pdfs:
                print(f"    - {pdf.name}")
            print(f"  [原因] stock_name参数未正确传递，导致保存路径错误")
        else:
            print(f"\n  [正常] 所有文件都在公司子目录中")

if __name__ == "__main__":
    analyze_stock_name_flow()
    check_current_debug_markers()
    check_actual_vs_expected_structure()

    print("\n" + "=" * 80)
    print("分析完成")
    print("=" * 80)