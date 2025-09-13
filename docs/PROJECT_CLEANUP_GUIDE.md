# 项目清理指南

## 📋 概述

本文档描述了StockInfoDownloader项目的清理过程和最佳实践，帮助维护代码库的整洁性和可维护性。

## 🎯 清理目标

- **移除临时文件**: 清理开发过程中产生的调试文件和临时数据
- **整理工具分类**: 将相关工具按功能分类存放
- **优化项目结构**: 保持清晰的项目目录结构
- **提高维护性**: 减少代码库中的杂乱文件

## 🗑️ 已清理的文件类型

### 1. 调试文件
移动至 `tools/debug/` 目录：
- `debug_download.py` - 下载功能调试脚本
- `debug_links.py` - 链接查找调试脚本
- `test_download_fix.py` - 下载修复测试脚本
- `test_helper_cleaner.py` - 清理助手测试脚本

### 2. 验证工具
移动至 `tools/validators/` 目录：
- `validate_page_content.py` - 页面内容验证工具
- `quick_validate_pages.py` - 快速页面验证工具

### 3. 临时目录
已删除的目录：
- `debug_downloads/` - 调试下载输出目录
- `test_debug/` - 测试调试目录
- `test_temp/` - 临时测试目录
- `end2end_test/` - 端到端测试临时输出目录

### 4. 临时数据文件
已删除的文件：
- `debug_page_source.html` - 调试页面源码
- `page_monitor_*.json` - 页面监控临时数据
- `temp_missing_file_test.json` - 临时测试配置
- `test_case3_config.json` - 测试用例配置

## 📁 优化后的目录结构

```
tools/
├── debug/                          # 调试工具
│   ├── debug_download.py           # 下载调试
│   ├── debug_links.py              # 链接调试
│   ├── test_download_fix.py        # 下载修复测试
│   └── test_helper_cleaner.py     # 清理助手测试
├── validators/                     # 验证工具
│   ├── validate_page_content.py   # 页面内容验证
│   └── quick_validate_pages.py    # 快速页面验证
├── content_validator.py            # 内容验证工具
├── page_monitor.py               # 页面监控工具
└── README.md                     # 工具使用说明
```

## 🛠️ 清理最佳实践

### 1. 文件分类原则
- **调试文件**: 放入 `tools/debug/`
- **验证工具**: 放入 `tools/validators/`
- **通用工具**: 放入 `tools/` 根目录
- **测试文件**: 放入 `tests/` 相应目录

### 2. 临时文件处理
- 开发完成后立即清理调试文件
- 使用版本控制忽略临时文件模式
- 定期检查和清理临时目录

### 3. 工具管理
- 为每个工具提供明确的使用说明
- 保持工具代码的可维护性
- 避免工具之间的功能重复

## 🔍 清理检查清单

### 定期清理项目
- [ ] 检查根目录是否有临时文件
- [ ] 清理 `downloads/` 目录中的测试文件
- [ ] 检查 `logs/` 目录大小，必要时清理旧日志
- [ ] 清理 `__pycache__/` 目录
- [ ] 清理 `.pytest_cache/` 目录

### 开发完成后
- [ ] 移动调试文件到 `tools/debug/`
- [ ] 删除临时目录和数据文件
- [ ] 更新相关文档
- [ ] 验证项目仍能正常运行

### 发布前
- [ ] 确保没有调试代码提交到主分支
- [ ] 清理所有临时文件和目录
- [ ] 验证测试完整性
- [ ] 更新版本和变更日志

## 📋 清理脚本

### 自动清理脚本
创建 `tools/cleanup.py` 用于自动清理：

```python
#!/usr/bin/env python3
"""
项目清理脚本
自动清理临时文件和目录
"""

import os
import shutil
from pathlib import Path

def cleanup_project():
    """执行项目清理"""
    project_root = Path(__file__).parent.parent

    # 要删除的临时目录
    temp_dirs = [
        "debug_downloads",
        "test_debug",
        "test_temp",
        "end2end_test",
        "__pycache__",
        ".pytest_cache"
    ]

    # 要删除的临时文件模式
    temp_file_patterns = [
        "debug_page_source.html",
        "page_monitor_*.json",
        "temp_*.json",
        "test_case*.json",
        "*.tmp",
        "*.log"
    ]

    # 删除临时目录
    for dir_name in temp_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists() and dir_path.is_dir():
            try:
                shutil.rmtree(dir_path)
                print(f"✅ 删除目录: {dir_name}")
            except Exception as e:
                print(f"❌ 删除目录失败 {dir_name}: {e}")

    # 删除临时文件
    for pattern in temp_file_patterns:
        for file_path in project_root.glob(pattern):
            try:
                if file_path.is_file():
                    file_path.unlink()
                    print(f"✅ 删除文件: {file_path.name}")
            except Exception as e:
                print(f"❌ 删除文件失败 {file_path}: {e}")

    print("🎉 项目清理完成!")

if __name__ == "__main__":
    cleanup_project()
```

## 📝 维护指南

### 1. 日常维护
- 每次开发完成后清理临时文件
- 定期运行清理脚本
- 保持目录结构整洁

### 2. 团队协作
- 在 `.gitignore` 中添加临时文件模式
- 建立代码审查时检查文件清理
- 使用pre-commit钩子进行自动清理

### 3. 版本控制
- 避免提交临时文件到版本控制
- 使用分支进行开发和调试
- 合并前清理分支

## 🎯 清理效果

### 清理前
- 根目录散布调试文件
- 多个临时目录占用空间
- 项目结构混乱

### 清理后
- 清晰的目录结构
- 工具按功能分类
- 更好的可维护性
- 减少版本控制噪音

## 📚 相关文档

- [项目结构说明](../README.md#项目结构)
- [开发指南](../CLAUDE.md)
- [测试工具文档](TESTING_TOOLS.md)

---

**维护说明**: 本文档应随项目结构调整而更新，确保清理指南的准确性和时效性。

**最后更新**: 2025年9月13日