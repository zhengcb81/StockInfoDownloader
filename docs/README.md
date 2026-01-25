# StockInfoDownloader 项目文档库

欢迎查阅 **StockInfoDownloader** 官方文档。本项目是一个模块化、高可靠的巨潮资讯网股票信息自动化下载系统。

---

## 🧭 快速索引

### 1. [核心架构 (Core Architecture)](core/)
了解系统的灵魂：
- **[系统架构总览](core/MICROSERVICES_ARCHITECTURE.md)**: 微服务与模块化设计。
- **[代码规范](core/CODE_STANDARDS.md)**: 开发者提交代码的必读准则。
- **[更新日志](core/CHANGELOG.md)**: 记录每一次重大演进。

### 2. [开发与操作指南 (Guides)](guides/)
从入门到精通：
- **[浏览器策略选择](guides/BROWSER_STRATEGY_GUIDE.md)**: 深度对比 Playwright 与 Selenium。
- **[微服务快速启动](guides/MICROSERVICES_QUICKSTART.md)**: 分布式部署指南。
- **[CI/CD 自动化](guides/ci_cd.md)**: 持续集成与部署流程说明。
- **[保护ExpectedResults目录](guides/PROTECTING_EXPECTED_RESULTS.md)**: 防止测试目录被污染的长效方案。

### 3. [自动化测试体系 (Testing)](testing/)
质量保证的基石：
- **[测试总览 (Test Master)](testing/test_master.md)**: **[推荐]** 一站式掌握如何运行所有测试。
- **[官方 E2E 验收测试](testing/official_e2e_test.md)**: 业务规范的终极校验。
- **[测试技术规范](testing/test_specifications.md)**: 单元测试与集成测试的编写要求。

---

## 🚀 常用命令

| 任务 | 命令 |
| :--- | :--- |
| **启动主程序** | `python main.py <stock_code>` |
| **并发下载** | `python main.py --parallel --workers 5` |
| **全量质量校验** | `python tests/verify_modern_tests.py` |
| **运行开发者工具** | `python src/tools/cli.py --help` |

---

## 🗄️ [历史档案 (Archive)](archive/)
包含已完成阶段的重构报告、分页修复总结及早期测试记录。
