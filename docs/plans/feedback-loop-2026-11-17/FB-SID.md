# FB-SID　CNINFO 候选与暂存反馈

施工状态：可立即交给一名独立 harness。唯一工作目录为 `C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite`。目标分支是 `v2-clean-rewrite`，计划核对基线 `fb8c8ba`。本地目录的 Git remote 使用 StockInfoDownloader 旧名称，实际工作固定在此简化版本的分支。当前计划入口为 [MB-SID task_plan](../mb11-sid-2026-11-11/task_plan.md)。

## 交付范围和现有依据

SID 负责 CNINFO 发现、来源证券归属、受限取件与暂存收据。实现本仓专用反馈投影、修理技能 `skills/repair-stockinfo-dl-simple-issue/SKILL.md`、契约回放/CLI 测试与本目录。允许在 `src/company_wiki_adapter_cli.py` 的原有 discover/fetch 入口接线；数据取自 `src/company_wiki_adapter.py` 的原生候选和收据。CWP 负责入库或复用判断，FF 负责调用策略。保留 `a_share_companies.txt` 和 `companies.txt` 两份用户资料。本卡不占用 G2-12 跨仓组合。

- [来源身份回归](../mb11-sid-2026-11-11/task_plan.md) 记录了 M3 旧行为：候选缺 security_id，原公告缺 secCode 时误补请求证券。exact/latest 的归属证据和受限取件已在主线修复，此卡观察其行为。
- `stockinfo-cninfo/1.3.0` 继续通过 stdout 返回成功响应，失败以非零退出及 stderr 最末一行结构化错误表达，含 code、retryable 及可用的 acquisition_usage。候选标识与暂存收据中的 provider_document_id/content_sha256/byte_size 可作来源证据。物理 staged_path 只由原暂存协议消费。
- [历史下载验证器审查](../mb11-sid-2026-11-11/review.md) 另有“两份下载一份失败却整体成功”的独立根因。可作为成功退出仍含业务问题的回放对照；CLI 只透出本次动作真实能证明的结果。

## 与 ROOT 的交接格式

观察格式为 feedback-observation/1。一行一个独立对象。必填字符串字段为 schema_version、owner、run_id、attempt_id、step_id、check_id、expected、actual。expected 和 actual 是适用于该检查的稳定结果词。可选字段为 issue_key、evidence_ref、version、parent_step_id、details_ref、disposition、origin_owner。disposition 仅取 expected、deviation 或 unknown；issue_key 是有证据支持的责任仓规则签名。引用为不含凭据、路径和可执行命令的本仓不透明标识。version 记录被观察运行的版本，交接报告另列被测代码版本。合法拒绝按实际预期归类。例子仅说明协议字段，运行时产生真实 ID 和版本。

~~~json
{"schema_version":"feedback-observation/1","owner":"stockinfo-dl-simple","run_id":"run-example","attempt_id":"try-1","step_id":"step-1","check_id":"candidate-listing-identity","expected":"verified","actual":"missing","disposition":"deviation","issue_key":"verified-candidate-id-missing","evidence_ref":"case-example","version":"fixture-v1"}
~~~

实现和校验 owner 只在本仓完成。ROOT 从公开交接文件读取，负责派工、跨仓原场景复验与公司池调度。ROOT 计划位于公司总控仓 docs/plans/feedback-loop-2026-11-17/task_plan.md，当前文档已包含单仓实施所需接口，允许独立并行开工。

总调度与各 owner 约定三个可选环境量。RESEARCH_FEEDBACK_OUT 提供本次独占 sidecar 路径，RESEARCH_FEEDBACK_RUN_ID 和 RESEARCH_FEEDBACK_ATTEMPT_ID 提供父运行及尝试编号；独立 E2E 可自建编号。输出位置通过宿主配置或测试入口注入，避免把任意写路径暴露给财报正文或网络输入。业务协议允许省略这些诊断字段。父进程启动子 worker 时分配不同的输出文件，或清除其 OUT 并由父进程记录该子调用的公开结果，确保每个文件只有一个写者。已写入的事件重放时复用原 ID。另一次真实尝试要单独设置 attempt_id。

## 三个实施节点

1. **TDD 固定差异。** 新建 `tests/unit/test_feedback_observation.py`。用既有本机 CNINFO 响应构造同页已证实、缺码、异股三行；验证 exact/latest 保留正确的候选，未证明记录被跳过且不误报缺陷。注入历史“返回声称验证的候选但缺少证据”的小型输出，得到具名偏差并保留首次证据。不从请求公司代码或文件名推出公告归属。
2. **接入真实操作。** 映射 discover_exact、discover_latest、fetch、staging 完成及失败；保留实际动作、原生 candidate/announcement ID、已知预算和真实来源结果。原件字节、响应全文、下载 URL 查询和物理暂存目录不进入反馈。覆盖正向取件、预算拒绝、已发生部分用量的失败、诊断写入故障；核预算操作数、stdout、stderr 最末一行和退出码。进程中断无收据时保留 unknown。
3. **完成技能与闭环。** 来源身份缺失与批量遗漏成功路径是不同共因，给出丢字段错误与合法同类对照。用真实公开 CLI 加本机 loopback/fixture 重放。在仓内保留最小 fixture，引导技能从同样的提交/输入重现错误、找到相同机制的另一挂牌或期次并完成 RED/GREEN。诊断导入两遍、不同尝试、进程中断分别验证，避免回报状态导致重复取件。下游入库验收由 ROOT 运行。

## 本仓实施与修理技能

把观察分为动作开始和动作结果。记录公开操作、时间、原生请求或作业编号、结果、是否有重试或复用、错误的稳定类型和原因链。开始后中断而没有终态时保留未知，新的尝试沿用运行编号并更换 attempt。诊断明细按需保存在本次运行目录，敏感头、凭据、原文正文、原始响应、未脱敏的异常文本和物理绝对路径留在反馈数据之外。成功日志短期轮转；开放问题绑定可随仓复现的小样本或现有永久来源引用。原件和正式运行产物继续由原 owner 保存。

每个外部参加联调的值仅通过文件内容公开。启用反馈的实际运行及模块 E2E 在原生步骤完成时自动产出观察。独立用例自行提供运行编号，调用方有上下文时继承其运行编号。由调用环境指定独占输出位置，每次调用由一个写者写一份 UTF-8 JSONL。观察不混入业务 stdout/stderr。写入失败由现有测试/作业记录报告诊断不完整，业务退出码、返回值、已有费用、原件和重试行为保持原合同。

当相同已判定根因跨运行出现时，把新的运行和证据引用挂到同一张本仓问题卡。原生观察保留原始 attempt，根因可以待定；只在有区分证据时分拆或合并。第一版沿用本仓存放回归用例的 Git 与本计划，需修理的共因可登记在本计划下的 issues/，一因一卡。开发用的缺陷编号与真实运行证据相链。重复导入同一次观察应为零新增，同一个错误码下不同根因保持可分，临时外部条件写恢复条件。

修理技能从本仓 issue 或给定运行引用出发。先核预期、实际、代码/配置版本及真实输入来源，从公开入口复现第一次偏离合同的位置，再查同类入口和相似合法对照。业务错误、测试夹具、部署环境和外部条件分别归因。可在本仓实施的修复及其测试写进 canonical PWF；属于邻仓的偏差交 ROOT 提供公开输入输出和证据。依据旧错误和对照先写 RED，再修共同责任层，在定向 GREEN 后用原场景复验。记录修复版本、回归用例、消费者待验或已验状态。相同版本、相同输入和同一失败不触发循环重跑。技能放在本仓 skills/ 下，只消费本仓受控的回放入口和不可执行的证据引用。

## 定向验证入口

使用 tmp_path 分配本机模拟响应和本次 staging，在子进程/fixture 内隔离网络、用户配置和公司名单。优先走已声明的本机隔离入口，清除测试自建目录前先确认其位置，保留所有真实原件。

~~~powershell
& 'C:/Miniconda/python.exe' -B -m pytest -q tests/unit/test_feedback_observation.py tests/unit/test_company_wiki_adapter.py tests/unit/test_company_wiki_adapter_cli_budget.py tests/e2e/test_g4_latest_cli_offline.py
~~~

先单跑新增测试观察 RED；组合 GREEN 要核 single-line wire、终态、筛选后的源 ID、实际字节与 unknown 行为。给 ROOT 交正常发现、合法拒绝、误接受及预算失败的脱敏样本，说明需真 CNINFO 才能验证的剩余范围。

## 独审、清理与交接

先让独立审查 agent 在未获知作者预期结论的情况下，仅凭本卡和可复现样例验证一次完整性、质量、协议兼容、误开单、重放和恢复。审查覆盖整段生产路径及故障路径，逐项修复并在最终源码上复核。正常 hooks 提交；远端发布前核本仓主线和并行变动，只发布本卡文件。业务链的跨仓再验交给 ROOT。

在本目录交 handoff.md（含一段 JSON），字段如下。记录实际事实，尚未运行的现场测试写明条件。git status 逐路径区分开工遗留和本卡变化，测试临时目录在采集必要证据后恢复原样。不要提交运行目录、整份业务产物或调试副本。

~~~json
{"lane":"FB-SID","owner":"<owner>","base":"<开工 SHA>","reviewed_commit":"<最终受审源码 SHA>","published_commit":"<实际发布 SHA 或本地说明>","status":"<完成或具体缺口>","tests":[{"command":"<定向命令>","result":"<通过数/失败/跳过及原因>"}],"native_refs":["<原生收据或测试标识>"],"sample_refs":["<可重放的观察样本>"],"review":"<独审范围/版本/复验和余项>","cleanup":"<仅本轮临时目录及结果>","remaining":["<组合验收归属>"]}
~~~
