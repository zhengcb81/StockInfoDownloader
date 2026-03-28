# Task Plan: StockInfoDownloader 代码质量改进计划
<!--
  WHAT: 基于5个agent teams全面审查结果的改进计划
  WHY: 项目评分8.14/10，存在关键问题需要修复
  WHEN: 创建于2026-02-08审查完成后
-->

## Goal
将 StockInfoDownloader 项目从当前评分 8.14/10 提升到 9.0+，修复关键代码质量问题，提升测试覆盖率到60%+，完善文档体系。

## Current Phase
Phase 3: 提升测试覆盖率到60%+ (0%覆盖率模块测试创建)

---

## 🔴 E2E 测试强制要求（所有阶段）

**每个阶段结束时，必须运行端到端测试（Playwright 和 Selenium 模式），保证 100% 成功。**

**不通过测试则不能进入下一阶段。**

### E2E 测试执行命令
```bash
# 阶段出口必须执行（两种模式都必须 100% 通过）
python tests/e2e/official_e2e_test.py --browser-strategy=playwright  # 必须显示 "Perfect match"
python tests/e2e/official_e2e_test.py --browser-strategy=selenium    # 必须显示 "Perfect match"
```

### 阶段通过标准（全部必须满足）
- [ ] **Playwright 模式 E2E 测试 100% 通过**（显示 "Perfect match"）
- [ ] **Selenium 模式 E2E 测试 100% 通过**（显示 "Perfect match"）
- [ ] 所有单元测试通过
- [ ] 阶段目标完成
- [ ] progress.md 已更新测试结果

### E2E 测试失败处理流程
```
┌─────────────────────────────────────────────────────────────┐
│  1. 🛑 立即停止                                              │
│     → 不得进入下一阶段                                       │
│     → 不得合并代码                                           │
│     → 不得标记阶段完成                                       │
├─────────────────────────────────────────────────────────────┤
│  2. 🔍 诊断问题                                              │
│     → 分析失败日志                                           │
│     → 确定根因（代码问题/环境问题/网络问题）                    │
│     → 评估影响范围                                           │
├─────────────────────────────────────────────────────────────┤
│  3. 🔧 修复问题                                              │
│     → 在当前阶段内修复                                       │
│     → 小步修改，频繁测试                                     │
│     → 不得绕过问题继续                                       │
├─────────────────────────────────────────────────────────────┤
│  4. 🔄 重新测试                                              │
│     → 两种模式都必须重新运行                                 │
│     → 不能只测试通过的那个模式                               │
│     → 确保修复没有引入新问题                                 │
├─────────────────────────────────────────────────────────────┤
│  5. 📝 记录结果                                              │
│     → 在 progress.md 记录失败原因                            │
│     → 记录修复方案                                           │
│     → 更新 findings.md 如果需要                              │
└─────────────────────────────────────────────────────────────┘
```

### 阶段出口检查清单模板
每个阶段完成时，必须勾选以下清单：
```markdown
## Phase N 出口检查清单
- [ ] 阶段任务全部完成
- [ ] **Playwright E2E 测试 100% 通过** ✅
- [ ] **Selenium E2E 测试 100% 通过** ✅
- [ ] 所有单元测试通过
- [ ] progress.md 已更新测试结果
- [ ] findings.md 已更新（如有新发现）
```

## 综合评分现状

| 维度 | 当前评分 | 目标评分 | 差距 |
|------|----------|----------|------|
| 架构设计 | 8.2/10 | 9.0/10 | +0.8 |
| 代码质量 | 7.5/10 | 9.0/10 | +1.5 |
| 测试覆盖 | 8.5/10 | 9.0/10 | +0.5 |
| 文档完整 | 8.2/10 | 9.0/10 | +0.8 |
| 基础设施 | 8.5/10 | 9.0/10 | +0.5 |
| **综合** | **8.14/10** | **9.0/10** | **+0.86** |

## Phases

### Phase 1: 修复代码质量问题 (P0 - 立即执行)
<!--
  WHAT: 修复空except块和过于宽泛的异常捕获
  WHY: 20处空except块和40+处宽泛异常捕获严重影响代码稳定性
-->
- [ ] 修复20处空except块
  - [ ] `src/core/exceptions.py:218` 及其他位置
  - [ ] 添加具体异常类型和错误日志
  - [ ] 添加适当的恢复逻辑
- [ ] 修复40+处过于宽泛的异常捕获
  - [ ] `src/web/selenium_strategy.py:108` 等位置
  - [ ] 替换 `except Exception` 为具体异常类型
  - [ ] 确保所有异常都有适当的处理
- [ ] 运行所有测试验证修改
- [ ] **🔴 E2E 验证**：运行两种模式的 official_e2e_test.py
- [ ] **Status:** completed
- **预计工作量:** 1-2天
- **预期收益:** 稳定性+30%，可维护性+20%

#### Phase 1 E2E 测试结果
| 测试 | 结果 | 状态 |
|------|------|------|
| Playwright 模式 | Perfect match | ✅ PASS |
| Selenium 模式 | Perfect match | ✅ PASS |

#### Phase 1 出口检查清单
- [x] 空except块全部修复（39处 → 0处）
- [x] 所有单元测试通过（626 passed）
- [x] **Playwright E2E 测试 100% 通过**
- [x] **Selenium E2E 测试 100% 通过**
- [x] progress.md 已更新

---

## Phase 1 完成摘要

**完成日期**: 2026-02-08
**实际工作量**: 约1小时

### 修复的空except块 (39处)
| 文件 | 修复数量 |
|------|----------|
| `src/core/exceptions.py` | 1 |
| `src/data/mapping.py` | 3 |
| `src/services/file_service.py` | 1 |
| `src/services/validation_service.py` | 1 |
| `src/utils/debug_marker.py` | 2 |
| `src/core/company_config_manager.py` | 2 |
| `src/core/degradation.py` | 2 |
| `src/config/downloader_config.py` | 1 |
| `src/web/scraper.py` | 2 |
| `src/web/common_browser_ops.py` | 2 |
| `src/web/selenium_strategy.py` | 4 |
| `src/web/enhanced_driver_pool.py` | 2 |
| `src/web/playwright_strategy.py` | 2 |
| `src/web/selenium/download_manager.py` | 8 |
| `src/adapters/legacy_downloader_adapter.py` | 1 |
| `src/services/unified_downloader.py` | 2 |

### 测试结果
- **单元测试**: 626 passed ✅
- **Playwright E2E**: Perfect match ✅
- **Selenium E2E**: Perfect match ✅

### Phase 2: 拆分ConfigManager (P0 - 架构改进)
<!--
  WHAT: 将ConfigManager拆分为多个职责单一的类
  WHY: 当前937行代码，32个方法，违反单一职责原则
-->
- [ ] 分析ConfigManager的所有职责
  - [ ] 基础配置管理 (12个方法)
  - [ ] 属性访问 (8个方法)
  - [ ] 多公司管理 (9个方法)
  - [ ] 测试配置 (7个方法)
- [ ] 设计拆分方案
  - [ ] ConfigLoader - 文件读写
  - [ ] ConfigValidator - 配置验证
  - [ ] ConfigProvider - 配置访问
  - [ ] ConfigManager - 协调组件
- [ ] 实现拆分
  - [ ] 创建 `src/core/config/` 目录
  - [ ] 保持向后兼容的API
  - [ ] 更新所有调用点
- [ ] 运行所有测试验证修改
- [ ] **🔴 E2E 验证**：运行两种模式的 official_e2e_test.py
- [ ] **Status:** pending
- **预计工作量:** 3-5天
- **预期收益:** 可维护性+25%，降低耦合度

#### Phase 2 E2E 测试结果（待执行）
| 测试 | 结果 | 状态 |
|------|------|------|
| Playwright 模式 | 待执行 | ⏳ |
| Selenium 模式 | 待执行 | ⏳ |

#### Phase 2 出口检查清单
- [ ] ConfigManager 拆分完成
- [ ] 向后兼容性验证通过
- [ ] 所有单元测试通过
- [ ] **Playwright E2E 测试 100% 通过**
- [ ] **Selenium E2E 测试 100% 通过**
- [ ] progress.md 已更新

### Phase 3: 提升测试覆盖率到60%+ (P0 - 质量保证)
<!--
  WHAT: 从当前35.49%提升到60%+
  WHY: 7个核心模块0%覆盖率，存在质量盲区
-->
- [ ] 为0%覆盖率模块添加测试
  - [ ] `src/web/driver_pool.py` (145行) - 驱动池管理
  - [ ] `src/web/enhanced_driver_pool.py` (354行) - 增强驱动池
  - [ ] `src/web/proxy_manager.py` (372行) - 代理管理
  - [ ] `src/web/rate_limiter.py` (203行) - 限流器
  - [ ] `src/web/selenium/strategy.py` (260行) - Selenium策略
  - [ ] `src/web/selenium/download_manager.py` (330行) - 下载管理器
- [ ] 提升反爬虫模块覆盖率
  - [ ] `src/web/anti_crawler_py.py` (16.78% → 60%+)
  - [ ] `src/web/scraper.py` (32.09% → 60%+)
- [ ] 使用Fake替代Mock
  - [ ] 识别过度使用Mock的测试
  - [ ] 创建FakeBrowserStrategy等Fake实现
- [ ] 运行所有测试验证修改
- [ ] **🔴 E2E 验证**：运行两种模式的 official_e2e_test.py
- [ ] **Status:** pending
- **预计工作量:** 5-7天
- **预期收益:** 代码信心+40%，覆盖率+25%

#### Phase 3 E2E 测试结果（待执行）
| 测试 | 结果 | 状态 |
|------|------|------|
| Playwright 模式 | 待执行 | ⏳ |
| Selenium 模式 | 待执行 | ⏳ |

#### Phase 3 出口检查清单
- [ ] 0%覆盖率模块全部添加测试
- [ ] 测试覆盖率 ≥ 60%
- [ ] 所有单元测试通过
- [ ] **Playwright E2E 测试 100% 通过**
- [ ] **Selenium E2E 测试 100% 通过**
- [ ] progress.md 已更新

### Phase 4: 完善类型注解 (P1 - 可维护性)
<!--
  WHAT: 从当前~50%提升到80%+类型注解覆盖率
  WHY: 提高代码可维护性，IDE友好度
-->
- [ ] 分析当前类型覆盖缺口
  - [ ] 运行 `mypy src/ --ignore-missing-imports`
  - [ ] 生成类型覆盖报告
- [ ] 完善核心模块类型注解
  - [ ] `src/core/logger.py` - 日志模块
  - [ ] `src/core/debug_tracker.py` - 调试追踪
  - [ ] `src/web/anti_crawler/` - 反爬虫模块
  - [ ] `src/utils/` - 工具函数
- [ ] 更新mypy配置提高检查严格度
- [ ] 确保mypy检查通过
- [ ] **🔴 E2E 验证**：运行两种模式的 official_e2e_test.py
- [ ] **Status:** pending
- **预计工作量:** 3-5天
- **预期收益:** IDE友好度+50%，类型安全

#### Phase 4 E2E 测试结果（待执行）
| 测试 | 结果 | 状态 |
|------|------|------|
| Playwright 模式 | 待执行 | ⏳ |
| Selenium 模式 | 待执行 | ⏳ |

#### Phase 4 出口检查清单
- [ ] 类型注解覆盖率 ≥ 80%
- [ ] mypy 检查 0 错误
- [ ] 所有单元测试通过
- [ ] **Playwright E2E 测试 100% 通过**
- [ ] **Selenium E2E 测试 100% 通过**
- [ ] progress.md 已更新

### Phase 5: 完善文档体系 (P1 - 开发者体验)
<!--
  WHAT: 添加缺失的关键文档
  WHY: 缺少贡献指南、部署指南、最佳实践文档
-->
- [ ] 创建 `CONTRIBUTING.md` - 贡献指南
  - [ ] 代码贡献流程
  - [ ] 代码审查规范
  - [ ] 提交信息规范
- [ ] 创建 `docs/guides/DEPLOYMENT.md` - 部署指南
  - [ ] 生产环境部署步骤
  - [ ] Docker部署详细说明
  - [ ] 监控配置指南
- [ ] 创建 `docs/guides/BEST_PRACTICES.md` - 最佳实践
  - [ ] 使用建议
  - [ ] 性能优化建议
  - [ ] 常见问题解决方案
- [ ] 创建 `docs/guides/PERFORMANCE.md` - 性能优化指南
- [ ] 更新过时文档
  - [ ] `PHASE10_ASSESSMENT.md`
  - [ ] `IMPLEMENTATION_PLAN.md`
- [ ] **🔴 E2E 验证**：运行两种模式的 official_e2e_test.py
- [ ] **Status:** pending
- **预计工作量:** 2-3天
- **预期收益:** 开发者体验+30%

#### Phase 5 E2E 测试结果（待执行）
| 测试 | 结果 | 状态 |
|------|------|------|
| Playwright 模式 | 待执行 | ⏳ |
| Selenium 模式 | 待执行 | ⏳ |

#### Phase 5 出口检查清单
- [ ] 缺失文档全部创建
- [ ] 过时文档全部更新
- [ ] 所有单元测试通过
- [ ] **Playwright E2E 测试 100% 通过**
- [ ] **Selenium E2E 测试 100% 通过**
- [ ] progress.md 已更新

### Phase 6: 重构UnifiedDownloader (P1 - 架构优化)
<!--
  WHAT: 拆分UnifiedDownloader的职责
  WHY: 当前类承担过多责任，可测试性差
-->
- [ ] 分析UnifiedDownloader的职责
- [ ] 设计拆分方案
  - [ ] DownloadOrchestrator - 流程协调
  - [ ] StockDownloader - 单只股票下载
  - [ ] FileProcessor - 文件处理
  - [ ] RequestBuilder - 请求构建
- [ ] 实现拆分并保持向后兼容
- [ ] 更新所有调用点
- [ ] **🔴 E2E 验证**：运行两种模式的 official_e2e_test.py
- [ ] **Status:** pending
- **预计工作量:** 3-5天
- **预期收益:** 可测试性+30%，可读性+25%

#### Phase 6 E2E 测试结果（待执行）
| 测试 | 结果 | 状态 |
|------|------|------|
| Playwright 模式 | 待执行 | ⏳ |
| Selenium 模式 | 待执行 | ⏳ |

#### Phase 6 出口检查清单
- [ ] UnifiedDownloader 拆分完成
- [ ] 向后兼容性验证通过
- [ ] 所有单元测试通过
- [ ] **Playwright E2E 测试 100% 通过**
- [ ] **Selenium E2E 测试 100% 通过**
- [ ] progress.md 已更新

### Phase 7: 完善微服务架构 (P2 - 可扩展性)
<!--
  WHAT: 完善微服务治理能力
  WHY: 当前微服务标记为Beta，缺少服务治理
-->
- [ ] 添加服务注册发现机制
- [ ] 实现熔断器模式
- [ ] 添加负载均衡
- [ ] 实现配置热更新
- [ ] 添加服务间认证
- [ ] **🔴 E2E 验证**：运行两种模式的 official_e2e_test.py
- [ ] **Status:** pending
- **预计工作量:** 10-15天
- **预期收益:** 可扩展性+50%

#### Phase 7 E2E 测试结果（待执行）
| 测试 | 结果 | 状态 |
|------|------|------|
| Playwright 模式 | 待执行 | ⏳ |
| Selenium 模式 | 待执行 | ⏳ |

#### Phase 7 出口检查清单
- [ ] 微服务治理功能完成
- [ ] 所有单元测试通过
- [ ] **Playwright E2E 测试 100% 通过**
- [ ] **Selenium E2E 测试 100% 通过**
- [ ] progress.md 已更新

### Phase 8: 统一错误处理 (P2 - 一致性)
<!--
  WHAT: 建立统一的错误处理体系
  WHY: 当前错误处理不一致
-->
- [ ] 设计错误层次结构
  - [ ] errors/base.py - 基础错误类
  - [ ] errors/downloader.py - 下载错误
  - [ ] errors/browser.py - 浏览器错误
  - [ ] error_handler.py - 全局处理器
- [ ] 实现统一错误处理
- [ ] 更新所有模块使用新错误体系
- [ ] **🔴 E2E 验证**：运行两种模式的 official_e2e_test.py
- [ ] **Status:** pending
- **预计工作量:** 5天
- **预期收益:** 一致性+40%

#### Phase 8 E2E 测试结果（待执行）
| 测试 | 结果 | 状态 |
|------|------|------|
| Playwright 模式 | 待执行 | ⏳ |
| Selenium 模式 | 待执行 | ⏳ |

#### Phase 8 出口检查清单
- [ ] 统一错误处理体系完成
- [ ] 所有模块使用新错误体系
- [ ] 所有单元测试通过
- [ ] **Playwright E2E 测试 100% 通过**
- [ ] **Selenium E2E 测试 100% 通过**
- [ ] progress.md 已更新

### Phase 9: 最终验证与评估
<!--
  WHAT: 验证所有改进并重新评估项目
  WHY: 确保所有改进有效，达到目标评分
-->
- [ ] 运行完整测试套件
  - [ ] 单元测试 (626+)
  - [ ] E2E测试 (Playwright + Selenium)
  - [ ] 覆盖率测试 (目标60%+)
- [ ] 代码质量检查
  - [ ] mypy类型检查 (0错误)
  - [ ] black/isort格式检查
  - [ ] 空except块检查 (0个)
- [ ] 重新评估项目
  - [ ] 架构设计
  - [ ] 代码质量
  - [ ] 测试覆盖
  - [ ] 文档完整
  - [ ] 基础设施
- [ ] 生成最终改进报告
- [ ] **🔴 E2E 验证**：运行两种模式的 official_e2e_test.py（最终验证）
- [ ] **Status:** pending
- **预计工作量:** 1-2天
- **预期收益:** 确认达到9.0/10目标

#### Phase 9 最终 E2E 测试结果（待执行）
| 测试 | 结果 | 状态 |
|------|------|------|
| Playwright 模式 | 待执行 | ⏳ |
| Selenium 模式 | 待执行 | ⏳ |

#### Phase 9 出口检查清单
- [ ] 所有测试套件通过
- [ ] 覆盖率 ≥ 60%
- [ ] mypy 检查 0 错误
- [ ] 空except块 0 个
- [ ] **Playwright E2E 测试 100% 通过**
- [ ] **Selenium E2E 测试 100% 通过**
- [ ] 综合评分 ≥ 9.0/10
- [ ] 最终改进报告生成

## Key Questions
1. ConfigManager拆分时如何保持向后兼容？
   → 使用适配器模式，旧API调用新实现
2. 测试覆盖率提升时是否需要重写现有测试？
   → 优先为0%覆盖模块添加测试，现有测试保持稳定
3. 微服务完善是否影响单体模式？
   → 保持单体模式作为默认，微服务作为可选部署方式
4. 如何平衡改进速度和稳定性？
   → 每个Phase完成后必须运行E2E测试验证

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 优先修复空except块 | 影响代码稳定性，风险最高 |
| 拆分ConfigManager而非重写 | 保持向后兼容，降低风险 |
| 测试覆盖率目标60%而非80% | 平衡工作量和收益 |
| 微服务标记为可选 | 不强制所有用户使用微服务 |
| 每个Phase后E2E验证 | 确保改进不破坏现有功能 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| (待记录) | 1 | (待记录) |

## 依赖关系
```
Phase 1 (空except块)
    ↓
Phase 2 (ConfigManager) ←→ Phase 3 (测试覆盖)
    ↓
Phase 4 (类型注解) ←→ Phase 5 (文档)
    ↓
Phase 6 (UnifiedDownloader)
    ↓
Phase 7 (微服务) ←→ Phase 8 (错误处理)
    ↓
Phase 9 (最终验证)
```

## 成功指标
- [ ] 空except块: 20处 → 0处
- [ ] 测试覆盖率: 35.49% → 60%+
- [ ] 类型注解覆盖: ~50% → 80%+
- [ ] E2E测试: 100% 通过 (保持)
- [ ] 综合评分: 8.14/10 → 9.0/10

## Notes
- 每个Phase完成后必须运行E2E测试验证
- 保持向后兼容性是重要原则
- 记录所有决策到findings.md
- 更新progress.md跟踪每日进展
- 使用TodoWrite工具跟踪任务状态
