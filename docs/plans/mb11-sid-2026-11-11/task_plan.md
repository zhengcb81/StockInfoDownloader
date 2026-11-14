# MB-SID — SID 唯一当前状态入口（canonical PWF）

> **2026-11-14 · SID-PLAN-WORKTREE-CLOSEOUT 收口**：本文件是 `StockInfoDLSimple/v2-clean-rewrite` 仓**唯一**当前状态入口。
> 同目录 `progress.md` / `findings.md` / `handoff.md` / `handoff.json` / `review.md` / `compliance.md` / `runtime_inventory.md` / `history/` / `inputs/` / `evidence/`，
> `.planning/g5-sid-runtime/` 与 `docs/implementation/g4-sid-latest/` 一律是**历史证据或子计划**，只回链本入口，不得另建第二个 START_HERE、不得据其历史 "Next Step" 判断当前工作。
> 本次收尾交接：[handoff.md](../module-pwf-reconciliation-2026-11-14/review/sid-closeout-handoff.md) · [handoff.json](../module-pwf-reconciliation-2026-11-14/review/sid-closeout-handoff.json) · [独立审查](../module-pwf-reconciliation-2026-11-14/review/sid-closeout-review.md)。

## 当前状态（实时 Git 核对，2026-11-14）

| 项 | 值 |
|---|---|
| 唯一写入仓 / 长期主仓 | `C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite` |
| 目标主线（实时确认，不假设为 `main`） | `v2-clean-rewrite` |
| 开工 base HEAD | `d084c4aab48f5f83275f65982bf561e6870ff3a4` |
| base remote HEAD | `d084c4aab48f5f83275f65982bf561e6870ff3a4`（`git ls-remote origin refs/heads/v2-clean-rewrite` 实测） |
| 最新目标分支 HEAD（本卡收尾后的最终内容提交） | `73f436942e03df9276e1416f7771f29b26942876`（`v2-clean-rewrite`）；`git push` 后 `git ls-remote` 实测远端相同。提交链：`d084c4a`（base）→ `2fd2294`（首轮候选最终 HEAD，独立 reviewer 判 CHANGES REQUIRED）→ `73f4369`（修复复核 PASS 后发布）→ 之后若有纯交接记录修订提交，以 `git ls-remote origin refs/heads/v2-clean-rewrite` 为唯一准据 |
| 独审绑定 HEAD | 首轮 `2fd2294b387807b2031528120723ba7c90920470`；修复复核后最终 `PASS` 绑定 `73f436942e03df9276e1416f7771f29b26942876`，见 [交接](../module-pwf-reconciliation-2026-11-14/review/sid-closeout-handoff.md) 与 [独立审查](../module-pwf-reconciliation-2026-11-14/review/sid-closeout-review.md)。交接 JSON 不能自指包含自身提交 SHA，故 `final` 记录「经审查并发布的内容提交」，沿用本仓 MB11 的 `commit`/`docs_commit` 分记惯例 |
| tracked / untracked | tracked clean；未跟踪仅 `a_share_companies.txt`、`companies.txt` 两份**用户公司名单，原样保留** |
| 注册 worktree | 收尾前 3 个 → 收尾后 2 个（主仓 + `cwp-cninfo-bounded-budget`） |
| refs | 7 个本地分支（`codex/*` 6 个 + `v2-clean-rewrite` 主分支）全部是 `v2-clean-rewrite` 祖先；0 个 non-ancestor refs；远端仅 `origin/v2-clean-rewrite` |
| 在途改动 | 无；本卡写集合无 `UNCLASSIFIED_HOLD` 冲突 |

## 已完成（按 Git / 测试 / 交接收据）

| 项目 | 状态 | 证据 |
|---|---|---|
| MB-SID 交付 → ROOT 集成 → 主线推送 | MERGED / CLOSED | `codex/mb11-sid@a967913`、`codex/root-mb11-sid-integration-20261113@53b9358` 均为 HEAD 祖先；`6742eda`/`d084c4a` 收尾；`tests/unit` 340 passed / 0 failed；`review.md` 最终复核 PASS |
| G4 `mode=latest_as_of` 元数据发现 | MERGED / CLOSED | `eb8495ceb76892ff6f4a95889b6a19f0a78d769c` 是 HEAD 祖先；`docs/implementation/g4-sid-latest/MAIN_ACCEPTANCE.md` 记 127 passed / 27.02s 与 CWP route `df7d7ba58955e224c1799355f479ad5378ef38a7` 已发布 |
| **G4 旧待办「主线待做 1.3.0 路由升级」** | **SUPERSEDED（已完成，非待办）** | ① SID 源码 `src/company_wiki_adapter.py:30` `ADAPTER_VERSION = "1.3.0"`，CLI 成功/失败 JSON 均输出该版本；② 主线测试 `tests/unit/test_g4_latest_discovery.py`、`tests/unit/test_company_wiki_adapter.py`、`tests/e2e/test_g4_latest_cli_offline.py`、`tests/e2e/test_g5_browserless_provider.py` 断言 `stockinfo-cninfo/1.3.0`；③ 只读核对邻仓 `company-wiki@7361aad82` 的 `config/source_acquisition.yaml:9` 为 `version: 1.3.0`；④ `MAIN_ACCEPTANCE.md` 记 CWP route 1.3.0 已提交，`HANDOFF.md` §6 所要求 bump 已落地。G4 `HANDOFF.md` §10 第 1 项与 `task_plan.md` 的 "MAIN owns the 1.3.0 route bump" 是交付时点陈述，现已关闭，**不再作为 SID 待办** |
| G5 provider 解耦（无 Playwright/Chromium、共享预算） | ABSORBED | `codex/g5-sid-runtime@47e1059` 是 HEAD 祖先；`src/cninfo_identity.py`、`src/disclosure_matching.py`、`tests/unit/test_g5_provider_runtime.py`、`tests/e2e/test_g5_browserless_provider.py` 及 `.planning/g5-sid-runtime/` 12 个 PWF/evidence 文件均在 HEAD 树内；`git diff codex/g5-sid-runtime..HEAD` 剩余仅 MB11 后续改动 |

## 工区 / 目录处置（逐项，2026-11-14）

| 路径 | 关联 branch / PWF | 状态 | 依据 |
|---|---|---|---|
| `v2-clean-rewrite`（主工区） | `v2-clean-rewrite` | `ACTIVE_KEEP` | 唯一长期主仓；用户名单、真实返回数据、`downloads/`、运行日志与 MB11/G4/G5 证据均在此 |
| `Projects/_g5/sid` | `codex/g5-sid-runtime@47e1059` / G5 PWF | `DELETE_AFTER_OWNER_CONFIRMATION` | clean、`git status --ignored` 仅 `.mypy_cache`/`.ruff_cache` 可重建缓存；tracked 内容与 12 个 G5 PWF 文件全在 HEAD；无运行时配置引用；分支保留，可用 `git worktree add` 重建。已由 SID owner 精确移除，释放 713 文件 / 41,315,535 字节 |
| `Projects/StockInfoDLSimple/cwp-cninfo-bounded-budget` | `codex/cninfo-bounded-budget@8ed5fdd` / G4 基线 | `EVIDENCE_KEEP` | 注册工区且 clean；是 G4 基线 `8ed5fdd` 的物理现场，含 6 份 e2e 真实 PDF 与运行态 `logs/progress.json`、`src/stock_orgid_mapping.json`；名字涉及 CWP 面向任务，按保守原则保留，不按「已吸收/可重建」删除 |
| `Projects/StockInfoDLSimple/lineage-cleanup-backup-20261004` | 2026-10-04 1.1.0→1.2.0 回滚材料 | `EVIDENCE_KEEP` | 5 个唯一文件（85,874B staged patch、3,610B unstaged patch、20,179B 未入任何 commit 的 pre-budget `cninfo_api.py`、`status_before.txt`、README），是唯一回滚/审计资料；README 明确要求不移入仓内 |
| `Projects/StockInfoDLSimple/logs`、`nul`、隐藏工具目录 | 运行状态 / 外部工具 | `UNCLASSIFIED_HOLD` | 归属与用途未查清，合计极小；按卡规原样保留，不按名字当作临时文件删除 |
| 6 个 `codex/*` 分支 refs | 各交付/集成分支 | `ABSORBED` | 全部是 HEAD 祖先，作为交付证据保留，不删 ref |

## 唯一下一步（SID 主线）

**G2-12：把 `mode=latest_as_of` 从「已验收的元数据发现」推进到完整单意图 ensure 链**（FF → ET → CWP 下载→入库→复用）。
本仓只负责 provider 侧公开 wire 与有界预算行为；不改 CWP/FF 的 provider adapter。
验收证据：在本仓主线跑 `tests/unit/test_g4_latest_discovery.py`、`tests/unit/test_g5_provider_runtime.py`、`tests/e2e/test_g4_latest_cli_offline.py`、`tests/e2e/test_g5_browserless_provider.py` 及完整 `tests/unit`；随后由 ROOT 在 CWP 做一次有限公开接口组合验收。
父业务 goal `du11-source-closure-2026-10-18` 当前为 **paused**，本卡不自动恢复；恢复顺序由 ROOT 决定。

## 与 CWP / FF 的公开 wire 依赖（只记录，不改邻仓）

| 依赖 | 当前事实 | 归属 |
|---|---|---|
| provider 身份 | `stockinfo-cninfo` / `1.3.0`；wire `schema_version = 1.0` | SID 输出；CWP `config/source_acquisition.yaml` 校验 name+version |
| latest 请求字段 | `mode=latest_as_of` + `as_of_date`；`fiscal_year=null` 合法；`fiscal_period`/`form_type` 为显式等值过滤 | CWP `SourceRequest` 已具备，无需 SID 改接口 |
| 终态错误 | `discovery_incomplete` / `bounded_discovery_empty` / `schema_drift` / `budget_exceeded`，均 non-retryable | CWP 必须按诚实 GAP 处理，不得用旧本地文件冒充 latest |
|  acquisition budget | `acquisition_budget` / `acquisition_usage` 形状未变，字节+deadline 同一预算 | SID 与 CWP 共用 |
| FF → ET → CWP 链 | 尚未贯通（G2-12） | 跨仓差异只开 owner handoff，SID 不直接修改邻仓 |

---

> **以下为 2026-11-11 / 11-13 MB-SID 施工期历史记录**（historical evidence / subplan）。
> 当前 HEAD、G4 状态、工区处置与唯一下一步**一律以上方 canonical 段为准**；下方 "Next Step: 无" 只描述 MB-SID 卡本身已关闭。

## 实际基线与工区

| 项 | 值 |
|---|---|
| 原仓 | `C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite` |
| 基线 commit | `c0f07e12d4ba3e232d712bb6e5e491832023b0a0`（`v2-clean-rewrite` 当前 head） |
| 新工区 | `C:/Users/郑曾波/Projects/mb11-sid` |
| 分支 | `codex/mb11-sid` |
| 目标主线 | `v2-clean-rewrite` |
| remote | `origin https://github.com/zhengcb81/StockInfoDownloader.git` |

`git worktree add` 一次成功，无需唯一后缀；未 reset、未接管任何既有工区。

## 工作量与阶段

| 阶段 | 内容 | 提交 |
|---|---|---|
| A0-1 | 冻结 11 项 WIP patch + fixture 脚本哈希/出处，建工区与 PWF | — |
| A0-2 | 写 legacy 五类缺口的行为 RED（`test_legacy_download_contract.py`、e2e suffix 用例） | — |
| A0-3 | 按受审基线接收 patch（checkpoint），再按根因分小提交修复 | `f593535` → `4a5b30c`/`e238bdf`/`6ad33f4`/`2de8334`/`000f1cb` |
| B | SID-01 typed 错误贯通；SID-02 纯 metadata 域 + 依赖方向探针 | `6b2fd0b` |
| C | artifact 隔离 runtime 验收；独立审查两轮；交接 | `1f4f44c`/`5e4c3f7`/`f1fff01` |

## 计划与实际的差异

1. **接收顺序调整**：原计划"先 RED 再读入差量"。实际先写测试 → 在基线上跑一次（34 failed，多数是缺符号），应用 patch 后再跑（24 failed，其中 5 条是真实行为 RED）。两次记录都在 `evidence/`，行为 RED 以第二次为准。
2. **额外新增测试文件**：`test_provider_runtime_artifact.py`。卡里只要求"组合阶段"验证隔离 runtime，本卡把它固化成可重复测试（无安装器，用显式 manifest 复制）。
3. **`DownloadRequest` 增加可选尾字段 `confirmed_empty`**：卡要求"不可只预置私有属性模拟证明已接好真实API"。把上游确认空从事例私有属性改成请求公开字段，是唯一能在不接真实 API 的前提下证明"跨请求不继承"的写法；默认 `False`，对既有调用方无影响。
4. **两轮独立审查**：第一轮判 CHANGES REQUIRED（3 个阻断），修复后第二轮判 PASS，但提出 4 条非阻断缺陷，其中"`_request_failures` 未按尝试复位"是真实 bug，已一并修复（`f1fff01`）。

## 不做的事

- 不跑真实采集/E2E（卡允许，但只有确有验收需求才由 ROOT 安排）。
- 不写原工区 11 项 WIP、生产 config/cache/canonical、CWP/FF/Dayu。
- 不合并主线、不改 ROOT 总 PWF。
- 不部署到全局技能目录（本仓无安装器）。


## ROOT 并线收尾（2026-11-13）

- [x] 对账并恢复已由交付覆盖的原始 WIP 副本。
- [x] 保留输入名单，只删除已证实重复的来源脚本副本。
- [x] 完整交付分支快进至 v2-clean-rewrite，并验证远端 ref。
- [x] 集成测试 340/340 通过，独立审查 PASS。
- [x] 回写最终交接与远端状态。

## Next Step（历史记录：MB-SID 卡已关闭）

无；MB-SID 已并入主线并推送。**SID 仓当前唯一下一步见本文件顶部 canonical 段的「唯一下一步」。**


## ROOT 工区清理（2026-11-13）

- [x] 两个 clean 专用 worktree 已回收。
- [x] 保留公司输入名单，远端交付分支保留。
- [x] 本卡关闭，无下一步。
