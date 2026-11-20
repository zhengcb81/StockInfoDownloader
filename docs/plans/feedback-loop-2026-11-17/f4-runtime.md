# StockInfoDLSimple 的 F4 本机运行

## 入口和职责

发布基线为 `v2-clean-rewrite@4796a871`。CWP 的已发布 CN 路由使用 `stockinfo-cninfo/1.3.0`。本卡仅修改 SID 仓的发现反馈和本机公开端口，正常发现、暂存、原件验证以及下载限额继续按既有协议执行。总控拥有宿主配置和跨仓组合验收。

本次覆盖的问题是 `verified-candidate-id-missing` 的其中一种根因：公告在 SID 已持有的候选对象里有真实的证券代码，但同一对象序列化时丢了该字段。过去原生记录可定位偏差，而保存的观察无法证明原对象里的值或重建原输出。现在先从同一份真实输出判断，再将原输出、所属发生和原对象已检验的身份保存为一条证据。修理只恢复这一个字段。多个偏差合并在同一个发现步骤、原生字段也缺失、证券市场不匹配或旧现场缺少可验原记录时，等待更完整的证据。

## 宿主接线

工作目录使用发布后的 SID checkout，Python 使用可启动该仓的正常宿主运行时。下列固定命令中的数据库、旁路目录是部署专用的绝对路径：

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
