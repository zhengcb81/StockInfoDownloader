# MB-SID — 独立审查记录

审查在模块交付前执行，审的是完整分支而不是单文件。两轮都由未参与写作的独立 agent 完成，只读，不改文件。

## 第一轮

- **审查者**：独立 agent `agent-b23d2f95-2581-4679-99fd-419cb819a871`
- **审查范围**：`c0f07e12..1f4f44c`（全部 9 个提交，含 checkpoint），`src/`、`main.py`、`tests/` 全量 diff
- **结论**：`VERDICT: CHANGES REQUIRED`
- **自跑测试**：`tests/unit` 328 passed / 0 failed / 0 skipped / 54.37s

### 阻断项

| ID | 位置 | 问题 | 复现方式 |
|---|---|---|---|
| B1 | `src/downloader.py` `_switch_tab` | 未知 suffix 时 `_TAB_MENU_TEXT.get()` 返回 None，直接跳过点击，再用整页/默认页签链接判定"切换成功"，于是下载了默认页签的文档 —— gap 3 的原形仍在 | 假 DOM，`suffix="announcements"`，默认页签放一条招股说明书 → `success=True` 且下载该文档 |
| B2 | `src/browser.py` `find_active_tab_links` | 可见性只认 `is-hidden` 类；Element UI 默认用内联 `display:none`。用 lxml 对同一 XPath 求值：`style-hidden` 形状返回两个页签的链接，无 `el-tab-pane` 形状返回空 | lxml 6.1.1 XPath 求值两种标记 |
| B3 | `src/downloader.py` `_verify_downloads` | 只接收成功路径，不读 `_failed_logger`；2 个候选 1 个失败仍 `success=True`、`verification.ok=True`，而 `logs/failed_downloads.json` 已记录失败 | 2 链接、第 2 个 `download_file=False` |

### 非阻断项（第一轮）

失败通道可能被日志污染（"最后一行是 JSON"契约）；空页签被当上游故障并按 `max_retries` 放大；adapter 自身 staging 校验丢 typed code；`__all__` 导出私有名；`mapping.py` 去 catch-all；RED 证据质量不齐（gap 1 是缺功能 RED、`red-provider.log` 里有一条误发的真实 HTTPS 请求）；源码字符串断言；report suffix 死分支与校验过晚；`[None]` 日志。

## 第二轮

- **审查者**：独立 agent `agent-0d946b9c-c87e-469b-9c64-c4449ad9e178`
- **审查范围**：`5e4c3f7` 修复提交，针对第一轮三项阻断复验 + 新洞排查
- **结论**：`VERDICT: PASS`
- **自跑测试**：禁用宿主 safe-delete shim 后 `332 passed / 0 failed / 0 skipped / 42.80s`（直接跑会挂在 `test_g5_provider_runtime.py` 的 `rmdir` shim，属环境问题）

### 复验结果

- **B1 已关闭**：未知后缀抛 `DownloadError` → `success=False`、零下载；菜单不可达 → `infrastructure_fail`、零下载。两条 fail-open 路径都消失。
- **B3 已关闭**：1 失败 + 1 成功 → `success=False`，issues 恰为 `['download_failed']`。
- **B2 部分关闭**：内联 `display:none` 场景真正关闭（`offsetParent`）；"无 pane 容器"从"返回空"改为"整页兜底"，属于设计取舍而非遗留 bug，但其安全性仍缺真页证据。`visibility:hidden` 未覆盖。

### 第二轮非阻断项及处置

| 项 | 是否本卡修复 | 处置 |
|---|---|---|
| `_request_failures` 只在 `download()` 开头复位，重试尝试间泄漏（重试成功仍报 `verification_failed`，重复 issue） | 是 | `f1fff01`：每次尝试前复位，并加 `test_each_retry_attempt_starts_with_no_recorded_failures` |
| `active_tab_label()` 取文档序第一个 `.is-active`，真页可能是侧栏分类项 → 假失败；该分支零测试 | 是 | `f1fff01`：点击与选中判定合并为作用域内 `select_menu_item()`，返回 `active/inactive/unknown/missing`，`unknown` 退回链接证据；补 `test_click_that_does_not_change_the_selection_is_refused` |
| cleanup 抛异常会吞掉失败 JSON；`assert` 在 `-O` 下失效 | 是 | `f1fff01`：cleanup 包 try/except 记日志，结果判空改为显式分支 |
| `test_provider_error_contract.py` 同名测试重复两份（第一份死代码） | 是 | `f1fff01`：删除重复 |
| "菜单缺失"与"页签为空"未在结果码上区分 | 否 | 两者都是 `infrastructure_fail`；日志可区分。列入 findings 残余风险 |
| 无 pane 容器时整页兜底、`visibility:hidden` 未覆盖 | 否 | 需真实页面 DOM 快照；列入 findings 残余风险，交 ROOT 决定是否安排真实采集 |

## 审查未覆盖

- 真实 cninfo 页面（无网络、无 DOM 快照）。
- 真实 PDF 下载与 E2E（卡明确不默认执行）。
- 远端 CI。


## 最终复核（2026-11-13）

- 审查者：独立 agent /root/audit_rf_sid_delivery（未参与代码修改）。
- 审查绑定：90e7a25720581850783fd64ac055cd049eb58afe。
- 结论：PASS。复查点击作用域、延迟选中态、失败重试状态清理及 cleanup 不吞结果；无未修 in-scope finding。
- ROOT 在同一代码 tip 上另行运行完整单元测试：340 passed / 0 failed / 0 skipped，37.23 秒。完整日志见 evidence/unit-root-final-20261113.log。


## ROOT 集成验收（2026-11-13）

- 最终产品代码仍绑定 90e7a25720581850783fd64ac055cd049eb58afe；包内独审 PASS。
- 隔离集成分支以 v2-clean-rewrite 的远端 c0f07e12 为基线，快进至 a96791397bfcae0be73ab90265bb198f5a9c8d7c；完整 tests/unit 为 340 passed / 0 failed / 0 skipped，40.44 秒。
- 整合包含原工作区 WIP checkpoint 和其后的修复；没有改变测试失败行为或放宽断言。日志证据见 evidence/unit-integrated-final-20261113.log。
