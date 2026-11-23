# F4-SID-FAILURES — handoff

状态入口：[F4-SID-FAILURES 施工卡](F4-SID-FAILURES.md)（本目录）。本文件记录本卡的交付与独审结果，供 ROOT 通过公开接口做跨仓组合。总控审计发现位于邻仓 `company-wiki/docs/plans/feedback-loop-2026-11-17/issues/failure-coverage-20261121.jsonl` 第 12–13 行（owner `stockinfo-dl-simple`，run `f4-coverage-audit-20261121`）。

## 1. 交付要点

| 项 | 值 |
|---|---|
| 卡号 | F4-SID-FAILURES（下载失败记录防丢与普通任务结算） |
| 工作目录 | `C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite` |
| 审计基线 | `ae94406730425659695f80d5ee59b7d9ea15544b`（开工 HEAD `9553379`，其上仅文档提交） |
| 分支 / 远端 | `v2-clean-rewrite`（origin/v2-clean-rewrite，开工时远端 = 本地 = `9553379`） |
| 最终源码 SHA-256 | 见 §9（规范 Git blob 原始字节），§6 为原作者交接快照 |
| 发布线 | 本仓正式维护线 v2-clean-rewrite。ROOT 接收变动和实际证据见 §9。§8 保留原交接时的发布历史。 |

## 2. 对应的两条原发生与修复

| 原发生（issue_key） | 修复 |
|---|---|
| 第 12 行 `log-ack-before-persistence`（expected `failed-write-remains-recoverable`） | `src/downloader.py` `FailedDownloadLogger.flush()` 重写：批先换出、成功 `os.replace` 后才确认；拒写把本批放回队首并保留 flush 期间新到项（`batch + self._pending`）；旧文件（纯 JSON list）保持可读，坏文件抛错不覆盖；新增 `read_failed_records`/`_atomic_write_json`（同目录临时文件 + fsync + 原子替换，任何失败清理临时文件）。 |
| 第 13 行 `business-failure-classified-expected`（expected `failed-task-accounted-for`） | `main.py` 结算重写：`run_single`/`run_multi`/`run_test_cases` 真实结果向 CLI 汇总，`run_multi` 返回 `{"succeeded","failed","skipped"}`；任一失败 `sys.exit(1)` 并记录 `Tasks settled: …`，仅全部成功才输出 `All tasks completed`（外层形状保留）。普通启动在参数解析与副作用之前建立身份并写启动回执（`src/feedback_publish.py` `OrdinaryRunFeedback`），每任务 started/terminal 观察按请求意图派生 step_id，终态 `failed`/`deviation`/`ordinary-task-failed`，运行结算观察 `all_completed/partial/all_failed/not_started`。 |

失败队列（B 节）：记录、写出、确认分离；只有整批成功持久化后才确认；拒写保留本批与后到项。恢复只读原记录：`python -B -m src.feedback_publish republish|reconcile` 只消费 owner 自有 pending/回执，不构造 provider、不下载、不发现（替身计数增量为零；无收据保持未知）。

## 3. 直启发布接口（ROOT `native_observation_dirs` 配置项）

- 显式 `RESEARCH_FEEDBACK_OUT`：沿用单次 sidecar 及既有明细格式（`FeedbackSink`，OUT 优先于 DIR）。
- `RESEARCH_FEEDBACK_DIR`：隔离公开收件目录。
- 两者均未设置：owner 自有持久状态根（`RESEARCH_FEEDBACK_STATE_ROOT` 可映射，缺省 `C:\Users\郑曾波\.stockinfo-dl-simple`）。
- **正式默认收件目录（绝对路径）**：`C:\Users\郑曾波\.stockinfo-dl-simple\observations`
- **相对状态根的计算方法**：`<state_root>\observations`，其中 `<state_root>` = 环境变量 `RESEARCH_FEEDBACK_STATE_ROOT`（若设置），否则 `%USERPROFILE%\.stockinfo-dl-simple`。
- **示例文件名**：数据 `feedback-3f2c9a1e4d5b6a7c8d9e0f1a2b3c4d5e.jsonl`；同 basename 明细 `…details.jsonl` 与就绪标记 `…ready`。就绪标记 JSON 固定字段：`schema_version="sid-ready/1"`、`owner`、`origin_owner`、`run_id`、`attempt_id`、`step_id`、`check_id`、`occurrence_id`（64 hex，绑定同一份原发生），不放路径或命令。
- ROOT 从收件目录消费并负责确认（删除 `.ready` 即回告）。owner 侧先保存（`<state_root>\pending\<occurrence>.json`）再投递后确认；三个窗口（数据已落 ready 未发、ready 已发回告丢失、并发消费）均由投递台账 `<state_root>\deliveries\<occurrence>.json` 复用同一交付身份补发，一次发生只发布一次；台账独占创建（O_EXCL）并固定 observation 摘要，冲突重送不覆盖首份证据。启动回执在 `<state_root>\runs\<run_id>__<attempt_id>.json`，首终态不可覆盖；强退仅存 started 即未确认区间，`reconcile` 冷读可见。
- 冷读样例：`evidence/f4-sid-feedback-*.jsonl` + 同名 `.details.jsonl`/`.ready`、`evidence/f4-sid-sid-sample__try-sample.json`（成功尝试回执）；生成命令见 §5。

## 4. 改动路径

- `src/downloader.py` — FailedDownloadLogger 先落盘后确认
- `src/feedback_publish.py`（新增）— 持久 pending、投递台账、启动/终态回执、`OrdinaryRunFeedback`、`Publisher`、`republish`/`reconcile` CLI
- `src/feedback_observation.py` — 新 check/issue 常量、`filter_details` 全字段校验、白名单增补（`stage`/`sent`/`executed_state`/`stock_code`/`exit_code`/`succeeded`/`failed`/`skipped`/`cause_types`/`code_site`）
- `src/company_wiki_adapter_cli.py` — 阶段跟踪 + 失败详情区补 `stage`/`sent`/`cause_types`/`code_site`（外层错误码与 stderr 信封不变）
- `main.py` — 身份先行、真实结算、诚实退出码
- `tests/unit/test_f4_ordinary_failures.py`（新增 28 项）、`tests/unit/test_main.py`（autouse 状态根隔离）

## 5. 隔离复现与冷读命令

```powershell
C:/Miniconda/python.exe -B -m pytest -q tests/unit/test_f4_ordinary_failures.py
C:/Miniconda/python.exe -B -m pytest -q tests/unit/test_failed_logger.py tests/unit/test_main.py tests/unit/test_feedback_owner.py tests/unit/test_feedback_observation.py tests/unit/test_company_wiki_adapter_cli.py tests/unit/test_company_wiki_adapter_cli_budget.py
C:/Miniconda/python.exe docs/plans/feedback-loop-2026-11-17/evidence/f4-sid-node-c-check.py   # 大节点 C 全矩阵，stdout 输出 JSON
```

实测：F4 文件 28 通过（含补齐的正常空结果 `no_candidates` 对照与两任务同时失败的"两条不同事件"结算对照）；回归集 83 通过；全量 `tests/unit` 405 通过 / 5 失败（5 项均为开工前已存在的 `stock_orgid_mapping.json` 残留与历史 fixture pin，`git stash` 复跑确认与本卡无关）；`tests/e2e/test_g4_latest_cli_offline.py`（`G4_CWP_COMMIT=7e0ecebb01096e202d5ec11847cd28e927edf4c9`）17 通过。全部离线：审计钩子屏蔽 socket，公司列表为合成 900001/900002/900003，用户两份名单未跟踪、未改动、未提交。

**调用数**：真实网络调用 **0 次**（审计钩子全程在线，无任何 socket 连接）；付费/计费调用 0 次；恢复路径（`republish`/`reconcile`）不构造 provider、浏览器或传输，下载与发现替身计数增量 **0**；未知费用一律保留未知，确知未发送才报 `not_sent`。

RED 证据：`evidence/f4-sid-red-20261121.log`（22 失败 / 3 通过；两条核心 RED 信号：`assert 0 == 2` 拒写后队列已空、普通任务失败 `assert 0 != 0` 退出码 0）。大节点 C 矩阵：`evidence/f4-sid-node-c-20261121.json`，分母 19 项注入入口事件，**19/19 covered**；同外层（`upstream_unavailable`）不同内因（staging `FileExistsError` vs transport `TimeoutError`）冷读可分别复现。有效拒绝、降级/正常成功、失败、强退未知、正常成功均有对照。已核实不可注入路径：空 config 因 `load_config` 默认注入空 `test_cases` 而表现为零任务空成功（预存语义，如实记录，usage 拒绝分支经公共入口不可达）。

大节点 C 四类路径标注：
- **已覆盖（本机实测）**：19 项注入入口全部——普通 CLI 的成功/失败/两败一结算/双任务一成一败/坏配置、适配器的 bad-action/坏 stdin/staging 文件/传输超时/正常候选/空结果/缺 security_id/预算拒绝、失败日志拒写恢复与旧数据迁移、强杀未知与相邻尝试独立、reconcile 冷读、三个投递窗口、三种发布模式。
- **待投递语义（已证明机制，消费侧未测）**：pending 先存后投、拒投保留、同交付身份补发、恰一次发布均已实测；ROOT 侧从公开收件目录消费并回告属跨仓动作，由 ROOT 在 `native_observation_dirs` 配置后验收。
- **原因仍未知（协议内诚实留痕）**：强退（`os._exit`）后仅存启动回执的未确认区间——回执与 reconcile 冷读实测；真实生产强退现场未在本机发生。
- **未在现场实测**：真 CNINFO 网络、付费服务、跨仓组合、宿主中断恢复（见 §8 归属）。

脱敏样例生成命令（隔离临时根，经真实 CLI）：

```powershell
C:/Miniconda/python.exe docs/plans/feedback-loop-2026-11-17/evidence/f4-sid-samples-generate.py
```

## 6. 原作者交接源码 SHA-256（历史独审快照）

```
e5484c48c9dab28003f5d66f2b2a844a563e251b89002473565ed7930976ceea  src/downloader.py
d87678be6a2b3b9cd44615037418f5672486398df3d4e9aee45b56b9a5df4d80  src/feedback_publish.py
9c337e8c42fb22fa65d91384ed8bc734b430422f821f858f1913ff1bcd441d29  src/feedback_observation.py
c9e8a47dc2931b0be001ea5406e4f95ca19077e148eee8af4f37fd9059a7f285  src/company_wiki_adapter_cli.py
268564c1402199d88cf5a976c1137f275e3bb12e32bd4402694c1f3d0ae9e0b3  main.py
becf18bc4de1c71db6dda0b7042cc60fb8e5b7562a7af0a565b8c46ef00a2084  tests/unit/test_f4_ordinary_failures.py
2bd2237bafa26225cc1e63ae865b2383225ea0f122a1b3b0e072eb1e8573996a  tests/unit/test_main.py
```

## 7. 独审与修复

独立审查 agent（Explore，只读，未获作者预期结论）首轮 **FAIL / 1 阻断 + 11 非阻断**，并独立复跑了 F4 测试、回归集与大节点 C。全部可修问题已修复并在最终源码复核：

| # | 发现 | 处置 |
|---|---|---|
| 1 [阻断] | fetch 传输完成后的本地写失败被标 `staging`+`not_sent`，虚假"确知未发送" | `_sent_state` 仅 payload/request/config 报 `not_sent`，staging 报 `unknown`；新增 fetch 阶段 OSError 专项测试（不得报 not_sent） |
| 2 | 3 个发布模式测试与 node-C 写入真实用户状态根；一处断言空真 | 全部映射到临时状态根；本轮污染的真实状态根（34 回执/57 台账，均本会话产生）已删除还原 |
| 3 | DIR 路径明细缺 `observed_at` | `_publish_to_inbox` 补时戳 |
| 4 | ack 后同发生不同内容的重送覆盖已发布文件 | 投递台账固定 observation 摘要，冲突重送拒绝（首证据获胜，对齐回执首终态不可覆盖） |
| 5 | 台账首建竞态可致同发生两文件 | 台账改独占创建（O_EXCL），败者读取胜者交付身份 |
| 6 | 并行 worker 无锁递增结算计数器 | `threading.Lock` 保护，`run_finished` 锁内读取 |
| 7 | reconcile 输出泄漏私有 `inbox` 路径与未过滤 details | `_reconcile_report` 剥离 inbox、details 过 `filter_details` |
| 8 | 白名单仅校验新增键 | 全部 token 字段（error_code/action/mode/source_result/cause_chain/cause_types/retried/reused/retryable/budget_usage）按类型与安全引用校验 |
| 9 | 卡片要求"本仓相对代码位置"未落 | 新白名单键 `code_site`：`main.py:download`、`main.py:main`、`company_wiki_adapter_cli.py:failure-handler` |
| 11 | 临时文件在 dump/fsync 失败时残留 | 三个原子写器在 replace 前任何失败均清理临时文件 |
| 10 | 交接 Markdown 未写 | 本文件 |

首轮修复后复核：**PASS / 0 阻断**（审查 agent 独立复测 83 通过、node-C 19/19、全量 unit 405 通过），另报 3 项残留非阻断，已在本轮全部收口：① 台账 O_EXCL 写入补 fsync，且空/坏台账自愈一次（消除"该发生永久 deferred"窗口）；② `observed_at` 纳入 `filter_details` 安全引用校验；③ fetch 阶段 OSError 测试更名并如实陈述前提。收口后独审按 §6 全部 7 个 SHA 复核（哈希逐一比对一致，含自愈路径在 Windows/POSIX 各交错下的恰一次发布分析）：**最终判定 PASS / 0 阻断**。对照施工卡逐节完整性核查补齐两处对照缺口（A 表第 3 行正常空结果 `no_candidates` 对照、B 节两任务同时失败的"两条不同事件"结算对照，均为纯测试增量，独审 delta 复核 PASS 且哈希比对一致）；收口后实测：F4 文件 **28 通过**、F4+回归 **85 通过**、全量 unit **407 通过**（5 项预存失败不变）、大节点 C **19/19 covered**。

## 8. 原作者交接时的未执行事项和事实记录

- **发布被 Mimosa 提交门禁拦截（需 ROOT/操作者处置）**：`git commit` 被操作者安装的 Mimosa L3 门禁强制拦截，报 11 项高危——全部位于本卡所有权之外的预存文件（`src/cninfo_api.py`/`src/stock.py`/`scripts/capture_byd_fy2024_fixture.py` 的 SSRF：实际是带 `TRANSPORT_HOSTS` 白名单的 CNINFO 专用客户端与固定常量端点；`src/storage.py`、`tests/e2e/test_skip_existing_files.py`、`tests/test_config.py` 的"路径穿越"：动态路径/`os.path.join` 惯用法的启发式误报）。**本卡改动的 7 个文件在密封扫描中零发现**（scanId `scan-2026-11-21T18-29-38.132Z-b5926fa1d664`，seal `sha256:870029e2997b62c5af2aa6d3392b4a6b75f58a21ce842397012d162f623c5377`，9 项发现 verdict effect `none`、运行状态 inconclusive）。本卡不越所有权范围改写他人卡片的受审模块（对 provider 传输的核心启发式重写有真实回归风险），故按门禁保留未提交。处置选项（ROOT 决定）：修复上述预存项后重扫提交；或对启发式误报建立 accept 基线后提交。改动已全部 `git add` 暂存，处置后一条命令发布：
  `git commit -m "fix(sid): durable download-failure records and honest ordinary settlement" && git push origin v2-clean-rewrite`
- 真 CNINFO 现场与付费服务未触碰（无网络，全部离线替身）；跨仓组合、宿主中断恢复与 `native_observation_dirs` 配置由 ROOT 验收。
- 预存事项（非本卡引入，如实交接）：① 零任务运行因默认配置注入空 `test_cases` 报空成功（`src/config.py` 预存语义）；② 并行 `run_multi` 各公司各自构造 `StockDownloader`，其 `FailedDownloadLogger` 对同一 `logs/failed_downloads.json` 的读改写存在基线已有的跨实例竞态（原作者交接时已保证单次写原子与不丢队列，跨实例合并于 §9 关闭）；③ 全量 unit 的 5 项预存失败与本卡无关。
- 清理：会话临时目录已删除；真实状态根已还原（删除）；仓库根无新增临时目录；`.mimosa/`（hook 状态）与两份用户名单保持未跟踪不动。

## 9. ROOT 独立接收与最终候选

工作区和 origin 均从 95533795b448d7a8e9d05c12f822d70b41f74258 接收，原作者的暂存交接与其独审快照可对应。总控接收复验重现了两个真实 logger 同时写同一失败日志、后一份覆盖前一份的情况，以及 fsync 失败后留下临时文件的情况。收据也存在两个结算进程同时读入未完成状态后互相覆盖的窗口。

- 失败日志由本仓 OS 文件锁串行执行读取、合并和原子替换，失败会保留队列。原生 IO 集中处理同目录临时文件、原子落盘和 Windows 长路径。保留过去可读的 JSON 记录和只读 API。
- 投递台账固定发生标识及第一份内容。新文件用 feedback-<occurrence前32个hex> 命名，已有台账继续沿用其记录的名字。数据及明细落盘后发 sid-ready/1，台账记已发布后确认 pending。收件方已删除 .ready 后，已确认的同一发生再次投递只返回原确认状态。启动和结算回执的读取、选择首次终态与写入共享本仓锁。
- 普通直启和适配器 CLI 共用默认公开收件目录 C:/Users/郑曾波/.stockinfo-dl-simple/observations。仍可选显式 OUT 或 DIR。适配器参数拒绝保留退出码 2，录入 arguments 和 not_sent。请求/预算的有效拒绝先登记 gate_review，意外 I/O/传输失败进入分诊。
- src.feedback_owner 的公开 --sidecar-dir 可重复，用旧监督目录和原生目录组合。冷进程按绑定的原运行、尝试、步骤和终态定位原作业。只有原明细明确 not_sent 才返回 known/not_applicable，其余保持 cost_unknown/unknown。无原终态或证据冲突时保留未确认。总控独立用普通 PermissionError 发生复验，两次打开得到同一个 failed/cost_unknown/unknown，无新 SQLite，原观察字节一致。

本轮复验口径以下列最终候选 Git blob SHA-256 为绑定。旧快照 §6 与旧 RED/C JSON 是接收前的历史证据。ROOT 宿主组合另有验收。两份用户名单和并行工区保持原状，集中测试在独立短目录及显式超长嵌套样本里执行。

```text
a9ed13d37ed6a1a80e6cbecbd859238e5d7319e71f943b8a1a936a438e45ee03  main.py
c517ada4d52ffed16c42af5dfa13f631531a319d56609f9d91c314a5ac704049  src/company_wiki_adapter_cli.py
88d64d2ff6e3c7450316fef1eed8480013223c5489da724cbc8d6749ada2dc11  src/downloader.py
0d39523dd52a9c68cbc436700fdeb517b93f13e7d3ff2feea6abc91a5e80d176  src/feedback_candidate_capture.py
c1fe99345b62567163dd1cefb181741c6211390ff22d51ea62108c9cbd2fede1  src/feedback_files.py
5f2d3ddfd699420df5cf043ac3e7cac96dda72f4383948c31302d80df2517ca1  src/feedback_observation.py
6a1e8aed624485002b92799041fb974229174d5b8b21455fdf17c1f776815611  src/feedback_owner.py
15ae85553a0397f2beda68c402a4554821ec4ce8876cdb11ee37b4171aa81a14  src/feedback_publish.py
d90ddde6d2fce47d1517a43ef06f398a261e7dc07b09900b944abb94e6efd426  tests/unit/test_f4_ordinary_failures.py
f2b17edd8abaa649b9438c815c2c7a26db2d9c08a3f93aad3c597f868b1fece2  tests/unit/test_main.py
c053a2817998d641fbc66dae367620c7523f553d4c1e42d181f63445959527ce  tests/provider_runtime_fixture.py
f54ccb4aca115061905ef7b5972da3a662802dd1c3c35668ba8515a61620c70b  tests/unit/test_provider_runtime_artifact.py
0ca2c83c041ca3b77db125e7baff4e2df83ed2c4b344ab04a58f0300122c6cd7  tests/e2e/test_g4_latest_cli_offline.py
```

### 接收复验

- Windows Python 3.13.9，7 个集中测试文件合计 **90/90**，另跑原大节点 C 离线矩阵 **19/19**。新覆盖包含跨实例合并、拒写时临时文件清理、默认适配器事件双目录冷对账、长路径的发布后消费再送和并行首次终态保护。
- SID 的浏览器无关制品清单加入实际传递依赖 feedback_files.py 和 feedback_publish.py。独立制品测试 **7/7**，其中 test_artifact_discover_and_fetch_work_from_an_empty_cwd[default] 从空工作目录运行 discover 和 fetch，两类操作均产出默认收件标记。旧显式 OUT、不可写 OUT、无效显式上下文有对照。
- 固定 CWP 版本 7e0ecebb01096e202d5ec11847cd28e927edf4c9，G4 离线组合 **17/17** 通过，含四个 committed-route。接收首轮四项在 Git 前置退出 128，stderr 显示缺 GIT_CONFIG_VALUE_0。原因是旧测试把环境整份回写，Windows 删除了宿主注入的空值。夹具现只更新实际需要的四个变量并完整恢复，保留宿主设置和业务断言。
- 新回归和制品验证全部离线。G4 只连本机 loopback 夹具。真实网络、付费和额外下载次数均为 0。接收中创建的隔离运行目录已清理。
