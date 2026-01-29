# StockInfoDownloader 开发指南

## 核心原则 (Core Principles)

1.  **先理解后行动 (Understand First)**
    *   在修改代码前，仔细阅读相关业务逻辑和测试。
    *   不做无根据的假设，使用 `read_file` 或 `grep` 验证代码现状。

2.  **计划驱动 (Plan Driven)**
    *   维护 `progress.md` 和 `task_plan.md`。
    *   每完成一个阶段的任务，更新进度文件。

3.  **配置驱动 (Configuration Driven)**
    *   **严禁硬编码**：URL、超时时间、XPath 选择器、反爬参数等必须定义在 `configs/business_rules.json` 中。
    *   使用 `src.core.config_constants.ConfigConstants` 访问这些配置。
    *   微服务地址必须通过环境变量配置（如 `os.getenv("DOWNLOAD_SERVICE_HOST")`）。

4.  **类型安全 (Type Safety)**
    *   新代码必须包含完整的类型注解 (Type Hints)。
    *   通过 `mypy src/` 检查类型一致性。

5.  **原子化提交 (Atomic Commits)**
    *   每次修改应保持原子性，确保单一职责。
    *   提交前必须通过相关单元测试。

## 测试协议 (Testing Protocol)

1.  **E2E 优先 (E2E First)**
    *   任何核心逻辑修改后，必须运行官方端到端测试：
        ```bash
        # Playwright 模式
        python tests/e2e/official_e2e_test.py --browser-strategy=playwright
        
        # Selenium 模式
        python tests/e2e/official_e2e_test.py --browser-strategy=selenium
        ```
    *   **验收标准**：必须看到 "Perfect match" 字样，且无报错。

2.  **回归测试 (Regression)**
    *   运行所有单元测试：`python tests/run_tests.py`。
    *   确保 540+ 个测试用例全部通过。

3.  **性能监控 (Performance)**
    *   涉及性能优化的修改，需运行 `python tests/performance_test_runner.py`。

## 代码规范 (Code Standards)

1.  **日志记录 (Logging)**
    *   使用 `src.core.logger.get_logger(__name__)`。
    *   日志文件支持 UTF-8 编码，确保中文不乱码。

2.  **异常处理 (Error Handling)**
    *   使用 `src.core.exceptions` 中的自定义异常。
    *   关键业务逻辑使用 `@with_error_handling` 装饰器。

3.  **资源清理 (Cleanup)**
    *   浏览器驱动、临时文件必须在 `finally` 块或 `context manager` (`with` 语句) 中清理。
    *   使用 `src.utils.cleanup_utils` 提供的工具函数。

4.  **导入规范 (Imports)**
    *   顺序：标准库 -> 第三方库 -> 项目本地模块。
    *   本地模块推荐使用绝对导入 `src.xxx`。

## 常用命令 (Cheat Sheet)

| 任务 | 命令 |
| :--- | :--- |
| **单元测试** | `pytest tests/unit/` |
| **E2E 测试 (Playwright)** | `python tests/e2e/official_e2e_test.py --browser-strategy=playwright` |
| **E2E 测试 (Selenium)** | `python tests/e2e/official_e2e_test.py --browser-strategy=selenium` |
| **类型检查** | `mypy src/ --ignore-missing-imports` |
| **代码格式化** | `black .` 和 `isort .` |
| **覆盖率检查** | `pytest --cov=src tests/` |
| **运行微服务网关** | `python microservices/api-gateway/gateway.py` |

## 目录结构说明

*   `src/`: 核心源代码
    *   `core/`: 基础组件 (日志, 配置, 异常)
    *   `services/`: 业务服务 (下载, 验证, 文件)
    *   `web/`: 爬虫与浏览器策略
    *   `adapters/`: 兼容性适配器
*   `configs/`: 配置文件 (JSON)
*   `tests/`: 测试套件
    *   `unit/`: 单元测试
    *   `e2e/`: 端到端测试
    *   `integration/`: 集成测试
*   `microservices/`: 微服务实现
*   `docs/`: 项目文档
