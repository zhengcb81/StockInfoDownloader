# StockInfoDLSimple 的 F4 本机运行

**2026-11-23 当前施工入口**为[直启任务清单与失败复原](F4-SID-START-INPUT.md)，交付见[独立交接](F4-SID-START-INPUT-handoff.md)。此前 **2026-11-21 的施工入口**是[下载失败记录防丢与普通任务结算](F4-SID-FAILURES.md)。后者以普通 CLI 的原生失败为起点，覆盖两条已经登记的 F4 发生。下文保留原运行端口与此前验收范围。

## 普通直启的输入合同与结算词汇（F4-SID-START-INPUT）

普通直启 `main.py` 的输入来源只在 `plan_work` 一处决策，优先级沿用 README 既有合同：

```text
CLI stock_code > --companies 文件 > config.test_cases > config.companies > config.stock_code > 无输入
```

- **来源"已指定"的判据是至少含一项。** 配置读取默认注入的空 `companies`/`test_cases`（以及合并后无法区分的显式空列表）不参与遮蔽：空 `test_cases` 让位于非空 `companies`，两者皆空时落到 `stock_code`。
- **只有显式 `--companies` 才触发名单读取**，读取发生在任何派发之前。文件不存在或不可读（原生 OS 错误、解码错误）统一为带原生 `__cause__` 的 `ConfigError`。
- **五类结果各自的公开词汇**（`ordinary-run-settlement` 的 `actual`，明细在同名 `.details.jsonl`）：

| 情形 | 退出 | `actual` | `disposition` | 明细要点 |
|---|---|---|---|---|
| 名单读取失败（含配置读取失败） | 1 | `not_started` | `expected` | `stage`=`companies`/`config`，`cause_chain` 原生类型链，`attempted`=0，`sent`=`not_sent` |
| 显式空工作项 / 无输入 | 0 | `no_tasks` | `expected` | `attempted`=0，`skipped`=0，`sent`=`not_sent` |
| 合法全跳过 | 0 | `all_completed` | `expected` | `attempted`=0，`skipped`=N，`sent`=`not_sent` |
| 供应商返回零候选 | 0 | `all_completed` | `expected` | 任务确已启动：`attempted`≥1，无 `sent` 键（费用保持未知） |
| 实际失败 | 1 | `all_failed` / `partial` | `deviation` | `attempted`=`succeeded`+`failed`，无 `sent` 键 |

`attempted` 只统计真正启动的子项（每个公司或每个测试用例一次），由 `UnifiedRunner.settlement` 这一份业务台账同时驱动退出码和发布内容。

- **冷读**：`src.feedback_owner reconcile` 对 `no_tasks` 返回 `job_status=succeeded`、`status=known`、`cost_state=not_applicable`；对 `not_started` 返回 `job_status=failed` 且费用不适用；对已启动的运行保持 `cost_unknown`。`no_tasks` 是对 `SUCCEEDED` 词汇的纯新增。
- 显式空名单不再写 `logs/progress.json`；无输入的启动退出 0 并如实报告 `No tasks to run`，不再是 `All tasks completed`。

## 入口和职责

发布基线为 `v2-clean-rewrite@4796a871`。CWP 的已发布 CN 路由使用 `stockinfo-cninfo/1.3.0`。本卡仅修改 SID 仓的发现反馈和本机公开端口，正常发现、暂存、原件验证以及下载限额继续按既有协议执行。总控拥有宿主配置和跨仓组合验收。

本次覆盖的问题是 `verified-candidate-id-missing` 的其中一种根因：公告在 SID 已持有的候选对象里有真实的证券代码，但同一对象序列化时丢了该字段。过去原生记录可定位偏差，而保存的观察无法证明原对象里的值或重建原输出。现在先从同一份真实输出判断，再将原输出、所属发生和原对象已检验的身份保存为一条证据。修理只恢复这一个字段。多个偏差合并在同一个发现步骤、原生字段也缺失、证券市场不匹配或旧现场缺少可验原记录时，等待更完整的证据。

## 宿主接线

工作目录使用发布后的 SID checkout，Python 使用可启动该仓的正常宿主运行时。下列命令使用部署专用的绝对路径。现有 `--sidecar-dir` 保持兼容，组合恢复时对旧监督目录和直启收件目录各传一次。默认原生收件目录和最新契约见 [F4-SID-FAILURES 交接 §9](F4-SID-FAILURES-handoff.md#9-root-独立接收与最终候选)。

```text
<python> -B -m src.feedback_owner --db <owner-db> --sidecar-dir <native-sidecars> triage
<python> -B -m src.feedback_owner --db <owner-db> --sidecar-dir <native-sidecars> repair
<python> -B -m src.feedback_owner --db <owner-db> --sidecar-dir <native-sidecars> replay
<python> -B -m src.feedback_owner --db <owner-db> --sidecar-dir <native-sidecars> report
<python> -B -m src.feedback_owner --db <owner-db> --sidecar-dir <native-sidecars> reconcile
<python> -B -m src.feedback_owner --db <owner-db> --sidecar-dir <native-sidecars> get-action <action-id>
<python> -B -m src.feedback_owner --db <owner-db> --sidecar-dir <native-sidecars> get-publication <repair-action-id>
```

- 生产继续调用 `python -m src.company_wiki_adapter_cli discover --config <原配置>`。总控在每次 invocation 传入唯一的绝对 `RESEARCH_FEEDBACK_OUT`，在同一运行内提供稳定且区分尝试的 `RESEARCH_FEEDBACK_RUN_ID` 和 `RESEARCH_FEEDBACK_ATTEMPT_ID`。`--sidecar-dir` 只放本仓可信的原始 JSONL。运行收据分散时可用重复的 `--sidecar <file>` 作显式配置。
- 支持的发现偏差只保留一条公告候选、原生代码、公告号、观察身份和数据摘要。正常发现不创建捕获文件，原输出仍按既有方式返回。默认证据在原 JSONL 同级的 `.sid-candidate-captures`；另设目录时，生产进程用绝对 `RESEARCH_FEEDBACK_SID_CAPTURE_DIR`，本端口用同一绝对 `--capture-dir`。整个 HTTP 响应、头或 cookie 不归入捕获。不可辨别的 URL 查询参数不进入捕获。
- 已提交与恢复沿用总控协议 `owner-json`。四个动作经 stdin 接收 `feedback-action/1`，使用相同的 `lookup_argv`（上述 `get-action`，由宿主追加 action ID）。`reconcile` 只按原始 owner、run、attempt、step 和声明版本核对。相邻尝试的成功不代表原尝试成功。历史费用不足以核算时保持未知。
- 修复将候选和内容版本原子登记在 SID SQLite。同一动作重放拿到原回执，不启动新的发现和下载。独立核对时用 `get-publication` 读已落盘的候选，再与原发现范围和正常输出比对。本仓复验会从原侧车和证据重建候选来对照同一发布。回告必须匹配该复验版本和证据。路径与命令由可信宿主配置供应，观察仅含不透明引用。

## 回归命令和收据

- 使用 `C:/Miniconda/python.exe -B -m pytest -q` 运行新 `tests/unit/test_feedback_owner.py` 及原观察、适配器、预算、运行包、CNINFO provider 与旧下载契约，共 **147 项通过**（14.61 秒）。
- 以 `G4_CWP_COMMIT=7e0ecebb01096e202d5ec11847cd28e927edf4c9` 指定对照 CWP 路由，再以 `--basetemp=<本次短测试目录>` 运行 `tests/e2e/test_g4_latest_cli_offline.py`，共 **17 项通过**（34.23 秒）。第一次执行有 4 项在 Windows 解包夹具阶段失败。测试自建临时目录忽略了 pytest 的短路径设置，修复后沿用 pytest 分配目录，原断言全部通过。

- RED 使用保留的比亚迪 FY2024 公告行和原 F2 已知缺失字段案例，经 SID 公开 CLI 顺序跑正常、复现故障。现有行为缺少绑定至同一观察的证据，断言 `evidence_ref` 失败。
- GREEN 在发现传输边界回放留存公告，注入旧序列化遗漏。复验在相同原数据上进行。缺原生代码和异股对照继续由原提供方逻辑跳过。比较原始正常候选与持久化修复候选的全部字段。无法写捕获、多项偏差、原捕获缺失/更改、不同 attempt 和不透明 URL 查询均有负对照。
- 中断检查用真实单独进程 `os._exit`。发现的原作业只有 started 时，相邻的成功保持独立。原修理或回告在提交 SQLite 后、答复 stdout 前退出时，以同一 action ID 读回。重复消费仍只有分诊、修理、复验、回告各一条记录，原采集计数没有增加。
- 所有回放、运行数据库和收据均位于隔离测试目录，未下载原件或访问付费服务。当前交付完成本仓实现与原生回归。总控在自己的测试环境独立配置同一受支持路径，验证宿主中断及恢复后再记录上线。
