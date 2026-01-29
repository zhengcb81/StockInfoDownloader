# StockInfoDownloader 项目结构说明 (重构版)

## 项目概述
本项目是针对巨潮资讯网 (Cninfo) 的高度自动化下载引擎，经过大规模重构，实现了配置驱动、类型安全、多引擎支持（Playwright/Selenium）以及完善的异常恢复机制。

## 目录结构

### `/src` - 现代化模块化核心
```
src/
├── core/           # 基础设施层
│   ├── config.py           # 统一 ConfigManager，支持 Dataclass 同步
│   ├── config_definitions.py # 配置类型定义
│   ├── config_constants.py   # 配置常量（硬编码清理终点）
│   ├── logger.py           # 结构化日志
│   └── exceptions.py       # 异常分级与恢复策略
├── services/       # 业务服务层
│   ├── unified_downloader.py # 核心：统一下载器引擎
│   ├── validation_service.py # 下载结果验证
│   └── file_service.py       # 文件系统操作
├── factory/        # 工厂模式
│   └── downloader_factory.py # 下载器与策略的统一创建入口
├── web/            # 网络层
│   ├── browser_strategy.py   # 策略模式接口
│   ├── playwright_strategy.py # Playwright 实现 (推荐)
│   └── selenium_strategy.py   # Selenium 实现 (稳定)
├── adapters/       # 兼容层
│   └── legacy_downloader_adapter.py # 对接旧代码的适配器
└── data/           # 数据访问
    └── mapping.py          # 股票代码与 OrgID 映射管理
```

### `/tests` - 阶梯式测试体系
- **`unit/`**: 覆盖配置管理、数据映射、工厂模式等逻辑，540+ 测试。
- **`integration/`**: 验证下载器与本地文件系统的交互。
- **`e2e/`**: 
    - `official_e2e_test.py`: 核心端到端验证，支持 `--browser-strategy`。
- **`performance/`**: 批量下载压力测试。

### `/tools` - 生产辅助工具
- `protect_expected_results.py`: 锁定 E2E 测试的基准结果，防止污染。
- `run_protection.bat`: 一键保护测试基准。

## 核心组件流程

1. **初始化**: `ConfigManager` 加载 `config.json` 并同步到 `ConfigConstants`。
2. **工厂创建**: `DownloaderFactory` 根据配置选择 `BrowserStrategy` 并创建 `UnifiedDownloader`。
3. **任务路由**: `UnifiedDownloader` 生成 URL，通过 `BrowserStrategy` 执行导航和 SPA 切换。
4. **下载控制**: 支持 AJAX 数据等待、自动分页、验证码规避和下载后的文件重命名。
5. **异常恢复**: 遇到超时或崩溃时，根据 `exceptions.py` 定义的策略进行重启或重试。

## 关键技术点
- **Dataclass Config**: 配置项强类型化，IDE 友好且减少运行时错误。
- **SPA 兼容**: 针对 Vue/ElementUI 优化的分页逻辑和 Tab 切换。
- **Anti-Detection**: 集成多种反爬指纹修改，降低被封禁风险。
- **Encoding**: 完美支持中文路径、中文日志和 GBK/UTF-8 混合内容。

## 开发规范
参考 `docs/core/CLAUDE.md` 获取详细的编码和测试指南。
