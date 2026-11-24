# F4-SID-START-INPUT — handoff

状态入口：[F4-SID-START-INPUT 施工卡](F4-SID-START-INPUT.md)（本目录，总控 owner 卡的原样副本）。本文件是本卡的独立交接，供 ROOT 通过公开接口做跨仓组合。前置卡：[F4-SID-FAILURES 交接](F4-SID-FAILURES-handoff.md)（其 §8 记录的"零任务空成功"预存事项由本卡关闭）。

## 1. 交付要点

| 项 | 值 |
|---|---|
| 卡号 | F4-SID-START-INPUT（直启任务清单与失败复原） |
| 工作目录 | `C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite` |
| 开工基线 | `521941ef`（本地 = origin/v2-clean-rewrite，工作区仅既有未跟踪文件） |
| 分支 / 远端 | `v2-clean-rewrite` / origin/v2-clean-rewrite（快进，无合并提交） |
| 最终源码 | 见 §7（规范 Git blob 原始字节 SHA-256）及提交 SHA |
| 写入范围 | 仅本仓直启任务清单（`main.py`）、配置读取必要职责（`src/config.py` 的 `load_companies`）、原生反馈接线（`src/feedback_publish.py`、`src/feedback_observation.py`、`src/feedback_owner.py` 各一处词汇/白名单新增）、定向测试、PWF 与 evidence。供应商、下载限额、CWP adapter、生产名单与正式配置未改。 |

## 2. 三个原发生的 RED 实测与修复

隔离子进程真实运行 `main.py`（合成代码 9000xx，audit hook 拒绝 socket，owner 状态根映射到临时目录，未设置 `RESEARCH_FEEDBACK_OUT`/`DIR`）。"启动数"由下载引擎边界的计数替身写入磁盘后读回。

| 原发生 | RED（`521941ef`）实测 | 修复后实测 |
|---|---|---|
| `--companies` 指向不存在的文件 | 退出 1；stderr 含原生 `Traceback`；启动 0；**零反馈**（仅启动回执，无结算观察） | 退出 1，无 Traceback；结算 `not_started`/`expected`，明细 `stage=companies`、`cause_chain=["ConfigError"]`、`attempted=0`、`sent=not_sent`；启动 0，无 `logs/progress.json` |
| `--companies` 仅含注释 | 退出 0；stderr `All tasks completed`；启动 0；结算写成 `all_completed` | 退出 0；stderr `No tasks to run: companies list … has no entries`；结算 `no_tasks`/`expected`，`attempted=0`、`sent=not_sent`；无 `action-started` |
| 配置 `companies` 非空（另有默认空 `test_cases`、`stock_code`） | 退出 0；启动 **0**（期望 2）；结算 `all_completed` | 退出 0；启动 **2**（`900001`、`900002`，`stock_code` 未启动）；结算 `all_completed`，`attempted=succeeded=2`；进度文件记录两家 |

RED 证据：`evidence/f4-sid-start-input-red-20261123.log`（**13 失败 / 3 通过**；3 个通过项是显式输入覆盖配置的既有对照）。GREEN：`evidence/f4-sid-start-input-green-20261123.log`。

## 3. 输入来源合同（单点决策）

`main.py` 的 `plan_work(cli_stock_code, companies_path, config) -> WorkPlan` 是唯一下决策点，优先级沿用 README 既有合同，既有调用语义不变：

```text
CLI stock_code > --companies 文件 > config.test_cases > config.companies > config.stock_code > 无输入
```

- 来源"已指定"的判据是**至少含一项**。`load_config` 默认注入的空 `companies`/`test_cases`（及合并后无法区分的显式空列表）不再遮蔽低优先级的非空来源。`load_config` 的返回形状未改。
- 只有显式 `--companies` 触发名单读取，且在任何派发之前。`load_companies` 现把读失败（原生 OS 错误、解码错误）统一为 `raise ConfigError(...) from e`，原生异常留在 `__cause__`；"不存在"仍是 `ConfigError`（无内因）。
- `WorkPlan.source == "none"`（显式空名单，或任何来源都无项）是合法空工作项，不是拒绝。

## 4. 五类结果各自保留

| 情形 | 退出 | `actual` | `disposition` | 明细 |
|---|---|---|---|---|
| 名单读取失败 | 1 | `not_started` | `expected` | `stage=companies`、`cause_chain`、`attempted=0`、`sent=not_sent` |
| 配置读取失败（既有路径，补齐异常链） | 1 | `not_started` | `expected` | `stage=config`、`cause_chain=["ConfigError","JSONDecodeError"]`、`attempted=0`、`sent=not_sent` |
| 显式空工作项 / 无输入 | 0 | **`no_tasks`**（新词） | `expected` | `attempted=0`、`skipped=0`、`sent=not_sent` |
| 合法全跳过 | 0 | `all_completed` | `expected` | `attempted=0`、`skipped=N`、`sent=not_sent` |
| 供应商返回零候选 | 0 | `all_completed` | `expected` | 任务确已启动：`attempted=1`，**无 `sent` 键** |
| 实际失败 | 1 | `all_failed` / `partial` | `deviation` | `attempted = succeeded + failed`，无 `sent` 键 |

`attempted` 只统计真正启动的子项。`UnifiedRunner` 持有一份业务台账 `settlement`（`attempted/succeeded/failed/skipped`），每个公司/测试用例在启动时计 `attempted`、结束时计 `succeeded`/`failed` 各一次；退出码与发布的结算读同一台账（`OrdinaryRunFeedback.run_finished(exit_code=, settlement=)`，原先的反馈内部计数器与 `mark_skipped` 移除）。`attempted=0` 时才写 `sent=not_sent`（确知未发送才报零）。

`no_tasks` 是对 `src/feedback_owner.py` `SUCCEEDED` 词汇的**纯新增**；`_reconcile` 其余逻辑未改。company-wiki 源码中没有硬编码 `all_completed`/`ordinary-run-settlement` 的消费者（已 grep），ROOT 如有自建词汇表需接收该词。

## 5. 冷读证据（公开 `src.feedback_owner`，新进程，两次）

`python -B -m src.feedback_owner --db <tmp>/a.sqlite --sidecar-dir <state>/observations reconcile`，以结算观察原行构造 `feedback-action/1` 请求。两次结果逐字节一致，且未创建 SQLite。

| 启动 | 退出 | 启动数 | `job_status` | `status` | `cost_state` |
|---|---|---|---|---|---|
| 名单不存在 | 1 | 0 | `failed` | `known` | `not_applicable` |
| 名单不可读（路径是目录 → `["ConfigError","PermissionError"]`） | 1 | 0 | `failed` | `known` | `not_applicable` |
| 仅注释名单 | 0 | 0 | `succeeded` | `known` | `not_applicable` |
| 合法全跳过（2 家） | 0 | 0 | `succeeded` | `known` | `not_applicable` |
| 真实失败（1 家） | 1 | 1 | `failed` | `cost_unknown` | `unknown` |
| 配置 2 家实际启动 | 0 | 2 | `succeeded` | `cost_unknown` | `unknown` |

两种失败原因冷读可分别复现：参数原因链 `["ConfigError"]`，I/O 原因链 `["ConfigError","PermissionError"]`（Windows；其它平台为对应 `OSError` 子类）。脱敏样本（`f4-sid-start-input-{refusal,no-tasks,started}-*`，共 24 个文件，已扫描无路径/命令/原文/Traceback）由下列命令经真实 CLI 生成：

```text
C:/Miniconda/python.exe -B docs/plans/feedback-loop-2026-11-17/evidence/f4-sid-start-input-samples-generate.py
```

## 6. 运行命令与计数

```text
C:/Miniconda/python.exe -B -m pytest -q tests/unit/test_f4_start_input.py tests/unit/test_main.py tests/unit/test_config.py tests/unit/test_parallel.py tests/unit/test_f4_ordinary_failures.py tests/unit/test_feedback_owner.py tests/unit/test_feedback_observation.py tests/unit/test_company_wiki_adapter_cli.py tests/unit/test_company_wiki_adapter_cli_budget.py tests/unit/test_failed_logger.py tests/unit/test_provider_runtime_artifact.py tests/unit/test_downloader.py tests/unit/test_progress.py --basetemp=<短目录> -p no:cacheprovider
C:/Miniconda/python.exe -B -m pytest -q tests/e2e/test_g4_latest_cli_offline.py --basetemp=<短目录> -p no:cacheprovider      # G4_CWP_COMMIT=7e0ecebb01096e202d5ec11847cd28e927edf4c9
C:/Miniconda/python.exe -B docs/plans/feedback-loop-2026-11-17/evidence/f4-sid-node-c-check.py
```

- RED `test_f4_start_input.py`：**13 失败 / 3 通过**（修复前）。
- GREEN 定向 13 个文件：**210 通过 / 0 失败**（`evidence/f4-sid-start-input-green-20261123.log`）。其中新文件 16 项、`test_main.py` 10 项（含 `TestPlanWork` 6 项）、`test_config.py` 新增 2 项原生 cause 测试。
- G4 离线组合（固定 CWP `7e0ecebb…`）：**17 通过**（`evidence/f4-sid-start-input-g4-offline-20261123.log`）。
- 大节点 C 矩阵重跑：**19/19 covered**（`evidence/f4-sid-node-c-20261123-start-input.json`；空配置一例现记 `no_tasks`，矩阵脚本只改该一例的期望词，2026-11-21 的旧 JSON 保留为历史证据）。
- 全量 `tests/unit`（最终 HEAD `1c9d8f3`）：**436 通过 / 5 失败**（`evidence/f4-sid-start-input-full-unit-20261123.log`）。5 项逐项归因、均与本卡无关：4 项 `test_g5_provider_runtime` 断言 `src/stock_orgid_mapping.json` 不存在，该文件是本机 2026-07-31 遗留的 gitignore 本地缓存（未跟踪、不随 `git archive` 导出）——在干净的 `521941e` 导出树上这 4 项通过；1 项 `test_provider_dependency_direction::test_announcement_filtering_keeps_each_period_fixture_semantics[exact_legacy_year]` 在干净的 `521941e` 导出树上同样失败（历史 fixture pin），与本卡无关。全量日志与 G4 日志均取自最终 HEAD；此前一次全量与 G4 并发执行时出现过 loopback 竞争导致的额外失败，已用顺序重跑取代。
- **调用数**：真实网络 0 次（子进程 audit hook 全程拒绝 `socket.connect`/`getaddrinfo`），付费/计费 0 次；冷读不构造 provider、不下载、不发现。
- 必须显式传 `--basetemp=<短目录>`：不传时 pytest 清理共享临时根会触发本机批量删除确认钩子（SAFE_DELETE_BULK_CONFIRM_REQUIRED），运行被中断。

## 7. 最终源码 SHA-256（规范 Git blob 原始字节）

最终源码候选提交 `32664fe`（主体）与 `78dd784`（并行计数加锁）；文档提交在其后，仅改 `docs/**`，不追自引用 SHA。SHA-256 为规范 Git blob 原始字节（工作区与上述提交内容一致）：

```text
907818dfd105d2cb6f856b5444f2e52cc8a1bd417811d342f1ad16561086e16f  main.py
644340b7c9af7a35a35ec2143e4b099f5ee8d1230363052206e9ad98b8bb5378  src/config.py
f319f02d2fc0d9f34079c13fa5edfdd51607e8fd09f108096750e51c1d716a6e  src/feedback_publish.py
82ed74d40c335b7cef62150e53a02e64a6488b1b44100a3120b770cb50466d1d  src/feedback_observation.py
70a622ec1354f77b6f70c393ce3c32da8f3e511c3c78020d3729af936899d4e8  src/feedback_owner.py
43817fa01c9eacd6fbf0dea53cbd663dbdbbe474726fe81d473f6e80e7fbbfba  tests/conftest.py
2df496ecb058de39f2d430ab890d0ee7ddb1b103a3e1e39e108c6bbe9da62fba  tests/unit/test_main.py
45d90d149a04d709e45dbbdaed4263414ace940c1c71abf59d91e07295c294c7  tests/unit/test_config.py
3880a7500ddb061e98ab09ab007e532559af37fe7c31197ce2f5cb5a02e7fda9  tests/unit/test_f4_start_input.py
```

## 8. 独立审查

首位独立审查 agent（Explore、只读、未获作者预期结论）在跑了定向集与 45 组正反例探针（非 list 配置、`--companies ""`、空白名单、坏编码、BOM、并行/串行多任务、构造/清理抛错、全跳过/部分跳过、反馈关闭等）后，因宿主额度 429 中断，**未交回结论，不计为通过**。另起一名只读 agent 对最终候选 `32664fe` 复审，结论 **PASS / 0 阻断 / 2 非阻挡**：

| # | 发现 | 处置 |
|---|---|---|
| 1 [non-blocking] | `no_tasks` 的 `expected` 仍是 `all_completed`（检查的规范期望未变），只有 `actual`/`disposition` 描述空工作项 | 保留：owner 冷读以 `actual` 与 `sent` 为准，改 `expected` 会改变检查契约；在本节记录 |
| 2 [non-blocking] | 并行模式把计数移入工作线程且删除了旧 `_count_lock`，`dict[k] += 1` 理论上可丢增量 | **已修**：`main.py` 增加 `_SETTLEMENT_LOCK` 与 `_bump()`，所有台账递增都走锁；8 轮 × 10 线程 × 500 次压力探针 0 丢失，提交 `78dd784` |

复审确认：`plan_work` 优先级与 README 一致，默认空键不遮蔽真实配置；五类结果在发布明细与 `feedback_owner reconcile` 中可区分；`tests/conftest.py` 不影响任何显式 OUT/DIR/RUN_ID/ATTEMPT_ID 调用；没有本提交引入的阻断缺陷。复审未发现的问题以探针输出为准；首位 agent 的探针中没有出现 PUBLISHED 观察的路径/命令/原文泄漏（`leak []`）。

修复后另起一名只读 agent 对**最终源码**复核（`78dd784` 相对 `32664fe` 只改 `main.py` 的加锁接线）：`git diff 78dd784..HEAD -- main.py src tests` 为空；§7 的 9 个 SHA-256 与工作区逐一一致；无绕过 `_bump` 的递增、无重入/死锁风险；并行异常路径（`cleanup()` 抛出）只补计一次 `failed`，不重复也不漏计。判定 **PASS / 0 阻断**。残留非阻断备注：`_SETTLEMENT_LOCK` 是进程级全局锁（多 runner 并发只多争用）；`BaseException`（如 `KeyboardInterrupt`）不被 `except Exception` 捕获，属既有边界。

## 9. 有意的行为变化与交 ROOT 的事项

- **显式空名单不再写 `logs/progress.json`**（此前会写入 `total=0` 的进度文件）。空名单不派发任何任务，也不触碰进度状态。
- **无输入的启动退出 0 并报告 `No tasks to run`**（此前退出 0 且报 `All tasks completed`）。保留退出 0 是因为 `python main.py --clean` 这类既有调用依赖它；原代码里"usage 拒绝退出 1"的分支自配置默认注入空键以来就不可达，本卡将其收敛为合法空工作项。若 ROOT 希望"无输入"成为 usage 拒绝，属另一张卡的决策。
- `run_multi` 返回 runner 的共享台账（`{"attempted","succeeded","failed","skipped"}`，是原三元组的超集）；`run_test_cases`/`run_single` 仍返回 `bool`。
- README 第 40 行的优先级合同与实现一致，未改 README（不在本卡写入范围）；建议 ROOT 在下一次 README 修订时补一句"空列表不参与遮蔽"。
- 预存事项（非本卡引入）：§6 所列 11 项全量失败、本机 `stock_orgid_mapping.json` 缓存残留。
- 清理：本卡创建的测试临时目录（`%TEMP%/si-*`、`f4si-*`、HEAD 归档树 `si-head`）、失败生成器遗留的旧 refusal 样本、仓内 `.planning/test-tmp/`（全量测试残留）已删除；两份用户名单、`.mimosa/` 与 `evidence/.mimosa/` 保持未跟踪不动。本卡的直启子进程全部映射状态根，未写入真实状态根。

- **待操作者确认的既有污染**：未映射反馈目标的适配器回归套件（如 `tests/unit/test_company_wiki_adapter_cli.py`、`test_g5_provider_runtime.py`、`test_provider_error_contract.py`）在真实默认收件目录 `C:/Users/郑曾波/.stockinfo-dl-simple` 写入了本会话测试与复审探针产生的合成观察（最后核对 **801 个文件**：`deliveries` 283、`observations` 495、`pending` 22、根 1；该目录在本会话前无文件，全部为本会话产物）。这不是本卡代码引入的行为（ROOT §9 默认发布以来即存在），但会被 ROOT 当作真实观察消费，必须清掉。已新增 `tests/conftest.py` 的 autouse 夹具阻断 pytest 测试的后续写入（128 项显式/默认目标测试复验通过）；不经过 pytest 的直接 CLI 探针仍需自行映射状态根（复审探针因此又产生 6 个文件）。完整清单在 `%TEMP%/si-state-root-pollution-manifest.txt`（801 行，逐文件时间戳与绝对路径）。删除这 734 个个人目录下的文件需要操作者明确确认，届时按批次移入回收站；**在确认前不要进行跨仓组合验收**。

## 10. 提交与发布

```text
32664fe fix(sid): decide the ordinary launch input in one place and report empty work honestly
78dd784 fix(sid): lock the parallel business settlement tally
<docs commit> docs(sid): F4-SID-START-INPUT PWF and handoff   # 即本文件所在提交，不追自引用 SHA
```

发布线为正式维护分支 `v2-clean-rewrite`；开工时本地与 origin 同为 `521941e`，两次源码提交均为快进。未合并其它分支，未改写历史，未跳过钩子。
