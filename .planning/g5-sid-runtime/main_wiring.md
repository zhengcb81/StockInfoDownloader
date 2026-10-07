# G5-SID-RUNTIME → MAIN 接线

目标分支仍是原仓 `v2-clean-rewrite` 执行分支（remote 名仍为 StockInfoDownloader；不因此维护旧 main）。
本包分支 `codex/g5-sid-runtime`，基线 `0cb3c1f0b4a5784757971265b2b20a7a0b4c5104`，正常 commit，不与执行分支合并 —— 合并/推送由 MAIN 负责。

## 1. 合并范围（apply_after_merge）

| repo | path | symbol | 动作 |
|------|------|--------|------|
| StockInfoDLSimple | `src/company_wiki_adapter.py` | `OrgIdResolver`、`StockInfoCompanyWikiAdapter.__init__`、`StockInfoCompanyWikiAdapter._resolve_org_id` | apply_after_merge |
| StockInfoDLSimple | `src/company_wiki_adapter_cli.py` | `_build_adapter`、`_cleanup`、`main.finally` | apply_after_merge |
| StockInfoDLSimple | `src/cninfo_api.py` | `CninfoAnnouncementClient.resolve_org_id` | apply_after_merge |
| StockInfoDLSimple | `src/cninfo_identity.py` | `candidate_paths`、`LocalOrgIdCache`、`OrgIdIdentityResolver` | apply_after_merge（新文件） |
| StockInfoDLSimple | `src/disclosure_matching.py` | `matches_excluded`、`matches_keywords` | apply_after_merge（新文件） |
| StockInfoDLSimple | `tests/unit/test_g5_provider_runtime.py` | — | apply_after_merge（新文件） |
| StockInfoDLSimple | `tests/e2e/test_g5_browserless_provider.py` | — | apply_after_merge（新文件） |
| StockInfoDLSimple | `tests/fixtures/g5_provider/sitecustomize.py` | — | apply_after_merge（新文件） |
| StockInfoDLSimple | `tests/unit/test_company_wiki_adapter_cli_budget.py` | `test_cli_budgeted_real_discovery_path_reports_http_body_bytes` | apply_after_merge |
| StockInfoDLSimple | `tests/e2e/test_g4_latest_cli_offline.py` | `_seed_org_mapping` docstring | apply_after_merge |

## 2. 不需要改动（no_change）

| repo | path | symbol | 原因 |
|------|------|--------|------|
| company-wiki | `config/source_acquisition.yaml` | `adapters.cn.name/version` | wire 仍是 `stockinfo-cninfo/1.3.0`，无新 wire 形状，不另造版本门 |
| company-wiki | `src/company_wiki/source_catalog/adapter_process.py` | `JsonCommandAdapter.discover_bounded` | success/failure JSON `schema_version=1.0`、candidate/receipt 字段不变 |
| company-wiki | `src/company_wiki/source_catalog/resolver.py` | `SourceRequest` | 仍然不携带 `org_id`；本包正是覆盖“真实无 org_id 请求”，**不得**给 CWP 强制新 org_id 字段 |
| StockInfoDLSimple | `src/config.py`、`config*.json` | — | config 含义与字段未变 |
| StockInfoDLSimple | `src/downloader.py`、`src/mapping.py`、`src/orgid.py`、`src/browser.py`、`src/logger.py`、`src/models.py` | — | owner 文件，只读；legacy 人工浏览器下载器不在这次改造范围 |

## 3. MAIN 合并后必须做的验证（verify）

1. **真实无 cache、无 org_id 的 CWP 请求**（本包已覆盖，MAIN 需在合并后的执行分支上重跑）：

   ```powershell
   $env:G4_CWP_REPO='C:/Users/郑曾波/Projects/company-wiki'
   $env:G4_CWP_COMMIT='df7d7ba58955e224c1799355f479ad5378ef38a7'
   $env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'
   python -B -m pytest -q -p no:cacheprovider `
     tests/unit/test_g4_latest_discovery.py `
     tests/unit/test_company_wiki_adapter.py `
     tests/unit/test_company_wiki_adapter_cli.py `
     tests/unit/test_company_wiki_adapter_cli_budget.py `
     tests/unit/test_cninfo_api.py `
     tests/unit/test_cninfo_api_fixture_contract.py `
     tests/unit/test_cninfo_api_budget.py `
     tests/unit/test_g5_provider_runtime.py `
     tests/e2e/test_g4_latest_cli_offline.py `
     tests/e2e/test_g5_browserless_provider.py
   ```

   预期 163 passed / exit 0，`external_network_requests = 0`。

2. **冻 CWP 真实 `JsonCommandAdapter` 消费**：`test_committed_cwp_route_consumes_candidates_or_honest_gap` 与
   `test_cwp_discover_bounded_consumes_the_1_3_0_response` 必须在 `G4_CWP_REPO`/`G4_CWP_COMMIT` 显式设置下跑到
   （不是 skip）。若 CWP 侧对错误 usage 有新的断言，用真实 child CLI 的 stderr JSON 核对，不 mock 该 CLI 返回。

3. **owner 保护复核**：

   ```powershell
   git diff --name-only 0cb3c1f0b4a5784757971265b2b20a7a0b4c5104 -- README.md config_template.json main.py src/browser.py src/downloader.py src/logger.py src/mapping.py src/models.py tests/e2e/official_e2e_test.py tests/unit/test_downloader.py tests/unit/test_official_e2e_contract.py
   ```

   必须为空（本包交付时为空）。

4. **不做**：不安装 Playwright/Chromium，不跑 `tests/e2e/test_orgid_resolution.py`、`official_e2e_test.py`、
   `test_pagination_behavior.py`、`test_skip_existing_files.py`（需外网/浏览器），不称 CI 绿（仓无 workflow）。

## 4. 明确不在本包内

- **G2-12**：下载/入库/并发复用仍是 MAIN 的未完成工作；provider 解耦绿**不能**冒充完整 ensure 链已完成。
- 本包不改变另外两线（G5-CWP-CHECKS、G5-RF-INSTALL）的接口，无须等它们。
- `mypy` 仍 exit 1（11 个错误，全部为 base 既有；base 是 12），不设新门。
