# Task Plan: G5-SID-RUNTIME 纯API provider 解耦与完整预算

Use this file as the durable roadmap for the task. Create it before complex work and keep it current as phases change.

## Goal

让 CWP provider（company_wiki_adapter / CLI）在无 Playwright/Chromium、无 downloader/browser 导入的前提下完成 discover/fetch，orgID 解析与公告查询共用同一传入 `ProviderAcquisitionBudget`，零预算外网络。

## Next Step

无 —— 本卡交付完成，等 MAIN 按 `main_wiring.md` 复验并合并到 `v2-clean-rewrite`。

## Current Phase

Phase 6（complete）

## Phases

### Phase 1: 基线与依赖勘察

- [x] 记录基线/owner SHA 与 worktree 状态
- [x] 读 `company_wiki_adapter{,_cli}.py`、`cninfo_api.py`、`acquisition_budget.py`
- [x] 只读 `downloader.py/mapping.py/orgid.py/string_utils.py`
- [x] 读 G4 `MAIN_ACCEPTANCE.md` 与对应 unit/CLI/budget/G4 E2E
- [x] 列出 provider 所有 runtime 依赖与外网出口
- [x] 核对 cache 读取路径的旧实现规则
- **Status:** complete

### Phase 2: RED 反例

- [x] `tests/unit/test_g5_provider_runtime.py`：拦截 playwright/src.browser/src.downloader/src.orgid
- [x] literal CLI 无 org_id 请求成功（browser 导入被拒时）
- [x] 有 cache 请求不启动浏览器、不写失败日志
- [x] `tests/e2e/test_g5_browserless_provider.py`：loopback + sitecustomize 拒绝非 loopback 外网
- [x] RED 证据 `.planning/g5-sid-runtime/evidence/red_run.txt`（33 failed / 3 passed, exit 1）
- **Status:** complete

### Phase 3: adapter 身份依赖拆分

- [x] 新 `src/cninfo_identity.py`：只读 `LocalOrgIdCache` + `OrgIdIdentityResolver`
- [x] 新 `src/disclosure_matching.py`：`matches_excluded` / `matches_keywords` 等价迁移
- [x] `src/company_wiki_adapter.py` 不再模块级 import downloader；`OrgIdResolver` Protocol
- [x] CLI `_build_adapter` 纯 API runtime；`finally` 走 `_cleanup()`
- [x] 保留旧 public constructor（位置参数 downloader 可为 None）
- **Status:** complete

### Phase 4: 三路径 orgID 与 budget 贯通

- [x] 显式有效 org_id → 本地 cache 只读 → 同 budget 官方 API
- [x] 错 SEC / 多 orgID / 坏 schema 拒绝（不取首条）
- [x] `CninfoAnnouncementClient.resolve_org_id` 复用 `_post_json`（流式计量、timeout<=remaining）
- [x] 无 budget 兼容调用仍 API-only（无 browser fallback）
- [x] 身份失败 code=`org_id_unresolved`，schema=`schema_drift`，网络保留原 code/retryable/usage
- **Status:** complete

### Phase 5: 测试与回归

- [x] 新 unit 23 passed
- [x] 新 E2E 13 passed
- [x] G4+G5 组合 163 passed
- [x] 全量 `tests/unit` 242 passed
- [x] ruff check/format 0；mypy 11（base 12，未新增）
- **Status:** complete

### Phase 6: 交付

- [x] 三 PWF + evidence（red/green/unit/ruff/mypy）
- [x] HANDOFF.md / handoff.json / main_wiring.md / dependency_map.json（handoff.json 对 g5_handoff.schema.json 校验 0 errors）
- [x] 两次提交（实现 + 交接），实际 tip 交给调用方
- **Status:** complete

## Key Questions

1. cache 读取路径的旧规则 → 已核：显式文件 > `src/stock_orgid_mapping.json` > cwd > `configs/`，取第一个存在的。
2. 旧 requests.post orgID 与浏览器 fallback 调用链 → 已核：`src/mapping._crawl_org_id` → `src/orgid.OrgIdCrawler`（`requests.post` 无 budget + 浏览器 fallback）。本次完全不走。
3. 哪些 runtime import 让 adapter 拖入 downloader → 已核：`company_wiki_adapter.py:19` 与 `company_wiki_adapter_cli.py:25` 的模块级 `from .downloader import ...`。

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 新建 worktree `_g5/sid` 分支 `codex/g5-sid-runtime` 于 `0cb3c1f` | 卡§1 指定；原仓 working tree 有 11 个 tracked 修改不可 reset |
| identity HTTP 放 `CninfoAnnouncementClient.resolve_org_id`，复用 `_post_json` | 卡§3 “由同一Cninfo客户端有界HTTP实现，复用现有stream预算代码” |
| `StockInfoCompanyWikiAdapter(downloader=None, *, cninfo_client=None, identity_resolver=None)` + `OrgIdResolver` Protocol | 保留旧位置参数；新依赖可注入、可被反例证明 |
| 身份失败 code：`org_id_unresolved` / `schema_drift`，retryable=False | 卡§4.3 “身份未确认是身份失败，不能报最新财报覆盖但空” |
| 单页 identity 查询（pageSize=30，含 `searchkey`） | 与 `src/orgid._query_api` 同端点同参数族；orgid 旧实现 pageSize=5 已证明单页足够 |
| E2E sitecustomize 放 `tests/fixtures/g5_provider/sitecustomize.py` | 卡§3 明确的新 fixture 目录 |
| 测试 root 用 `<worktree>/.planning/test-tmp/g5-runtime`，退出时 rmtree + rmdir 恢复 absent | 卡§5；并修掉 Windows 不能删 cwd 的问题 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| RED 后 `_browserless_runtime` 退出留下 `src.__dict__` 旧子模块属性、`sys.modules` 却没有 → 后续 `from src import ...` 拿到 stale 模块、`isinstance` 失败 | 1 | finally 中同时快照/恢复 `src` 包属性与 `sys.modules`，并把未预先存在的属性删掉 |
| `_JsonBody.read(-1)` 断言失败（无 budget 的兼容路径本来就 read-all） | 1 | 改为计数 `unbounded_reads`，预算路径断言其为 0 |
| `_PdfBody.read(-1)` 同上 | 1 | 允许 size<0 |
| 测试结束后 `.planning/test-tmp/g5-runtime/*` 残留（空目录） | 1 | `monkeypatch.chdir(root)` 让 cwd 停在被删目录内；finally 先 `os.chdir(WORKTREE)` 再 rmtree |
| E2E `announcement_bytes` 345 vs 实发 384 | 1 | handler 与属性都改成 `ensure_ascii=False` |
| E2E `loopback.posts[0]["stock"]` 元组下标错误 | 1 | 用 `identity_posts[0]` |
| `test_cli_budgeted_real_discovery_path_reports_http_body_bytes` 因新身份路径返回身份失败 | 1 | urlopen 改为先身份体后公告体，断言累计 bytes（可写测试集内调整） |
| `git show base:file \| sha256` 与工作区 sha 不等 | 1 | CRLF 过滤差异；改用 `git diff --name-only base -- <owner paths>` 为空证明未改 |

## Notes

- 卡§3 写集与禁写名单是硬约束，已对照：`git diff --name-only` 只含 5 个 owned 文件。
- 公开 wire（CLI 参数、schema 1.0、`stockinfo-cninfo/1.3.0`）未变。
- 仓无 workflow，不称 CI 绿；`mypy` 11 < base 12，不设新门。
