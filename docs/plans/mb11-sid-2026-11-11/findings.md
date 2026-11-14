> **状态入口（2026-11-14）**：本文件为历史证据/子计划，SID 仓当前状态唯一以 [MB-SID task_plan](task_plan.md) 顶部 canonical 段为准；本文件的历史 Next Step 不代表当前待办。

# MB-SID — findings

## 1. 11 项 WIP 的真实价值与缺陷

差量本身（743 增 / 94 删）来自 7 月 CW-2.27D/H 下载器改进。逐文件结论：

| 文件 | 有价值的部分 | 接收时发现的问题 | 处置 |
|---|---|---|---|
| `src/downloader.py` | typed 空结果、tab 切换、post-download 校验 | ① `CONFIRMED_EMPTY` 存在实例属性上跨请求继承；② `save_subdir` 反斜杠替换+子串；③ tab 校验用整页链接数、`_get_links` 空 pane 回退整页；④ `success=True` 携带 blocking warnings | 全部在本卡修复 |
| `src/models.py` | `load_state`/`error_code`/`retryable` | 无 | 保留，另加 `VerificationResult` |
| `main.py` | 消费验证结果 | 用英文 warnings 二次判失败，与 owner 语义分裂 | 改为只读 `result.success` |
| `src/browser.py` | 关键 host 逐个 DNS 解析、button 即时检测 | 只有源码字符串测试 | 保留行为，补 mock DNS 行为测试；页签 DOM 访问收进 browser |
| `src/logger.py` | stdout→stderr | 只测了被 CLI 重定向后的情况 | 保留，补新进程流测试 |
| `src/mapping.py` | 去掉 `_crawl_org_id` 的 catch-all | 不在本卡五个缺口内 | 保留，列入残余风险 |
| `tests/e2e/official_e2e_test.py` | report suffix 分轮 | suffix 直接拼进文件名（可穿越/覆盖） | 加单组件校验 + 入口前置校验 |
| `tests/unit/test_downloader.py` | 新增用例 | 部分断言 `_official_status` 私有 seam、部分查源码字符串 | 改写为公开契约；源码字符串用例保留为附加守卫 |
| `README.md` / `config_template.json` | 批量输入、页面说明 | 139 测试数未验证；`save_dir` 写死 CWP 主机路径 | 删除固定数字与主机路径，模板改相对路径并加 fixture 测试 |
| `tests/unit/test_official_e2e_contract.py` | mock 接受新参数 | 仅改 mock | 加 suffix 行为用例 |

WIP 自身测试并不绿：`TestCliErrorJsonContract` 用 `{}` 作 payload，请求校验先于 `_build_adapter` 失败，永远到不了它想测的分支。接收时已修 fixture（不是删断言）。

## 2. SID-01 / SID-02 的根因

- **SID-01**：`StockInfoCompanyWikiAdapter.fetch` 捕获 `CninfoApiError` 后 `raise AdapterError("cninfo_transport failed: ...")`，丢掉 `error_code`/`retryable`。CLI 的 `_emit_failure` 只在异常带 `code`/`error_code` 时使用 typed 身份，否则回落 `upstream_unavailable` + `retryable=True`。结果：host 白名单拒绝、无 `%PDF-`、内容过小三种永久失败全部被标成可重试。
- **SID-02**：`src/cninfo_api.py` 在 `_filter_page` / `_filter_latest_page` 内部 `from .company_wiki_adapter import _report_metadata`。反向依赖在模块导入时不炸（函数内 import），所以"能 import"不等于"方向正确"；一旦过滤任何一页就必须加载 adapter。这是本卡把依赖方向测试写成子进程 + 真实过滤、而不是只 `import` 的原因。

## 3. 审查发现（两轮）

第一轮（agent-b23d2f95）判 CHANGES REQUIRED：

- **B1** `_switch_tab` fail-open：未知 suffix 跳过点击、随后读默认页签。用仓库假 DOM 复现"没有点击仍下载默认页签文档"。
- **B2** 可见性判据未验证：用 lxml 对同一 XPath 求值，`style="display:none"` 形状会返回两个页签的链接；没有 `el-tab-pane` 形状返回空（旧代码靠整页兜底恰好能工作）。
- **B3** 部分失败仍报成功：2 个候选 1 个失败 → `success=True`，`verification.ok=True`。

第二轮（agent-0d946b9c）判 PASS，并指出修复引入的 4 条非阻断缺陷，其中：

- `_request_failures` 只在 `download()` 开头复位，`_download_with_retry` 每次尝试不复位 → 首次失败会污染成功的重试，并产生重复 `download_failed`。**已修**（`f1fff01`）。
- `active_tab_label()` 取文档序第一个 `.is-active`，真实页面可能是侧栏分类项 → 假失败。**已修**：点击与选中判定合成一次作用域内调用 `select_menu_item()`，返回 `active/inactive/unknown/missing`，`unknown` 退回链接证据。
- cleanup 抛异常会吞掉失败 JSON；`assert` 在 `-O` 下失效。**已修**。
- 重复的测试函数（同名两份，第一份死代码）。**已修**。

## 4. 残余风险（不在本卡可行动范围）

1. **真实页签 DOM 未抓取**：`find_active_tab_links()` 用 `offsetParent` 判定可见性，并在"页面完全没有 pane 容器"时把整页当作作用域。前者覆盖 `display:none`（无论来自 class 还是内联），后者让"没有 `el-tab-pane`"退化为整页而不是空。`visibility:hidden` 与"有 pane 容器但用未知方式隐藏"仍无法离线判定。需要一次真实页面 DOM 快照才能把这条假设变成证据；卡明确允许由 ROOT 决定是否安排真实采集。
2. **`confirmed_empty` 在生产链路没有生产者**：legacy SPA 路径不产生该标记，`main.py` 也不会传。因此"本页确实没有公告"仍会按 `INFRASTRUCTURE_FAIL/upstream_unavailable` 处理并重试。这是卡内明确接受的语义（去掉 `success=True/0 files` 掩盖），但接上 API 确认是后续集成工作。
3. **`src/mapping.py` 去掉 catch-all 后**，`OrgIdCrawler` 构造/导入异常会直接冒泡到 `download()` 的兜底，错误文本从 `Cannot resolve org_id ...` 变成原始异常。风险低（`get_org_id` 内部仍吞异常），但不在本卡五个缺口内，未改。
4. **`_TAB_MENU_TEXT` 硬编码三个中文菜单文案**：文案变动会让 `select_menu_item` 返回 `missing`，结果是 fail-closed（不下载），不会串页签。
