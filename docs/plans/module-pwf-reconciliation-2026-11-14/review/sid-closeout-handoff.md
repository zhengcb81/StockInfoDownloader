# SID-PLAN-WORKTREE-CLOSEOUT — 交接（handoff）

**Lane**：SID · **日期**：2026-11-14 · **场景**：日常开发（scene#54）
**Owner / 唯一写入仓**：`C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite`
**canonical PWF**：`docs/plans/mb11-sid-2026-11-11/task_plan.md` 顶部「SID 唯一当前状态入口」段
**交付落点**：`docs/plans/module-pwf-reconciliation-2026-11-14/review/sid-closeout-handoff.md`、`sid-closeout-handoff.json`、`sid-closeout-review.md`。
> 路径归属说明：卡要求「只在本卡唯一写入仓做文件和 Git 修改」「不要写到其他仓」，因此该相对路径解析为**本 SID 仓内**目录（本次新建），而不是 `company-wiki` 总控计划下的同名目录；ROOT 可跨仓只读本目录。三文件不与其它 lane 共用路径。

## 1. 实时 Git 基线

| 项 | 值 |
|---|---|
| 目标主线（实时确认，非 `main`） | `v2-clean-rewrite` |
| base branch / HEAD | `v2-clean-rewrite` / `d084c4aab48f5f83275f65982bf561e6870ff3a4` |
| base remote HEAD | `d084c4aab48f5f83275f65982bf561e6870ff3a4`，由 `git ls-remote origin refs/heads/v2-clean-rewrite` 实测，与本地一致 |
| 卡片快照差异 | 无：`v2-clean-rewrite@d084c4a` = origin；3 个注册 worktree；0 个 non-ancestor refs；tracked clean、两份未跟踪用户名单均与快照一致。未回滚任何新工作 |
| 候选最终 HEAD（首轮独审绑定） | `2fd2294b387807b2031528120723ba7c90920470`（`docs(sid): converge canonical PWF…`；独立 reviewer 首轮按此 HEAD 审查，判 CHANGES REQUIRED）。**该提交从未成为远端 HEAD** |
| final branch / HEAD（经复核并发布的最终内容提交） | `v2-clean-rewrite` / `73f436942e03df9276e1416f7771f29b26942876`（修复项提交，reviewer 复核 PASS 后推送） |
| final remote HEAD | `73f436942e03df9276e1416f7771f29b26942876`，`git push origin v2-clean-rewrite` 后由 `git ls-remote` 实测与本地一致。**本次清单对照修订提交（本文件所在提交）推送后，远端 HEAD 即为该修订提交**；当前远端以 `git ls-remote origin refs/heads/v2-clean-rewrite` 为唯一准据，见 §11 |
| 独审复核绑定 HEAD | `73f436942e03df9276e1416f7771f29b26942876`（修复复核后的最终 PASS；首轮绑定 `2fd2294…`）。`handoff.json` 的 `independent_review.reviewed_head` 按卡措辞保留首轮候选 HEAD |
| remote | `origin https://github.com/zhengcb81/StockInfoDownloader.git`（有 remote，非「无 remote」情形） |
| tracked | clean |
| 未跟踪例外 | `a_share_companies.txt`（3,898 B）、`companies.txt`（137 B）——用户公司名单，**原样保留**，未 add / 未删除 / 未改写 |
| refs | 7 个本地分支（`codex/*` 6 个 + `v2-clean-rewrite` 主分支）：`v2-clean-rewrite`、`codex/g4-main-sid@0cb3c1f`、`codex/g4-sid-latest@201a8f0`、`codex/g5-sid-runtime@47e1059`、`codex/cninfo-bounded-budget@8ed5fdd`、`codex/mb11-sid@a967913`、`codex/root-mb11-sid-integration-20261113@53b9358`；逐一 `git merge-base --is-ancestor` 全部为 HEAD 祖先，0 个 non-ancestor refs |
| 在途改动 | 无；本卡写集合与其它 owner 无重叠，无 `UNCLASSIFIED_HOLD` 冲突需要协调 |

## 2. PWF 收敛与 G4/G5 状态校正

- 把 `docs/plans/mb11-sid-2026-11-11/task_plan.md` 固定为 SID **唯一** canonical 状态入口：顶部写明实时主线/HEAD/remote、已完成收据、工区逐项处置、唯一下一步与 CWP/FF 公开 wire 依赖；旧 `Next Step: 无` 明确标为历史记录且回指顶部。
- 同目录 6 个 MD、`.planning/g5-sid-runtime/` 5 个 MD、`docs/implementation/g4-sid-latest/` 4 个 MD 共 **15 个历史证据/子计划**各加一行「状态入口」回链 banner，标明历史状态不是当前状态、不另建第二个 START_HERE；未删除任何历史 handoff、evidence、inputs 或 compliance 材料。
- **G4 旧待办「主线待做 1.3.0 路由升级」= SUPERSEDED（已完成）**，逐项收据：
  1. 主线源码 `src/company_wiki_adapter.py:30` `ADAPTER_VERSION = "1.3.0"`，`src/company_wiki_adapter_cli.py` 成功/失败 JSON 均输出 `{"name":"stockinfo-cninfo","version":"1.3.0"}`；
  2. 主线测试 `tests/unit/test_g4_latest_discovery.py`、`tests/unit/test_company_wiki_adapter.py`、`tests/e2e/test_g4_latest_cli_offline.py`、`tests/e2e/test_g5_browserless_provider.py` 断言 1.3.0；
  3. `eb8495ceb76892ff6f4a95889b6a19f0a78d769c`（G4 已发布代码）是 HEAD 祖先；`MAIN_ACCEPTANCE.md` 记 127 passed / 27.02s 与 CWP route `df7d7ba58955e224c1799355f479ad5378ef38a7` 已提交；
  4. 只读核对邻仓 `company-wiki@7361aad82` 的 `config/source_acquisition.yaml:9` = `version: 1.3.0`（**未写入邻仓**）。
  G4 `HANDOFF.md` §10 第 1 项与 `task_plan.md` 的 "MAIN owns the 1.3.0 route bump" 均为交付时点陈述，本卡把其标为 superseded，不作为 SID 待办。
- **G5**：`codex/g5-sid-runtime@47e1059` 为 HEAD 祖先；`src/cninfo_identity.py`、`src/disclosure_matching.py`、`tests/unit/test_g5_provider_runtime.py`、`tests/e2e/test_g5_browserless_provider.py` 与 `.planning/g5-sid-runtime/` 12 个 PWF/evidence 文件都在 HEAD 树内；`git diff codex/g5-sid-runtime..HEAD` 仅剩 MB11 后续改动 → `ABSORBED`，其「等 MAIN 合并」历史 Next Step 不再有效。清单对照复核时补读了卡第 5 行列出的 `.planning/g5-sid-runtime/handoff.json`：`schema_version=g5-handoff/1`、`delivery_status=ready_for_main`、`public_contracts` 明确 `stockinfo-cninfo/1.3.0 unchanged`、`remaining` 中「本次未推远端分支／合推由 MAIN 执行」为交付时点陈述；与「分支已是主线祖先、wire 未变」结论一致，不改变任何处置。
- **MB11**：`a967913` / `53b9358` 为 HEAD 祖先，`6742eda`、`d084c4a` 为收尾提交；`tests/unit` 340 passed / 0 failed，`review.md` 最终复核 PASS → `MERGED / CLOSED`。

## 3. 逐项处置（branch / worktree / Projects 目录）

| kind | path | status | reason | evidence |
|---|---|---|---|---|
| branch | `refs/heads/v2-clean-rewrite` | `ACTIVE_KEEP` | 目标主线，唯一长期主仓 | `git rev-parse HEAD` = `d084c4a…` |
| branch | 6 个 `codex/*` refs（含 g4/g5/mb11/bounded-budget） | `ABSORBED` | 全部是 HEAD 祖先，作为交付/集成证据保留，不删 ref | 逐个 `git merge-base --is-ancestor` 退出码 0；`git for-each-ref` |
| worktree | `Projects/StockInfoDLSimple/v2-clean-rewrite` | `ACTIVE_KEEP` | 主工区；含用户名单、`downloads/` 真实返回数据、MB11/G4/G5 全部证据 | `git worktree list`；`git status --porcelain -uall` |
| worktree | `Projects/_g5/sid`（`codex/g5-sid-runtime@47e1059`） | `DELETE_AFTER_OWNER_CONFIRMATION` | 已结案、clean、可重建：tracked 内容与 12 个 G5 PWF 文件全在 HEAD；ignored 仅 `.mypy_cache`/`.ruff_cache` 可重建缓存；无运行时配置引用；分支保留可 `git worktree add` 重建 | `git -C … status --porcelain --ignored` 仅两条 `!!`；`git diff --stat codex/g5-sid-runtime..HEAD`；主仓 `config*.json` 与 CWP `config/` 均无该路径引用；见 §5 收据 |
| worktree | `Projects/StockInfoDLSimple/cwp-cninfo-bounded-budget`（`codex/cninfo-bounded-budget@8ed5fdd`） | `EVIDENCE_KEEP` | G4 基线 `8ed5fdd` 的物理现场；clean，含 6 份 e2e 真实 PDF 与运行态 `logs/progress.json`、`src/stock_orgid_mapping.json`；名称涉及 CWP 面向任务，按卡规不以「已吸收/可重建/名字像临时」单独判删，保守保留 | `git -C … status --porcelain --ignored`；`git ls-tree -r HEAD` 含同 6 份 PDF；目录 87 文件 / 19,422,917 B |
| dir | `Projects/StockInfoDLSimple/lineage-cleanup-backup-20261004` | `EVIDENCE_KEEP` | 唯一回滚/审计材料：85,874 B `staged_1_1_0_index.patch`、3,610 B `am_unstaged_edits.patch`、20,179 B 未入任何 commit 的 pre-budget `cninfo_api.py`、`status_before.txt`、README；README 明确要求勿移入仓内 | 目录 5 文件 / 116,155 B；README「完整恢复步骤」 |
| dir | `Projects/StockInfoDLSimple/logs`（`progress.json`） | `UNCLASSIFIED_HOLD` | 运行态进度，归属未查清，原样保留 | 1 文件 / 175 B |
| file | `Projects/StockInfoDLSimple/nul` | `UNCLASSIFIED_HOLD` | 名称可疑但内容/用途未查清；按卡规不以名字推断可删 | 1 文件 / 893 B |
| dir | 容器隐藏工具目录 `.claude`/`.codegraph`/`.mimocode`/`.ruff_cache`/`.benchmarks` | `UNCLASSIFIED_HOLD` | 外部工具状态，非 SID owner 归属；合计 3,467 文件 / 53,148,299 B，原样保留 | 逐目录 `find`/`du -sb` |
| file | 主仓 `a_share_companies.txt`、`companies.txt` | `EVIDENCE_KEEP` | 用户公司名单，卡明确要求保留 | 3,898 B + 137 B，`git status` 仍为 `??` |
| dir | 主仓 `downloads/`（1.58 GB）、`logs/`、`end2end_test/` | `EVIDENCE_KEEP` | 真实返回数据/运行日志/唯一 e2e 证据，未纳入清理 | `du -sb`：1,578,575,618 B / 34,464,255 B / 18,947,517 B |

`DELETE_AFTER_OWNER_CONFIRMATION` 的 owner 判定：该工区是**本 SID 仓 `.git/worktrees` 注册**、挂在 SID 本地分支 `codex/g5-sid-runtime` 上，PWF 为 `.planning/g5-sid-runtime/`（已随主线提交），不属于其它 owner，因此由 SID owner 依收据结案；`cwp-cninfo-bounded-budget` 因跨模块语义保守保留，未套用该结论。

## 4. 未提交例外

- `a_share_companies.txt`、`companies.txt`：用户名单，保留，未跟踪状态不变。
- 主仓 ignored 运行态（`.pytest_cache/`、`__pycache__/`、`downloads/`、`logs/`、`e2e_official_report*.json`、`src/stock_orgid_mapping.json` 等）：均为真实数据/缓存，保留。
- 被移除的 `_g5/sid` 中 ignored 内容仅 `.mypy_cache/`（599 文件 / 21,703,613 B）与 `.ruff_cache/`（5 文件 / 741 B），为可重建工具缓存；tracked 内容全部已在主线，无唯一内容损失。

## 5. 精确清理收据

| path | file_count | bytes | 动作 | 可恢复依据 |
|---|---:|---:|---|---|
| `C:/Users/郑曾波/Projects/_g5/sid` | 713 | 41,315,535 | `git worktree remove <path>`（未用通配删除、未触碰同级 `_g5/rf`） | 分支 `codex/g5-sid-runtime@47e1059` 保留；`git worktree add <path> codex/g5-sid-runtime` 可重建全部 tracked 内容；主线已含 12 个 G5 PWF/evidence 文件 |

清理前：`git worktree list` 3 条、`status --porcelain --ignored` 仅两条缓存；清理后：`git worktree list` 2 条（主仓 + `cwp-cninfo-bounded-budget`），`codex/g5-sid-runtime` ref 仍在，路径已不存在。其余 Projects 目录全部保留，无其它删除。

## 6. 测试与检查

本次为**纯文档/PWF 收尾**（未改 `src/`、`tests/` 或任何产品代码），按卡规定做 JSON / link / `git diff --check` 检查，不重复跑产品全量测试；主线代码正确性沿用已提交的 MB11 340 passed、G4 127 passed、G5 163 passed 收据。

| command | result |
|---|---|
| `python -X utf8 -c "json.load(...)"` 校验 `sid-closeout-handoff.json` 为裸 JSON、`schema_version=1`、13 个固定顶层键与全部子字段 | **PASS**：裸 JSON 可解析（无 BOM / 无 Markdown 围栏），顶层键顺序精确一致，`base/final` 含 `branch/head/remote_head`，`dispositions` 每项含 5 字段，`cleanup` 含 3 字段，`tests` 每项含 2 字段，`independent_review` 含 4 字段 |
| 相对 Markdown 链接解析（canonical PWF ↔ 三份交付文件、15 个历史 banner 回链） | **PASS**：35 个 MD 全量解析，**0 broken link**；独立 reviewer 亦复跑 |
| `git diff --check` | **PASS**：exit 0，无空白错误（工作区与 `d084c4a..HEAD` 均复跑） |
| `git diff --name-only d084c4a..HEAD -- src tests main.py` | **PASS（空）**：全程纯文档/PWF，无产品代码改动，故按卡不重复跑产品全量回归 |
| `git status --porcelain -uall` | **PASS**：仅 `?? a_share_companies.txt`、`?? companies.txt` 两份用户名单，tracked clean |
| `git worktree list` / `git for-each-ref` / 逐个 `git merge-base --is-ancestor` / `git show-ref --verify refs/heads/codex/g5-sid-runtime` | **PASS**：3→2 worktree；7 个本地分支全为 HEAD 祖先、0 non-ancestor refs；被删工区分支 ref 仍在；逐项明细见 §3 与 `handoff.json.dispositions` |
| `git push origin v2-clean-rewrite` → `git ls-remote origin refs/heads/v2-clean-rewrite` | **PASS**：远端 = 本地 HEAD = `73f436942e03df9276e1416f7771f29b26942876`；清单对照修订提交推送后远端为本次修订提交，见 §1、§11 |

## 7. 独立审查

由**未参与实施**的另一名 agent/harness 审查完整变更与交接，结论绑定已提交的候选最终 HEAD；发现问题由 owner 修复、复测并提交新 HEAD 后复核。范围、绑定 HEAD、发现及关闭状态、最终 PASS/FAIL 记录在 `sid-closeout-review.md`，机器可读值在 `sid-closeout-handoff.json` 的 `independent_review`。

审查节点计数（卡第 19 行「只设这一个审查节点，必要修复后的复核除外」）：**一个最终大节点**，由同一独立 reviewer 完成 —— ① 对候选 HEAD `2fd2294…` 首轮 `CHANGES REQUIRED`；② owner 修复提交 `73f4369…` 后**必要修复复核** `PASS`；③ 用户后续要求「对照最初要求清单检查」，同一 reviewer 对清单对照修订提交再做一次只读合规复核（属同节点的延伸，未新增签收关卡，未引入新的 reviewer）。三次交互均为只读审查 + 仅写审查报告，未参与实施。

## 8. 剩余项

1. **G2-12**：`mode=latest_as_of` 目前只验收了元数据发现 + 受控 loopback fetch；FF → ET → CWP 下载→入库→复用链尚未贯通（属 MAIN/CWP/FF，非本卡写集）。
2. `cwp-cninfo-bounded-budget` 与 `lineage-cleanup-backup-20261004` 按 `EVIDENCE_KEEP` 保留；如后续 CWP/SID owner 出具「无唯一内容 + 无配置引用」的收据，可再评估清理，本卡不代其它 owner 决定。
3. 容器 `logs/`、`nul` 与隐藏工具目录为 `UNCLASSIFIED_HOLD`，待归属查清后再处置。
4. 父业务 goal `du11-source-closure-2026-10-18` 仍为 **paused**，本卡不自动恢复。

## 9. 唯一下一步

**推进 G2-12 完整单意图 latest ensure 链**：在本仓主线先跑 provider 相关回归（`tests/unit/test_g4_latest_discovery.py`、`tests/unit/test_g5_provider_runtime.py`、`tests/e2e/test_g4_latest_cli_offline.py`、`tests/e2e/test_g5_browserless_provider.py` 及完整 `tests/unit`），再由 ROOT 在 CWP 做一次有限公开接口组合验收；SID 只维护 `stockinfo-cninfo/1.3.0`、wire `schema_version=1.0`、共享 `ProviderAcquisitionBudget` 与 `discovery_incomplete`/`bounded_discovery_empty` 诚实 GAP 语义，跨仓差异只开 owner handoff，不直接改邻仓。

## 10. 边界声明

- 只在 `StockInfoDLSimple/v2-clean-rewrite` 做**产品文件与 Git 修改**；未对 `company-wiki`、`filing-fetch`、`revenue-forecast`、`earnings-transcripts`、`investment-dashboard`、`StockWiki`、`invest-quick-scan` 做任何 checkout / stage / restore / commit / merge / push / 删除 / 移动。
- **仓外写入的唯一例外（如实登记）**：WorkBuddy 会话工作日志 `C:/Users/郑曾波/Projects/StockInfoDLSimple/.workbuddy-ai/memory/2026-11-14.md` 位于容器根、SID 仓外，是环境要求的会话记忆文件（append-only 工作记录），不是产品文件、不是 Git 修改、不属任何 lane 的写集；未触碰其它模块仓。
- 对 CWP 仅做只读核对（`git rev-parse`、`grep config/source_acquisition.yaml`）；未改 CWP/FF 的 provider adapter。
- 未读取或复制任何密钥；未发起真实采集 / 付费 API / LLM 调用；未恢复 paused 的业务目标。

## 11. 清单对照复核记录（2026-11-14 16:36，用户要求）

按 `owner_cards/sid_closeout.md` 全文、`dispatch.md` §Owner 卡共用执行约定、`task_plan.md` §写入与交接规则逐条重核。**结论：核心要求全部满足，发现 6 处记录性缺陷，已全部关闭；`PASS` 保持。**

| ID | 级别 | 发现 | 对应要求 | 关闭动作 |
|---|---|---|---|---|
| R-01 | **P1 事实错误** | `handoff.json` 的 `final.head` / `final.remote_head` 曾填 `2fd2294…`，但该提交**从未成为远端 HEAD**（两个提交一次性推送，远端直接为 `73f4369…`）；`finalization_note` 中「该 HEAD 推送时经 `git ls-remote` 确认远端与之相等」与事实不符 | 卡第 17、18 行「base/final branch+HEAD、remote HEAD」 | 两值更正为 `73f436942e03df9276e1416f7771f29b26942876`；note 改写为完整提交链与自指约定说明；`handoff.md` §1 补明示 base / 候选 / final / 独审复核四个 HEAD |
| R-02 | **P1 事实错误** | `sid-closeout-review.md` §4/§5/§6 三处写「远端应等于已审候选最终 HEAD `2fd2294…`」，实际远端为 `73f4369…` | 卡第 19 行「推送并确认远端等于已审 HEAD」 | 由同一独立 reviewer 改写为「远端 = 经复核并发布的最终内容 HEAD `73f4369…`，其父提交为首轮候选 `2fd2294…`；清单对照修订提交为之后的纯文档 bookkeeping」 |
| R-03 | P2 | canonical PWF 顶部「最终 HEAD / 独审绑定 HEAD」只写「见 `handoff.json`」，未写最新目标分支 HEAD | 卡执行步骤 1「在顶部更新最新目标分支 HEAD」 | 顶部改为明示 `2fd2294…`（候选）、`73f4369…`（final / 远端 / 复核）、并注明修订提交后以 `git ls-remote` 为准 |
| R-04 | P2 | `handoff.md` §6 三条 `result` 写「见 `tests` 字段」「见审查报告」等占位，未给实际结果 | 卡第 17 行「测试命令及结果」 | 全部填实（PASS / 0 broken / exit 0 / 空 diff / 远端 SHA），并补 `git ls-remote` 一行 |
| R-05 | P2 | 6 个 `codex/*` 分支合并为 1 条 disposition；`logs`/`nul`/5 个隐藏目录合并为 1 条；MB11/G5/G4 目录与两份名单合并为 1 条 | 卡第 17 行「**每个** branch/worktree/Projects候选的 disposition 和依据」、`dispatch.md` §2/§7「逐项处置」、卡步骤 4「为**每条** Projects 目录记录 keep/delete 与字节收据」 | `dispositions` 由 9 条拆为 **24 条**逐项记录（7 个分支、3 个 worktree、backup、7 个容器路径、3 个证据目录、2 份名单、1 条 wire），每条含 `kind/path/status/reason/evidence`，逐目录带文件数/字节 |
| R-06 | P3 | 卡第 5 行要求读 `.planning/g5-sid-runtime/` 的「handoff 和依赖图」，首轮只读了 `HANDOFF.md` 与 `dependency_map.json`，未读 `handoff.json` | 卡第 5 行 | 补读 `handoff.json`：`schema_version=g5-handoff/1`、`delivery_status=ready_for_main`、`public_contracts` 明确 `stockinfo-cninfo/1.3.0 unchanged`；与 `ABSORBED` 结论一致，**不改变任何处置**（§2 已记录） |

**非缺陷、需向 ROOT 明示的三点**：
1. **哈希自指固有约束**：交接 JSON 无法包含自身所在提交的 SHA，故 `final` 沿用本仓 MB11 的 `commit`（内容提交）/`docs_commit`（含交接元数据提交）分记惯例，记录「经独立审查并发布的最终内容提交」`73f4369…`；本次清单对照修订提交（本文件所在提交）为之后的纯文档 bookkeeping，其 SHA 用 `git log -1` / `git ls-remote` 查询。R-01 的错误是把 `final` 填成了**从未发布到远端的候选提交**，与自指无关，属真实笔误，已更正。
2. **交付路径归属**：卡要求「只写唯一写入仓、不要写到其他仓」，因此三份交付写在 SID 仓 `docs/plans/module-pwf-reconciliation-2026-11-14/review/`（与 Dashboard 卡写自己仓内 `.planning/.../handoffs/...` 同构）。ROOT 整合时需跨仓只读该目录；若总控需要索引指针，由 ROOT 在 `company-wiki` 自行登记，本卡不代写。
3. **仓外 memory 文件**：见 §10 例外登记，非产品/ Git 改动。

复核后重跑：裸 JSON + 13 顶层键 + 子字段、35 个 MD **0 broken link**、`git diff --check` = 0、`src/tests/main.py` diff 为空、7 个分支逐一祖先、worktree 2 条、两份名单仍在；同一独立 reviewer 对该修订提交只读复核，`PASS` 保持。
