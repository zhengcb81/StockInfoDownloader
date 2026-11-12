# MB-SID — 证据索引

命令统一为 `python -B -m pytest … -q -p no:cacheprovider`，Python 3.13.9 / pytest 9.1.1 / Windows 11。

| 文件 | 阶段 | 内容 | 结果 |
|---|---|---|---|
| `red-baseline.log` | A0 RED（基线 `c0f07e12`） | 新写的 legacy 契约 + e2e suffix 用例跑在未打补丁的基线 | 34 failed / 19 passed；多数是缺符号（`confirmed_empty` 不存在、`_path_is_within_subdir` 不存在），只作为"测试先于实现"的记录，**不作为产品 RED** |
| `red-wip-baseline.log` | A0 RED（checkpoint `f593535`） | 同一批用例跑在受审 WIP 上 | 24 failed / 6 passed；其中 `test_empty_active_tab_never_downloads_another_tab`（下载了隐藏页签 2 条）、`test_download_in_the_wrong_sibling_directory_is_not_a_success`（`success=True`）、`test_missing_file_fails_the_owner_result`（`success=True`）、`test_zero_files_is_not_a_silent_success`（`success=True`）、`test_cli_does_not_rejudge_a_successful_owner_result`（`False`）是**真实行为 RED** |
| `red-provider.log` | B RED（checkpoint） | `test_provider_error_contract.py` + `test_provider_dependency_direction.py` | 18 failed / 2 passed；CLI 侧全部落到 `upstream_unavailable`，依赖探针以 `ImportError: provider domain import refused: src.company_wiki_adapter` 失败。注意：本文件里 `test_adapter_preserves_the_upstream_error_identity` 的一次失败来自**误发的真实 HTTPS 请求**（`static.cninfo.com.cn` 返回 404），该用例随后改为拒绝域；这次请求不计为产品行为证据 |
| `unit-after-a0.log` | A0 GREEN | `tests/unit` | 305 passed / 57.09s |
| `unit-after-provider.log` | B GREEN | `tests/unit` | 325 passed / 53.90s |
| `unit-final.log` | C 初版 | `tests/unit` | 328 passed / 59.61s |
| `unit-after-review.log` | 审查修复 1 | `tests/unit` | 332 passed / 58.14s |
| `unit-after-review2.log` | 审查修复 2 | `tests/unit` | 334 passed / 0 failed / 0 skipped / 61.25s |
| `unit-after-compliance.log` | 交付 | `tests/unit` | **337 passed / 0 failed / 0 skipped / 59.96s**（补 3 条年/半年/季报期间过滤） |

## 未落盘但可复算的证据

- 原工区 WIP 未变：`git -C 'C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite' status --porcelain` → 11 modified + 3 untracked；`git diff --stat` → `743 insertions(+), 94 deletions(-)`。
- WIP patch 哈希：`08a8b63148f2cb47cf77c1b852cf7b93ebc8c3148dddbd2fa6166520a0864dd1`（`company-wiki/docs/plans/module-boundaries-2026-11-11/review/mb11-sid-wip/wip-11files.patch`）。
- fixture 脚本哈希：`86ad034fc79e04025e48d5c5c821298620b926838ba757f4482c9bc765a52914`（原工区与本 PWF 归档副本一致）。
- G4 镜像归档：`history/g4-sid-latest/{task_plan,findings,progress}.md`，哈希 `feb0fd9e…` / `651f7387…` / `137b72dc…`，与源文件逐一相同后才回收工区。
- 公司名单只记哈希，未读内容、未入库：`a_share_companies.txt` `16a94e94…0a5ce4`、`companies.txt` `4210e465…4845ce`。
