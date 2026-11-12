# MB-SID — progress

## 时间线（2026-11-12）

| 时间 | 动作 | 结果 |
|---|---|---|
| 18:58 | 读卡、总控 interfaces/acceptance/runtime_verification/handoff_contract、acquisition_review §4 | 确认 SID 无待合旧分支，问题只是 11 项 WIP |
| 18:58 | 冻结 WIP：`wip-11files.patch`（53,423B，sha256 `08a8b631…4dd1`）、diffstat、fixture 脚本副本（sha256 `86ad034f…2914`）、公司名单只记哈希 | 存档于 company-wiki `review/mb11-sid-wip/` |
| 18:58 | `git worktree add -b codex/mb11-sid … c0f07e12` | 工区建立，head `c0f07e12` |
| 19:02 | 写 `test_legacy_download_contract.py` + e2e suffix 用例，基线运行 | 34 failed（多为缺符号），`evidence/red-baseline.log` |
| 19:03 | 应用 WIP patch，提交 checkpoint `f593535`，再跑 RED | 24 failed，其中 5 条真实行为 RED，`evidence/red-wip-baseline.log` |
| 19:10 | 修 downloader/models/browser/main/e2e | `4a5b30c` `e238bdf` `6ad33f4` |
| 19:13 | README/模板去未验证数字与主机路径 | `2de8334` |
| 19:14 | CLI 流保护（关闭流 + setStream） | `000f1cb`；unit 305 passed |
| 19:17 | provider typed 错误 + 纯 metadata 域 + 依赖方向探针 | `6b2fd0b`；unit 325 passed |
| 19:25 | artifact 隔离 runtime 验收 | `1f4f44c`；unit 328 passed |
| 19:40 | 独立审查第一轮 | CHANGES REQUIRED（B1/B2/B3） |
| 19:52 | 修复 B1/B2/B3 + 5 条非阻断 | `5e4c3f7`；unit 332 passed |
| 20:05 | 独立审查第二轮 | PASS + 4 条非阻断（含 1 个真实 bug） |
| 20:12 | 修复 `_request_failures` 复位、页签选中态、cleanup 异常、重复测试 | `f1fff01`；unit 334 passed |

## 2026-11-12 20:xx 合规复核

按用户要求逐条对照卡片，发现并补齐 5 处遗漏：

1. `scripts/capture_byd_fy2024_fixture.py` 未进交付树 → 已接收 + 说明 + README（标 `NO_RUNTIME_REFERENCE`）。
2. G4 三份 PWF 镜像未归档回收 → 原字节归档（哈希复核）后 `worktree remove` + `prune`。
3. 缺"活动入口/模块/公开面/owner/依赖方向"清单 → 新增 `runtime_inventory.md`。
4. 依赖方向探针只用了年报 fixture → 补 `exact_legacy_year` / `semi_annual_visible` / `quarterly_cutover` 三条期间过滤。
5. handoff 缺 ROOT 消费 fixture 的执行命令 → 已补；另补 `compliance.md` 逐条对照与 §8 偏差。

测试从 334 → 337 passed。

## 当前状态

- 代码：`codex/mb11-sid` @ `f1fff01`（代码）+ 其后一个 PWF 文档提交，相对基线 11 个提交，工作树干净，已推送 origin。
- 测试：`tests/unit` 334 passed / 0 failed / 0 skipped，61.25s（`evidence/unit-after-review2.log`）。
- 未执行：真实 E2E（需网络）、真实采集、CI 远端。
- 待办：推送分支、ROOT 集成。

## 恢复记录

- 原工区 `v2-clean-rewrite` 仍是 11 modified / 743+ / 94-，`scripts/capture_byd_fy2024_fixture.py` 哈希未变（`86ad034f…2914`）。本卡没有对它执行 add/commit/restore/clean。
- 新工区测试只用 pytest `tmp_path`；未在仓库内留下 `logs/`、`.planning/test-tmp` 或 staging 目录。
- 未写生产 `config.json`、`src/stock_orgid_mapping.json`、cache/canonical 目录。
