# Stock Downloader V2

从 StockInfoDownloader (29,000 行) 重构为 ~2,300 行的精简版巨潮资讯网股票文档下载器。
保留全部功能，仅使用 Playwright，零过度抽象。

## Quick Start

```bash
# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 下载单个股票的研究报告（前5页）
python main.py 000001

# 使用配置文件
python main.py --config config.json

# 使用 TXT 公司列表批量下载
python main.py --companies companies.txt

# 并行下载多家公司
python main.py --companies companies.txt --parallel --workers 5

# 清除进度记录，从头开始
python main.py --companies companies.txt --parallel --clean
```

### CLI 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `stock_code` | 位置参数 | — | 单只股票代码 |
| `--config` | string | `config.json` | 配置文件路径 |
| `--companies` | string | — | TXT 公司列表文件（每行格式：`股票代码 [公司名]`） |
| `--parallel` | flag | false | 启用并行下载模式 |
| `--workers` | int | 3 | 并行线程数 |
| `--clean` | flag | false | 删除进度文件，从头开始 |

**执行优先级：** CLI stock_code > `--companies` 文件 > config.test_cases > config.companies > config.stock_code

### TXT 公司列表格式

```
# 注释行以 # 开头，空行自动跳过
# 格式：stock_code [company_name]  （公司名可选）
300470 中密控股
002371 北方华创
300750
```

## 使用案例：批量下载 A 股公司

以 `config_template.json` 为配置模板，`a_share_companies.txt`（192 家公司）为股票列表：

```bash
# 顺序下载（稳定，适合长时间运行）
python main.py --config config_template.json --companies a_share_companies.txt

# 并行下载（5 线程，速度快但反爬风险更高）
python main.py --config config_template.json --companies a_share_companies.txt --parallel --workers 5

# 中途中断后继续（进度自动保存，重新运行即可断点续传）
python main.py --config config_template.json --companies a_share_companies.txt --parallel --workers 5

# 从头重新开始（清除之前的进度记录）
python main.py --config config_template.json --companies a_share_companies.txt --parallel --clean
```

`config_template.json` 会为每家公司下载三类文档：

| 页面 | 说明 | 保存位置 |
|------|------|----------|
| 招股说明书 | 最新公告中的招股说明书，排除摘要 | `{save_dir}/{公司名}/raw/prospectus/` |
| 定期报告 | 年报/半年报/季报，排除摘要 | `{save_dir}/{公司名}/raw/financial_reports/` |
| 研究报告 | 所有研究报告 | `{save_dir}/{公司名}/raw/research/` |

> **注意：** `save_dir` 默认为 `C:/Users/郑曾波/Projects/company-wiki/companies`，请根据实际路径修改。192 家公司全量下载预计耗时数小时，建议使用 `--parallel` 并在后台运行。

## 架构

```
src/
  browser.py         Playwright 浏览器封装 (485 行)
  downloader.py      核心下载逻辑 + 失败日志 (588 行)
  mapping.py         股票代码 → org_id 映射 + 自动爬取 (248 行)
  config.py          配置加载 (103 行)
  constants.py       URL/选择器/超时常量
  models.py          数据模型 (DownloadRequest/Result/OrgIdMapping)
  storage.py         JSON 存储
  orgid.py           org_id 网络爬取 (177 行)
  progress.py        下载进度追踪 — 断点续传 (108 行)
  stock.py           股票名称查询 (腾讯财经 API)
  string_utils.py    字符串工具
  logger.py          日志
  exceptions.py      自定义异常
main.py              CLI 入口 (252 行)
```

## 功能

| 功能 | 说明 |
|------|------|
| Playwright 驱动 | 现代浏览器自动化，无 Selenium 依赖 |
| org_id 自动解析 | 本地映射查找 → 网络爬取 → 自动保存 |
| 股票名称查询 | 腾讯财经 API / 巨潮 API 双源 |
| 多页下载 | 正序（第1页开始）和反序（最后页开始） |
| 关键词过滤 | 支持日期格式匹配（如 20250725） |
| 跳过已存在 | 文件已下载则自动跳过 |
| 反爬虫 | 随机 UA、Referer、Anti-detection JS、Cookie 轮换、指数退避 |
| 失败日志 | 下载失败自动记录到 logs/failed_downloads.json |
| 进度追踪 | 自动记录完成/失败状态，支持断点续传（`--clean` 可清除） |
| TXT 公司列表 | `--companies` 支持从文本文件加载，每行一只股票 |
| 并行下载 | ThreadPoolExecutor 多线程 |

## 配置

### 完整配置项

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `save_dir` | string | `"downloads"` | 下载文件保存目录 |
| `headless` | bool | `true` | 浏览器是否无头运行 |
| `max_retries` | int | `3` | 下载失败重试次数 |
| `timeout_seconds` | int | `180` | 页面超时时间（秒） |
| `browser.strategy` | string | `"playwright"` | 浏览器策略（仅支持 playwright） |
| `browser.headless` | bool | `true` | 浏览器无头模式（可覆盖顶层 headless） |
| `download.max_pages` | int | `5` | 每类页面最大下载页数 |
| `download.download_delay` | float | `0.5` | 下载间隔（秒） |
| `anti_crawler.enabled` | bool | `true` | 是否启用反爬措施 |
| `anti_crawler.base_delay` | float | `1.0` | 请求基础延迟（秒） |
| `anti_crawler.random_delay_range` | [float, float] | `[0.5, 2.0]` | 随机延迟范围 |
| `logging.level` | string | `"INFO"` | 日志级别 |
| `logging.log_to_file` | bool | `true` | 是否写入日志文件 |
| `logging.log_file` | string | `"logs/downloader.log"` | 日志文件路径 |
| `pages` | array | `[]` | 页面配置列表（见下） |
| `companies` | array | `[]` | 公司列表，用于批量下载 |
| `test_cases` | array | `[]` | E2E 测试用例列表 |

### 页面配置 (pages)

```json
{
  "pages": [
    {
      "name": "Research Reports",
      "suffix": "research",
      "max_pages": 5,
      "allowed_keywords": ["投资者关系"],
      "reverse_order": false,
      "save_dir": "custom/downloads"
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `suffix` | string | 页面标识：`research`、`periodicReports`、`latestAnnouncement` |
| `name` | string | 页面名称（仅用于日志） |
| `max_pages` | int | 最大下载页数 |
| `allowed_keywords` | string[] | 包含关键词过滤，支持日期格式如 `"20250725"` |
| `excluded_keywords` | string[] | 排除关键词过滤，如 `["摘要"]` |
| `reverse_order` | bool | 是否从最后一页开始倒序下载 |
| `save_dir` | string | 覆盖全局 `save_dir` |
| `save_subdir` | string | 子目录，如 `"raw/prospectus"`，与 `save_dir` 拼接 |

### config.json 结构示例

```json
{
  "save_dir": "downloads",
  "headless": true,
  "max_retries": 3,
  "timeout_seconds": 180,
  "pages": [
    {
      "name": "招股说明书",
      "suffix": "latestAnnouncement",
      "allowed_keywords": ["招股说明书"],
      "excluded_keywords": ["摘要"],
      "max_pages": 3,
      "reverse_order": true,
      "save_subdir": "raw/prospectus"
    },
    {
      "name": "定期报告",
      "suffix": "periodicReports",
      "allowed_keywords": ["年度报告", "半年度报告", "季度报告"],
      "excluded_keywords": ["摘要"],
      "max_pages": 999,
      "save_subdir": "raw/financial_reports"
    },
    {
      "name": "研究报告",
      "suffix": "research",
      "max_pages": 999,
      "save_subdir": "raw/research"
    }
  ],
  "companies": [
    {"stock_code": "000001", "company_name": "平安银行"}
  ]
}
```

### E2E 测试配置 (config_e2e_official.json)

```json
{
  "save_dir": "end2end_test/test_results",
  "expected_result_dir": "end2end_test/expected_results",
  "test_cases": [
    {
      "stock_code": "301611",
      "suffix": "research",
      "allowed_keywords": ["投资者关系管理信息20250725"],
      "max_pages": 1,
      "delete_later": false
    }
  ]
}
```

### 支持的页面类型 (suffix)

| suffix | 说明 |
|--------|------|
| research | 研究报告 / 投资者关系 |
| periodicReports | 定期报告（年报、季报） |
| latestAnnouncement | 最新公告（通常配合 reverse_order: true） |

## 测试

```bash
# 全部测试
pytest tests/ -v

# 仅单元测试
pytest tests/unit/ -v

# 仅 E2E 行为测试
pytest tests/e2e/ -v

# 官方 E2E 测试（需要网络，约 3 分钟）
python tests/e2e/official_e2e_test.py --browser-strategy playwright
```

### 测试统计

| 类别 | 数量 |
|------|------|
| 单元测试 (config/models/mapping/downloader/storage/parallel/failed_logger/progress) | 104 |
| E2E 行为测试 (翻页/跳过文件/orgid解析) | 35 |
| **总计** | **139** |

## 项目对比

| 指标 | V1 (旧) | V2 (新) |
|------|---------|---------|
| 源代码行数 | 29,335 | **~2,300** |
| 文件数 | 86 | **14** |
| 类数量 | 205 | **15** |
| 配置文件 | 32 | **2** |
| 浏览器引擎 | Selenium + Playwright | **仅 Playwright** |
| 微服务容器 | 5 个 | **无** |
| 测试数 | 不确定 | **139 (100% 通过)** |

## License

MIT
