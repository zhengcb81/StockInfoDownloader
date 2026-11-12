# MB-SID — 逐条合规对照

对照对象：`inputs/MB-SID.md`（本卡）+ `inputs/handoff_contract.md`（交接格式）。
状态口径：**PASS** 已按要求完成；**PASS\*** 完成但形式与原话有偏离（附理由）；**FIXED** 初版遗漏、本轮已补；**OPEN** 仍缺，交 ROOT。

## A. A0 接收

| # | 要求原文要点 | 状态 | 证据 / 说明 |
|---|---|---|---|
| A1 | 先读 `reconciliation.md` 与 `acquisition_review.md` §4 SID 逐文件表 | PASS | 两个文件都读过；§4.3/§4.4 的 11 文件表与 3 个 untracked 项逐一对照 |
| A2 | 保留输入精确 11 路径 | PASS | `f593535` 原样应用 11 文件 patch（743+/94-），未增删路径 |
| A3 | 额外 `scripts/capture_byd_fy2024_fixture.py` 保留到测试工具/说明，不执行成新公司特判采集 | **FIXED** | 初版只归档到 company-wiki，未进交付树。现已在 `scripts/` 接收，加 A0 说明头 + `scripts/README.md` 标明 `NO_RUNTIME_REFERENCE`；逻辑未改（哈希仍 `86ad034f…`） |
| A4 | 公司名单是用户输入，保留；原件/运行 config 不动 | PASS | 名单留在原工区，未入库；只记哈希 |
| A5 | 先写行为 RED，允许增加 legacy 模块与测试 | PASS\* | 先写测试，但基线首跑多为缺符号，**真实行为 RED 以 checkpoint `f593535` 那次为准**（24 failed，其中 5 条是行为缺陷）；两次日志都在 `evidence/` |
| A6 | gap1：同实例先 CONFIRMED_EMPTY 再换公司/期次，第二请求必须重新取得状态；不可只预置私有属性 | PASS\* | 状态移到 `DownloadRequest.confirmed_empty`（公开可选字段），实例不再保存空结果；三条连续请求用例。**偏离**：仍未接真实 API 生产者，属"公开输入契约"而非"已接好 API"，已在 findings 列为残余风险 |
| A7 | gap2：目录按组件匹配，POSIX/Windows 大小写分隔符，`prospectus` vs `prospectus-extra` | PASS | `_subdir_components`/`_path_is_within_subdir`；8 条用例含 POSIX/Windows/反斜杠/兄弟目录/前缀/`..`/绝对路径 |
| A8 | gap3：空活动页签不得退回整页下载其他类型/期次；测真实 DOM 行为，不查源码字符串 | PASS\* | 用假页面模型（菜单/选中/每页签链接）断言"下载了哪些链接"；未知 suffix 抛错、点击未生效 fail-closed、菜单缺失 fail-closed。**偏离**：不是真实 DOM 快照，可见性判据（`offsetParent`）仍待真页确认 |
| A9 | gap4：stdout 只有协议结果，诊断走 stderr；配置/CLI/业务模型兼容；不真实下载；不拿旧 139 测试数字 | PASS | 新进程日志测试 + CLI 失败通道测试；README 删除 139 与固定测试数；E2E 未运行 |
| A10 | 通用改进分成可回退小提交 | PASS | 10 个提交，按 gap/模块拆分，每个可单独 revert |
| A11 | 完成 SID-01 typed 错误、SID-02 纯 metadata 边界 | PASS | 见 C 段 |
| A12 | C 阶段集中跑受影响 unit/协议测试与独审 | PASS | 两轮独立审查 + 全量 unit |
| A13 | 可选真实采集只在确有需求时由 ROOT 安排 | PASS | 0 次真实采集 |
| A14 | 旧 WIP 原工区在 ROOT 确认等价接收后才清理 | PASS | 原工区 11 modified / 743+94- 未变 |
| A15 | SID G4 三份 PWF 镜像先保留唯一历史说明再回收 | **FIXED** | 初版未做。现原字节归档到 `history/g4-sid-latest/`（哈希逐一复核），写 README 说明，然后 `worktree remove --force` + `prune`；`git worktree list` 已无该工区 |

## B. 工区与流程

| # | 要求 | 状态 | 证据 |
|---|---|---|---|
| B1 | 原仓/基线 `c0f07e12`/目标 `v2-clean-rewrite` | PASS | `git log` 首提交父为 `c0f07e12` |
| B2 | 新工区 `mb11-sid`，分支 `codex/mb11-sid` | PASS | `git worktree list` |
| B3 | PWF 先建 `task_plan/findings/progress`，复制卡与公共接口说明到 inputs | PASS\* | 文件齐全、内容记录真实基线与工作量；**偏离**：实际是边做边补，不是开工前先建（进度与决策没有因此丢失，时间线在 `progress.md`） |
| B4 | 开工只需读本卡 + interfaces/acceptance/runtime_verification + 本仓 AGENTS | PASS\* | 前三者已读；**本仓没有 `AGENTS.md`**（`ls` 无此文件），无可读内容，已在 handoff 记录 |
| B5 | 不 reset、不清别人工区、不接管未知工区 | PASS | 未对任何既有工区做 reset/clean；G4 回收走 `worktree remove` 且有归档 |
| B6 | 用仓库实际可用的 Python/离线依赖，不重新抓原件、不部署全局技能 | PASS | `C:\Miniconda\python` 3.13.9；0 次抓取；未部署 |

## C. 共用完成规则

| # | 要求 | 状态 | 证据 |
|---|---|---|---|
| C1 | 先列活动入口/逻辑模块/公开面/状态 owner/依赖方向，含兼容/退休分类 | **FIXED** | 初版只在 findings 零散提及。现 `runtime_inventory.md` 给出 4 个入口、20 个模块、依赖图、5 类分类、包边界 |
| C2 | 保留现有公开协议；各模块只写自己代码和状态 | PASS | JSON 1.0 结构未变；预算/进度/缓存各自 owner；adapter 不决定 canonical 路径 |
| C3 | 公开协议真需改时先交 ROOT 协调 | PASS\* | 只做了**追加可选字段**（`DownloadRequest.confirmed_empty`、`DownloadResult.verification`），未改必需字段/schema major；已在 handoff §3 明示，未擅自改邻仓 |
| C4 | A 写行为/隔离测试 → B 修 owner 根因 → C 验收 | PASS | 每项都有 RED→GREEN→证据 |
| C5 | 负例体现真实能力/依赖错误；fixture/缺依赖/沙箱失败不冒产品 RED | PASS | 基线缺符号那轮明确标注"不作为产品 RED"，行为 RED 引用 checkpoint 那轮 |
| C6 | 交付前独立审查，修完复核；范围外发现列给 ROOT | PASS | 两轮审查；`review.md`；`out_of_scope_findings` 5 条 |
| C7 | 新临时目录、恢复初始状态；生产原件/配置/既有 WIP 不动；不每小步全量；不删断言换绿 | PASS | 全部 `tmp_path`；原工区未变；只在节点跑全量；被替换的断言都改成更严的 typed 断言（`TestVerifyDownloads` 10 条场景全保留） |
| C8 | 提交推送交付分支；不自行合并主线；不改 ROOT 总 PWF | PASS | 已推送 `origin/codex/mb11-sid`；未合并；未改 company-wiki |
| C9 | 交付 handoff.md/json、独审报告、测试/恢复证据索引 | PASS | 四者齐全 |

## D. 写集合

| # | 要求 | 状态 | 说明 |
|---|---|---|---|
| D1 | provider 四文件 + 两个新测试 | PASS | `company_wiki_adapter.py`、`company_wiki_adapter_cli.py`、`cninfo_api.py`、`cninfo_report_metadata.py`；`test_provider_error_contract.py`、`test_provider_dependency_direction.py` |
| D2 | A0 允许增加 legacy browser/downloader/日志/映射/命令模块与测试 | PASS | 均在 A0 授权内 |
| D3 | 本仓 PWF 与最小引用文档可写 | PASS | `docs/plans/mb11-sid-2026-11-11/**`、README、`config_template.json`、`.gitignore` |
| D4 | 不得写原工区 11 项 WIP、生产 config/cache/canonical、CWP/FF/Dayu | PASS | 未触碰 |
| D5 | 纯 metadata 模块不依赖 browser/downloader 上层 | PASS | 子进程 import-blocker 证明 |

**写集合外的偏差（需 ROOT 知晓）**：

1. `tests/unit/test_provider_runtime_artifact.py` —— 卡的字面写集合只列了两个新 provider 测试，但 C 段"组合"要求验证隔离 runtime，本卡把它固化成可重复测试。属**新增测试文件**，未改任何生产面。若 ROOT 认为超出，可只保留其 manifest 常量而删测试。
2. `scripts/`、`scripts/README.md` —— A0 明确要求接收 fixture 脚本，属授权范围。
3. `.gitignore` 增加 `!docs/plans/**/*.json|log` —— 为让 PWF 证据能入库；只影响本仓忽略规则。

## E. A/B/C 与测试

| # | 要求 | 状态 | 证据 |
|---|---|---|---|
| E1 | 三个非 retryable + 一个真 timeout，全部经公开 CLI 验证 code/retryable/usage | PASS | `test_provider_error_contract.py` 9 条；RED 在 `evidence/red-provider.log` |
| E2 | API 纯读取/过滤在拒绝 import adapter/browser/downloader 的子进程仍工作；用年/半年/季报/类型/期间 fixture 锁语义 | **FIXED** | 初版只用了 BYD 年报 fixture。现补 `exact_legacy_year` / `semi_annual_visible` / `quarterly_cutover` 三条真实过滤（含 Q3/FY2026 在 as-of 之后被排除），全部在 import-blocker 子进程内跑 |
| E3 | GREEN：typed cause 全链；usage 不丢、unknown 不写 0；`_report_metadata` 移入纯域，API/adapter 共用，旧兼容只在 adapter 侧重导出 | PASS | `test_api_and_adapter_share_the_exact_same_function`；无预算时不出现 `acquisition_usage` |
| E4 | 组合：临时 runtime + 公开 CLI + 本地 HTTP；只写 staging；`.part` 清理；hash/receipt 一致；无 CWP 内部库/浏览器 | PASS | `test_provider_runtime_artifact.py` 3 条 |
| E5 | 独立审查全部变化与测试，修完交付；两部分分提交、同一节点验收 | PASS | checkpoint `f593535` + provider `6b2fd0b` 分属两部分；审查记录在 `review.md` |
| E6 | 卡内两条测试命令 | PASS | 56 passed / 12.58s；21 passed / 1.97s（补 fixture 后仍为 21，因新增 3 条在依赖文件内） |

## F. 出口

| # | 要求 | 状态 |
|---|---|---|
| F1 | API→domain←adapter 单向 | PASS（子进程探针） |
| F2 | 错误类别/可重试性/计量贯通 | PASS |
| F3 | staging-only / 预算 / 旧入口无退化 | PASS（budget 7+5 条、artifact 3 条、legacy 73 条） |
| F4 | 独审通过 | PASS（第二轮 PASS） |
| F5 | 目标分支与现有 owner WIP 关系在 handoff 清楚 | PASS（handoff §1/§6/§7） |

## G. handoff_contract 对照

| # | 要求 | 状态 | 位置 |
|---|---|---|---|
| G1 | 基线、最终 commit/branch/remote、目标主线、实际 diff 文件表 | PASS | handoff §1（另记 `docs_commit` 区分代码与文档） |
| G2 | 每项卡要求：根因、先红、修复归属、兼容、证明；无改动项 NO_CHANGE_PROVEN | PASS | handoff §2（本卡无"无改动"项，故无 NO_CHANGE_PROVEN） |
| G3 | 公开接口变化（默认 none）、兼容方式、ROOT 消费的 fixture 路径与执行命令 | **FIXED** | 初版缺"执行命令"。现补：ROOT 用 `python -m pytest tests/unit/test_provider_runtime_artifact.py -q` 复跑 manifest，fixture 路径已列 |
| G4 | 实际测试：命令/版本/退出码/pass/fail/skip/耗时/未执行原因/日志 | PASS | handoff §4 + `evidence/` |
| G5 | 独立审查：agent、范围、发现、修复 commit、复核 | PASS | handoff §5 + `review.md` |
| G6 | 隔离恢复：目录初末状态、原件/WIP 未变、网络/模型调用数、费用 unknown、清理归属 | PASS | handoff §6（网络 1 次已如实记录，非伪造 0） |
| G7 | 安装/部署/CI/合并分开；ROOT 下一步一条可执行命令与输入 | PASS | handoff §7 |
| G8 | handoff.json 字段完整，未知填 null 并解释 | PASS | 8 个 requirements、`network_calls: 1`、`model_calls: 0` |

## 结论

- 初版有 **5 处未做到位**：fixture 脚本未入交付树、G4 镜像未归档回收、缺 runtime 清单、依赖探针缺半年/季报过滤、handoff 缺 ROOT 消费命令。**本轮已全部补齐**。
- 仍有 **2 处形式偏离**，不属于可自行消除的缺陷：真实页签 DOM 未抓取（需 ROOT 决定是否安排真实采集）；`confirmed_empty` 尚无生产生产者（需接 API 层）。
- 另有 **1 处写集合外新增**（`test_provider_runtime_artifact.py`），已在 handoff 与本节明示，等 ROOT 判断保留或裁剪。
