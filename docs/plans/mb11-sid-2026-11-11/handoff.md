# MB-SID — handoff

## 1. 基线与提交

| 项 | 值 |
|---|---|
| 实际代码基线 | `c0f07e12d4ba3e232d712bb6e5e491832023b0a0`（原仓 `v2-clean-rewrite` head，工作树 11 项 WIP 未提交） |
| 交付分支 | `codex/mb11-sid` |
| 最终代码 tip | `f1fff01394a41ec797d7317cce1c78b6778d2966`（独立审查第二轮审的就是这个提交） |
| 文档提交 | PWF 提交在其后，仅新增/更新 `docs/plans/mb11-sid-2026-11-11/**`，不改代码 |
| 目标主线 | `v2-clean-rewrite` |
| remote | `origin` = `https://github.com/zhengcb81/StockInfoDownloader.git`，已推送 `codex/mb11-sid`（新建分支，未开 PR，未合并） |
| 提交数 | 11（含 1 个 checkpoint；最后一个只改 PWF/scripts） |

提交序列：

```
f1fff01 fix(review2): per-attempt failure reset and a scoped tab-selection state
5e4c3f7 fix(review): close the tab-scope and partial-failure gaps found in review
1f4f44c test(provider): prove the delivered CLI runs from a browser-free artifact
6b2fd0b fix(provider): typed error identity and a pure report-metadata domain
000f1cb fix(cli): tolerate a closed handler stream when guarding stdout
2de8334 docs(config): drop unverified test counts and the host-specific output path
6ad33f4 fix(downloader): request-scoped empty state, active-pane scope, typed verification
e238bdf fix(browser): expose the active SPA pane as its own accessor
4a5b30c fix(e2e): validate the report suffix before it becomes a path
f593535 receive: accept reviewed CW-2.27D/H legacy WIP as a checkpoint
```

`f593535` 是**接收检查点**，不是交付：它原样保存受审 WIP（743 增 / 94 删），其上的提交才是修复。ROOT 只应把 `f593535..f1fff01` 当作本卡成果；checkpoint 本身带有已知缺陷，不单独验收。

### 实际 diff 文件表（相对 `c0f07e12`）

| 文件 | 增/删 | 归属 |
|---|---|---|
| `src/downloader.py` | +386/-… | A0 gap 1/2/3/4 |
| `src/models.py` | +42 | A0 gap 1/4（`confirmed_empty`、`VerificationResult`） |
| `src/browser.py` | +192 | A0 gap 3/5（页签作用域、DNS） |
| `src/logger.py` | +2/-2 | A0 gap 5（stdout→stderr） |
| `src/mapping.py` | +38/-… | A0 接收（去 catch-all） |
| `main.py` | +10/-… | A0 gap 4（不再二次判失败） |
| `src/cninfo_report_metadata.py` | +48（新） | SID-02 纯域 |
| `src/cninfo_api.py` | +13/-… | SID-02 依赖方向 |
| `src/company_wiki_adapter.py` | +54/-… | SID-01 typed 错误 + SID-02 再导出 |
| `src/company_wiki_adapter_cli.py` | +35/-… | SID-01 失败通道 + cleanup 顺序 |
| `tests/unit/test_legacy_download_contract.py` | +781（新） | A0 行为契约 |
| `tests/unit/test_provider_error_contract.py` | +325（新） | SID-01 |
| `tests/unit/test_provider_dependency_direction.py` | +201（新） | SID-02 |
| `tests/unit/test_provider_runtime_artifact.py` | +330（新） | 组合/隔离 runtime |
| `tests/unit/test_downloader.py` | +322/-… | 接收 + typed 契约 |
| `tests/unit/test_config.py` | +38 | 模板契约 |
| `tests/unit/test_official_e2e_contract.py` | +25 | report suffix |
| `tests/e2e/official_e2e_test.py` | +64/-… | report suffix 校验 |
| `scripts/capture_byd_fy2024_fixture.py`、`scripts/README.md` | 新 | A0 接收 fixture 出处，标 `NO_RUNTIME_REFERENCE` |
| `README.md`、`config_template.json` | +127/+5 | 去未验证数字与主机路径 |
| `docs/plans/mb11-sid-2026-11-11/**` | 新 | 本 PWF（含 `runtime_inventory.md`、`compliance.md`、`history/g4-sid-latest/`） |

未触碰：原工区 11 项 WIP、`config.json`、`config_e2e_*.json`、`src/stock_orgid_mapping.json`、`end2end_test/**`、CWP/FF/Dayu 任何文件。

## 2. 每项卡要求

### A0-1 请求作用域的空结果

- **根因**：`_official_status` 是实例属性；`_download_internal` 只在"不是 CONFIRMED_EMPTY"时才复位，于是第一次确认空会粘住，第二次请求（不同公司/期次）继承空结果。
- **RED**：`test_second_request_does_not_inherit_the_first_confirmed_empty` —— 基线/checkpoint 上第二次请求拿到 `confirmed_empty` 或直接 `TypeError`；checkpoint 上的真实行为 RED 记录在 `evidence/red-wip-baseline.log`。
- **修复归属**：`src/downloader.py` + `src/models.py`。状态从实例移到 `DownloadRequest.confirmed_empty`（公开可选字段，默认 False），`_download_internal` 用局部变量，实例上不再保存任何空结果。
- **兼容**：`DownloadRequest` 新字段在尾部、有默认值；既有位置/关键字构造不变。
- **证明**：同实例连续三次请求（确认空 → 不同公司空页 → 有内容）分别得到 `confirmed_empty` / `infrastructure_fail` / 成功下载 1 个文件。

### A0-2 目的目录按组件匹配

- **根因**：`expected = save_subdir.replace("/", "\\")` 后 `if expected not in str(path.parent)`。POSIX 路径被误拒；`raw/prospectus-extra` 被误接受。
- **RED**：`test_download_in_the_wrong_sibling_directory_is_not_a_success`（checkpoint 上 `success=True`）+ 6 个纯函数用例（POSIX/Windows 大小写/反斜杠输入/兄弟目录/前缀/`..`）。
- **修复归属**：`src/downloader.py` 新增 `_subdir_components()` / `_path_is_within_subdir()`；写入端与校验端共用同一拆分。
- **兼容**：`save_subdir` 仍接受 `raw/prospectus` 与 `raw\prospectus`；`..` 与绝对路径现在显式报错（原先会被静默拼接）。
- **证明**：兄弟目录、前缀目录、POSIX 路径、Windows 大小写四类断言；`test_correct_directory_ok` 保持通过。

### A0-3 页签范围

- **根因**：`_switch_tab` 用整页 `querySelectorAll('a[href*=detail]').length` 判定切换成功；`_get_links` 在活动 pane 为空时回退整页 XPath。
- **RED**：`test_empty_active_tab_never_downloads_another_tab` —— checkpoint 上 `dom.downloaded` 多出隐藏页签的 2 条链接。
- **修复归属**：`src/browser.py` 拥有 DOM 知识（`select_menu_item()` 三态、`find_active_tab_links()` 按 `offsetParent` 过滤、无 pane 容器才退回整页）；`src/downloader.py` 只在作用域内取链接，未知 suffix 抛 `DownloadError`，菜单不可达/点击未生效一律 fail-closed。
- **兼容**：无 suffix 的请求仍走整页 XPath（原行为）；已知 suffix 集合不变。
- **证明**：空活动页签、点击未生效、菜单缺失、未知 suffix、仅选中页签被下载、无 suffix 允许整页，共 6 条。

### A0-4 验证结果语义统一

- **根因**：`_verify_downloads` 返回英文 list，`main.py` 用它二次判失败；同时 `success=True` 可以与 blocking 告警共存，且 owner 已知的下载失败完全没进入验证。
- **RED**：`test_missing_file_fails_the_owner_result`、`test_zero_files_is_not_a_silent_success`、`test_partial_download_failure_is_not_a_success`、`test_cli_does_not_rejudge_a_successful_owner_result`（checkpoint 上分别 `success=True` / `True` / `True` / `run_single=False`）。
- **修复归属**：`src/models.py` 新增 `VerificationIssue` / `VerificationResult`；`src/downloader.py` 产出 typed issues（`no_files`、`file_missing`、`file_too_small`、`keyword_mismatch`、`excluded_keyword_present`、`unexpected_directory`、`download_failed`）并把 `verification.ok` 折进 `success`；`main.py` 只读 `result.success`。
- **兼容**：`DownloadResult` 新字段有默认值；`metadata` 不再被当作结果信号。
- **证明**：部分失败（1 成功 + 1 失败）→ `success=False`、issues 恰为 `["download_failed"]`；CLI 对 `success=True` + 任意 metadata 不再改判。

### A0-5 流与路径输入

- **根因**：`logger` 控制台 handler 绑 stdout；`report_path_for_config` 把 `--report-suffix` 直接拼进文件名。
- **RED**：新进程日志测试（stdout 必须为空）、`test_report_suffix_rejects_path_like_values`、`test_report_suffix_keeps_consecutive_rounds_from_overwriting`。
- **修复归属**：`src/logger.py`（owner 修流）、`tests/e2e/official_e2e_test.py`（单组件正则 + `main()` 入口前置校验）。
- **兼容**：无 suffix 时报告名不变；合法 suffix 仍生成不同文件。
- **证明**：`round1`/`round2`/无后缀三条路径互不相同；`../escape`、`a/b`、`a\b`、`/absolute`、`round 1`、`.`、`..` 全部 `ValueError`。

### SID-01 typed 错误贯通

- **根因**：`adapter.fetch` 的 `except CninfoApiError` 只保留 message；CLI 只能按类型名回落 `upstream_unavailable/retryable=true`。
- **RED**：`test_host_outside_the_allowlist_is_non_retryable` 等 4 条经公开 CLI 断言 `code`/`retryable`，checkpoint 上全部得到 `upstream_unavailable` + `True`（`evidence/red-provider.log`）。
- **修复归属**：`src/company_wiki_adapter.py` 透传 `code`/`retryable`；adapter 自身 staging 校验补 `candidate_missing_transport`/`staging_escape`/`content_too_small`/`pdf_magic_invalid`。
- **兼容**：JSON 1.0 结构不变；错误码集合扩大（新增的是原先被折叠掉的真实身份），`type` 字段仍为 `AdapterError`。
- **证明**：host 不允许 / 非 PDF / 过小 → `retryable=false`；超时 → `upstream_timeout/true`；有预算时 `acquisition_usage.response_bytes` 为实测值，无预算时字段不出现（不写 0）。

### SID-02 纯 metadata 边界

- **根因**：`cninfo_api` 在 `_filter_page`/`_filter_latest_page` 内 `from .company_wiki_adapter import _report_metadata`，纯读取器依赖上层 adapter。
- **RED**：`test_announcement_filtering_runs_without_the_adapter_or_browser_layers` —— 修复前子进程以 `ImportError: provider domain import refused: src.company_wiki_adapter` 失败。
- **修复归属**：新增 `src/cninfo_report_metadata.py`（`report_metadata`）；`cninfo_api` 与 `company_wiki_adapter` 都向下依赖它；adapter 保留 `_report_metadata = report_metadata` 再导出。
- **兼容**：`from src.company_wiki_adapter import _report_metadata` 仍可用且是同一函数对象；`cninfo_api` 不再以任何形式导入 adapter。
- **证明**：import-blocker 子进程用真实 fixture（002594 / FY2024）过滤出年报且 `state=ready`，`sys.modules` 中无被禁模块；8 条标题分类表覆盖年/半年/一季/三季/修订/摘要/临时公告/无年份。

## 3. 公开接口变化

默认 none 之外，实际新增都是**可选、向后兼容**：

| 接口 | 变化 | 兼容性 |
|---|---|---|
| `DownloadRequest` | 尾部新增 `confirmed_empty: bool = False` | 位置/关键字构造不变；不传即旧行为 |
| `DownloadResult` | 新增 `verification: VerificationResult`（默认 `ok=True, issues=()`）；`load_state`/`error_code`/`retryable`（checkpoint 引入） | 默认构造结果不变；`success` 已含验证结论 |
| `src.models.VerificationIssue` / `VerificationResult` | 新类型 | 纯新增 |
| `PlaywrightBrowser` | 新增 `select_menu_item(label) -> str`、`find_active_tab_links() -> list[tuple[str,str]]` | 纯新增，provider 内部使用 |
| `src.cninfo_report_metadata.report_metadata` | 新模块/函数 | 纯新增；旧私有名保留为别名 |
| `tests/e2e` `report_path_for_config(config_path, suffix="")` | 新可选参数；非法 suffix 抛 `ValueError` | 旧调用（1 参）不变 |
| CLI JSON 1.0 | 结构不变；错误 `code` 可能取 `transport_url_host_not_allowed` / `pdf_magic_invalid` / `content_too_small` / `upstream_timeout` / `staging_escape` 等 | 未知 code 的消费者仍可读 `type`/`message`/`retryable` |

ROOT 需要的小 fixture：

- `tests/fixtures/cninfo/byd_fy2024_announcement.json`（已有，本卡未改）
- `tests/unit/test_provider_runtime_artifact.py` 的 runtime manifest 常量 `RUNTIME_FILES`（14 个文件，供 ROOT 组合时复用）
- 期间过滤 fixture：`tests/fixtures/g4_latest/{exact_legacy_year,semi_annual_visible,quarterly_cutover}.json`

ROOT 复算命令（在集成树执行，无需网络）：

```bash
python -B -m pytest tests/unit/test_provider_dependency_direction.py tests/unit/test_provider_runtime_artifact.py -q -p no:cacheprovider
```

## 4. 实际测试

环境：Windows 11，Python 3.13.9（`C:\Miniconda\python.exe`），pytest 9.1.1，`-B -p no:cacheprovider`。

| 命令 | 退出码 | 结果 | 耗时 | 日志 |
|---|---|---|---|---|
| `pytest tests/unit` | 0 | **337 passed**，0 failed，0 skipped | 59.96s | `evidence/unit-after-compliance.log` |
| 卡内命令 1（adapter/cli/budget/g5 五文件） | 0 | **56 passed** | 12.58s | 见 `evidence/unit-after-review2.log` 同批 |
| 卡内命令 2（provider 两文件） | 0 | **24 passed**（含新增 3 条期间 fixture） | 4.34s | `evidence/unit-after-compliance.log` |
| `pytest tests/unit/test_legacy_download_contract.py` | 0 | 35 passed | 2.71s | 同上 |
| `pytest tests/unit`（修复前，checkpoint 树） | 1 | 24 failed / 6 passed | 3.81s | `evidence/red-wip-baseline.log` |

未执行：

- `tests/e2e/**` 与官方 E2E：需要真实网络与浏览器，卡明确不默认执行，且没有验收需求。
- 远端 CI：本仓无 CI 配置。
- 真实采集：卡要求由 ROOT 按需安排。

## 5. 独立审查

| 轮次 | agent | 审的 commit | 结论 | 修复 |
|---|---|---|---|---|
| 1 | `agent-b23d2f95-2581-4679-99fd-419cb819a871` | `1f4f44c` | CHANGES REQUIRED（B1/B2/B3） | `5e4c3f7` |
| 2 | `agent-0d946b9c-c87e-469b-9c64-c4449ad9e178` | `5e4c3f7` | PASS + 4 条非阻断 | `f1fff01` |

第二轮提出的 `_request_failures` 跨尝试泄漏是真实缺陷，已修复并加用例。详细记录见 `review.md`。

残余（非本卡可行动，交 ROOT）：真实页签 DOM 未抓取（`offsetParent` 假设、无 pane 容器时的整页兜底、`visibility:hidden` 未覆盖）；`confirmed_empty` 在生产链路尚无生产者。

## 6. 隔离与恢复

| 项 | 状态 |
|---|---|
| 测试目录 | 全部用 pytest `tmp_path`；运行前后仓库内无新增 `logs/`、`.planning/test-tmp`、staging |
| 原工区 WIP | 未变：11 modified、743 增 / 94 删、`scripts/capture_byd_fy2024_fixture.py` sha256 `86ad034f…2914` |
| 生产 config / cache / canonical | 未写、未删 |
| 真实网络调用 | **1 次**（`red-provider.log` 记录的那次运行中，一条测试误用允许域 `static.cninfo.com.cn`，返回 404）。该测试随后改为拒绝域，之后 0 次。不计为产品行为证据 |
| 模型调用 | 0 |
| 费用 | 未知（无付费调用；CNINFO 为免费公开接口，`cost_usd` 恒 `"0"` 是实测而非估算） |
| 临时文件清理 | pytest `tmp_path` 由 pytest 清理；artifact 目录在 `tmp_path` 内，测试结束自动删除 |
| G4 PWF 镜像 | 三份原字节归档到 `docs/plans/mb11-sid-2026-11-11/history/g4-sid-latest/`（哈希逐一复核），随后 `worktree remove --force` + `prune` 回收 `_g4/SID-LATEST/StockInfoDLSimple`；复原命令写在归档 README |
| 全局技能目录 | 未部署（本仓无安装器） |

## 7. 安装 / 部署 / CI / 合并

- **安装**：本仓无 wheel/setup/安装器，按 `runtime_verification.md` 用显式 runtime manifest 复制到临时 artifact 验证，不新增发布系统。
- **部署**：无。未改任何全局技能目录或用户配置。
- **CI**：无远端 CI 配置；未接线。
- **合并**：**未合并**。分支已推送，`v2-clean-rewrite` 未动。

### ROOT 下一步（一条可执行命令）

```bash
git -C 'C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite' \
  merge --no-ff f1fff01394a41ec797d7317cce1c78b6778d2966
```

集成后请在集成树集中跑一次：

```bash
python -B -m pytest tests/unit -q -p no:cacheprovider
```

必须使用的输入：目标主线 `v2-clean-rewrite`（当前 head `c0f07e12`）；本卡写集合见 §1；原工区 11 项 WIP 保持未提交，接收后由 ROOT 决定是否清理。


## 8. 偏差与待 ROOT 判断

逐条对照见 `compliance.md`。需要 ROOT 知晓的三点：

1. **写集合外新增测试** `tests/unit/test_provider_runtime_artifact.py`。卡的字面写集合只列两个新 provider 测试，但 C 段"组合"要求验证隔离 runtime；本卡把它固化成可重复测试（不碰生产面）。若 ROOT 认为超出，可只保留其 `RUNTIME_FILES` manifest 而删测试。
2. **真实页签 DOM 未抓取**。`find_active_tab_links()` 用 `offsetParent` 判可见性，页面完全没有 pane 容器时退回整页；`visibility:hidden` 未覆盖。这条假设只能由一次真实页面快照确定，卡明确真实采集由 ROOT 安排。
3. **`DownloadRequest.confirmed_empty` 没有生产生产者**。legacy SPA 路径不会设置它，`main.py` 也不传；真空页仍按 `infrastructure_fail/upstream_unavailable` 重试。接 API 确认属后续集成工作。

另外：本仓没有 `AGENTS.md`（卡要求开工读"本仓AGENTS"，实际无此文件）。


## 9. 最终代码复核与根集成前验收（2026-11-13）

- 最终代码 tip：90e7a25720581850783fd64ac055cd049eb58afe；最终独审 agent /root/audit_rf_sid_delivery 对 exact tip 判定 PASS。最终代码复核后仅调整测试替身点击返回值以与生产接口一致，没有产品代码变更。
- ROOT 在 exact tip 90e7a25 上运行完整 tests/unit：340 passed / 0 failed / 0 skipped，37.23 秒；日志为 evidence/unit-root-final-20261113.log。交付分支现已推送并核实远端 ref 为 c2957c23cc68d0ded7762c0311b517afa4c87027。
- 原目标主线远端仍为 v2-clean-rewrite @ c0f07e12。下一步在独立 worktree 集成完整交付分支（包括已在 A0 明示接收、随后通过行为测试逐项修复的 WIP checkpoint），集成后再次跑完整 tests/unit。
- 原 SID 主工作区的 11 个 tracked WIP 路径与交付 checkpoint 一一对应；在集成通过前不恢复或删除。未跟踪的 a_share_companies.txt 和 companies.txt 是输入名单，保留；scripts/capture_byd_fy2024_fixture.py 若与已入交付树的 fixture 来源脚本字节相同，则集成后仅删除这个重复副本。


## 10. ROOT 隔离集成验收（2026-11-13）

- 集成基线：远端 v2-clean-rewrite @ c0f07e12d4ba3e232d712bb6e5e491832023b0a0。完整交付分支已快进到隔离集成树 HEAD a96791397bfcae0be73ab90265bb198f5a9c8d7c；交付代码 tip 90e7a25720581850783fd64ac055cd049eb58afe，经审独立 PASS。
- 集成树完整运行 C:/Miniconda/python -B -X utf8 -m pytest tests/unit -q -p no:cacheprovider：340 passed / 0 failed / 0 skipped，40.44 秒；日志 evidence/unit-integrated-final-20261113.log。没有网络抓取、真实下载或外部模型调用。
- 原主工作区的 11 项 tracked WIP 已逐一比对：10 个路径与交付 checkpoint f593535 的 Git blob 相同；剩下的 test_official_e2e_contract.py 也有相同的 report suffix 替身签名，但交付 checkpoint 多出后续 23 行安全合同用例。最终集成分支完整覆盖并增强了原 WIP。
- 原主工作区未跟踪 capture_byd_fy2024_fixture.py 与已交付脚本只有 15 行 A0 用途说明头不同，其余逻辑相同；集成后该副本可以删除。a_share_companies.txt 和 companies.txt 是输入名单，明确保留。
- 下一步：在原目标工作区只恢复已证明被分支覆盖的 11 个 tracked WIP，删除已比较过的重复 capture 脚本副本，快进 v2-clean-rewrite 到本集成 tip 并推送；两份公司名单不动。
