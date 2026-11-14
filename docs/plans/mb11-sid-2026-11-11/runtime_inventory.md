> **状态入口（2026-11-14）**：本文件为历史证据/子计划，SID 仓当前状态唯一以 [MB-SID task_plan](task_plan.md) 顶部 canonical 段为准；本文件的历史 Next Step 不代表当前待办。

# MB-SID — 交付 runtime 清单

按卡"全卡共用完成规则"第一条：先列本仓实际交付 runtime 的活动入口、逻辑模块、公开面、状态 owner 和依赖方向，并给出兼容/退休分类。

分类口径：

- **PRIMARY**：本卡交付的公开入口，必须可用。
- **ACTIVE-LEGACY**：仍在用、保留兼容，但不是本卡的边界目标。
- **CONTROLLED**：只在明确人工操作下运行（联网/E2E）。
- **RETIRED**：保留出处，无 runtime 引用，不得被默认调用。
- **NO_RUNTIME_REFERENCE**：不参与任何执行路径。

## 1. 活动入口

| 入口 | 调用方式 | 分类 | 公开面 | 状态 owner |
|---|---|---|---|---|
| provider JSON CLI | `python -m src.company_wiki_adapter_cli discover\|fetch` | PRIMARY | stdin 请求 JSON → stdout 单个 JSON 1.0；失败 JSON 走 stderr 最后一行；`--config`、`--staging-dir` | `company_wiki_adapter_cli` 拥有协议通道；`ProviderAcquisitionBudget` 拥有用量 |
| 批量下载 CLI | `python main.py <code>` / `--companies` / `--config` | ACTIVE-LEGACY | 退出码 + 日志；`config.json` 的 `pages[]` | `UnifiedRunner` 拥有批次成败；`StockDownloader` 拥有单请求结果 |
| 官方 E2E runner | `python tests/e2e/official_e2e_test.py --config … [--report-suffix …]` | CONTROLLED | 报告 JSON 文件名与内容 | runner 拥有报告；真实网络由人工触发 |
| fixture 捕获器 | `python scripts/capture_byd_fy2024_fixture.py` | RETIRED | 无（一次性脚本） | 无 runtime 状态；只写 `tests/fixtures/cninfo/` |

`scripts/capture_byd_fy2024_fixture.py` 是 `NO_RUNTIME_REFERENCE`：生产代码、测试、CLI 都不导入它，fixture 已入库，不得在构建/测试/自动化中执行。

## 2. 逻辑模块

| 模块 | 公开面 | 状态 owner | 直接依赖 | 分类 |
|---|---|---|---|---|
| `src/company_wiki_adapter_cli.py` | `main(argv)` | stdout/stderr 协议、budget 解析 | adapter, config, budget, logger | PRIMARY |
| `src/company_wiki_adapter.py` | `StockInfoCompanyWikiAdapter.discover/fetch`、`AdapterDiscoveryRequest`、`DisclosureCandidate`、`StagedDownloadReceipt`、`AdapterError` | candidate 映射、staging 回执；**不**决定 canonical 路径 | constants, `cninfo_report_metadata`, disclosure_matching, string_utils,（惰性）cninfo_api/cninfo_identity | PRIMARY |
| `src/cninfo_api.py` | `CninfoAnnouncementClient.discover_announcements/fetch_pdf/resolve_org_id`、`CninfoApiError` | HTTP 传输、字节预算计费、`.part`→final 原子改名 | budget, constants, `cninfo_report_metadata`, transport_states | PRIMARY |
| `src/cninfo_report_metadata.py` | `report_metadata(title)` | 无状态（纯函数） | `re` | PRIMARY（纯域） |
| `src/cninfo_identity.py` | `OrgIdIdentityResolver.resolve_org_id`、`LocalOrgIdCache` | 只读本地缓存 + 官方查询；不写缓存 | cninfo_api, constants, logger, string_utils | PRIMARY |
| `src/acquisition_budget.py` | `ProviderAcquisitionBudget`、`AcquisitionBudgetExceeded` | 唯一预算账本（字节/截止/费用） | 标准库 | PRIMARY |
| `src/transport_states.py` | `LoadState`（READY/CONFIRMED_EMPTY/INFRASTRUCTURE_FAIL/TIMEOUT） | 无状态枚举 | — | PRIMARY |
| `src/disclosure_matching.py` | `_matches_keywords`、`_matches_excluded` | 无状态（纯函数） | `re` | PRIMARY |
| `src/downloader.py` | `StockDownloader.download/cleanup`、`DownloadRequest`→`DownloadResult` | 单请求下载流水线、`_request_failures`、验证结论 | browser, mapping, models, logger, exceptions, constants, string_utils, transport_states | ACTIVE-LEGACY |
| `src/browser.py` | `PlaywrightBrowser`（含 `select_menu_item`、`find_active_tab_links`） | 浏览器/页面生命周期、SPA 页签 DOM 知识 | constants, exceptions, logger | ACTIVE-LEGACY |
| `src/mapping.py` | `MappingManager.get_org_id/get_stock_name/add_mapping` | `stock_orgid_mapping.json` 的读写 | logger, models, storage, string_utils | ACTIVE-LEGACY |
| `src/orgid.py` | `OrgIdCrawler.get_org_id` | 网页爬取（依赖 browser strategy） | constants, logger, string_utils | ACTIVE-LEGACY |
| `src/models.py` | `DownloadRequest`、`DownloadResult`、`VerificationResult`、`VerificationIssue`、`OrgIdMapping` | 无状态数据契约 | transport_states | ACTIVE-LEGACY |
| `src/config.py` | `load_config`、`load_companies` | 无状态（读文件 + 合并默认值） | constants, exceptions, logger | ACTIVE-LEGACY |
| `src/progress.py` | `ProgressTracker` | 断点续传进度文件 | 标准库 | ACTIVE-LEGACY |
| `src/storage.py` | `JsonStorage` | 单个 JSON 文件的原子读写 | 标准库 | ACTIVE-LEGACY |
| `src/stock.py` | 股票名称查询 | 无状态（外部 API 调用） | 标准库 | ACTIVE-LEGACY |
| `src/logger.py` | `setup_logger`、`log` | 控制台 handler 流（stderr）与文件 handler | 标准库 | ACTIVE-LEGACY |
| `src/constants.py` | 常量 | 无状态 | — | ACTIVE-LEGACY |
| `src/exceptions.py` | 异常类型 | 无状态 | — | ACTIVE-LEGACY |
| `src/string_utils.py` | `clean_filename`、`standardize_stock_code` | 无状态（纯函数） | `re` | ACTIVE-LEGACY |

## 3. 依赖方向

```
company_wiki_adapter_cli
  ├─→ company_wiki_adapter ─→ cninfo_report_metadata
  │        │                └→ disclosure_matching / string_utils / constants
  │        ├─(惰性)→ cninfo_api ─→ acquisition_budget / transport_states
  │        └─(惰性)→ cninfo_identity ─→ cninfo_api
  └─→ config / acquisition_budget / logger

main.py → downloader → browser / mapping / models / logger / exceptions
        → config / progress / mapping / models
```

规则：

1. **API → domain ← adapter** 单向。`cninfo_api` 与 `company_wiki_adapter` 都只向下依赖 `cninfo_report_metadata`，两者互不导入（`cninfo_api` 里对 adapter 的引用已全部移除，测试用 import-blocker 子进程证明）。
2. 纯域（`cninfo_report_metadata`、`disclosure_matching`、`string_utils`、`transport_states`、`constants`）不导入任何上层模块。
3. provider 链（CLI/adapter/API/identity/budget）不导入 `browser`/`downloader`/`mapping`/`orgid`/`playwright`；`test_provider_dependency_direction.py` 在拒绝这些导入的子进程里跑真实过滤。
4. 状态只由 owner 写：预算归 `ProviderAcquisitionBudget`，staging 归调用者分配的目录，下载进度归 `ProgressTracker`，org_id 缓存只读（`LocalOrgIdCache` 不写）。

## 4. 交付包边界

无 wheel/安装器。`tests/unit/test_provider_runtime_artifact.py` 用显式 manifest 复制 14 个文件构成 provider runtime：

```
__init__.py, acquisition_budget.py, cninfo_api.py, cninfo_identity.py,
cninfo_report_metadata.py, company_wiki_adapter.py, company_wiki_adapter_cli.py,
config.py, constants.py, disclosure_matching.py, exceptions.py, logger.py,
string_utils.py, transport_states.py
```

不在包内（有意）：`browser.py`、`downloader.py`、`mapping.py`、`models.py`、`orgid.py`、`progress.py`、`storage.py`、`stock.py`。空 cwd + 仅 artifact 在 import path 时可完成 discover/fetch。

## 5. 本卡改动对清单的影响

- 新增模块 `cninfo_report_metadata.py`（纯域），已在依赖图中定位。
- `cninfo_api` 从"函数内反向导入 adapter"变为"模块级向下依赖纯域"。
- `browser` 新增页签作用域访问器，DOM 知识集中在它身上，`downloader` 不再自己拼选择器。
- `downloader` 新增单请求失败记录与验证结论，仍是 ACTIVE-LEGACY，不进入 provider 包。
- `scripts/` 首次入库，只有一支 RETIRED 工具，不构成入口扩张。
