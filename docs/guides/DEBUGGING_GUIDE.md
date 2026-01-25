# 调试工具和系统完整指南

## 概述

本文档是股票信息下载器项目中所有调试工具和系统的完整指南。这些工具是在解决测试失败和问题诊断过程中创建的，旨在帮助开发者快速定位和解决问题。

## 文档导航

### 核心调试系统
- **[Debug Marker System](DEBUG_MARKER_SYSTEM.md)** - 执行流程跟踪和标记系统
- **[Debugging Tools Documentation](DEBUGGING_TOOLS_DOCUMENTATION.md)** - 专用诊断工具集合

### 测试相关
- **[TESTING_PROTOCOL.md](TESTING_PROTOCOL.md)** - 测试协议和最佳实践
- **[e2e_test.py](e2e_test.py)** - 端到端测试框架

### 项目文档
- **[README.md](README.md)** - 项目概述和使用指南
- **[CLAUDE.md](CLAUDE.md)** - 开发指南和规范

## 快速开始

### 1. 问题诊断流程

当遇到测试失败时，按以下步骤进行诊断：

```bash
# 步骤1: 运行测试观察失败点
python e2e_test.py --browser-strategy selenium

# 步骤2: 查看调试标记摘要
# 在测试输出中查找类似内容：
# [DEBUG_MARKER] SUCCESS ORG_ID_MAPPING | Details: {"result":"9900056250"}
# [DEBUG_MARKER] SUCCESS URL_GENERATION | Details: {"result":"https://..."}
# [DEBUG_MARKER] SUCCESS WEBPAGE_CONNECTION | Details: {...}
# 但后续步骤失败
```

### 2. 根据失败步骤选择工具

| 失败步骤 | 诊断工具 | 命令 |
|---------|---------|------|
| ORG_ID_MAPPING | 检查映射文件 | `cat stock_orgid_mapping.json` |
| URL_GENERATION | 检查URL构建逻辑 | 查看 `unified_downloader.py` |
| WEBPAGE_CONNECTION | 检查网络连接 | 手动访问URL测试 |
| PDF_VISIBILITY | 检查页面元素 | 使用浏览器开发者工具 |
| PAGINATION | Pagination Structure Dumper | `python tools/debug/pagination_structure_dumper.py` |
| KEYWORD_MATCHING | 检查关键词配置 | 查看测试用例配置 |
| DOWNLOAD_PAGE_OPENING | 检查详情页链接 | 查看调试标记details |
| DOWNLOAD_SUCCESS | 检查下载辅助器 | 查看 `download_helper.py` |

### 3. 使用专用诊断工具

```bash
# 如果是分页问题
python tools/debug/pagination_structure_dumper.py

# 如果是研究标签页问题
python tools/debug/research_tab_diagnostic.py

# 清理测试环境
python tools/debug/test_helper_cleaner.py --clean
```

## 调试系统架构

### 系统层次

```
┌─────────────────────────────────────────┐
│         E2E 测试框架 (e2e_test.py)       │
│  - 测试用例管理                          │
│  - 结果验证                              │
│  - 调试标记收集                          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│    Debug Marker System (核心系统)        │
│  - DebugStep 枚举 (8个步骤)              │
│  - DebugMarker 类                        │
│  - DebugMarkerManager (单例)             │
│  - JSONL 文件持久化                      │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌─────────────────┐  ┌──────────────────┐
│  Unified        │  │  Selenium/       │
│  Downloader     │  │  Playwright      │
│  (封装器模式)   │  │  Strategy        │
└─────────────────┘  └──────────────────┘
        │                   │
        └─────────┬─────────┘
                  ▼
┌─────────────────────────────────────────┐
│      诊断工具集 (tools/debug/)           │
│  - Pagination Structure Dumper          │
│  - Research Tab Diagnostic              │
│  - Test Helper Cleaner                  │
└─────────────────────────────────────────┘
```

## 调试标记使用示例

### 在代码中添加调试标记

#### 1. 封装器模式（推荐）
```python
# 在 UnifiedDownloader 中
def _perform_download(self, request: DownloadRequest) -> DownloadResult:
    # 自动记录成功/失败
    return self._debug_step(
        DebugStep.DOWNLOAD_SUCCESS,
        self._real_download_file,
        url, filename, save_dir, request
    )
```

#### 2. 手动记录模式
```python
# 在 Selenium Strategy 中
def go_to_next_page(self, timeout: int = 10) -> bool:
    from ..utils.debug_marker import DebugMarker

    marker = DebugMarker("pagination")
    marker.add_step("pagination_start", "开始翻页操作", {
        "current_url": self.driver.current_url
    })

    try:
        # 翻页逻辑...
        marker.add_step("pagination_success", "翻页成功", {"selector": selector})
        marker.save()
        return True
    except Exception as e:
        marker.add_step("pagination_failed", "翻页失败", {"error": str(e)})
        marker.save()
        return False
```

### 读取和分析调试标记

```python
# 在测试代码中
from src.services.unified_downloader import UnifiedDownloader

downloader = UnifiedDownloader(config)
result = downloader.download_stock_pdfs(request)

# 获取调试摘要
summary = downloader.get_debug_summary()
print(f"成功: {summary['successful']}, 失败: {summary['failed']}")

# 查看每个步骤的统计
for step_name, stats in summary['steps'].items():
    print(f"{step_name}: {stats['successful']}/{stats['total']} 成功")
```

## 诊断工具详解

### 1. Pagination Structure Dumper

**用途**: 分析Element UI分页的HTML结构，找出正确的CSS选择器

**使用场景**:
- 分页按钮找不到
- 翻页操作失败
- 需要验证选择器正确性

**输出示例**:
```json
{
  "recommended_selectors": {
    "has_next_page": ".el-pager li.number.active + li.number",
    "go_to_next_page": "button.el-pagination__next:not(.is-disabled)"
  }
}
```

### 2. Research Tab Diagnostic

**用途**: 专门分析研究标签页的特殊结构

**使用场景**:
- 研究标签页分页失败
- 标签页切换问题
- 研究标签页元素定位

**特点**:
- 自动切换到研究标签页
- 验证URL hash (#research)
- 分析动态加载内容

### 3. Test Helper Cleaner

**用途**: 智能管理测试目录，保留重要文件

**使用场景**:
- 测试前清理环境
- 测试后删除临时文件
- 保留delete_later=False的用例

**使用示例**:
```python
from tools.debug.test_helper_cleaner import clean_test_files

# 保留特定测试用例
preserve_cases = [
    {"stock_code": "301611", "delete_later": False}
]

result = clean_test_files("end2end_test/test_results", preserve_cases)
print(f"删除: {result['cleaned_files']} 个文件")
print(f"保留: {result['preserved_files']} 个文件")
```

## 实际调试案例

### 案例1: 分页失败（已解决）

**问题**: Selenium E2E测试在分页步骤失败

**诊断过程**:
1. 运行测试发现前3步成功，PAGINATION步骤失败
2. 使用 `pagination_structure_dumper.py` 分析HTML
3. 发现Element UI使用 `.el-pager li.number.active + li.number` 作为下一页选择器
4. 更新 `selenium_strategy.py` 中的选择器

**解决方案**:
```python
# 旧代码（错误）
next_selectors = [
    "button.el-pagination__next",
    ".pagination .next"
]

# 新代码（正确）
next_selectors = [
    ".el-pager li.number.active + li.number",  # 主要选择器
    "button.el-pagination__next:not(.is-disabled)",
    ".el-pager li.active + li.number"
]
```

### 案例2: 属性访问错误（进行中）

**问题**: `'DownloadRequest' object has no attribute 'keyword'`

**诊断过程**:
1. 调试标记显示前3步成功
2. 错误发生在后续步骤
3. 搜索发现错误源在 `microservices/download-service/download_service.py`

**当前状态**: 需要修复该文件中的属性访问错误

## 调试最佳实践

### 1. 标记放置原则
- ✅ **关键路径**: 每个主要步骤都要标记
- ✅ **异常处理**: catch块中记录失败标记
- ✅ **边界条件**: 特殊情况也要记录
- ❌ **避免过度**: 不要在循环内部频繁标记

### 2. 详细信息内容
```python
# 好的实践
self._log_debug_marker(
    DebugStep.PAGINATION,
    True,
    {
        "current_page": page_num,
        "next_page": page_num + 1,
        "selector_used": selector,
        "page_url": current_url
    }
)

# 避免空的details
self._log_debug_marker(DebugStep.PAGINATION, True, {})  # ❌
```

### 3. 测试环境管理
```python
# 测试前重置
from src.services.unified_downloader import get_debug_marker_manager
manager = get_debug_marker_manager()
manager.reset_instance()

# 清理目录
from tools.debug.test_helper_cleaner import clean_test_files
clean_test_files(save_dir, preserve_cases)
```

### 4. 调试工作流
```
1. 运行测试 → 观察失败
2. 查看标记 → 定位失败步骤
3. 选择工具 → 诊断具体问题
4. 修复代码 → 更新选择器/逻辑
5. 重新测试 → 验证修复
6. 清理环境 → 准备下次测试
```

## 文件位置速查

### 调试系统核心
- `src/services/unified_downloader.py` - DebugStep, DebugMarker, DebugMarkerManager
- `src/utils/debug_marker.py` - 独立DebugMarker工具类

### 诊断工具
- `tools/debug/pagination_structure_dumper.py` - 分页结构分析
- `tools/debug/research_tab_diagnostic.py` - 研究标签页诊断
- `tools/debug/test_helper_cleaner.py` - 测试目录清理

### 调试数据
- `logs/debug_markers/` - 调试标记JSONL文件
- `tools/debug/pagination_diagnostic_results.json` - 分页诊断报告
- `e2e_test_report.json` - E2E测试报告

### 文档
- `DEBUG_MARKER_SYSTEM.md` - 调试标记系统详细文档
- `DEBUGGING_TOOLS_DOCUMENTATION.md` - 调试工具详细文档
- `TESTING_PROTOCOL.md` - 测试协议和规范

## 常见问题解答

### Q: 调试标记没有记录到文件？
**A**: 检查 `logs/debug_markers/` 目录权限，确认磁盘空间充足

### Q: 如何重置调试状态？
**A**: 使用 `DebugMarkerManager.reset_instance()` 重置单例

### Q: 为什么需要两种DebugMarker类？
**A**:
- UnifiedDownloader中的DebugMarker: 简单的单步骤标记
- src/utils/debug_marker.py: 复杂的多步骤流程跟踪

### Q: 如何查看历史调试数据？
**A**: 查看 `logs/debug_markers/` 目录下的JSONL文件，每行一个完整的调试标记

## 扩展指南

### 添加新的调试步骤

1. 在 `DebugStep` 枚举中添加：
```python
class DebugStep(Enum):
    # ... 现有步骤
    NEW_STEP = "new_step"
```

2. 在代码中使用：
```python
self._debug_step(DebugStep.NEW_STEP, your_function, *args)
```

3. 更新文档和测试报告解析器

### 创建新的诊断工具

1. 创建工具文件：`tools/debug/your_tool.py`
2. 实现分析函数：
```python
def analyze_your_structure(url: str) -> Dict[str, Any]:
    # 分析逻辑
    return results
```
3. 保存诊断报告到JSON文件
4. 更新本文档的工具列表

## 总结

这套调试系统提供了完整的诊断能力：

1. **Debug Marker System** - 实时跟踪执行流程
2. **Diagnostic Tools** - 深入分析具体问题
3. **Test Management** - 智能环境清理

通过这些工具的组合使用，可以快速定位和解决下载器的各类问题，显著提高调试效率。

---

**文档版本**: 1.0
**最后更新**: 2025-12-21
**维护者**: 开发团队
**相关文档**: DEBUG_MARKER_SYSTEM.md, DEBUGGING_TOOLS_DOCUMENTATION.md