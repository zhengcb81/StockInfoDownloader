#!/usr/bin/env python3
"""分析测试覆盖率数据"""
import json
from pathlib import Path

def main():
    with open("coverage.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    files_data = []
    for filepath, info in data.get("files", {}).items():
        if "summary" in info:
            summary = info["summary"]
            files_data.append({
                "path": filepath,
                "percent": summary.get("percent_covered", 0),
                "covered": summary.get("covered_lines", 0),
                "total": summary.get("num_statements", 0),
                "missing": summary.get("missing_lines", 0)
            })
    
    # 按覆盖率排序
    files_data.sort(key=lambda x: x["percent"])
    
    print("=" * 70)
    print("测试覆盖率分析报告")
    print("=" * 70)
    
    # 总体统计
    total_covered = sum(f["covered"] for f in files_data)
    total_statements = sum(f["total"] for f in files_data)
    overall = (total_covered / total_statements * 100) if total_statements > 0 else 0
    
    print(f"\n总体覆盖率: {overall:.1f}% ({total_covered}/{total_statements} statements)")
    print(f"分析文件数: {len(files_data)}")
    
    # 分类统计
    low = [f for f in files_data if f["percent"] < 30]
    medium = [f for f in files_data if 30 <= f["percent"] < 70]
    high = [f for f in files_data if f["percent"] >= 70]
    
    print(f"\n覆盖率分布:")
    print(f"  低覆盖率 (<30%):   {len(low)} 个文件")
    print(f"  中覆盖率 (30-70%): {len(medium)} 个文件")
    print(f"  高覆盖率 (≥70%):   {len(high)} 个文件")
    
    # 最低覆盖率的文件
    print(f"\n最低覆盖率的文件 (Top 20):")
    print("-" * 70)
    print(f"{'File':<50} {'Coverage':>10} {'Missing':>8}")
    print("-" * 70)
    for f in files_data[:20]:
        print(f"{f['path']:<50} {f['percent']:>9.1f}% {f['missing']:>8}")
    
    # 按模块分组统计
    print(f"\n\n按模块统计:")
    print("-" * 70)
    modules = {}
    for f in files_data:
        parts = f["path"].split("\\")
        if len(parts) >= 2 and parts[0] == "src":
            module = parts[1] if len(parts) > 1 else "root"
        else:
            module = "other"
        
        if module not in modules:
            modules[module] = {"covered": 0, "total": 0, "files": 0}
        modules[module]["covered"] += f["covered"]
        modules[module]["total"] += f["total"]
        modules[module]["files"] += 1
    
    print(f"{'Module':<20} {'Files':>8} {'Coverage':>12} {'Statements':>12}")
    print("-" * 70)
    for mod, stats in sorted(modules.items(), key=lambda x: x[1]["total"], reverse=True):
        pct = (stats["covered"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"{mod:<20} {stats['files']:>8} {pct:>11.1f}% {stats['total']:>12}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
