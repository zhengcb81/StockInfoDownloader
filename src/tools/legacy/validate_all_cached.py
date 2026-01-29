#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量验证和修正所有缓存的org ID
"""

import json
import time
from typing import Dict

from orgid_utils import _load_mapping
from validate_org_id import (
    invalidate_cache,
    load_validation_config,
    validate_org_id_url,
)


def validate_all_cached_org_ids(
    mapping_file: str = None, fix_invalid: bool = True
) -> Dict[str, any]:
    """
    验证所有缓存的org ID并修正错误

    Args:
        mapping_file: 映射文件路径，从配置读取
        fix_invalid: 是否自动修正无效的org ID

    Returns:
        Dict: 验证结果统计
    """
    from validate_org_id import load_cache_config

    cache_config = load_cache_config()
    if mapping_file is None:
        mapping_file = cache_config.get("mapping_file", "stock_orgid_mapping.json")

    # 加载映射文件
    mapping = _load_mapping(mapping_file)

    if not mapping:
        print("映射文件为空，无需验证")
        return {"total": 0, "valid": 0, "invalid": 0, "fixed": 0, "results": []}

    validation_config = load_validation_config()

    results = []
    stats = {"total": len(mapping), "valid": 0, "invalid": 0, "fixed": 0}

    print(f"开始验证 {len(mapping)} 个缓存的org ID...")

    for stock_code, data in mapping.items():
        org_id = data.get("orgId")
        if not org_id:
            continue

        print(f"验证 {stock_code}: {org_id}...")

        # 验证org ID
        is_valid = validate_org_id_url(stock_code, org_id, validation_config)

        result = {
            "stock_code": stock_code,
            "org_id": org_id,
            "original_data": data,
            "is_valid": is_valid,
            "fixed": False,
        }

        if is_valid:
            stats["valid"] += 1
            print("  有效")
        else:
            stats["invalid"] += 1
            print("  无效")

            if fix_invalid:
                print("  正在重新获取...")
                new_org_id = invalidate_cache(stock_code, mapping_file)

                if new_org_id:
                    stats["fixed"] += 1
                    result["new_org_id"] = new_org_id
                    result["fixed"] = True
                    print(f"  已修正为: {new_org_id}")
                else:
                    print("  修正失败")

        results.append(result)

        # 避免请求过于频繁
        time.sleep(1)

    # 生成报告
    report = {
        **stats,
        "results": results,
        "mapping_file": mapping_file,
        "timestamp": time.time(),
    }

    # 保存验证报告
    report_file = "org_id_validation_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n验证完成:")
    print(f"总数: {stats['total']}")
    print(f"有效: {stats['valid']}")
    print(f"无效: {stats['invalid']}")
    print(f"已修正: {stats['fixed']}")
    print(f"详细报告保存到: {report_file}")

    return report


def generate_test_data_for_units():
    """为单元测试生成测试数据"""
    mapping_file = "stock_orgid_mapping.json"

    if not os.path.exists(mapping_file):
        return []

    with open(mapping_file, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    # 获取前5个作为测试样本
    test_samples = []
    for i, (stock_code, data) in enumerate(list(mapping.items())[:5]):
        test_samples.append(
            {
                "stock_code": stock_code,
                "expected_org_id": data.get("orgId"),
                "test_case": f"test_case_{i+1}",
            }
        )

    test_file = "test_org_id_samples.json"
    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(test_samples, f, ensure_ascii=False, indent=2)

    print(f"生成了 {len(test_samples)} 个测试样本到 {test_file}")
    return test_samples


if __name__ == "__main__":
    import os

    print("=== 开始批量验证所有缓存的org ID ===")

    # 验证所有缓存
    report = validate_all_cached_org_ids(fix_invalid=True)

    # 生成测试数据
    if report["total"] > 0:
        generate_test_data_for_units()

    print("=== 验证完成 ===")
