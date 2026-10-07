# G5-SID-RUNTIME 交接 — 纯API provider 解耦与完整预算

**package**: `G5-SID-RUNTIME` · **branch**: `codex/g5-sid-runtime`（未推远端）
**base**: `0cb3c1f0b4a5784757971265b2b20a7a0b4c5104`
**implementation**: `7a4bf0d97dba197e4accf0bd47707f012a6a7413`
**worktree**: `C:/Users/郑曾波/Projects/_g5/sid`（原仓 `C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite` 的 worktree）
**冻结 CWP consumer**: `C:/Users/郑曾波/Projects/company-wiki` @ `df7d7ba58955e224c1799355f479ad5378ef38a7`（`git archive` 只取已提交内容，未用原仓未提交 G2-12）

机器可读交接见同目录 `handoff.json`（对 `harness_lanes/g5_handoff.schema.json` 校验 **0 errors**）。
依赖/HTTP出口/预算/写盘说明见 `dependency_map.json`，接线见 `main_wiring.md`。

## 1. 已证问题（G4 交付上的依赖/预算补漏）

| 缺口 | 改造前 | 改造后 |
|------|--------|--------|
| CLI 构造 provider | `_build_adapter` → `StockDownloader(...)`，`__init__` 立刻 `mkdir logs/` 建失败日志目录 | `load_config(config)` 后 `StockInfoCompanyWikiAdapter(None)`；反例断言 `<test-root>/logs` 不存在 |
| adapter runtime 依赖 | 模块级 `from .downloader import StockDownloader, _matches_excluded, _matches_keywords` → 连带 `src.browser` → `playwright` | 只 import `src.disclosure_matching`（新）与 `string_utils`；`downloader` 仅在 `TYPE_CHECKING` 下出现 |
| 无 org_id 的 discover | `downloader.mapping` → `StockDownloader.browser` → `PlaywrightBrowser.initialize()`；cache 未命中再走 `MappingManager.auto_fetch` → `src.orgid` 裸 `requests.post`（无 budget、15s 固定 timeout）+ 浏览器 fallback | 三路径：请求 `org_id` → 只读 cache → `CninfoAnnouncementClient.resolve_org_id`（同一 budget） |
| 预算账本 | orgID 与公告分属两套，orgID 完全不计 bytes/deadline | 单个 `ProviderAcquisitionBudget` 贯穿 identity → 分页 → fetch；`usage()` 报累计真实字节 |
| CLI `finally` | `adapter.downloader.cleanup()` —— 纯 API 对象直接 `AttributeError` 掩盖原始结果 | `_cleanup()`：`getattr(adapter, "downloader", None)`，缺失即跳过 |

**没有做**（卡§2 明确禁止）：没有给 CWP 强制新 `org_id` 字段，没有永久预 seed 全公司映射，没有改 `src/config.py`，没有动 11 个 tracked owner 文件，没有把 `--headless` 当作无需 browser 的证明，没有重构 legacy 下载器/全部 types，没有安装 Playwright。

## 2. 身份三路径与错误语义

1. `AdapterDiscoveryRequest.org_id` 非空 → 直接采用（不标准化、不查 cache、不发请求）。
2. 只读 `stock_orgid_mapping.json`，候选顺序复刻 `src/mapping.py`：显式文件 → `src/` → cwd → `configs/`，取第一个存在的；schema 同旧实现（`orgId`/`org_id` 非空，否则跳过该条）。**只读**，bytes 与 `mtime_ns` 由反例证明不变。
3. 官方查询 `CninfoAnnouncementClient.resolve_org_id`：单页 `POST /new/hisAnnouncement/query`（含 `searchkey`），复用 `_post_json` 的 `ensure_open` / `remaining>0` 前置守卫、`_copy_bounded_response` 逐块计量、`timeout = min(20, budget.remaining_seconds)`。

拒绝规则（**绝不取首条**）：错 SEC → 不匹配；多个不同 `orgId` → `None`；根/记录坏 schema → `schema_drift`；空匹配 → `None`。

CLI 错误码：身份未确认 `org_id_unresolved`（`retryable=false`，类型 `AdapterError`）；坏 schema `schema_drift`；网络失败保留 `upstream_unavailable` / `upstream_timeout` 等原码与 `retryable=true`，并带 `error.acquisition_usage`。**身份失败不会被报成"最新财报覆盖但空"**（`bounded_discovery_empty` 只在公告窗口被完全覆盖后为空时出现）。

## 3. TDD

**RED**（`evidence/red_run.txt`）

```
$ python -B -m pytest -q -p no:cacheprovider tests/unit/test_g5_provider_runtime.py tests/e2e/test_g5_browserless_provider.py
33 failed, 3 passed in 8.80s   exit=1
```

对得上卡§4.1 的真实 RED：

- `ImportError: provider runtime import refused: src.downloader`（模块级 import 未拆）
- `AttributeError: 'NoneType' object has no attribute 'mapping'`（仍走 legacy mapping）
- `AttributeError: '_BrokenAdapter' object has no attribute 'downloader'`（CLI finally 无空保护）
- `TypeError: ... unexpected keyword argument 'identity_resolver'`
- E2E 子进程 `ImportError: g5 offline bootstrap: browser runtime import refused: src.downloader`

**GREEN**（`evidence/green_run.txt`）

```powershell
$env:G4_CWP_REPO='C:/Users/郑曾波/Projects/company-wiki'
$env:G4_CWP_COMMIT='df7d7ba58955e224c1799355f479ad5378ef38a7'
$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'
python -B -m pytest -q -p no:cacheprovider tests/unit/test_g4_latest_discovery.py tests/unit/test_company_wiki_adapter.py tests/unit/test_company_wiki_adapter_cli.py tests/unit/test_company_wiki_adapter_cli_budget.py tests/unit/test_cninfo_api.py tests/unit/test_cninfo_api_fixture_contract.py tests/unit/test_cninfo_api_budget.py tests/unit/test_g5_provider_runtime.py tests/e2e/test_g4_latest_cli_offline.py tests/e2e/test_g5_browserless_provider.py
```

**163 passed / 0 failed / 0 skipped，exit 0，41.21s。**

同命令插桩重跑（统计 `BaseHTTPRequestHandler` 的响应次数与 `Content-Length`）：**42 次 loopback 请求、18782 真实 response bytes、163 passed**。
G5 browserless E2E 单跑：**13 passed、15 次请求、5939 bytes、11.68s**，与逐例断言一致
（无 org_id 2 / cache 命中 1 / 显式 org_id 1 / identity 超预算 1 / identity 吃满预算 1 / deadline 0 / 公告超预算 2 / 错 SEC 1 / 歧义 1 / 坏 schema 1 / fetch 成功 2 / fetch 超预算 2 / bootstrap 探针 0）。
全量 `tests/unit`：**242 passed、exit 0、22.75s**（`evidence/unit_run.txt`）。

**external_network_requests = 0**：E2E 子进程的 sitecustomize 在 `socket.getaddrinfo` / `socket.socket.connect` 上直接拒绝非 loopback，server 只绑 127.0.0.1，且探针用例断言四个 guard（sitecustomize 已装载、urlopen/getaddrinfo/connect 均已包裹）与四个模块导入全部被拒。

**lint / type**

```
$ ruff check <11 个改动文件>            All checks passed!   exit=0   (evidence/ruff_run.txt)
$ ruff format --check <同 11 个文件>     11 files already formatted   exit=0
$ mypy src/company_wiki_adapter.py src/company_wiki_adapter_cli.py src/cninfo_api.py
  Found 11 errors in 5 files   exit=1   (evidence/mypy_run.txt)
```

base 为 **12** 个 mypy 错误；本包没有新增，还消掉了 `company_wiki_adapter.py` 的 `org_id` 赋值错误。仓无 workflow，**不称 CI 绿**，不设新门。

## 4. 独立测试包

新文件：

- `tests/unit/test_g5_provider_runtime.py`（23 例）
- `tests/e2e/test_g5_browserless_provider.py`（13 例）
- `tests/fixtures/g5_provider/sitecustomize.py`

覆盖：三种 orgID 路径；cache 原 bytes/`mtime_ns` 不变；错 SEC / 歧义 / 坏 schema 拒绝；身份+公告同 budget 精确总量；首次 lookup 耗尽 budget 后公告 0 次调用；deadline 到期 0 次 HTTP；异常 usage 完整传播；过滤 helper 与 downloader 等价（差分反例）；旧位置参数 constructor；CLI finally 兼容无 `.downloader` 且不掩盖原始失败；fetch 不触发身份 cache/browser/downloader、`.part` 清理；literal CLI 无 org_id 成功。

**替换 seam 只有三处**（`tests/fixtures/g5_provider/sitecustomize.py`）：

1. `urllib.request.urlopen` 仅把 `www.cninfo.com.cn` / `static.cninfo.com.cn` 映射到 `G5_LOOPBACK`（官方 host → 127.0.0.1），未设 `G5_LOOPBACK` 时对 cninfo URL 直接 `URLError`；
2. `socket.getaddrinfo` + `socket.socket.connect` 拒绝一切非 loopback 目的地址；
3. `sys.meta_path` 对 `playwright` / `src.browser` / `src.downloader` / `src.orgid` 抛 `ImportError`（不是 mock `initialize` 之后宣称不需要依赖）。

**测试 root** `<worktree>/.planning/test-tmp/g5-runtime`：先建父目录并记录 absent，每例只在自己子目录写真实 cache/config/PDF/staging，finally 离开该目录（Windows 不允许删 cwd）→ rmtree → rmdir 恢复 absent。不写 `src/stock_orgid_mapping`，不碰真实用户下载目录，不删原 owner 资料。

## 5. 保护与清理

- `git diff --name-only 0cb3c1f -- <11 个 tracked owner 文件>` → **空**；`git diff --name-only` 只有 5 个 owned 文件。
- `protection`: `production_writes=0`、`raw_deletions=0`、`paid_calls=0`；11 个 owner 文件 `before_sha256 == after_sha256`（见 `handoff.json`）。
- `cleanup`: `.planning/test-tmp/g5-runtime` 与 `.planning/test-tmp` absent → absent；`logs/`、`downloads/`、`src/stock_orgid_mapping.json` absent → absent。
- 全量 `tests/unit` 里 owner 的 `test_progress.py` 会按 `src/progress.py` 默认值建 `logs/progress.json`（`logs/` 已 gitignore）——既有行为，已清除；**G5 交付命令不产生该目录**。
- 未跑 `tests/e2e/test_orgid_resolution.py`、`official_e2e_test.py`、`test_pagination_behavior.py`、`test_skip_existing_files.py`（需外网/Chromium）→ `handoff.json` 里如实记为 `not_run`。

## 6. 公开契约（未变）

CLI `discover`/`fetch` + `--config`/`--staging-dir`；成功/失败 JSON `schema_version=1.0`；`adapter = {"name":"stockinfo-cninfo","version":"1.3.0"}`；candidate/receipt 字段与 `transport_url` 对 CWP 保持 opaque；exact / latest_as_of 语义与 G4 五页完整性；`acquisition_budget` payload 1.0。
兼容扩展：`StockInfoCompanyWikiAdapter(downloader, *, cninfo_client=..., identity_resolver=None)`（`downloader` 可为 `None`）、`CninfoAnnouncementClient.resolve_org_id`。

## 7. 交给 MAIN

见 `main_wiring.md`：合并范围（apply_after_merge）、明确不改（company-wiki 路由与 `SourceRequest`）、合并后必须重跑的 verify 清单。
`delivery_status = ready_for_main`；`remaining` 首条即 MAIN 复验，G2-12 仍未完成，本包不冒充完整 ensure 链。
