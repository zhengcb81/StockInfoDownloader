# Debug Marker System 文档

## 概述

Debug Marker System 是一个用于跟踪和记录代码执行流程的调试工具系统。它在测试和故障排除过程中提供详细的执行步骤记录，帮助开发者快速定位问题所在。

## 系统架构

### 核心组件

#### 1. DebugStep 枚举 (src/services/unified_downloader.py)

定义了8个关键调试步骤，覆盖完整的下载流程：

```python
class DebugStep(Enum):
    ORG_ID_MAPPING = "org_id_mapping"      # 映射org ID
    URL_GENERATION = "url_generation"      # 生成URL
    WEBPAGE_CONNECTION = "webpage_connection"  # 连接到目标网页
    PDF_VISIBILITY = "pdf_visibility"      # 看到PDF文档
    PAGINATION = "pagination"              # 翻页操作
    KEYWORD_MATCHING = "keyword_matching"  # 关键词匹配
    DOWNLOAD_PAGE_OPENING = "download_page_opening"  # 打开下载页面
    DOWNLOAD_SUCCESS = "download_success"  # 成功下载
```

#### 2. DebugMarker 类 (src/services/unified_downloader.py)

单个调试标记的数据结构，记录每个步骤的执行状态。

**属性：**
- `step`: DebugStep 枚举值
- `success`: 是否成功
- `details`: 详细信息字典
- `error`: 错误信息
- `timestamp`: 时间戳
- `marker_id`: 唯一标识符

**方法：**
- `to_dict()`: 转换为字典格式
- `to_log_string()`: 转换为日志字符串

#### 3. DebugMarkerManager 类 (src/services/unified_downloader.py)

单例模式的调试标记管理器，负责存储和管理所有标记。

**核心功能：**
- 单例模式确保全局唯一实例
- 自动写入文件，防止程序崩溃丢失数据
- 提供统计摘要和E2E测试数据接口
- 支持标记清空（用于测试）

**文件存储：**
- 位置：`logs/debug_markers/markers_session_{timestamp}.jsonl`
- 格式：每行一个完整的JSON对象

#### 4. 独立 DebugMarker 工具类 (src/utils/debug_marker.py)

用于更细粒度的调试流程跟踪，支持多步骤记录。

**特点：**
- 支持单个标记内记录多个步骤
- 自动计算每个步骤的耗时
- 保存完整的执行流程历史

## 使用方法

### 1. 在 UnifiedDownloader 中使用

#### 基本用法 - 封装器模式

```python
# 在方法中使用封装器自动记录调试标记
def _build_target_url(self, request: DownloadRequest) -> str:
    return self._debug_step(
        DebugStep.URL_GENERATION,
        self._real_build_target_url,
        request
    )
```

#### 手动记录模式

```python
# 手动添加调试标记
try:
    result = some_operation()
    self._log_debug_marker(DebugStep.PAGINATION, True, {"result": result})
except Exception as e:
    self._log_debug_marker(DebugStep.PAGINATION, False, {}, str(e))
    raise
```

#### 获取调试信息

```python
# 获取所有调试标记（供E2E测试使用）
markers = downloader.get_debug_markers()

# 获取调试摘要
summary = downloader.get_debug_summary()
# 返回格式：
# {
#     "session_id": "session_20251221_063011",
#     "total_markers": 18,
#     "successful": 18,
#     "failed": 0,
#     "success_rate": 100.0,
#     "steps": {
#         "org_id_mapping": {"total": 6, "successful": 6, "failed": 0},
#         "url_generation": {"total": 6, "successful": 6, "failed": 0},
#         "webpage_connection": {"total": 6, "successful": 6, "failed": 0}
#     }
# }
```

### 2. 在 Selenium Strategy 中使用

```python
from ..utils.debug_marker import DebugMarker

def go_to_next_page(self, timeout: int = 10) -> bool:
    marker = DebugMarker("pagination")
    marker.add_step("pagination_start", "开始翻页操作", {
        "current_url": self.driver.current_url if self.driver else "no_driver"
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

## API 详细文档

### DebugStep 枚举

**文件位置**: `src/services/unified_downloader.py`

**完整定义**:
```python
from enum import Enum

class DebugStep(Enum):
    """调试步骤枚举 - 覆盖完整的下载流程"""

    ORG_ID_MAPPING = "org_id_mapping"              # 步骤1: 股票代码到组织ID的映射
    URL_GENERATION = "url_generation"              # 步骤2: 构建目标URL
    WEBPAGE_CONNECTION = "webpage_connection"      # 步骤3: 连接到目标网页
    PDF_VISIBILITY = "pdf_visibility"              # 步骤4: 查找PDF相关链接
    PAGINATION = "pagination"                      # 步骤5: 翻页操作
    KEYWORD_MATCHING = "keyword_matching"          # 步骤6: 关键词过滤
    DOWNLOAD_PAGE_OPENING = "download_page_opening" # 步骤7: 打开下载详情页
    DOWNLOAD_SUCCESS = "download_success"          # 步骤8: 文件下载完成
```

**使用示例**:
```python
# 引用枚举值
step = DebugStep.ORG_ID_MAPPING
print(step.value)  # 输出: "org_id_mapping"
print(step.name)   # 输出: "ORG_ID_MAPPING"
```

### DebugMarker 类 (UnifiedDownloader)

**文件位置**: `src/services/unified_downloader.py` (第48-83行)

**构造函数**:
```python
class DebugMarker:
    def __init__(self, step: DebugStep, success: bool, details: Dict[str, Any] = None, error: str = None):
        """
        创建调试标记

        Args:
            step: 调试步骤枚举值
            success: 是否成功
            details: 详细信息字典（可选）
            error: 错误信息（可选）
        """
```

**属性**:
- `step`: DebugStep - 步骤枚举
- `success`: bool - 成功状态
- `details`: Dict[str, Any] - 详细信息
- `error`: str | None - 错误信息
- `timestamp`: datetime - 创建时间戳
- `marker_id`: str - 唯一标识符 (格式: `{step.value}_{timestamp_ms}`)

**方法**:

#### to_dict()
```python
def to_dict(self) -> Dict[str, Any]:
    """
    转换为字典格式（用于JSON序列化）

    Returns:
        {
            "marker_id": "org_id_mapping_1734769811000",
            "step": "org_id_mapping",
            "step_name": "ORG_ID_MAPPING",
            "success": true,
            "details": {"result": "9900056250"},
            "error": null,
            "timestamp": "2025-12-21T06:30:11.000",
            "timestamp_ms": 1734769811000
        }
    """
```

#### to_log_string()
```python
def to_log_string(self) -> str:
    """
    转换为日志字符串（用于控制台输出）

    Returns:
        "[DEBUG_MARKER] SUCCESS ORG_ID_MAPPING | Details: {\"result\":\"9900056250\"}"
        或
        "[DEBUG_MARKER] FAILED PAGINATION | Details: {} | Error: 无法找到下一页按钮"
    """
```

### DebugMarkerManager 类

**文件位置**: `src/services/unified_downloader.py` (第85-178行)

**单例模式**: 全局唯一实例，确保跨模块的标记一致性

**构造函数**:
```python
class DebugMarkerManager:
    def __new__(cls, log_dir: str = "logs/debug_markers"):
        """
        创建单例实例

        Args:
            log_dir: 日志目录路径
        """

    def __init__(self, log_dir: str = "logs/debug_markers"):
        """
        初始化管理器（仅在首次调用时执行）

        Args:
            log_dir: 日志目录路径
        """
```

**核心方法**:

#### add_marker()
```python
def add_marker(self, step: DebugStep, success: bool, details: Dict[str, Any] = None, error: str = None) -> DebugMarker:
    """
    添加调试标记

    Args:
        step: 调试步骤
        success: 成功状态
        details: 详细信息
        error: 错误信息

    Returns:
        创建的DebugMarker实例

    功能:
        1. 创建DebugMarker对象
        2. 添加到内部列表
        3. 立即写入JSONL文件
        4. 输出到控制台
    """
```

#### get_summary()
```python
def get_summary(self) -> Dict[str, Any]:
    """
    获取标记统计摘要

    Returns:
        {
            "session_id": "session_20251221_063011",
            "total_markers": 18,
            "successful": 18,
            "failed": 0,
            "success_rate": 100.0,
            "steps": {
                "org_id_mapping": {"total": 6, "successful": 6, "failed": 0},
                "url_generation": {"total": 6, "successful": 6, "failed": 0},
                ...
            }
        }
    """
```

#### get_markers_for_e2e_test()
```python
def get_markers_for_e2e_test(self) -> List[Dict[str, Any]]:
    """
    为E2E测试提供标记数据

    Returns:
        [marker.to_dict() for marker in self.markers]
    """
```

#### reset_instance()
```python
@classmethod
def reset_instance(cls):
    """
    重置单例实例（用于测试）

    使用场景:
        - 测试前清理状态
        - 避免跨测试污染
    """
```

#### clear()
```python
def clear(self):
    """
    清空所有标记（用于测试）

    区别于reset_instance():
        - clear(): 仅清空标记列表
        - reset_instance(): 重置整个单例实例
    """
```

### 独立 DebugMarker 工具类

**文件位置**: `src/utils/debug_marker.py`

**构造函数**:
```python
class DebugMarker:
    def __init__(self, marker_type: str):
        """
        初始化调试标记

        Args:
            marker_type: 标记类型 (如: "pagination", "download", "url_generation")

        特点:
            - 支持多步骤记录
            - 自动计算耗时
            - 保存完整执行历史
        """
```

**属性**:
- `marker_type`: str - 标记类型
- `steps`: List[Dict[str, Any]] - 步骤列表
- `start_time`: float - 开始时间戳
- `marker_id`: str - 唯一标识符

**方法**:

#### add_step()
```python
def add_step(self, step_id: str, description: str, details: Dict[str, Any] = None):
    """
    添加步骤记录

    Args:
        step_id: 步骤ID (如: "pagination_start")
        description: 步骤描述 (如: "开始翻页操作")
        details: 详细信息字典

    自动计算:
        - timestamp: 绝对时间戳
        - elapsed_ms: 相对耗时（毫秒）

    示例:
        marker.add_step("pagination_start", "开始翻页操作", {
            "current_url": "https://...",
            "page_num": 1
        })
    """
```

#### save()
```python
def save(self, log_dir: str = "logs/debug_markers"):
    """
    保存调试标记到文件

    Args:
        log_dir: 日志目录

    文件格式:
        logs/debug_markers/markers_session_20251221_153605.jsonl

    每行内容:
        {
            "marker_id": "pagination_1734770165000",
            "marker_type": "pagination",
            "start_time": "2025-12-21T15:36:05.000",
            "total_elapsed_ms": 1234,
            "step_count": 5,
            "steps": [
                {
                    "step_id": "pagination_start",
                    "description": "开始翻页操作",
                    "details": {...},
                    "timestamp": 1734770165.123,
                    "elapsed_ms": 0
                },
                ...
            ]
        }
    """
```

## 高级使用场景

### 场景1: 嵌套调试标记

```python
# 在复杂流程中使用嵌套标记
def complex_download_flow(self, request):
    # 外层标记：整个下载流程
    outer_marker = DebugMarker("download_flow")
    outer_marker.add_step("flow_start", "开始下载流程", {
        "stock_code": request.stock_code
    })

    try:
        # 内层标记：分页操作
        for page in range(request.max_pages):
            page_marker = DebugMarker(f"page_{page}")
            page_marker.add_step("page_start", f"第{page}页开始")

            # 查找链接
            links = self.find_links()
            page_marker.add_step("links_found", f"找到{len(links)}个链接", {
                "count": len(links)
            })

            # 下载文件
            for link in links:
                file_marker = DebugMarker("file_download")
                file_marker.add_step("download_start", "开始下载", {
                    "url": link['url']
                })

                try:
                    result = self.download_file(link)
                    file_marker.add_step("download_success", "下载成功", {
                        "file_path": result
                    })
                    file_marker.save()
                except Exception as e:
                    file_marker.add_step("download_failed", "下载失败", {
                        "error": str(e)
                    })
                    file_marker.save()
                    raise

            page_marker.add_step("page_complete", "页面完成")
            page_marker.save()

        outer_marker.add_step("flow_complete", "下载流程完成")
        outer_marker.save()

    except Exception as e:
        outer_marker.add_step("flow_failed", "下载流程失败", {
            "error": str(e)
        })
        outer_marker.save()
        raise
```

### 场景2: 条件调试标记

```python
def conditional_debugging(self, request, debug_mode=False):
    """
    根据条件启用调试标记
    """
    if debug_mode:
        marker = DebugMarker("conditional_debug")
        marker.add_step("debug_start", "调试模式已启用")

    # 正常业务逻辑
    result = self.process_request(request)

    if debug_mode:
        marker.add_step("debug_result", "处理结果", {
            "result_type": type(result).__name__,
            "result_size": len(str(result))
        })
        marker.save()

    return result
```

### 场景3: 性能监控标记

```python
def performance_monitored_operation(self):
    """
    使用调试标记监控性能
    """
    marker = DebugMarker("performance_monitor")

    # 阶段1: 初始化
    start = time.time()
    marker.add_step("phase1_init", "初始化阶段", {"timestamp": start})

    # 执行操作
    self.initialize()

    # 阶段2: 处理
    marker.add_step("phase2_process", "处理阶段", {
        "init_duration": time.time() - start
    })

    self.process()

    # 阶段3: 完成
    marker.add_step("phase3_complete", "完成阶段", {
        "total_duration": time.time() - start
    })

    marker.save()
```

## 调试标记输出示例

### 控制台输出
```
[DEBUG_MARKER] SUCCESS ORG_ID_MAPPING | Details: {"result":"9900056250"}
[DEBUG_MARKER] SUCCESS URL_GENERATION | Details: {"result":"https://www.cninfo.com.cn/new/disclosure/stock?stockCode=301611&orgId=9900056250#research"}
[DEBUG_MARKER] SUCCESS WEBPAGE_CONNECTION | Details: {"result":{"url":"https://...","page_title":"巨潮资讯网"}}
[DEBUG_MARKER] FAILED PAGINATION | Details: {} | Error: 无法找到下一页按钮
```

### JSONL 文件内容
```json
{"marker_id": "org_id_mapping_1734769811000", "step": "org_id_mapping", "step_name": "ORG_ID_MAPPING", "success": true, "details": {"result": "9900056250"}, "error": null, "timestamp": "2025-12-21T06:30:11.000", "timestamp_ms": 1734769811000}
{"marker_id": "url_generation_1734769812000", "step": "url_generation", "step_name": "URL_GENERATION", "success": true, "details": {"result": "https://www.cninfo.com.cn/new/disclosure/stock?stockCode=301611&orgId=9900056250#research"}, "error": null, "timestamp": "2025-12-21T06:30:12.000", "timestamp_ms": 1734769812000}
```

### E2E 测试摘要输出
```
获取到 18 个调试标记
调试标记摘要: 成功=18, 失败=0
  - org_id_mapping: 6/6 成功
  - url_generation: 6/6 成功
  - webpage_connection: 6/6 成功
  - pdf_visibility: 6/6 成功
  - pagination: 4/6 成功
  - keyword_matching: 6/6 成功
  - download_page_opening: 6/6 成功
  - download_success: 6/6 成功
```

## 调试步骤详解

### 完整下载流程（8个步骤）

1. **ORG_ID_MAPPING** - 股票代码到组织ID的映射
   - 成功：返回有效的org_id
   - 失败：无法找到对应股票代码的组织ID

2. **URL_GENERATION** - 构建目标URL
   - 成功：返回完整的URL（包含hash后缀）
   - 失败：URL构建异常

3. **WEBPAGE_CONNECTION** - 连接到目标网页
   - 成功：页面加载完成，获取到页面标题
   - 失败：页面导航失败或加载超时

4. **PDF_VISIBILITY** - 查找PDF相关链接
   - 成功：找到符合条件的下载链接
   - 失败：未找到任何链接

5. **PAGINATION** - 翻页操作
   - 成功：成功翻到下一页
   - 失败：找不到下一页按钮或翻页异常

6. **KEYWORD_MATCHING** - 关键词过滤
   - 成功：匹配到关键词的链接数量
   - 失败：无匹配链接

7. **DOWNLOAD_PAGE_OPENING** - 打开下载详情页
   - 成功：记录详情页URL和文件名
   - 失败：无法打开详情页

8. **DOWNLOAD_SUCCESS** - 文件下载完成
   - 成功：返回保存路径
   - 失败：下载失败或文件不存在

## 调试工具程序

### 1. Pagination Structure Dumper (tools/debug/pagination_structure_dumper.py)

**功能：** 分析网页的HTML结构，找出正确的分页选择器

**使用场景：** 当分页失败时，用于诊断实际的HTML结构

**输出：** 保存到 `tools/debug/pagination_structure_dumper.py` 同目录下的 `pagination_diagnostic_results.json`

### 2. Research Tab Diagnostic (tools/debug/research_tab_diagnostic.py)

**功能：** 专门分析研究标签页的分页结构

**使用场景：** 研究标签页分页失败时的专用诊断工具

**输出：** 详细的HTML结构和可点击元素分析

### 3. Test Helper Cleaner (tools/debug/test_helper_cleaner.py)

**功能：** 智能清理测试目录，保留指定的测试用例文件

**使用场景：** 测试前的目录准备和测试后的清理

**主要函数：**
- `get_test_directory_status()`: 检查目录状态
- `clean_test_files()`: 智能清理文件

## 调试工作流

### 问题诊断流程

1. **运行测试并观察失败**
   ```bash
   python e2e_test.py --browser-strategy selenium
   ```

2. **检查调试标记摘要**
   ```python
   # 在测试输出中查看调试标记摘要
   # 成功=18, 失败=0
   # - org_id_mapping: 6/6 成功
   # - url_generation: 6/6 成功
   # - webpage_connection: 6/6 成功
   ```

3. **分析失败步骤**
   - 如果前3步成功，但后续失败 → 问题在下载流程中
   - 如果特定步骤失败 → 针对性修复该步骤

4. **使用专用诊断工具**
   ```python
   # 如果是分页问题
   python tools/debug/pagination_structure_dumper.py

   # 如果是研究标签页问题
   python tools/debug/research_tab_diagnostic.py
   ```

5. **查看详细日志**
   - 检查 `logs/debug_markers/` 目录下的JSONL文件
   - 每行包含完整的调试标记数据

## 实际案例分析

### 案例1：URL生成成功但下载失败

**现象：**
```
[DEBUG_MARKER] SUCCESS ORG_ID_MAPPING | Details: {"result":"9900056250"}
[DEBUG_MARKER] SUCCESS URL_GENERATION | Details: {"result":"https://..."}
[DEBUG_MARKER] SUCCESS WEBPAGE_CONNECTION | Details: {"result":{...}}
但最终报错：'DownloadRequest' object has no attribute 'keyword'
```

**分析：**
- 前3个步骤成功，说明基础流程正常
- 错误发生在后续步骤，可能是属性访问问题
- 需要检查 `DownloadRequest` 对象的属性定义

### 案例2：分页失败

**现象：**
```
[DEBUG_MARKER] FAILED PAGINATION | Error: 无法找到下一页按钮
```

**解决方案：**
1. 使用 `pagination_structure_dumper.py` 分析实际HTML
2. 发现正确的选择器：`.el-pager li.number.active + li.number`
3. 更新 `selenium_strategy.py` 中的选择器

## 最佳实践

### 1. 调试标记的放置位置

- **关键路径**：每个主要功能步骤都应该有标记
- **异常处理**：在catch块中记录失败标记
- **边界条件**：特殊情况下也要记录状态

### 2. 详细信息的内容

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

### 3. 调试标记的清理

```python
# 在测试代码中
from src.services.unified_downloader import get_debug_marker_manager

manager = get_debug_marker_manager()
manager.reset_instance()  # 重置单例，避免跨测试污染
```

## 文件格式说明

### JSONL 文件格式

每行一个完整的JSON对象：

```json
{
    "marker_id": "org_id_mapping_1734769811000",
    "step": "org_id_mapping",
    "step_name": "ORG_ID_MAPPING",
    "success": true,
    "details": {"result": "9900056250"},
    "error": null,
    "timestamp": "2025-12-21T06:30:11.000",
    "timestamp_ms": 1734769811000
}
```

### E2E 测试数据格式

```python
markers = downloader.get_debug_markers()
# 返回列表，每个元素是上述JSON格式的字典
```

## 与其他系统的集成

### 与 E2E 测试框架集成

```python
# 在 e2e_test.py 中
result = run_test_with_new_downloader(test_case, config, strategy)

# 读取调试标记
if hasattr(downloader, 'get_debug_markers'):
    debug_markers = downloader.get_debug_markers()
    log(f"获取到 {len(debug_markers)} 个调试标记")

if hasattr(downloader, 'get_debug_summary'):
    debug_summary = downloader.get_debug_summary()
    log(f"调试标记摘要: 成功={debug_summary.get('successful', 0)}, 失败={debug_summary.get('failed', 0)}")
```

### 与日志系统集成

调试标记会同时输出到：
1. 控制台（通过 `print(marker.to_log_string())`）
2. JSONL 文件（持久化存储）
3. E2E 测试报告（通过 `get_debug_markers()`）

## 故障排除

### 常见问题

1. **标记未记录**
   - 检查是否正确调用 `_debug_step()` 或 `_log_debug_marker()`
   - 确认 DebugMarkerManager 实例已正确初始化

2. **文件写入失败**
   - 检查 `logs/debug_markers/` 目录权限
   - 确认磁盘空间充足

3. **单例模式问题**
   - 使用 `DebugMarkerManager.reset_instance()` 重置实例
   - 确保在测试环境中正确清理

## 扩展指南

### 添加新的调试步骤

1. 在 `DebugStep` 枚举中添加新步骤：
```python
class DebugStep(Enum):
    # ... 现有步骤
    NEW_STEP = "new_step"  # 新步骤
```

2. 在代码中使用：
```python
self._debug_step(DebugStep.NEW_STEP, your_function, *args)
```

3. 更新文档和测试报告解析器

### 自定义调试标记管理器

```python
class CustomDebugMarkerManager(DebugMarkerManager):
    def __init__(self, log_dir: str = "custom_logs"):
        super().__init__(log_dir)
        # 添加自定义功能

    def generate_report(self):
        # 生成自定义格式的报告
        pass
```

## 总结

Debug Marker System 是一个强大的调试工具，通过：
- **8个关键步骤** 覆盖完整下载流程
- **自动记录** 防止数据丢失
- **详细统计** 快速定位问题
- **文件持久化** 支持事后分析

帮助开发者快速诊断和修复下载器问题。