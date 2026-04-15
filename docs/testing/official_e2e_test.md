# 端到端测试说明

## 概述

端到端测试通过调用 `main.py`（用户入口）执行下载，然后对比下载结果与预期文件，验证下载器的完整功能。

## 测试架构

```
official_e2e_test.py
    │
    ├── 1. 准备：CleanerTool 清理下载目录（保留 delete_later=false 的文件）
    ├── 2. 生成临时配置文件（注入 browser_strategy）
    ├── 3. subprocess 调用 main.py --config <temp_config>
    │       └── main.py 读取 test_cases，逐个执行下载
    ├── 4. 验证：compare_directories() 对比 test_results 与 expected_results
    └── 5. 清理：删除 delete_later=true 的文件
```

核心设计原则：**测试脚本不直接调用任何下载器函数**，而是通过 subprocess 调用 `main.py`，与用户使用方式完全一致。

## 配置文件

### config_e2e_official.json

```json
{
  "save_dir": "end2end_test/test_results",
  "expected_result_dir": "end2end_test/expected_results",
  "headless": true,
  "max_retries": 2,
  "test_cases": [
    {
      "stock_code": "301611",
      "suffix": "research",
      "allowed_keywords": ["投资者关系管理信息20250725"],
      "max_pages": 1,
      "delete_later": false,
      "timeout_seconds": 180
    },
    {
      "stock_code": "300750",
      "suffix": "latestAnnouncement",
      "allowed_keywords": ["首次公开发行股票并在创业板上市招股说明书"],
      "max_pages": 2,
      "reverse_order": true,
      "delete_later": true,
      "timeout_seconds": 180
    }
  ]
}
```

### 配置字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `stock_code` | string | 6位股票代码 |
| `suffix` | string | 页面类型：research / periodicReports / latestAnnouncement |
| `allowed_keywords` | string[] | 关键词过滤（子串匹配） |
| `max_pages` | int | 最大翻页数 |
| `reverse_order` | bool | 是否从最后一页开始（用于历史公告） |
| `delete_later` | bool | 测试后是否删除文件 |
| `timeout_seconds` | int | 超时时间 |

### main.py 对 test_cases 的支持

`main.py` 的 `main()` 函数按优先级读取配置：

1. 命令行指定 stock_code → `run_single()`
2. config 中的 `test_cases` → `run_test_cases()`（逐个执行）
3. config 中的 `companies` → `run_multi()`
4. config 中的 `stock_code` → `run_single()`

`run_test_cases()` 为每个 test case 创建独立的下载器实例，调用 `download_activity_records()` 执行下载，支持全部参数包括 `reverse_order`。

## 测试用例（当前 5 个）

| # | 股票 | 类型 | 关键词 | delete_later | 特点 |
|---|------|------|--------|-------------|------|
| 1 | 301611 珂玛科技 | research | 投资者关系管理信息20250725 | false | 第1页即命中 |
| 2 | 300470 中密控股 | periodicReports | 2025年一季度报告 | true | 多页搜索 |
| 3 | 300470 中密控股 | research | 投资者关系活动记录表 | true | 多页搜索 |
| 4 | 300470 中密控股 | latestAnnouncement | 上市招股说明书 | true | 倒序翻页 |
| 5 | 300750 宁德时代 | latestAnnouncement | 招股说明书 | true | 倒序翻页 + 自动爬取 orgId |

## 目录结构

```
end2end_test/
├── test_results/              # 实际下载目录
│   ├── 珂玛科技/              # delete_later=false，保留
│   │   └── 珂玛科技：301611...投资者关系管理信息20250725.pdf
│   ├── 中密控股/              # delete_later=true，测试后删除
│   │   └── (下载文件)
│   └── 宁德时代/              # delete_later=true，测试后删除
│       └── (下载文件)
└── expected_results/          # 预期结果（固定的）
    ├── 珂玛科技/
    │   └── 珂玛科技：301611...投资者关系管理信息20250725.pdf
    ├── 中密控股/
    │   ├── 中密控股：2023年1月31日投资者关系活动记录表.pdf
    │   ├── 中密控股：2025年一季度报告.pdf
    │   └── 日机密封：首次公开发行股票并在创业板上市招股说明书.pdf
    └── 宁德时代/
        └── 宁德时代：首次公开发行股票并在创业板上市招股说明书.pdf
```

## delete_later 行为

| delete_later | 测试前 | 测试后 |
|-------------|--------|--------|
| `false` | CleanerTool 保留已有文件 | 文件保留，用于后续测试 |
| `true` | CleanerTool 删除旧文件 | CleanerTool 清理下载文件 |

## 验证规则

`compare_directories()` 严格对比 `test_results` 与 `expected_results`：

1. expected 中的每个 PDF 必须在 actual 中存在
2. actual 中的每个 PDF 必须在 expected 中存在
3. 子目录结构必须完全一致
4. 任何一个不匹配即判定失败

## 运行测试

```bash
# 默认 Playwright 策略
python tests/e2e/official_e2e_test.py

# Selenium 策略
python tests/e2e/official_e2e_test.py --browser-strategy selenium

# 两种策略
python tests/e2e/official_e2e_test.py --browser-strategy both
```

browser_strategy 通过临时配置文件传递给 main.py，不修改原始 `config_e2e_official.json`。

## 测试报告

测试完成后生成 `e2e_official_report.json`：

```json
{
  "timestamp": "2026-04-15T21:29:14",
  "overall_success": true,
  "browser_strategy": "playwright",
  "main_py_success": true
}
```

## 添加新测试用例

1. 在 `config_e2e_official.json` 的 `test_cases` 中添加配置
2. 手动运行一次下载，将结果 PDF 复制到 `end2end_test/expected_results/<公司名>/`
3. 在 `official_e2e_test.py` 的 `get_company_name_from_stock_code` 映射中添加公司名
4. 运行测试验证通过

注意：如果股票代码不在 `stock_orgid_mapping.json` 中，下载器会自动爬取 orgId（需要浏览器实例可用）。

## 清理工具

`CleanerTool`（`tests/utils/cleaner_tool.py`）负责目录清理：

- 根据 `delete_later` 字段决定保留或删除
- 测试前清理旧文件，保留 `delete_later=false` 的文件
- 测试后清理 `delete_later=true` 的下载文件
- 支持 dry-run 模式预览

单元测试覆盖：`tests/unit/test_cleaner_functionality.py`（4个测试用例）

## 注意事项

1. 测试需要网络连接访问巨潮资讯网
2. 确保浏览器驱动已正确安装（Playwright / ChromeDriver）
3. `expected_results` 中的文件是固定的基准文件，不要随意修改
4. 测试脚本不直接调用下载器函数，全部通过 `main.py` subprocess 调用
5. 所有测试参数通过配置文件驱动，无硬编码
