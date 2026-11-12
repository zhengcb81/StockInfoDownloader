# 历史归档：G4-SID-LATEST PWF 镜像

## 这是什么

`_g4/SID-LATEST/StockInfoDLSimple` 工区（HEAD `201a8f059b658eb0b3c12cb7e4db2ef08e3907da`）
里唯一未跟踪的内容是 `docs/implementation/.planning/g4-sid-latest/` 三份 PWF 文件。
它们与主线正式 `docs/` 中的交接**不是逐字节相同**（含历史时点），因此不能当作
"已被 main 吸收的重复文件"直接删掉。

MB-SID A0 按 `reconciliation.md` 的处置表"归档唯一证据再回收"，把三份原字节保存到
本目录，然后回收该工区。

## 归档清单

| 文件 | sha256 | 字节 |
|---|---|---|
| `task_plan.md` | `feb0fd9e197c2530ef6dbbc6b0ecffd085a0d502c699a018688d940b0be9f889` | 8,086 |
| `findings.md` | `651f738787f5a904aaa5431c9316aac44d610fdb4c3ca34a6041aed66db6d1ab` | 8,708 |
| `progress.md` | `137b72dc6335d8f524348fdbcea13a52aacff9049a8e82a89ee0332ee6cf1ac7` | 3,983 |

归档副本与源文件哈希逐一相同（复制后复核）。

## 为什么可以回收

- 该工区 HEAD `201a8f0` 是 `v2-clean-rewrite` 的**祖先**，tracked 树没有独有提交。
- `git status --porcelain` 只有一行 `?? docs/implementation/.planning/`，即上述三份。
- 三份已原字节归档；回收后不再有独有内容。

## 回收记录

```
git -C 'C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite' worktree remove --force 'C:/Users/郑曾波/Projects/_g4/SID-LATEST/StockInfoDLSimple'
git -C 'C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite' worktree prune
```

执行后 `git worktree list` 只剩主工区、`_g5/sid`、`cwp-cninfo-bounded-budget` 与本卡工区。
如需复原：`git worktree add 'C:/Users/郑曾波/Projects/_g4/SID-LATEST/StockInfoDLSimple' 201a8f059b65`。

## 边界

- 这三份是**历史证据**，不是当前状态，也不代表 G4 验收结论仍然有效。
- 本卡没有把它们的任何结论当作当前测试结果。
- 不复制原件、密钥或生产数据；这里只有 PWF 文本。
