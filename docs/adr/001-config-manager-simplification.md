# ADR 001: ConfigManager 职责边界与简化策略

**状态**: 已接受  
**日期**: 2026-02-01  
**作者**: StockInfoDownloader Team

## 背景

ConfigManager 类当前包含 937 行代码和 46 个方法，职责涵盖：
- 基础配置加载/保存
- 多公司配置管理
- 测试配置管理

这违反了单一职责原则，维护困难。

## 决策

**采用文档化边界方案（方案 B）**，暂缓完全拆分。

### 考虑的方案

#### 方案 A: 完全拆分
将 ConfigManager 拆分为三个类：
- `ConfigManager`: 基础配置管理
- `CompanyConfigManager`: 多公司配置管理  
- `TestConfigManager`: 测试配置管理

**优点**: 职责清晰，符合 SOLID 原则
**缺点**: 
- 需要修改 20+ 个调用点
- 风险高，可能引入新 bug
- 需要 3-5 天工作量

#### 方案 B: 文档化边界（选中）
在 ConfigManager 中添加清晰的职责分区注释，明确各区域边界。

**优点**:
- 零风险，立即生效
- 成本低（1 小时工作量）
- 为将来拆分提供路线图

**缺点**:
- 未从根本上解决问题
- 类仍然较大

## 决策理由

1. **稳定性优先**: 当前系统稳定，E2E 测试 100% 通过
2. **风险收益比**: 重构风险高于收益
3. **渐进改进**: 文档化是向完全拆分的第一步
4. **监控指标**: 如果类增长到 1000+ 行，再考虑拆分

## 实施

### 已完成
- [x] 添加职责分区注释到 ConfigManager
- [x] 创建 ADR 记录决策
- [x] 更新项目文档

### 代码示例

```python
class ConfigManager:
    """
    配置管理器 (Unified)
    
    职责范围（当前集中实现，未来可考虑拆分）：
    1. 基础配置管理（加载/保存/访问）- 核心职责
    2. 多公司配置管理（CRUD 操作）- 业务职责  
    3. 测试配置管理（测试环境专用）- 测试职责
    
    TODO: 如果该类继续增长超过 1000 行，考虑拆分为：
    - ConfigManager: 基础配置管理
    - CompanyConfigManager: 多公司配置管理
    - TestConfigManager: 测试配置管理
    """
```

## 后续监控

**重构触发条件**:
- ConfigManager 超过 1000 行
- 新增 5+ 个多公司相关方法
- 测试配置相关方法超过 15 个

**监控周期**: 每季度审查一次

## 相关链接

- [Phase 10 评估报告](../../PHASE10_ASSESSMENT.md)
- [ConfigManager 源码](../../src/core/config.py)
- [Code Standards](../core/CODE_STANDARDS.md)
