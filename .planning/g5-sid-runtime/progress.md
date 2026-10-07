# Progress: G5-SID-RUNTIME

## Session 1 — 勘察与 RED

- 2026-10-07 核对原仓：`v2-clean-rewrite` HEAD=`0cb3c1f`，working tree 有 11 个 tracked 修改 + 未跟踪名单/scripts（属原 owner，禁写）。
- 创建 worktree `C:/Users/郑曾波/Projects/_g5/sid`，分支 `codex/g5-sid-runtime`，基线 `0cb3c1f0b4a5784757971265b2b20a7a0b4c5104`。
- 创建 `.planning/g5-sid-runtime/` 三 PWF，`PLAN_ID=g5-sid-runtime` / `PWF_PLAN_ROOT=<worktree>` 解析成功。
- CWP 冻结 commit `df7d7ba58955e224c1799355f479ad5378ef38a7` 存在（CWP 当前 HEAD=`bfd6a4d`，有未提交改动 → 只用 `git archive` 取已提交内容）。
- 基线（未改代码）G4 集合：**127 passed / 41.68s**。
- 基线 mypy：**12 errors**；ruff check + format：**0**。

### RED

命令：

```
python -B -m pytest -q -p no:cacheprovider \
  tests/unit/test_g5_provider_runtime.py tests/e2e/test_g5_browserless_provider.py
```

结果：**33 failed, 3 passed, exit 1, 8.80s** → `evidence/red_run.txt`

关键 RED 原因（对得上卡§4.1）：

- `ImportError: provider runtime import refused: src.downloader`（模块级 import 未拆）
- `AttributeError: 'NoneType' object has no attribute 'mapping'`（仍走 legacy mapping）
- `AttributeError: '_BrokenAdapter' object has no attribute 'downloader'`（CLI finally 未做空保护）
- `TypeError: ... unexpected keyword argument 'identity_resolver'`
- E2E 子进程 `ImportError: g5 offline bootstrap: browser runtime import refused: src.downloader`

## Session 2 — GREEN

实现：

- 新 `src/disclosure_matching.py`（两个纯过滤 helper，与 downloader 等价）
- 新 `src/cninfo_identity.py`（`candidate_paths` / `LocalOrgIdCache` / `OrgIdIdentityResolver`）
- `src/cninfo_api.py`：新增 `CninfoAnnouncementClient.resolve_org_id(stock_code, *, budget=None)`，复用 `_post_json` + `_validated_page`
- `src/company_wiki_adapter.py`：去掉模块级 `.downloader` import；`OrgIdResolver` Protocol；`__init__(downloader=None, *, cninfo_client=None, identity_resolver=None)`；`_resolve_org_id` 三路径 + `AdapterError(code=..., retryable=...)`
- `src/company_wiki_adapter_cli.py`：`_build_adapter` 不再构造 `StockDownloader`；新增 `_cleanup()` 空保护
- 新 `tests/fixtures/g5_provider/sitecustomize.py`（host 映射 + 非 loopback 拒绝 + 导入拒绝）
- 新 `tests/unit/test_g5_provider_runtime.py`（23）、`tests/e2e/test_g5_browserless_provider.py`（13）
- 可写既有测试调整：`test_company_wiki_adapter_cli_budget.py`（身份体+公告体两段 mock）、`test_g4_latest_cli_offline.py`（`_seed_org_mapping` docstring 同步到新身份缓存路径）

### Test Runs

| # | 命令 | exit | 结果 | 耗时 |
|---|------|------|------|------|
| RED | `python -B -m pytest -q -p no:cacheprovider tests/unit/test_g5_provider_runtime.py tests/e2e/test_g5_browserless_provider.py` | 1 | 33 failed / 3 passed | 8.80s |
| GREEN | `python -B -m pytest -q -p no:cacheprovider tests/unit/test_g4_latest_discovery.py tests/unit/test_company_wiki_adapter.py tests/unit/test_company_wiki_adapter_cli.py tests/unit/test_company_wiki_adapter_cli_budget.py tests/unit/test_cninfo_api.py tests/unit/test_cninfo_api_fixture_contract.py tests/unit/test_cninfo_api_budget.py tests/unit/test_g5_provider_runtime.py tests/e2e/test_g4_latest_cli_offline.py tests/e2e/test_g5_browserless_provider.py` | 0 | **163 passed / 0 failed / 0 skipped** | 41.21s |
| 全量 unit | `python -B -m pytest -q -p no:cacheprovider tests/unit` | 0 | **242 passed / 0 failed / 0 skipped** | 22.75s |
| ruff | `ruff check <11 changed files>` + `ruff format --check <same>` | 0 | All checks passed / 11 already formatted | — |
| mypy | `mypy src/company_wiki_adapter.py src/company_wiki_adapter_cli.py src/cninfo_api.py` | 1 | **11 errors**（base 12，未新增） | — |

带 G4 跨仓环境：

```powershell
$env:G4_CWP_REPO='C:/Users/郑曾波/Projects/company-wiki'
$env:G4_CWP_COMMIT='df7d7ba58955e224c1799355f479ad5378ef38a7'
$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'
```

证据：`evidence/{red_run,green_run,unit_run,ruff_run,mypy_run}.txt`

### 保护与清理核验

- `git diff --name-only 0cb3c1f -- <11 个 tracked owner 文件>` → 空（owner 文件与基线一致）。
- `git diff --name-only` → 只有 5 个 owned 文件：`src/cninfo_api.py`、`src/company_wiki_adapter.py`、`src/company_wiki_adapter_cli.py`、`tests/e2e/test_g4_latest_cli_offline.py`、`tests/unit/test_company_wiki_adapter_cli_budget.py`。
- GREEN/全量 unit 跑完后：`logs/` 不存在、`.planning/test-tmp/` 不存在、`src/stock_orgid_mapping.json` 不存在、无 `downloads/` 产物。
- `external_network_requests = 0`：E2E 子进程 sitecustomize 直接拒绝非 loopback `getaddrinfo`/`connect`，并且 server 只绑 127.0.0.1；探针测试断言四个 guard 全部生效。
- 付费调用 0；未跑任何 live e2e（`tests/e2e/test_orgid_resolution.py`、`official_e2e_test.py`、`test_pagination_behavior.py`、`test_skip_existing_files.py` 需外网/浏览器，未执行）。

### Notes

- `tests/unit` 全量里 owner 的 `test_progress.py` 会按 `src/progress.py` 默认值创建 `logs/progress.json`（`logs/` 已被 .gitignore 忽略）。这是既有行为，交付命令跑完后已手工清除；G5 自己的命令不产生该目录。
- `.mypy_cache/` `.ruff_cache/` `.benchmarks/` 为工具自建缓存目录（各自内含 `.gitignore` 自忽略），已清理。
