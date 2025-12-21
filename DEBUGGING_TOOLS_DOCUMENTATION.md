# 调试工具文档

## 概述

在调试股票信息下载器的过程中，创建了多个专用调试工具。这些工具用于诊断问题、分析网页结构、验证数据流，以及维护测试环境。本文档详细记录所有调试工具的使用方法、功能说明和调用接口。

## 工具分类

### 1. 网页结构分析工具
- **Pagination Structure Dumper** - 分析分页HTML结构
- **Research Tab Diagnostic** - 研究标签页专用诊断

### 2. 测试环境管理工具
- **Test Helper Cleaner** - 智能测试目录清理

### 3. 调试标记系统
- **Debug Marker System** - 执行流程跟踪（已在单独文档中）

## 1. Pagination Structure Dumper

### 文件位置
`tools/debug/pagination_structure_dumper.py`

### 功能说明
分析网页的HTML结构，找出正确的分页选择器。当分页失败时，用于诊断实际的HTML结构，生成详细的诊断报告。

### 使用场景
- 分页操作失败时的诊断
- Element UI分页组件结构分析
- 寻找正确的CSS选择器

### 调用方法

#### 命令行调用
```bash
python tools/debug/pagination_structure_dumper.py
```

#### Python代码调用
```python
from tools.debug.pagination_structure_dumper import analyze_pagination_structure

# 分析当前页面的分页结构
results = analyze_pagination_structure(
    url="https://www.cninfo.com.cn/new/disclosure/stock?stockCode=301611&orgId=9900056250#research",
    browser_strategy="selenium"  # 或 "playwright"
)
```

### 输出内容

#### 诊断报告文件
位置：`tools/debug/pagination_diagnostic_results.json`

#### 报告结构
```json
{
  "timestamp": "2025-12-21T15:36:05.123",
  "url": "https://www.cninfo.com.cn/new/disclosure/stock?stockCode=301611&orgId=9900056250#research",
  "browser_strategy": "selenium",
  "analysis": {
    "pagination_containers": [
      {
        "selector": ".el-pagination",
        "elements_found": 1,
        "children": ["prev", "pager", "next", "sizes", "total"]
      }
    ],
    "pager_elements": [
      {
        "selector": ".el-pager li.number",
        "count": 5,
        "text_contents": ["1", "2", "3", "4", "5"],
        "active_element": {
          "selector": ".el-pager li.number.active",
          "text": "1"
        },
        "next_element": {
          "selector": ".el-pager li.number.active + li.number",
          "text": "2",
          "clickable": true
        }
      }
    ],
    "next_buttons": [
      {
        "selector": "button.el-pagination__next",
        "enabled": true,
        "text": "下一页"
      }
    ],
    "recommended_selectors": {
      "has_next_page": ".el-pager li.number.active + li.number",
      "go_to_next_page": "button.el-pagination__next:not(.is-disabled)",
      "alternative": ".el-pager li.active + li.number"
    }
  }
}
```

### 内部实现

#### 主要函数
```python
def analyze_pagination_structure(url: str, browser_strategy: str = "selenium") -> Dict[str, Any]:
    """
    分析网页的分页结构

    Args:
        url: 目标URL
        browser_strategy: 浏览器策略

    Returns:
        包含分页结构分析结果的字典
    """
```

#### 工作流程
1. 启动浏览器并导航到目标URL
2. 等待页面加载完成
3. 查找所有可能的分页容器
4. 分析Element UI分页组件结构
5. 识别当前页码和可点击元素
6. 生成推荐的选择器
7. 保存诊断报告

## 2. Research Tab Diagnostic

### 文件位置
`tools/debug/research_tab_diagnostic.py`

### 功能说明
专门分析研究标签页的分页结构，针对研究标签页的特殊HTML结构进行深入诊断。

### 使用场景
- 研究标签页分页失败时的专用诊断
- 验证研究标签页的特殊选择器
- 分析动态加载内容

### 调用方法

#### 命令行调用
```bash
python tools/debug/research_tab_diagnostic.py
```

#### Python代码调用
```python
from tools.debug.research_tab_diagnostic import analyze_research_tab

# 分析研究标签页
results = analyze_research_tab(
    stock_code="301611",
    org_id="9900056250"
)
```

### 输出内容

#### 诊断结果
直接在控制台输出详细的HTML结构和可点击元素分析，包括：
- 标签页切换机制
- 分页按钮状态
- 当前页面URL验证
- 可点击元素列表

### 内部实现

#### 主要函数
```python
def analyze_research_tab(stock_code: str, org_id: str) -> None:
    """
    专门分析研究标签页的结构

    Args:
        stock_code: 股票代码
        org_id: 组织ID
    """
```

#### 特殊功能
- 自动切换到研究标签页
- 验证URL hash (#research)
- 分析研究标签页特有的HTML结构
- 识别研究标签页的分页元素

## 3. Test Helper Cleaner

### 文件位置
`tools/debug/test_helper_cleaner.py`

### 功能说明
智能清理测试目录，保留指定的测试用例文件。用于测试前的目录准备和测试后的清理工作。

### 使用场景
- 测试前的目录清理准备
- 测试后的临时文件清理
- 保留特定测试用例的文件

### 调用方法

#### 命令行调用
```bash
# 查看目录状态
python tools/debug/test_helper_cleaner.py --status

# 清理测试文件（保留delete_later=False的用例）
python tools/debug/test_helper_cleaner.py --clean

# 指定配置文件
python tools/debug/test_helper_cleaner.py --config config_end2end_test.json
```

#### Python代码调用
```python
from tools.debug.test_helper_cleaner import get_test_directory_status, clean_test_files

# 检查目录状态
status = get_test_directory_status("end2end_test/test_results")
print(f"目录状态: {status}")

# 清理测试文件
preserve_cases = [
    {"stock_code": "301611", "delete_later": False}
]
result = clean_test_files("end2end_test/test_results", preserve_cases, dry_run=False)
print(f"清理结果: {result}")
```

### 输出内容

#### 目录状态
```python
{
    "exists": True,
    "total_dirs": 2,
    "total_files": 3,
    "company_dirs": ["中密控股", "珂玛科技"],
    "temp_files": 2,
    "root_files": 1
}
```

#### 清理结果
```python
{
    "cleaned_files": 3,
    "cleaned_dirs": 1,
    "cleaned_temp_files": 2,
    "cleaned_temp_dirs": 1,
    "preserved_files": 1,
    "preserved_dirs": 1,
    "preserved_companies": ["珂玛科技"]
}
```

### 主要函数

#### 1. get_test_directory_status()
```python
def get_test_directory_status(save_dir: str) -> Dict[str, Any]:
    """
    获取测试目录的详细状态

    Args:
        save_dir: 测试保存目录路径

    Returns:
        包含目录状态信息的字典
    """
```

#### 2. clean_test_files()
```python
def clean_test_files(save_dir: str, preserve_cases: List[Dict], dry_run: bool = True) -> Dict[str, Any]:
    """
    智能清理测试文件

    Args:
        save_dir: 测试保存目录路径
        preserve_cases: 需要保留的测试用例列表
        dry_run: 是否仅模拟运行

    Returns:
        清理结果统计
    """
```

#### 3. 智能保留逻辑
- 读取测试配置文件
- 识别delete_later=False的用例
- 提取对应的股票代码和公司名称
- 保留这些用例的文件和目录
- 删除其他所有临时文件和目录

## 4. 调试工具使用工作流

### 问题诊断流程

#### 步骤1: 确认问题类型
```bash
# 运行测试观察失败点
python e2e_test.py --browser-strategy selenium
```

#### 步骤2: 分析调试标记
```python
# 查看调试标记摘要
# 成功=3, 失败=0 表示前3步成功，问题在后续步骤
```

#### 步骤3: 使用专用诊断工具
```bash
# 如果是分页问题
python tools/debug/pagination_structure_dumper.py

# 如果是研究标签页问题
python tools/debug/research_tab_diagnostic.py
```

#### 步骤4: 清理测试环境
```bash
# 测试前清理
python tools/debug/test_helper_cleaner.py --clean
```

## 5. 工具集成示例

### 完整调试会话

```python
# 1. 准备测试环境
from tools.debug.test_helper_cleaner import clean_test_files
clean_result = clean_test_files("end2end_test/test_results", [], dry_run=False)

# 2. 运行测试并收集调试标记
from src.services.unified_downloader import UnifiedDownloader
downloader = UnifiedDownloader(config)
result = downloader.download_stock_pdfs(request)

# 3. 分析调试标记
debug_summary = downloader.get_debug_summary()
print(f"成功步骤: {debug_summary['successful']}")
print(f"失败步骤: {debug_summary['failed']}")

# 4. 如果分页失败，使用诊断工具
from tools.debug.pagination_structure_dumper import analyze_pagination_structure
diagnosis = analyze_pagination_structure(target_url, "selenium")

# 5. 根据诊断结果修复代码
# 更新 selenium_strategy.py 中的选择器
```

## 6. 工具配置

### 环境要求
- Python 3.8+
- Selenium WebDriver
- Chrome 浏览器
- 项目依赖已安装

### 文件路径约定
- 诊断报告：`tools/debug/pagination_diagnostic_results.json`
- 调试标记：`logs/debug_markers/markers_session_{timestamp}.jsonl`
- 测试结果：`end2end_test/test_results/`

## 7. 故障排除

### 工具执行失败
1. 检查浏览器驱动是否正确安装
2. 确认Chrome版本匹配ChromeDriver版本
3. 验证网络连接和目标网站可访问性

### 诊断报告为空
1. 检查URL是否正确
2. 确认页面是否成功加载
3. 查看浏览器控制台错误信息

### 清理工具误删文件
1. 使用 `dry_run=True` 预览清理操作
2. 检查 `preserve_cases` 配置是否正确
3. 确认测试用例的 `delete_later` 标志设置

## 8. 最佳实践

### 1. 调试前准备
```python
# 总是先清理测试环境
clean_test_files(save_dir, preserve_cases, dry_run=False)

# 确保调试标记系统已初始化
from src.services.unified_downloader import get_debug_marker_manager
manager = get_debug_marker_manager()
manager.reset_instance()
```

### 2. 诊断工具使用顺序
1. 运行测试观察失败点
2. 查看调试标记摘要
3. 根据失败步骤选择诊断工具
4. 分析诊断报告
5. 修复代码
6. 重新测试验证

### 3. 诊断报告管理
```bash
# 定期清理旧的诊断报告
rm tools/debug/pagination_diagnostic_results.json

# 备份重要的诊断报告
cp tools/debug/pagination_diagnostic_results.json tools/debug/archive/
```

## 9. 扩展工具

### 添加新的诊断工具

#### 模板结构
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新诊断工具说明
"""

import json
from pathlib import Path
from typing import Dict, Any

def analyze_xxx_structure(url: str, **kwargs) -> Dict[str, Any]:
    """
    分析XXX结构

    Args:
        url: 目标URL
        **kwargs: 其他参数

    Returns:
        诊断结果
    """
    # 实现逻辑
    results = {}

    # 保存报告
    report_file = Path("tools/debug/xxx_diagnostic_results.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results

if __name__ == "__main__":
    analyze_xxx_structure("https://example.com")
```

## 10. 总结

这些调试工具构成了完整的诊断体系：

1. **Debug Marker System** - 记录执行流程
2. **Pagination Structure Dumper** - 分析分页结构
3. **Research Tab Diagnostic** - 专用标签页诊断
4. **Test Helper Cleaner** - 环境管理

通过这些工具的组合使用，可以快速定位和解决下载器的问题，提高调试效率。

---

**文档版本**: 1.0
**最后更新**: 2025-12-21
**维护者**: 开发团队