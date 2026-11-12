# scripts/

本目录不是运行时入口。目前只有一支历史工具，按 MB-SID A0 要求保留出处。

## `capture_byd_fy2024_fixture.py`

- **来源**：CW-2.27E / Phase 4 Gate 4.1，2026-07 的一次性公开 API 元数据捕获器。
- **作用**：生成 `tests/fixtures/cninfo/byd_fy2024_announcement.json` 与
  `tests/fixtures/cninfo/synthetic_empty_from_real_schema.json`，这两个 fixture
  已经入库，契约测试离线读取它们。
- **状态**：`NO_RUNTIME_REFERENCE` —— 生产代码、测试、CLI 都不导入它。
- **不要做的事**：
  - 不要在构建/测试/自动化里调用它（会产生真实网络请求）。
  - 不要把它改成"任意公司采集器"；固定公司/期间是历史捕获参数，不是业务词典。
  - 不要因为它是 `.py` 就把它当成公开入口登记。
- **接收时的哈希**：`86ad034fc79e04025e48d5c5c821298620b926838ba757f4482c9bc765a52914`
  （与原工区未跟踪文件一致；本卡只在文件头补了 A0 说明，未改逻辑）。
