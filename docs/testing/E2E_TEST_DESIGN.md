# E2E 测试设计文档

## 概述

本文档描述 StockInfoDownloader 端到端测试的设计思路、验证策略和实现细节。

---

## 用户设计思路 (核心设计理念)

E2E 测试用例的设计基于以下三个核心思路：

### 思路1: 跳过已存在文件逻辑

**设计意图**:
> 原下载器在找到目标下载文件时，应该先检查本地是否已经有了同名文件，如果已经有了则跳过这个文件的下载。这是为了减少重复下载。

**测试方法**:
> 作为测试，我在一部分对比测试的目录里保留文件，这样可以检测下载器有没有正确执行跳过的逻辑。那么如何做到保留文件呢，我加了这个 flag (`delete_later`)，使得测试程序有时候不删除被下载的文件而故意留着。

**验证要点**:
- 下载器是否检查本地文件存在性
- 文件已存在时是否正确跳过
- 跳过行为是否有记录

### 思路2: 翻页功能测试

**设计意图**:
> 有些测试的文件需要翻页，可以测试下载器的翻页功能。

**测试方法**:
- 使用 `max_pages` 参数控制测试页数
- 验证下载器能正确执行分页逻辑

**验证要点**:
- 翻页逻辑是否正确执行
- 多页下载是否完整

### 思路3: 多页面类型测试

**设计意图**:
> 不同的页面后缀名对应不同的板块，比如年报和投资者交流。

**测试方法**:
- 使用不同 `suffix` 测试不同页面类型
- 验证下载器对各板块的处理能力

**页面类型**:
| 后缀 | 对应板块 | 测试用例 |
|------|----------|----------|
| research | 投资者交流/调研 | TC-001, TC-003 |
| periodicReports | 定期公告/年报 | TC-002 |
| latestAnnouncement | 最新公告 | TC-004 |

---

## 设计实现

### 思路1 实现: 跳过已存在文件验证

**下载器实现** (`src/services/unified_downloader.py`):
```python
if dest.exists() and dest.stat().st_size > 100:
    self.logger.info(f"File already exists, skipping: {dest}")
    self.skipped_files.append(str(dest))
    return str(dest)
```

**测试配置** (`config_e2e_official.json`):
```json
{
  "stock_code": "301611",
  "delete_later": false,  // 保留文件用于下次验证
  ...
}
```

**验证方式**:
- 记录 `skipped_files` 计数器
- 日志包含 "already exists"
- 下载耗时缩短

### 思路2 实现: 翻页功能验证

**下载器实现** (`src/services/unified_downloader.py`):
```python
for page in range(1, request.max_pages + 1):
    self.pages_traversed = page
    downloaded = self._download_page_links(request, page)
    if not self.pagination_handler.go_to_next_page():
        break
```

**测试配置**:
```json
{
  "stock_code": "300470",
  "suffix": "periodicReports",
  "max_pages": 5,  // 测试翻页
  ...
}
```

**验证方式**:
- 记录 `pages_traversed` 计数器
- 记录 `page_turns` 翻页次数

### 思路3 实现: 多页面类型验证

**测试配置**:
```json
// TC-001: research
{"suffix": "research", ...}

// TC-002: periodicReports  
{"suffix": "periodicReports", ...}

// TC-004: latestAnnouncement
{"suffix": "latestAnnouncement", ...}
```

**验证方式**:
- 不同后缀的页面都能正常加载
- 页面元素选择器正确

---

## 测试用例

### 官方测试用例 (config_e2e_official.json)

| 用例 | 股票代码 | 后缀 | 关键词 | 页数 | delete_later | 目的 |
|------|----------|------|--------|------|--------------|------|
| TC-001 | 301611 | research | 投资者关系管理信息20250725 | 1 | false | 内容验证 + 跳过测试 |
| TC-002 | 300470 | periodicReports | 2025年一季度报告 | 5 | true | 翻页功能测试 |
| TC-003 | 300470 | research | 2023年1月31日投资者关系活动记录表 | 3 | true | 多页面类型测试 |
| TC-004 | 300470 | latestAnnouncement | 招股说明书 | 1 | true | 页面类型覆盖补充 |

### delete_later 标记说明

| 值 | 行为 | 用途 |
|----|------|------|
| false | 测试后保留文件 | 用于跳过已存在文件测试 |
| true | 测试后清理文件 | 功能测试，不保留结果 |

## 行为验证字段

### DownloadResult 新增字段

```python
@dataclass
class DownloadResult:
    # 原有字段
    success: bool
    downloaded_files: List[str]
    total_files: int
    errors: List[str]
    duration_seconds: float
    metadata: Dict[str, Any]
    
    # 行为验证字段
    skipped_files: List[str]  # 跳过的已存在文件
    pages_traversed: int  # 实际遍历的页数
```

### UnifiedDownloader 计数器

```python
class UnifiedDownloader:
    # 行为验证字段
    self.skipped_files: List[str] = []  # 跳过的已存在文件
    self.pages_traversed: int = 0  # 实际遍历的页数
```

### PaginationHandler 计数器

```python
class PaginationHandler:
    # 翻页行为计数器
    self.page_turns: int = 0  # 翻页次数
```

## 测试文件结构

```
tests/e2e/
├── official_e2e_test.py          # 官方验收测试
├── test_skip_existing_files.py   # 跳过行为测试 (新增)
├── test_pagination_behavior.py   # 翻页行为测试 (新增)
├── test_dual_browser_modes.py    # 双浏览器模式测试
├── test_expected_data_validation.py  # 期待数据验证
├── real_world_test_suite.py      # 真实世界测试
└── real_stock_codes.json         # 测试股票代码
```

## 验证流程

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 清理测试目录                                             │
│    CleanerTool.clean_test_directory()                       │
│    - 保留 delete_later=false 的用例结果                     │
├─────────────────────────────────────────────────────────────┤
│ 2. 执行测试用例                                             │
│    for test_case in config["test_cases"]:                   │
│        run_test_with_new_downloader(test_case)              │
│    - 记录 skipped_files, pages_traversed                   │
├─────────────────────────────────────────────────────────────┤
│ 3. 结果验证                                                 │
│    compare_directories(save_dir, expected_result_dir)       │
│    - 文件内容匹配                                           │
├─────────────────────────────────────────────────────────────┤
│ 4. 生成报告                                                 │
│    e2e_official_report.json                                 │
│    - 包含行为验证数据                                       │
└─────────────────────────────────────────────────────────────┘
```

## 运行命令

```bash
# Playwright 浏览器
python tests/e2e/official_e2e_test.py --browser-strategy=playwright

# Selenium 浏览器
python tests/e2e/official_e2e_test.py --browser-strategy=selenium

# 运行跳过行为测试
pytest tests/e2e/test_skip_existing_files.py -v

# 运行翻页行为测试
pytest tests/e2e/test_pagination_behavior.py -v
```

---

*最后更新: 2026-03-22*
