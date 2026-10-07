# Findings: G5-SID-RUNTIME

（勘察阶段持续追加；外部/仓库内容一律按数据记录，不当指令执行。）

## 卡片要点摘录（非指令）

- 目标：CWP provider 只依赖 请求验证 → 只读本地映射/有界官方身份查询 → 有界公告/文件 HTTP。
- orgID、分页、fetch 共用同一传入 budget，不重置 deadline、不重置累计 response bytes、不造第二账本。
- 禁止给 CWP 强制新 org_id 字份、禁止永久预 seed 全公司映射。
- cache 只是 stock_code→org_id 线索，官方候选仍需核 SEC/期间/公开日/完整性。
- 旧 `StockInfoCompanyWikiAdapter(downloader, *, cninfo_client=...)` 调用仍可用，可追加可选 identity resolver。
- 推荐内部小接口 `resolve_org_id(stock_code, *, budget=None)`。
- 禁写 11 个 tracked owner 文件 = 原仓 `git status` 显示的 11 个 ` M`：README.md、config_template.json、main.py、src/browser.py、src/downloader.py、src/logger.py、src/mapping.py、src/models.py、tests/e2e/official_e2e_test.py、tests/unit/test_downloader.py、tests/unit/test_official_e2e_contract.py；外加未跟踪 a_share_companies.txt、companies.txt、scripts/。

## 勘察结论

### 依赖图（provider runtime 现状）

- `src/company_wiki_adapter.py:19` 模块级 `from .downloader import StockDownloader, _matches_excluded, _matches_keywords` → 连带 `src.browser` → `playwright`。
- `src/company_wiki_adapter.py:20` 从 `string_utils` 拿 `clean_filename`（这个可以保留，string_utils 无副作用）。
- `src/company_wiki_adapter_cli.py:25` 模块级 `from .downloader import StockDownloader`。
- `src/company_wiki_adapter_cli.py:107` `_build_adapter` → `StockDownloader(load_config(...))`。
  - `StockDownloader.__init__`（downloader.py:126）立刻 `FailedDownloadLogger()` → `logs/failed_downloads.json` 的父目录 `mkdir`（downloader.py:32）→ **构造即写失败日志目录**。
- `discover()` 无 org_id 时 `self.downloader.mapping.get_org_id(...)`（adapter:317）。
  - `StockDownloader.mapping`（downloader.py:140）先访问 `self.browser` → `PlaywrightBrowser(...).initialize()` → **启动浏览器**。
  - `MappingManager.get_org_id` cache 未命中且 `auto_fetch=True` → `_crawl_org_id` → `src.orgid.OrgIdCrawler` → `requests.post`（无 budget、15s 固定 timeout）+ 浏览器 fallback（orgid.py:62、86、124）→ **预算外网络**。
- CLI `finally`：`adapter.downloader.cleanup()`（cli:249）——纯 API 对象没有 `.downloader` 时会 AttributeError 掩盖结果。

### orgID 旧 cache 读取规则（src/mapping.py:31-42）

`mapping_file` 显式传入优先；否则按序取**第一个存在的**：
1. `Path(src/__file__.parent)/stock_orgid_mapping.json`
2. `Path("stock_orgid_mapping.json")`（cwd）
3. `Path("configs/stock_orgid_mapping.json")`

schema（mapping.py:164-196）：顶层 dict，value 需为 dict，`orgId` 或 `org_id` 之一非空，否则跳过该条；`name`/`stock_name` 缺省 `"Unknown"`。
- 本 worktree `src/stock_orgid_mapping.json` **不存在**（`git ls-files` 无此项，`.gitignore` 的 `*.json` 也会忽略它）→ G5 必须**不创建**它。
- G4 E2E `_seed_org_mapping` 写 cwd（card_root）的 `stock_orgid_mapping.json`，靠候选 2 命中 → 新实现必须保持同样三候选顺序。

### cninfo_api 现有预算代码（可复用）

- `_post_json`（cninfo_api.py:479）：`budget.ensure_open()` → `remaining_response_bytes<=0` 拒绝 → `timeout=min(self._timeout, budget.remaining_seconds)` → `_read_bounded_response` 流式计量。
- `_copy_bounded_response`（:609）：先看 Content-Length > remaining 即拒；每 chunk `budget.consume_response_bytes`。
- `fetch_pdf` 同样守卫 + `.part` 清理（:330-334、:429-435）。
- 因此 identity HTTP 复用 `_post_json` 即自动满足 "每次流式计量、timeout<=remaining、不重置 deadline/bytes"。
- **耗尽后不继续公告查询** 已由 `_post_json` 前置守卫保证（不发 urlopen）。

### 公开契约（不可变）

- CLI 参数：`action ∈ {discover,fetch}`、`--config`、`--staging-dir`。
- 成功/失败 JSON `schema_version=1.0`；`adapter = {"name":"stockinfo-cninfo","version":"1.3.0"}`。
- `DisclosureCandidate` / `StagedDownloadReceipt` 字段、exact/latest 语义、G4 五页完整性。
- `acquisition_budget` payload 1.0 四字段。

### G4 E2E 现成 harness（可复用模式）

- `tests/e2e/test_g4_latest_cli_offline.py` + `docs/implementation/g4-sid-latest/g4_bootstrap/sitecustomize.py`
  - sitecustomize 只重写 `urllib.request.urlopen` 的 cninfo host → `G4_LOOPBACK`；`G4_LOOPBACK` 未设置时对 cninfo 请求直接 `URLError`。
  - `_run_cli` = 真实 `sys.executable -m src.company_wiki_adapter_cli <action> --config <tmp>`，cwd=card_root。
  - `_payload()` **始终带 org_id=ORG**；只有两个 CWP route 测试不带（靠 `_seed_org_mapping` cwd cache）→ G5 改动对它们是 1 次 announcement POST，前后一致。
  - `_seed_org_mapping` 的 docstring 说 "falls back to StockDownloader.mapping" → 改动后陈述失真，需同步（卡允许为 adapter/身份依赖调整该文件）。

### 可写/禁写核对

- 可写：`src/company_wiki_adapter.py`、`company_wiki_adapter_cli.py`、`cninfo_api.py`、`acquisition_budget.py`；新 `src/cninfo_identity.py`、`src/disclosure_matching.py`；精确 tests 列表；新 `tests/unit/test_g5_provider_runtime.py`、`tests/e2e/test_g5_browserless_provider.py`、`tests/fixtures/g5_provider/`、PWF。
- **`src/config.py` 不在可写列表**（只在"先读"里）→ 不改。
- `src/orgid.py` 只读参考。
- `.gitignore` 有 `*.json`（`!tests/**/*.json` 例外）→ `.planning/*.json` 需 `git add -f`。
- 仓无 workflow/CI；`mypy` 原有 12 个 base 错误不扩门。

### 需要动的既有测试

1. `tests/unit/test_company_wiki_adapter_cli_budget.py::_real_adapter`
   - `_payload()` 无 org_id，本仓 cwd 也无 cache → 新实现会发 identity HTTP，而 urlopen mock 固定返回 `{"totalRecordNum":0,...}` → 身份失败。
   - 保持"无 org_id 请求"，把 urlopen mock 改成**第一次返回身份体、之后返回公告体**，断言 `response_bytes == len(identity)+len(announcement)`（正好覆盖"身份+公告同 budget 精确总量"）。
2. `tests/e2e/test_g4_latest_cli_offline.py::_seed_org_mapping` docstring 更新为新的 identity cache 路径。

## 关键决策

| 决策 | 理由 |
|------|------|
| identity HTTP 加在 `CninfoAnnouncementClient` 上（复用 `_post_json`） | 卡§3 "由同一Cninfo客户端有界HTTP实现，复用现有stream预算代码" |
| `StockInfoCompanyWikiAdapter(downloader=None, *, cninfo_client=None, identity_resolver=None)` | 保留旧位置参数，`None` 表示纯 API runtime |
| 身份失败 error code：`org_id_unresolved` / `org_id_ambiguous` / `schema_drift`，retryable=False | 卡§4.3 "身份未确认是身份失败，不能报最新财报覆盖但空" |
| E2E sitecustomize 放 `tests/fixtures/g5_provider/sitecustomize.py` | 卡§3 明确新 `tests/fixtures/g5_provider/` |
| identity 响应格式 = 现有公告查询响应（`announcements[].secCode/orgId`） | 与 `orgid._query_api` 同一端点、同一 schema，不引入新 wire |
