# FB-SID — handoff

状态入口：[FB-SID 施工卡](FB-SID.md)（本目录）。本文件只报告本轮实际事实，不替代 ROOT 的跨仓验收。

```json
{"lane":"FB-SID","owner":"stockinfo-dl-simple","base":"16499a036c34dc8522149dfcbe723a11a70e8b60","reviewed_commit":"1107c938574fc78b2b0de7419a0fff5ede203e76","published_commit":"1107c938574fc78b2b0de7419a0fff5ede203e76","status":"完成（本仓范围）；定向命令 1 项邻仓 CWP pin 失配预存失败交 ROOT","tests":[{"command":"C:/Miniconda/python.exe -B -m pytest -q tests/unit/test_feedback_observation.py","result":"29 passed / 0 failed（新增契约测试，RED 见 red-feedback-observation.log）"},{"command":"C:/Miniconda/python.exe -B -m pytest -q tests/unit/test_feedback_observation.py tests/unit/test_company_wiki_adapter.py tests/unit/test_company_wiki_adapter_cli_budget.py","result":"53 passed / 0 failed / 0 skipped（FB-SID.md 定向命令的 unit 子集）"},{"command":"C:/Miniconda/python.exe -B -m pytest -q tests/unit/test_feedback_observation.py tests/unit/test_company_wiki_adapter.py tests/unit/test_company_wiki_adapter_cli_budget.py tests/e2e/test_g4_latest_cli_offline.py","result":"65 passed / 1 failed / 4 skipped；唯一失败为 test_cwp_discover_bounded_consumes_the_1_3_0_response（外部 CWP 默认 pin 缺 security_id，baseline 复现，stash 已证，邻仓环境失配）"},{"command":"C:/Miniconda/python.exe -B -m pytest -q tests/unit/test_provider_runtime_artifact.py","result":"3 passed / 0 failed（G5 最小 runtime artifact 闭包未破坏，feedback 惰性 import）"},{"command":"C:/Miniconda/python.exe -B -m pytest -q tests/unit","result":"363 passed / 5 failed；5 项均为开工前已存在（stock_orgid_mapping.json 残留 + 历史 fixture pin），与 FB-SID 改动无关，stash 复跑确认"}],"native_refs":["stockinfo-cninfo/1.3.0 真实 CLI loopback：candidate ann=900001001 security_id=600000，stdout 单行、stderr 空、exit 0","tests/unit/test_feedback_observation.py::test_cli_process_interrupt_before_receipt_leaves_unknown","tests/unit/test_feedback_observation.py::test_budget_rejection_keeps_stderr_last_line_and_records_terminal","tests/unit/test_feedback_observation.py::test_real_adapter_keeps_only_the_verified_row_and_does_not_accuse_rejects[exact/latest]"],"sample_refs":["docs/plans/feedback-loop-2026-11-17/evidence/real-cli-sample.jsonl（正常发现+within_budget）","docs/plans/feedback-loop-2026-11-17/evidence/real-cli-budget-failure.jsonl（预算拒绝，stderr 末行 JSON、exit 1）","docs/plans/feedback-loop-2026-11-17/evidence/replay-samples.jsonl（已证实/缺码/异股合法拒绝 + 具名偏差）","docs/plans/feedback-loop-2026-11-17/evidence/real-cli-sample.details.jsonl（明细白名单）","tests/fixtures/feedback_observation/listing_identity_rows.json（最小可重放 fixture）"],"review":"独立审查 agent-a3130f11（Explore，只读，未获作者预期结论）：首轮 VERDICT PASS / 0 阻断；审查范围=生产路径+故障路径+协议/泄露+误开单+重放+恢复，绑定源码 1107c93。2 项非阻断已修并在最终源码复核 PASS：①新增 CLI 级 KeyboardInterrupt→unknown 测试（最终 29 passed）；②修正 SKILL pin 说明。审查确认全部 evidence/*.jsonl 零禁项泄露（%PDF/http/路径/凭据/原文/异常文本 0 命中）；G5 artifact 3 passed。","cleanup":"本轮仅产生 OS 临时目录 fb-sample-*/fb-budget-* 与两个 /tmp 生成脚本，均已删除；测试 tmp_path 由 pytest 自动回收；仓内根无新增临时目录；a_share_companies.txt 与 companies.txt 为开工前用户公司名单，未跟踪、未改动、未提交；未提交运行目录/整份业务产物/调试副本（中间 full-unit.log 已删）。","remaining":["CWP/FF 入库、复用判断与公司池调度由 ROOT 在 combos 验收","真 CNINFO 现场（无网络）与 G2-12 latest_as_of 完整 ensure 链由 ROOT 决定","邻仓 CWP pin 与 DownloadCandidate.security_id 字段对齐属 ROOT/邻仓；本仓只交公开输入输出与证据"]}
```

## 1. 范围与提交

| 项 | 值 |
|---|---|
| 开工 base HEAD | `16499a0`（= 计划核对基线 `fb8c8ba` + FB-SID 卡文档提交） |
| 目标分支 / 主线 | `v2-clean-rewrite` |
| 最终受审源码 | `1107c938574fc78b2b0de7419a0fff5ede203e76`（已独立审查 + 两项非阻断复核 PASS） |
| 实际发布 | 同上 SHA，已 `git push origin v2-clean-rewrite`；推送前 `ls-remote` 实测主线 = 本地 base `16499a0`，无并行变动；推送后远端 = `1107c93` |
| 本卡提交 | `1107c93 feat(sid): feedback-observation/1 sidecar, issue ledger and repair skill`（17 文件，+1644/-0） |
| 本文件 | 文档提交在源码提交之后，仅新增 `handoff.md`，不追自引用 SHA |

## 2. 三个实施节点对应实现与证明

- **节点 1（TDD 固定差异）**：`tests/unit/test_feedback_observation.py` 用 `tests/fixtures/feedback_observation/listing_identity_rows.json` 的同页三行（已证实/缺码/异股）验证 exact/latest 只保留正确候选且不误报缺陷；历史「声称验证但缺 native 证据」得到 `verified-candidate-id-missing` 具名偏差并保留首次证据。新增测试先在无模块时跑出 RED（`red-feedback-observation.log`：0 collected / ImportError），实现后 GREEN。
- **节点 2（接入真实操作）**：`src/feedback_observation.py` 产出 `feedback-observation/1` 单行 UTF-8 JSONL；`src/company_wiki_adapter_cli.py` 在 discover/fetch 入口接线，映射动作开始/结果、原生 announcement ID、预算与来源结果；原件字节、响应全文、下载 URL 查询、物理暂存路径不进入反馈；覆盖正向、预算拒绝、部分用量失败、诊断写故障、进程中断 unknown。`RESEARCH_FEEDBACK_OUT/RUN_ID/ATTEMPT_ID` 注入独占 sidecar；每文件单写者；观察不入业务 stdout/stderr。
- **节点 3（技能与闭环）**：`skills/repair-stockinfo-dl-simple-issue/SKILL.md` + 两张一因一卡（`issues/verified-candidate-id-missing.*`、`issues/batch-missed-success.*`）。用真实公开 CLI + 本机 loopback/fixture 重放（见 sample_refs），重复导入零新增、不同尝试可分、进程中断保留 unknown，`needs_refetch()` 有终态即 False 防重复取件。

## 3. 公开接口与兼容

- provider wire `stockinfo-cninfo/1.3.0` 与 JSON 1.0 成功/失败结构不变；反馈只写宿主注入的 sidecar，业务 stdout/stderr/退出码/预算/原件/重试行为不变。
- `feedback_observation` 在 CLI 内**惰性导入**：仅当 `RESEARCH_FEEDBACK_OUT` 非空时加载，G5 最小 runtime artifact 的传递闭包保持不变（`RUNTIME_FILES` manifest 不增文件，`test_provider_runtime_artifact.py` 3 passed）。
- 需 ROOT 消费的小 fixture 与命令见上 `sample_refs` 与 SKILL.md 第 2 步。

## 4. 测试与失败归因

定向命令和完整 `tests/unit` 的实际计数见顶部 JSON。关键归因：

- `test_g4_latest_cli_offline.py::test_cwp_discover_bounded_consumes_the_1_3_0_response`（1 failed）：M3 修复在 `fb8c8ba` 给该用例加了 `candidate.security_id == SEC` 断言，但测试默认 CWP pin `5930a644` 的 `DownloadCandidate` 无该字段；`git stash push src/company_wiki_adapter_cli.py` 后 baseline 同样失败，证明与 FB-SID 无关；改用含该字段的 CWP 修订可通过。属邻仓 pin 失配，交 ROOT。
- 4 skipped：需显式 CWP route commit（`"G4_CWP_COMMIT" not in os.environ`），本卡不默认跑跨仓组合。
- 完整 `tests/unit` 的 5 failed 均在开工前已存在（工作区 `src/stock_orgid_mapping.json` 残留与历史 fixture pin），stash 复跑确认，与本卡 diff 不重叠。

## 5. 独审与恢复

独立审查在第 4 节所述源码上进行，未获作者预期结论，首轮 PASS / 0 阻断；两项非阻断（CLI 级中断测试、SKILL pin 说明）已在最终源码修复并复核 PASS。协议/泄露审计对全部 `evidence/*.jsonl` 扫描 `%PDF|http|://|C:\|/tmp/|Token|Cookie|Traceback|Exception|announcementTime=` 零命中；明细白名单阻止原文正文与未脱敏异常进入反馈。诊断写失败只计数不改业务结果（`FeedbackSink.write_failures`）。

## 6. 未执行 / 归属

真 CNINFO 网络现场、公司池调度、CWP/FF 入库与 G2-12 完整 ensure 链未在本卡执行（无网络 / 跨仓），交 ROOT。本仓仅以本机 loopback/fixture 证明 provider 侧诚实终态与协议兼容。
