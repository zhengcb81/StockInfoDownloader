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
| final branch / HEAD / remote / 独审绑定 HEAD | 见 `sid-closeout-handoff.json` 的 `final` 与 `independent_review`；审查报告 `sid-closeout-review.md` 记录绑定值与复核状态。交接产物不与自身 SHA 自指 |
| remote | `origin https://github.com/zhengcb81/StockInfoDownloader.git`（有 remote） |
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
- **G5**：`codex/g5-sid-runtime@47e1059` 为 HEAD 祖先；`src/cninfo_identity.py`、`src/disclosure_matching.py`、`tests/unit/test_g5_provider_runtime.py`、`tests/e2e/test_g5_browserless_provider.py` 与 `.planning/g5-sid-runtime/` 12 个 PWF/evidence 文件都在 HEAD 树内；`git diff codex/g5-sid-runtime..HEAD` 仅剩 MB11 后续改动 → `ABSORBED`，其「等 MAIN 合并」历史 Next Step 不再有效。
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
| `python -X utf8 -c "json.load(...)"` 校验 `sid-closeout-handoff.json` 为裸 JSON、`schema_version=1`、顶层键/子字段齐全 | 见 `tests` 字段与审查报告 |
| 相对 Markdown 链接解析（canonical PWF ↔ 三份交付文件、15 个历史 banner 回链） | 见审查报告 |
| `git diff --check` | exit 0，无空白错误 |
| `git status --porcelain -uall` | 仅 2 份用户名单未跟踪 + 本次文档改动 |
| `git worktree list` / `git for-each-ref` / `git merge-base --is-ancestor` / `git ls-remote origin` | 逐项记录于 §1、§3 |

## 7. 独立审查

由**未参与实施**的另一名 agent/harness 审查完整变更与交接，结论绑定已提交的候选最终 HEAD；发现问题由 owner 修复、复测并提交新 HEAD 后复核。范围、绑定 HEAD、发现及关闭状态、最终 PASS/FAIL 记录在 `sid-closeout-review.md`，机器可读值在 `sid-closeout-handoff.json` 的 `independent_review`。仅此一个最终审查节点，修复复核除外。

## 8. 剩余项

1. **G2-12**：`mode=latest_as_of` 目前只验收了元数据发现 + 受控 loopback fetch；FF → ET → CWP 下载→入库→复用链尚未贯通（属 MAIN/CWP/FF，非本卡写集）。
2. `cwp-cninfo-bounded-budget` 与 `lineage-cleanup-backup-20261004` 按 `EVIDENCE_KEEP` 保留；如后续 CWP/SID owner 出具「无唯一内容 + 无配置引用」的收据，可再评估清理，本卡不代其它 owner 决定。
3. 容器 `logs/`、`nul` 与隐藏工具目录为 `UNCLASSIFIED_HOLD`，待归属查清后再处置。
4. 父业务 goal `du11-source-closure-2026-10-18` 仍为 **paused**，本卡不自动恢复。

## 9. 唯一下一步

**推进 G2-12 完整单意图 latest ensure 链**：在本仓主线先跑 provider 相关回归（`tests/unit/test_g4_latest_discovery.py`、`tests/unit/test_g5_provider_runtime.py`、`tests/e2e/test_g4_latest_cli_offline.py`、`tests/e2e/test_g5_browserless_provider.py` 及完整 `tests/unit`），再由 ROOT 在 CWP 做一次有限公开接口组合验收；SID 只维护 `stockinfo-cninfo/1.3.0`、wire `schema_version=1.0`、共享 `ProviderAcquisitionBudget` 与 `discovery_incomplete`/`bounded_discovery_empty` 诚实 GAP 语义，跨仓差异只开 owner handoff，不直接改邻仓。

## 10. 边界声明

- 只在 `StockInfoDLSimple/v2-clean-rewrite` 做文件与 Git 修改；未对 `company-wiki`、`filing-fetch`、`revenue-forecast`、`earnings-transcripts`、`investment-dashboard`、`StockWiki`、`invest-quick-scan` 做任何 checkout / stage / restore / commit / merge / push / 删除 / 移动。
- 对 CWP 仅做只读核对（`git rev-parse`、`grep config/source_acquisition.yaml`）；未改 CWP/FF 的 provider adapter。
- 未读取或复制任何密钥；未发起真实采集 / 付费 API / LLM 调用；未恢复 paused 的业务目标。
