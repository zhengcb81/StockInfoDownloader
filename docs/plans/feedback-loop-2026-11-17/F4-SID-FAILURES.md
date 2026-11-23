# F4-SID-FAILURES 下载失败记录防丢与普通任务结算

本仓 A/B/C 实现、独立接收与针对性验收已完成。发布范围是本仓维护线，跨仓组合由 ROOT 记录。当前接口及结算见[最终交接 §9](F4-SID-FAILURES-handoff.md#9-root-独立接收与最终候选)。工作目录为 `C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite`，正式维护线 `v2-clean-rewrite`，审计基线 `ae94406730425659695f80d5ee59b7d9ea15544b`。使用本仓已有的发现、下载和 [F4 动作端口](f4-runtime.md)。现场两份未跟踪列表 `a_share_companies.txt`、`companies.txt` 属用户资料，测试使用单独合成的公司列表。

## 工作约定

先在下述唯一工作目录执行 `git status --short --branch`、`git worktree list`、`git diff --name-only HEAD --` 和 `git log -4 --oneline`，记录起点。以下源码位置是审计时的定位，按当前方法和行为接续。若现有 harness 已改同一路径，将本卡排在该线后，先读取其差异和验收再接续。三个 owner 各有自己的目录、状态库、测试和提交。保留并行作者的暂存区、配置和产物。遇到确实需要改公共 wire 或其他模块的事项，把最小输入与期望交 ROOT，继续本仓可完成的部分。

隔离测试在真实 Python 子进程中调用普通入口。配置、用户数据根、工作目录、日志、数据库、暂存与输出全部映射到同一测试专用临时根；使用进程自己的环境，清除继承的 `RESEARCH_FEEDBACK_OUT`、运行号、尝试号再测默认路径，并单测过去显式设置的调用。替身仅放在本仓的磁盘故障注入点或真正外部传输、计费、引擎边界。保留原生 CLI、父子进程、结算、查询及文件操作。收尾核对临时目录恢复到原样。

## 已知事实与排他写入范围

总控 `company-wiki/docs/plans/feedback-loop-2026-11-17/issues/failure-coverage-20261121.jsonl` 原运行号 `f4-coverage-audit-20261121`，发现方 company-wiki。只读参照同目录 `probes/sid.py`。9 个场景中，7 个故障不能进入有效分诊，正常公告候选和已知候选丢证券身份是两个有效对照。

| 原发生位置和编号 | 原生结果与根因 |
|---|---|
| 第 12 行，`baseline-ae944067 / failure-log-flush / failure-coverage`，`log-ack-before-persistence` | `src/downloader.py:61` 的 FailedDownloadLogger 在落盘前清空队列。第一次写入注入 PermissionError，恢复后的第二次 flush 无文件，内存队列亦已空。 |
| 第 13 行，`baseline-ae944067 / ordinary-download / failure-coverage`，`business-failure-classified-expected` | 普通下载抛 PermissionError 时 `run_single` 已判任务失败，`main.py:218` 一带丢弃任务结果，最终报 All tasks completed，进程却退出 0。适配器把请求、临时文件错误和传输超时压成 upstream_unavailable。 |

本卡只拥有本仓 `main.py`、`src/downloader.py`、`src/company_wiki_adapter_cli.py`、现有 `src/feedback_*.py` 和直接关联的本仓测试、计划。原 CNINFO 预算、HTTP 协议、候选身份、CWP 原件入库存储各按既有端口运行。公司清单、下载历史和配置不能拿来做测试。ET、MC、StockInfoDownloader、Dayu、CWP、FF 都在本包写入范围外。

## A 先冻结失败

第一道 RED 用 `FailedDownloadLogger.record` 写两个不同的失败，用可控本地异常拒绝第一次持久化，恢复可写后再次 flush，从**另一进程**读原事件，断言两条均在且无重复，再加一条在 flush 过程中并发入队的失败。基线导出的队列和文件均空，保留证据。第二道 RED 通过 `main.py <测试代码> --config <隔离配置>` 启动真实 CLI，只替换下载传输使其抛出 `PermissionError`。冷读任务结果与进程结算，断言没有把真正失败报成全部成功。扩展到两个任务一成一败，分别核对。

| 真实入口与离线注入 | 期待的独立结果 |
|---|---|
| `python -B -m src.company_wiki_adapter_cli --bad-action`；`main.py --config <损坏JSON>`；discover 读坏 stdin | 记录请求拒绝或启动配置的具体阶段，保留公共 CLI 外形及实际退出。记录副作用确实未开始。 |
| fetch 指向临时普通文件作为 staging-dir；discover 在 CNINFO **传输边界**超时 | 稳定地区分本机暂存、响应超时与参数问题，包括 cause、是否可重试、是否实际发送；格式相同不把性质不同的失败合并。 |
| 正常发行人候选；受控地让同候选序列化漏 security_id；预期空结果和原预算拒绝 | 复用 `tests/fixtures/feedback_observation/listing_identity_rows.json`。正常空结果与预算耗尽保留各自语义。原候选修复回执及费用证据可正常复用。 |

## B 由原业务结算驱动投递

失败队列只在本批成功持久化后确认。采用能从 SID 原运行记录或轻量待投递项冷读的机制。记录、写出和确认分开；出现拒写保留本批和后到的新项。在两个进程重送同一发生时应得到同一业务发生和一次发布。测试覆盖两条不同事件同时失败、同一事件重复、磁盘恢复、两个并行补投者、事务落盘前后强制终止。既有 `FailedDownloadLogger` 旧数据保留可读，失败文件不能在迁移或重试中丢失。

`run_single`、`run_multi`、`run_test_cases` 的真正结果分别向 CLI 汇总。按现有命令语义保留账户预算和预期跳过，对失败/部分成功给出真实业务收尾。外层公共错误码若为兼容需要沿用，在本仓详情区留原阶段和底层类别，不用新的错误码白名单。用同一组低层故障检测普通下载与适配器，一次成功文件不得随同其他失败重下。恢复只读取原 job/失败记录，下载和发现替身的计数增量均为零；之前没有收据则保持未知。

新增 `tests/unit/test_f4_ordinary_failures.py`，用子进程运行两套公开 CLI，加一个独立读回进程。继承配置外网全部屏蔽，复用现有回归，重点先跑：

```powershell
python -B -m pytest -q tests/unit/test_f4_ordinary_failures.py
python -B -m pytest -q tests/unit/test_failed_logger.py tests/unit/test_main.py tests/unit/test_feedback_owner.py tests/unit/test_feedback_observation.py tests/unit/test_company_wiki_adapter_cli.py tests/unit/test_company_wiki_adapter_cli_budget.py
```

## 持久化和公开交接

沿用本仓既有日志、动作回执及 `feedback-observation/1`。普通启动在参数解析和副作用前建立本次身份，父调用传入的 ID 原样关联，缺省时生成可跨进程查回的 ID，两个并发任务隔离。利用原生业务终态或本仓已有持久目录保留待投递记录；先保存再确认，导出失败不覆盖业务原返回。新进程依据同一 owner/run/attempt/step 或 action 只读对账、补投。断在落盘与确认之间、重复消费或并发恢复均只登记一次原发生。所有可写介质均不可用时，外层已有启动收据才能标出未确认区间，明确哪些原因已经不可恢复。成功的兄弟任务不能覆盖失败或未知的那个尝试。

交给 ROOT 的公开观察沿用 `owner`、`origin_owner`、`run_id`、`attempt_id`、`step_id`、`check_id`、`version`、`expected`、`actual`、`disposition`、`issue_key`（如适用）、`evidence_ref`、`details_ref` 及已有拒绝码。原生明细补足未执行/已尝试/未知、退出码、阶段/输入引用、业务结果、脱敏异常类型链及本仓相对代码位置、使用量和其依据。未知费用保留未知，确知未发送才可报零。发现拒绝先按业务目的审视，识别正常请求被误拒时在本仓 PWF 记根因和减门方案；正常拒绝如实留痕，不必启动修复。向外只给既有可解析引用；不复制原始 argv、原文、密钥、完整 URL 查询或未脱敏 stderr。

### 直启发布接口

显式 `RESEARCH_FEEDBACK_OUT` 沿用单次文件及其既有明细格式。未传 OUT 时写 owner 自有的持久状态根下 `observations`，`RESEARCH_FEEDBACK_DIR` 可指定隔离的公开收件目录；两个变量都有值时 OUT 优先。使用同目录临时文件、关闭写入，原子发布 `feedback-<32位小写发生标识 hex>.jsonl`，对应的脱敏明细就绪后，再原子写同 basename 的 `.ready`。该 JSON 标记写 `owner`、`run_id`、`attempt_id`、`step_id` 并绑定同一份原发生，不放路径或命令。ROOT 从公开收件目录消费并负责确认标记；owner 保留原生证据，用记录过的交付身份补发。覆盖数据已落而 ready 未发、已发但回告丢失、并发消费三个窗口。确认失败只影响交付状态；业务返回、原请求和计量保持原样。用三组隔离运行覆盖显式 OUT、仅 DIR，以及两者均未设置而将本机状态根映射至临时目录。交接写本机正式默认收件目录的**绝对路径**、相对状态根的计算方法以及示例文件名，供 ROOT 在 `native_observation_dirs` 配置。若已有实现符合这些语义直接复用。

## 大节点 C 与交付

用新进程逐项对照入口受理清单、原生终态和 F4，列出每次运行及尝试的实测结果。分母用本次实际注入的入口事件，另外标明已覆盖、原因仍未知、待投递和未在现场实测的路径。冷读两种同外层异常但不同内因，核对是否可分别复现。有效拒绝、降级成功、失败、强退未知及正常成功都要有对照。针对拒绝先看门禁是否必要及能否简化，再决定修复。

实现和集中测试完成后，调用**独立审查 agent**，给它实际候选提交、两条原始发生及隔离复现命令，要求检查本卡全部覆盖、真实入口、错误/费用语义、故障恢复、数据脱敏及并发幂等。发现的可修问题全部修完，审查 agent 在最终源码版本复核，完成后才交接。把卡号、工作目录、基线和最终源码 SHA、分支/远端、改动路径、对应原发生、RED 前后实测、独审发现与修复版本、回归/冷恢复命令与退出码、调用数和清理结果写入本目录的交接 Markdown。提供可直接冷读的一份脱敏观察和同一尝试的明细示例或生成命令。发布本仓修复和交接，ROOT 通过公开接口做跨仓组合。
