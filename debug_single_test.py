#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
单个测试用例调试脚本
专门用于调试stock_name参数传递问题
"""

import sys
import json
import time
from pathlib import Path

# 设置路径
sys.path.insert(0, str(Path(__file__).parent))

def run_single_test():
    """运行单个测试用例进行调试"""

    print("=" * 80)
    print("单个测试用例调试 - stock_name参数追踪")
    print("=" * 80)

    # 加载配置
    config_file = "config_end2end_test.json"
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 只使用第一个测试用例
    test_case = config['test_cases'][0]

    print(f"\n测试用例配置:")
    print(f"  股票代码: {test_case['stock_code']}")
    print(f"  后缀: {test_case['suffix']}")
    print(f"  关键词: {test_case['allowed_keywords']}")
    print(f"  最大页数: {test_case['max_pages']}")
    print(f"  保存目录: {config['save_dir']}")

    # 清理之前的测试结果
    save_dir = Path(config['save_dir'])
    if save_dir.exists():
        import shutil
        shutil.rmtree(save_dir)
        print(f"\n清理旧的测试结果: {save_dir}")

    # 导入必要的模块
    from src.services.unified_downloader import UnifiedDownloader
    from src.interfaces.downloader_interface import DownloadRequest

    # 创建下载器实例
    print(f"\n创建UnifiedDownloader实例...")
    downloader_config = {
        'save_dir': config['save_dir'],
        'browser_strategy': 'playwright',
        'headless': True
    }

    downloader = UnifiedDownloader(downloader_config)

    # 获取股票名称和org_id
    from src.data.mapping import MappingManager
    mapping_manager = MappingManager("stock_orgid_mapping.json")

    stock_name = mapping_manager.get_stock_name(test_case['stock_code'])
    org_id = mapping_manager.get_org_id(test_case['stock_code'])

    print(f"\n从MappingManager获取:")
    print(f"  stock_name: {stock_name}")
    print(f"  org_id: {org_id}")

    # 创建请求对象（模拟download_activity_records的逻辑）
    print(f"\n创建DownloadRequest对象...")
    request = DownloadRequest(
        stock_code=test_case['stock_code'],
        suffix=test_case['suffix'],
        allowed_keywords=test_case['allowed_keywords'],
        max_pages=test_case['max_pages'],
        save_dir=config['save_dir']
    )

    # 使用setattr添加额外字段（如download_activity_records中所做的）
    request.org_id = org_id
    request.stock_name = stock_name

    print(f"  request.stock_code: {request.stock_code}")
    print(f"  request.suffix: {request.suffix}")
    print(f"  request.save_dir: {request.save_dir}")
    print(f"  request.org_id: {getattr(request, 'org_id', 'NOT_SET')}")
    print(f"  request.stock_name: {getattr(request, 'stock_name', 'NOT_SET')}")

    # 执行下载
    print(f"\n开始执行下载...")
    print(f"{'='*60}")

    try:
        result = downloader.download_stock_pdfs(request)

        print(f"\n{'='*60}")
        print(f"下载结果:")
        print(f"  成功: {result.success}")
        print(f"  下载文件数: {result.total_files}")
        print(f"  错误数: {len(result.errors)}")
        print(f"  下载的文件:")
        for f in result.downloaded_files:
            print(f"    - {f}")

        if result.errors:
            print(f"  错误信息:")
            for e in result.errors:
                print(f"    - {e}")

        # 检查目录结构
        print(f"\n目录结构检查:")
        if save_dir.exists():
            items = list(save_dir.iterdir())
            print(f"  目录内容 ({len(items)} 项):")
            for item in items:
                if item.is_file():
                    print(f"    [文件] {item.name}")
                elif item.is_dir():
                    print(f"    [目录] {item.name}/")
                    for subitem in item.iterdir():
                        if subitem.is_file():
                            print(f"          [文件] {subitem.name}")

            # 检查PDF分布
            all_pdfs = list(save_dir.rglob("*.pdf"))
            root_pdfs = [f for f in all_pdfs if f.parent == save_dir]
            subdir_pdfs = [f for f in all_pdfs if f.parent != save_dir]

            print(f"\n  PDF文件分布:")
            print(f"    总PDF数: {len(all_pdfs)}")
            print(f"    根目录PDF: {len(root_pdfs)}")
            print(f"    子目录PDF: {len(subdir_pdfs)}")

            if root_pdfs:
                print(f"\n  [问题] 发现 {len(root_pdfs)} 个文件在根目录:")
                for pdf in root_pdfs:
                    print(f"    - {pdf.name}")
            else:
                print(f"\n  [正常] 所有文件都在公司子目录中")
        else:
            print(f"  [错误] 保存目录不存在: {save_dir}")

        # 显示调试摘要
        print(f"\n调试摘要:")
        summary = downloader.get_debug_summary()
        print(f"  总标记数: {summary['total_markers']}")
        print(f"  成功: {summary['successful']}")
        print(f"  失败: {summary['failed']}")
        print(f"  成功率: {summary['success_rate']:.1f}%")

        print(f"\n详细标记:")
        markers = downloader.get_debug_markers()
        for marker in markers:
            status = "[OK]" if marker['success'] else "[FAIL]"
            print(f"  {status} {marker['step']}: {marker.get('details', {})}")
            if marker.get('error'):
                print(f"      错误: {marker['error']}")

        # 清理资源
        downloader.cleanup()

        return result.success

    except Exception as e:
        print(f"\n[错误] 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_single_test()
    sys.exit(0 if success else 1)