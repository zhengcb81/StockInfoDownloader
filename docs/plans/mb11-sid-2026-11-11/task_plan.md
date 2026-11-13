# MB-SID — task plan（本卡 PWF）

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

## Next Step

无；MB-SID 已并入主线并推送。
