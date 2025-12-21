# 调试标记系统使用指南

## 快速开始

### 1. 基本使用

调试标记系统已集成在 `UnifiedDownloader` 中，无需额外配置：

```python
from src.services.unified_downloader import UnifiedDownloader
from src.interfaces.downloader_interface import DownloadRequest

# 创建下载器
config = {
    'save_dir': 'downloads',
    'browser_strategy': 'playwright'
}
downloader = UnifiedDownloader(config)

# 创建请求
request = DownloadRequest(
    stock_code='002415',
    max_pages=5,
    suffix='research'
)

# 执行下载（自动记录标记）
result = downloader.download_stock_pdfs(request)

# 获取调试标记
markers = downloader.get_debug_markers()
summary = downloader.get_debug_summary()

print(f"总标记数: {summary['total_markers']}")
print(f"成功率: {summary['success_rate']:.1f}%")
```

### 2. 调试标记详解

#### 8个关键步骤

| 步骤 | 枚举值 | 说明 | 记录位置 |
|------|--------|------|----------|
| 1 | `ORG_ID_MAPPING` | 映射股票代码到org ID | `download_stock_pdfs()` |
| 2 | `URL_GENERATION` | 生成目标URL | `_build_target_url()` |
| 3 | `WEBPAGE_CONNECTION` | 连接网页并等待加载 | `_perform_download()` |
| 4 | `PDF_VISIBILITY` | 在页面上看到PDF链接 | `_find_download_links()` |
| 5 | `PAGINATION` | 翻页操作 | `_download_with_pagination()` |
| 6 | `KEYWORD_MATCHING` | 关键词匹配过滤 | `_find_download_links()` |
| 7 | `DOWNLOAD_PAGE_OPENING` | 打开下载详情页 | `_download_file()` |
| 8 | `DOWNLOAD_SUCCESS` | 文件下载成功 | `_download_file()` |

#### 标记数据结构

```python
{
    "marker_id": "org_id_mapping_1766249510374",
    "step": "org_id_mapping",
    "step_name": "ORG_ID_MAPPING",
    "success": True,
    "details": {"stock_code": "002415", "org_id": "9900012688"},
    "error": None,
    "timestamp": "2025-12-20T16:48:36.123456",
    "timestamp_ms": 1766249510374
}
```

### 3. 在E2E测试中使用

e2e_test.py 已自动集成调试标记读取：

```python
# 运行测试
result = run_test_with_new_downloader(test_case, config)

# 获取调试信息
debug_markers = result['debug_markers']
debug_summary = result['debug_summary']

# 输出摘要
print(f"测试结果: {'成功' if result['success'] else '失败'}")
print(f"下载文件: {result['downloaded_files']} 个")
print(f"调试标记: {len(debug_markers)} 个")

# 分析每个步骤
for step_name, stats in debug_summary['steps'].items():
    success_rate = stats['successful'] / stats['total'] * 100
    print(f"  {step_name}: {stats['successful']}/{stats['total']} ({success_rate:.1f}%)")
```

### 4. 标记文件位置

调试标记自动保存在：
```
logs/debug_markers/
  └── markers_session_20251220_164836.jsonl
```

每行是一个JSON格式的标记：
```json
{"marker_id":"org_id_mapping_1766249510374","step":"org_id_mapping","step_name":"ORG_ID_MAPPING","success":true,"details":{"stock_code":"002415","org_id":"9900012688"},"error":null,"timestamp":"2025-12-20T16:48:36.123456","timestamp_ms":1766249510374}
```

## 高级用法

### 1. 自定义调试标记

在自定义代码中使用调试标记：

```python
from src.services.unified_downloader import DebugStep, get_debug_marker_manager

# 获取标记管理器
manager = get_debug_marker_manager()

# 记录成功标记
manager.add_marker(
    step=DebugStep.CUSTOM_STEP,
    success=True,
    details={"custom_data": "value"}
)

# 记录失败标记
manager.add_marker(
    step=DebugStep.CUSTOM_STEP,
    success=False,
    details={"attempt": 1},
    error="自定义错误信息"
)
```

### 2. 分析调试结果

```python
# 获取摘要
summary = downloader.get_debug_summary()

# 检查特定步骤是否成功
if summary['steps']['url_generation']['failed'] > 0:
    print("URL生成步骤有失败！")

# 计算整体成功率
if summary['success_rate'] < 80:
    print("成功率低于80%，需要检查问题")
```

### 3. 读取历史标记文件

```python
from src.services.unified_downloader import DebugMarkerManager

# 读取指定会话的标记
manager = DebugMarkerManager()
markers = manager.get_markers_for_e2e_test()

# 或者使用便捷函数
from src.services.unified_downloader import get_debug_markers_for_e2e_test

markers = get_debug_markers_for_e2e_test(session_id="session_20251220_164836")
```

## 通用浏览器操作模块

### 1. 基本使用

```python
from src.web.common_browser_ops import CommonBrowserOperations

# 创建通用操作器
common_ops = CommonBrowserOperations(browser_strategy)

# 查找并点击
success = common_ops.find_and_click("button.submit", timeout=10)

# 获取文本
text = common_ops.get_element_text(".result", timeout=5)

# 导航并等待
success = common_ops.navigate_and_wait("https://example.com", timeout=30)
```

### 2. 配置标准化

```python
from src.web.common_browser_ops import normalize_config_for_engine

# 通用配置
config = {
    'window_size': '1920,1080',
    'timeout': 60,
    'download_dir': '/tmp/downloads'
}

# 转换为Selenium配置
selenium_config = normalize_config_for_engine('selenium', config)
# {'window_size': '1920,1080', 'timeout': 60, 'page_load_timeout': 60, ...}

# 转换为Playwright配置
playwright_config = normalize_config_for_engine('playwright', config)
# {'window_size': {'width': 1920, 'height': 1080}, 'timeout': 60000, ...}
```

### 3. 常用操作

```python
# 根据文本查找并点击
common_ops.click_element_by_text("下载", timeout=5)

# 检查元素是否可见
visible = common_ops.is_element_visible("#result", timeout=10)

# 等待URL变化
common_ops.wait_for_url_contains("success", timeout=15)

# 获取页面内容
content = common_ops.get_page_content()
```

## 故障诊断

### 1. 检查哪个步骤失败

```python
summary = downloader.get_debug_summary()

for step_name, stats in summary['steps'].items():
    if stats['failed'] > 0:
        print(f"❌ {step_name}: {stats['failed']} 次失败")
        # 查看具体失败的标记
        markers = downloader.get_debug_markers()
        failed_markers = [m for m in markers if m['step'] == step_name and not m['success']]
        for marker in failed_markers:
            print(f"   错误: {marker['error']}")
            print(f"   详情: {marker['details']}")
```

### 2. 常见问题分析

#### 问题：ORG_ID_MAPPING失败
```python
# 检查标记详情
markers = downloader.get_debug_markers()
org_markers = [m for m in markers if m['step'] == 'org_id_mapping']

for marker in org_markers:
    if not marker['success']:
        print(f"股票代码 {marker['details']['stock_code']} 无法映射到org_id")
        # 解决方案：检查mapping.json文件
```

#### 问题：URL_GENERATION失败
```python
# 检查URL构建参数
url_markers = [m for m in markers if m['step'] == 'url_generation']
for marker in url_markers:
    if not marker['success']:
        print(f"URL构建失败: {marker['error']}")
        # 解决方案：检查stock_code和org_id是否正确
```

#### 问题：WEBPAGE_CONNECTION失败
```python
# 检查网络连接和页面加载
conn_markers = [m for m in markers if m['step'] == 'webpage_connection']
for marker in conn_markers:
    if not marker['success']:
        print(f"网页连接失败: {marker['error']}")
        # 解决方案：检查网络、反爬虫设置
```

#### 问题：PDF_VISIBILITY失败
```python
# 检查页面上是否有PDF链接
pdf_markers = [m for m in markers if m['step'] == 'pdf_visibility']
for marker in pdf_markers:
    if not marker['success']:
        print(f"未找到PDF链接: {marker['error']}")
        # 解决方案：检查suffix是否正确，页面是否加载完整
```

#### 问题：DOWNLOAD_SUCCESS失败
```python
# 检查下载详情
dl_markers = [m for m in markers if m['step'] == 'download_success']
for marker in dl_markers:
    if not marker['success']:
        print(f"下载失败: {marker['error']}")
        print(f"文件: {marker['details']['filename']}")
        print(f"URL: {marker['details']['url']}")
        # 解决方案：检查下载目录权限、网络连接
```

### 3. 调试标记报告

```python
# 导出完整报告
from src.services.unified_downloader import DebugMarkerManager

manager = DebugMarkerManager()
report = manager.export_debug_markers_report("debug_report.json")

# 报告包含：
# - 生成时间
# - 摘要统计
# - 所有标记详情
```

## 最佳实践

### 1. 测试开发阶段

```python
# 在开发时开启详细日志
config = {
    'save_dir': 'test_downloads',
    'browser_strategy': 'playwright',
    'headless': False  # 可视化查看
}

downloader = UnifiedDownloader(config)
result = downloader.download_stock_pdfs(request)

# 立即检查调试标记
summary = downloader.get_debug_summary()
print(json.dumps(summary, indent=2, ensure_ascii=False))
```

### 2. 生产环境监控

```python
# 记录关键指标
summary = downloader.get_debug_summary()

# 监控成功率
if summary['success_rate'] < 90:
    # 发送告警
    send_alert(f"下载成功率过低: {summary['success_rate']:.1f}%")

# 监控特定步骤
for step_name, stats in summary['steps'].items():
    if stats['total'] > 0 and stats['successful'] / stats['total'] < 0.8:
        send_alert(f"{step_name} 成功率过低")
```

### 3. 性能分析

```python
# 分析每个步骤的耗时（需要在标记中添加时间戳）
markers = downloader.get_debug_markers()

# 计算URL生成到下载完成的总耗时
start_marker = next((m for m in markers if m['step'] == 'url_generation'), None)
end_marker = next((m for m in markers if m['step'] == 'download_success'), None)

if start_marker and end_marker:
    duration = end_marker['timestamp_ms'] - start_marker['timestamp_ms']
    print(f"总下载耗时: {duration}ms")
```

## 与其他系统集成

### 1. 与测试框架集成

```python
# pytest fixture
@pytest.fixture
def downloader_with_debug():
    config = {'save_dir': 'test_downloads'}
    downloader = UnifiedDownloader(config)
    yield downloader

    # 测试后输出调试摘要
    summary = downloader.get_debug_summary()
    print(f"\n调试摘要: {json.dumps(summary, indent=2)}")

# 测试用例
def test_download(downloader_with_debug):
    request = DownloadRequest(stock_code='002415')
    result = downloader_with_debug.download_stock_pdfs(request)

    # 验证所有步骤成功
    summary = downloader_with_debug.get_debug_summary()
    assert summary['failed'] == 0
```

### 2. 与日志系统集成

```python
import logging

logger = logging.getLogger(__name__)

# 在下载过程中记录标记
def log_download_progress(downloader):
    markers = downloader.get_debug_markers()
    for marker in markers:
        if marker['success']:
            logger.info(f"[{marker['step_name']}] 成功")
        else:
            logger.error(f"[{marker['step_name']}] 失败: {marker['error']}")
```

## 总结

调试标记系统提供了：

1. ✅ **8个关键步骤**的自动标记
2. ✅ **实时控制台输出**和**文件持久化**
3. ✅ **E2E测试集成**，自动读取和分析
4. ✅ **通用浏览器操作**，减少重复代码
5. ✅ **详细的故障诊断**能力

使用调试标记系统，可以快速定位下载过程中的问题，提高调试效率。