# 自动化测试系统总览 (Test Master)

本文档旨在整合项目中所有的测试资源，提供一站式的测试执行指南和技术说明。

---

## 1. 测试体系结构

项目采用分层测试策略，确保从底层逻辑到高层业务的全方位覆盖：

| 测试层次 | 目录位置 | 描述 | 运行命令 |
| :--- | :--- | :--- | :--- |
| **单元测试** | `tests/unit/` | 验证核心组件（映射、配置、清理）的隔离逻辑。 | `pytest tests/unit/` |
| **集成测试** | `tests/integration/` | 验证多个组件间的协作，包括多公司并发下载。 | `pytest tests/integration/` |
| **官方 E2E 测试** | `tests/e2e/` | **最高优先级**。模拟真实用户在真实网络下的下载行为。 | `python tests/e2e/official_e2e_test.py` |
| **性能测试** | `tests/performance/` | 压力测试与内存泄漏检测。 | `python tests/run_tests.py performance` |

---

## 2. 核心测试指南

### 2.1 官方端到端 (E2E) 测试
这是项目最重要的验收测试，严格遵循业务规范。
- **详细说明**: [官方 E2E 测试指南](testing/official_e2e_test.md)
- **核心配置**: `config_e2e_official.json`
- **预期结果**: `end2end_test/expected_results/`

### 2.2 单元与系统集成测试
现代化的 `pytest` 套件，用于日常开发快速迭代。
- **详细说明**: [测试规范与策略](testing/test_strategy.md)
- **关键技术**: 采用 `pytest-mock` 隔离网络，确保测试的可重复性。

---

## 3. 运行器 (Unified Runner)

为了方便开发者，项目提供了一个统一的测试运行器：

```bash
# 运行所有现代测试 (推荐)
python tests/verify_modern_tests.py

# 使用标准运行器运行特定类型
python tests/run_tests.py unit          # 仅单元测试
python tests/run_tests.py integration   # 仅集成测试
python tests/run_tests.py e2e           # 仅端到端测试
```

---

## 4. 辅助文档参考

- [浏览器自动化策略指南](reports/BROWSER_STRATEGY_ANALYSIS.md): Playwright 与 Selenium 的权衡。
- [调试标记系统说明](archive/reports/DEBUG_MARKER_SYSTEM.md): 如何利用 DebugStep 定位下载故障。
- [代码标准与质量](CODE_STANDARDS.md): 测试代码的编写规范。

---

## 5. 历史报告归档
所有的过往测试报告已归档至 `docs/archive/reports/` 目录下，供追溯使用。
