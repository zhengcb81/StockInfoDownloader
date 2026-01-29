# StockInfoDownloader 代码库改进计划（详细版）

## 项目概述

StockInfoDownloader 是一个用于从巨潮资讯网自动下载股票信息的 Python 项目。本计划基于详细代码分析，对代码库进行系统性改进。

## 核心目标

1. **统一配置管理**：消除 ConfigManager 和 DownloaderConfigManager 双重性
2. **清理适配器层**：减少对 LegacyDownloaderAdapter 的依赖
3. **提升测试质量**：减少 Mock 使用，增加 Fake 实现，提升 E2E 稳定性
4. **整理文档**：合并重复文档，清理归档目录
5. **增强可观测性**：添加类型检查，改进错误处理

---

## 关键要求

**⚠️ 强制性要求：每个阶段完成后，必须运行端到端测试验证，100% 通过才能进入下一阶段。**

### E2E 测试执行规范

每个任务完成后，必须执行以下测试：

```bash
# 1. Playwright 模式 E2E 测试
python tests/e2e/official_e2e_test.py --browser-strategy=playwright

# 2. Selenium 模式 E2E 测试
python tests/e2e/official_e2e_test.py --browser-strategy=selenium

# 3. 运行所有单元测试
python tests/run_tests.py
```

### 阶段通过标准

- [ ] Playwright 模式 E2E 测试 100% 通过（显示 "Perfect match"）
- [ ] Selenium 模式 E2E 测试 100% 通过（显示 "Perfect match"）
- [ ] 所有单元测试通过（540+ 测试）
- [ ] 代码审查完成
- [ ] 更新 progress.md 记录测试结果

### 测试失败处理流程

如果 E2E 测试失败：
1. **立即停止**：不得进入下一阶段
2. **诊断问题**：分析失败原因
3. **修复问题**：在当前阶段内修复
4. **重新测试**：两种模式都重新运行 E2E 测试
5. **记录结果**：在 progress.md 中记录失败原因和修复方案

---

## 阶段规划

### Phase 1: 基线建立与现状分析
**目标**：建立当前代码基线，运行所有测试确认当前状态

**任务清单**：
- [ ] 1.1 运行官方 E2E 测试（Playwright 模式），记录结果
- [ ] 1.2 运行官方 E2E 测试（Selenium 模式），记录结果
- [ ] 1.3 运行所有单元测试，记录通过率和失败项
- [ ] 1.4 分析 ConfigManager 使用情况（grep 查找所有使用点）
- [ ] 1.5 分析 DownloaderConfigManager 使用情况
- [ ] 1.6 分析适配器层使用情况
- [ ] 1.7 创建详细问题清单（按优先级排序）
- [ ] 1.8 更新 findings.md 记录所有发现

**成功标准**：
- 基线测试结果记录在 progress.md
- 所有使用点分析完成
- **Playwright E2E 测试 100% 通过**
- **Selenium E2E 测试 100% 通过**

**阶段出口检查清单**：
- [ ] 基线测试结果记录完成
- [ ] Playwright E2E 测试通过
- [ ] Selenium E2E 测试通过
- [ ] findings.md 已更新
- [ ] progress.md 已更新

---

### Phase 2: 统一配置管理（高优先级）
**目标**：移除 DownloaderConfigManager，完全迁移到 ConfigManager

**任务清单**：
- [ ] 2.1 分析两个配置系统的所有使用点
  - [ ] 搜索 `from src.config.downloader_config import`
  - [ ] 搜索 `DownloaderConfigManager` 使用
  - [ ] 搜索 `config_manager` 全局实例使用
- [ ] 2.2 更新工厂类
  - [ ] 修改 `src/factory/downloader_factory.py` 直接使用 ConfigManager
  - [ ] 移除对 DownloaderConfigManager 的依赖
- [ ] 2.3 更新所有使用 DownloaderConfigManager 的代码
  - [ ] 更新测试文件
  - [ ] 更新微服务代码
  - [ ] 更新工具脚本
- [ ] 2.4 标记 DownloaderConfigManager 为已废弃
  - [ ] 添加 DeprecationWarning
  - [ ] 更新文档说明迁移路径
- [ ] 2.5 运行单元测试验证配置加载正常
- [ ] 2.6 **E2E 验证**：运行两种模式的 official_e2e_test.py

**成功标准**：
- 所有代码使用 ConfigManager
- DownloaderConfigManager 标记为废弃
- 所有单元测试通过
- **Playwright E2E 测试 100% 通过**
- **Selenium E2E 测试 100% 通过**

**阶段出口检查清单**：
- [ ] 配置统一完成
- [ ] 旧配置系统标记废弃
- [ ] 所有单元测试通过
- [ ] Playwright E2E 测试通过
- [ ] Selenium E2E 测试通过
- [ ] progress.md 已更新

**涉及的文件**：
- `src/factory/downloader_factory.py`
- `src/config/downloader_config.py`
- `tests/**/*.py`
- `microservices/**/*.py`

---

### Phase 3: 清理适配器层（高优先级）
**目标**：简化适配器层，E2E 测试直接使用 UnifiedDownloader

**任务清单**：
- [ ] 3.1 分析适配器使用情况
  - [ ] 搜索 `DownloadServiceV2Adapter` 使用
  - [ ] 搜索 `RefactoredDownloaderAdapter` 使用
  - [ ] 搜索 `create_legacy_adapter` 使用
- [ ] 3.2 更新 E2E 测试
  - [ ] 修改 `tests/e2e/official_e2e_test.py` 使用 UnifiedDownloader
  - [ ] 修改 `tests/e2e/test_dual_browser_modes.py` 使用 UnifiedDownloader
  - [ ] 修改 `tests/e2e/test_expected_data_validation.py` 使用 UnifiedDownloader
- [ ] 3.3 更新其他测试文件中的适配器使用
  - [ ] 检查并更新 `tests/unit/test_downloader_factory.py`
  - [ ] 检查并更新其他单元测试
- [ ] 3.4 运行单元测试验证适配器功能正常
- [ ] 3.5 **E2E 验证**：运行两种模式的 official_e2e_test.py

**成功标准**：
- E2E 测试直接使用 UnifiedDownloader
- 适配器层代码减少
- 所有单元测试通过
- **Playwright E2E 测试 100% 通过**
- **Selenium E2E 测试 100% 通过**

**阶段出口检查清单**：
- [ ] E2E 测试更新完成
- [ ] 适配器清理完成
- [ ] 所有单元测试通过
- [ ] Playwright E2E 测试通过
- [ ] Selenium E2E 测试通过
- [ ] progress.md 已更新

**涉及的文件**：
- `tests/e2e/official_e2e_test.py`
- `tests/e2e/test_dual_browser_modes.py`
- `tests/e2e/test_expected_data_validation.py`
- `src/adapters/legacy_downloader_adapter.py`

---

### Phase 4: 文档整理（中优先级）
**目标**：清理重复和过时文档，合并迁移指南

**任务清单**：
- [ ] 4.1 对比迁移指南
  - [ ] 对比 `docs/guides/MIGRATION_GUIDE.md` 和 `docs/core/REFACTORING_MIGRATION_GUIDE.md`
  - [ ] 识别重复内容
  - [ ] 确定保留哪个版本
- [ ] 4.2 合并内容
  - [ ] 合并两个迁移指南
  - [ ] 确保内容准确反映当前架构
  - [ ] 更新代码示例
- [ ] 4.3 删除重复文档
  - [ ] 删除 `docs/core/REFACTORING_MIGRATION_GUIDE.md` 或 `docs/guides/MIGRATION_GUIDE.md`
- [ ] 4.4 更新 `docs/core/CLAUDE.md`
  - [ ] 更新架构描述
  - [ ] 更新开发规范
- [ ] 4.5 清理 `docs/archive/` 目录
  - [ ] 识别关键历史决策记录
  - [ ] 删除过时的报告文件
- [ ] 4.6 **E2E 验证**：运行两种模式的 official_e2e_test.py

**成功标准**：
- 迁移指南合并完成
- 文档无重复
- archive 目录清理完成
- **Playwright E2E 测试 100% 通过**
- **Selenium E2E 测试 100% 通过**

**阶段出口检查清单**：
- [ ] 文档合并完成
- [ ] 重复文档已删除
- [ ] Playwright E2E 测试通过
- [ ] Selenium E2E 测试通过
- [ ] progress.md 已更新

**涉及的文件**：
- `docs/guides/MIGRATION_GUIDE.md`
- `docs/core/REFACTORING_MIGRATION_GUIDE.md`
- `docs/core/CLAUDE.md`
- `docs/archive/**/*`

---

### Phase 5: 测试质量提升（中优先级）
**目标**：改进测试，减少 Mock 使用，增加 Fake 实现

**任务清单**：
- [ ] 5.1 创建 FakeBrowserStrategy
  - [ ] 在 `tests/` 下创建 `fake_browser_strategy.py`
  - [ ] 实现内存中的浏览器模拟
  - [ ] 支持模拟页面导航、元素查找、文件下载
- [ ] 5.2 更新单元测试
  - [ ] 修改 `tests/unit/test_basic.py` 使用 FakeBrowserStrategy
  - [ ] 移除 MagicMock 使用
- [ ] 5.3 添加浏览器崩溃恢复测试
  - [ ] 创建 `tests/unit/test_browser_recovery.py`
  - [ ] 测试浏览器崩溃后的恢复逻辑
- [ ] 5.4 添加并发下载压力测试
  - [ ] 更新 `tests/performance/` 下的测试
  - [ ] 测试多线程/多进程下载场景
- [ ] 5.5 实现测试重试机制
  - [ ] 添加 pytest 重试插件配置
  - [ ] 为不稳定测试添加重试装饰器
- [ ] 5.6 运行单元测试验证
- [ ] 5.7 **E2E 验证**：运行所有 E2E 测试

**成功标准**：
- FakeBrowserStrategy 实现完成
- 单元测试使用 Fake 替代 Mock
- 新增恢复测试和压力测试
- **所有 E2E 测试 100% 通过**

**阶段出口检查清单**：
- [ ] Fake 实现完成
- [ ] 测试更新完成
- [ ] 所有单元测试通过
- [ ] Playwright E2E 测试通过
- [ ] Selenium E2E 测试通过
- [ ] progress.md 已更新

**涉及的文件**：
- 新建：`tests/fake_browser_strategy.py`
- 新建：`tests/unit/test_browser_recovery.py`
- `tests/unit/test_basic.py`
- `tests/performance/*.py`

---

### Phase 6: 类型检查与代码质量（中优先级）
**目标**：添加 mypy 类型检查，提升代码质量

**任务清单**：
- [ ] 6.1 配置 mypy
  - [ ] 创建/更新 `mypy.ini` 或 `pyproject.toml`
  - [ ] 设置合理的检查级别
  - [ ] 排除第三方库缺失类型提示的警告
- [ ] 6.2 修复类型错误
  - [ ] 运行 `mypy src/ --ignore-missing-imports`
  - [ ] 修复发现的类型错误
  - [ ] 优先修复核心模块（core, services, web）
- [ ] 6.3 添加缺失的类型注解
  - [ ] 为公共 API 添加完整类型注解
  - [ ] 更新接口定义
- [ ] 6.4 运行单元测试验证
- [ ] 6.5 **E2E 验证**：运行两种模式的 official_e2e_test.py

**成功标准**：
- mypy 配置完成
- `mypy src/` 无错误
- 所有单元测试通过
- **Playwright E2E 测试 100% 通过**
- **Selenium E2E 测试 100% 通过**

**阶段出口检查清单**：
- [ ] mypy 配置完成
- [ ] 类型错误修复完成
- [ ] 所有单元测试通过
- [ ] Playwright E2E 测试通过
- [ ] Selenium E2E 测试通过
- [ ] progress.md 已更新

**涉及的文件**：
- 新建/修改：`mypy.ini` 或 `pyproject.toml`
- `src/**/*.py`

---

### Phase 7: 最终验证与交付（高优先级）
**目标**：完整验证所有改进，确保系统稳定性

**任务清单**：
- [ ] 7.1 运行完整测试套件
  - [ ] 运行所有单元测试（540+ 测试）
  - [ ] 运行所有集成测试
  - [ ] 运行所有 E2E 测试（Playwright 和 Selenium 模式）
- [ ] 7.2 运行性能测试
  - [ ] 执行 `tests/performance_test_runner.py`
  - [ ] 记录性能基准
- [ ] 7.3 代码质量检查
  - [ ] 运行 `mypy src/` 确保无类型错误
  - [ ] 运行代码格式化检查
- [ ] 7.4 生成最终报告
  - [ ] 汇总所有改进点
  - [ ] 记录测试通过率
  - [ ] 更新 README 文档
- [ ] 7.5 **最终 E2E 验证**
  - [ ] Playwright 模式 100% 通过
  - [ ] Selenium 模式 100% 通过

**成功标准**：
- 单元测试通过率 > 95%
- 集成测试通过率 100%
- E2E 测试通过率 100%
- mypy 零错误
- 性能基准稳定

**阶段出口检查清单**：
- [ ] 完整测试套件通过
- [ ] 性能测试完成
- [ ] 代码质量检查通过
- [ ] 最终报告生成
- [ ] Playwright E2E 测试 100% 通过
- [ ] Selenium E2E 测试 100% 通过
- [ ] progress.md 已更新

---

## 依赖关系

```
Phase 1 (基线建立)
    ↓
Phase 2 (配置统一) ←→ Phase 3 (适配器清理)
    ↓
Phase 4 (文档整理) ←→ Phase 5 (测试提升)
    ↓
Phase 6 (类型检查)
    ↓
Phase 7 (最终验证)
```

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 配置合并破坏现有功能 | 高 | 充分测试，保持向后兼容，E2E 验证 |
| 删除适配器导致测试失败 | 中 | 逐步迁移，保留必要兼容层，E2E 验证 |
| 类型注解引入错误 | 低 | 使用 mypy 验证，小步修改 |
| E2E 测试不稳定 | 中 | 增加重试机制，Fake 实现替代 Mock |
| 时间超出预期 | 中 | 分阶段交付，优先高价值任务 |

---

## 工具清单

- **格式化**：black, isort, autoflake
- **类型检查**：mypy
- **测试**：pytest, pytest-cov, pytest-benchmark
- **CI/CD**：GitHub Actions, pre-commit

---

## 成功指标

- [ ] 代码行数减少 10%+
- [ ] 测试覆盖率 >= 80%
- [ ] mypy 零错误
- [ ] flake8 零警告
- [ ] 文档完整度 100%
- [ ] **每个阶段 Playwright E2E 测试 100% 通过**
- [ ] **每个阶段 Selenium E2E 测试 100% 通过**

---

## E2E 测试执行命令参考

```bash
# 官方 E2E 测试（必须每次执行）
python tests/e2e/official_e2e_test.py --browser-strategy=playwright
python tests/e2e/official_e2e_test.py --browser-strategy=selenium

# 其他 E2E 测试
python tests/e2e/test_dual_browser_modes.py
python tests/e2e/test_expected_data_validation.py

# 单元测试
python tests/run_tests.py

# 性能测试
python tests/performance_test_runner.py
```

---

## 当前状态

| 阶段 | 状态 | 开始日期 | 完成日期 | E2E通过 |
|------|------|----------|----------|---------|
| Phase 1 | Not Started | - | - | - |
| Phase 2 | Not Started | - | - | - |
| Phase 3 | Not Started | - | - | - |
| Phase 4 | Not Started | - | - | - |
| Phase 5 | Not Started | - | - | - |
| Phase 6 | Not Started | - | - | - |
| Phase 7 | Not Started | - | - | - |

---

## 备注

- 每个阶段完成后立即更新此文件
- 遇到问题立即记录在 progress.md
- **E2E 测试 100% 通过是硬性要求，不可妥协**
- 保持与团队的沟通，及时同步进展
