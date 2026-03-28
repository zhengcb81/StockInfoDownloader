# StockInfoDownloader 架构重构计划

基于代码审查报告，实施以下架构重构。

---

## Phase 1: 消除重复 (已完成 ✅)

### 1.1 合并 ErrorHandler 类

**状态**: ✅ 已完成

**修改文件**:
- `src/core/exceptions.py` - 修复 print 语句，替换为 logging

**具体修改**:
- 第565行: `print(...)` → `logger.error(...)`
- 第588行: `print(...)` → `logger.error(...)`
- 第619-628行: 所有 print 语句 → logger.* 语句
- ErrorHandler 添加 `self.logger = logger` 实例属性

**保留现状**:
- `error_handling.py` - 基础工具模块
- `exceptions.py` - 异常类层次结构
- `enhanced_error_handler.py` - 高级功能（电路断路器）
- 三者用途不同，保持分离但统一错误处理风格

---

### 1.2 修复 ConfigManager 单例测试污染

**状态**: ✅ 已完成

**修改文件**:
- `src/core/config_manager.py`

**具体修改**:
添加 `reset_singleton()` 类方法:
```python
@classmethod
def reset_singleton(cls) -> None:
    """Reset the singleton state - useful for test isolation."""
    cls._instance = None
    cls._config = {}
    cls._global_config = GlobalConfig()
```

---

### 1.3 拆分 UnifiedDownloader

**状态**: ✅ 已完成

**新增文件**:
- `src/services/download_helpers.py`

**提取的类**:
| 类名 | 职责 | 原位置 |
|------|------|--------|
| `KeywordMatcher` | 关键词匹配 | `_matches()` 方法 |
| `LinkExtractor` | 链接提取 | `_get_links_safe()` 方法 |
| `PaginationHandler` | 分页导航 | `_perform_download()` 内联逻辑 |
| `DownloadHistoryTracker` | 下载历史 | `self.history` 列表 |

**UnifiedDownloader 现在**:
- 使用 helper 类处理具体逻辑
- 保留协调职责
- 代码行数减少

---

### 1.4 澄清重复 RateLimiter

**状态**: ✅ 已完成

**修改文件**:
- `src/web/anti_crawler/rate_limiter.py`

**说明**:
| 模块 | 用途 | API 风格 |
|------|------|---------|
| `src/web/rate_limiter.py` | 通用速率限制 | 阻塞式 `wait_if_needed()` |
| `src/web/anti_crawler/rate_limiter.py` | 反爬虫专用 | 非阻塞 `can_make_request()` + `record_request()` |

---

## Phase 2: 简化复杂度 (待实施)

### 2.1 重构 BaseConfigManager 单例模式

**问题**: 类级别可变状态可能跨测试持久化

**建议方案**:
```python
# 选项 A: 使用 pytest fixtures 进行依赖注入
@pytest.fixture
def config_manager():
    manager = BaseConfigManager()
    yield manager
    manager.reset_singleton()  # 清理

# 选项 B: 保留 reset_singleton() 供测试使用
```

### 2.2 合并分页逻辑

**问题**: `scraper.py` 和 `unified_downloader.py` 都有分页逻辑

**建议**:
- `PaginationHandler` 使用 `scraper.py` 的 `go_to_next_page()`
- 统一定义分页接口

### 2.3 减少 cast() 过度使用

**问题**:
```python
cast(Optional[IBrowserStrategy], ...)
cast(list, result)
```

**建议**:
- 重新设计类型层次
- 使用泛型或协议类型
- 避免绕过类型检查

---

## Phase 3: 提升质量 (待实施)

### 3.1 统一文档语言

**问题**: 部分 docstring 使用中文，部分使用英文

**建议**:
- 统一项目内所有 docstring 为英文
- 影响文件：大部分 src 文件

### 3.2 移除 type: ignore 滥用

**问题**: 使用 `# type: ignore` 绕过类型检查而非修复问题

**建议**:
- 逐个检查 `type: ignore` 注释
- 修复底层类型问题

### 3.3 提升测试覆盖率

**当前**: 35-40%
**目标**: 60%+

---

## Phase 4: 文档重构 (待实施)

### 4.1 重构 README.md

**问题**:
- README.md 缺乏结构化
- 大量文字缺乏表格和锚点导航

**建议**:
- 使用表格展示功能
- 添加锚点导航
- 精简冗长描述

### 4.2 添加 API 使用示例

**问题**: API 文档缺少使用示例

### 4.3 建立文档索引

**问题**: `docs/adr/` 目录有决策记录但未索引

---

## 任务清单

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 合并 ErrorHandler | 高 | ✅ 完成 |
| 修复 ConfigManager 单例 | 高 | ✅ 完成 |
| 拆分 UnifiedDownloader | 高 | ✅ 完成 |
| 澄清 RateLimiter | 高 | ✅ 完成 |
| 统一文档语言为英文 | 中 | ⏳ 待实施 |
| 减少 cast() 使用 | 中 | ⏳ 待实施 |
| 合并分页逻辑 | 中 | ⏳ 待实施 |
| 重构 README | 低 | ⏳ 待实施 |

---

*创建时间: 2026-03-18*
