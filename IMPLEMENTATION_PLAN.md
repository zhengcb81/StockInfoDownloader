# Stock Downloader V2 — 实施计划

> 基于对 StockInfoDownloader 的全面审查，从零构建精简、高效的替代版本。
> 核心原则：只保留 Playwright，删除所有过度抽象，500 行搞定 29,000 行的事。

---

## 目标

1. 仅保留 Playwright 浏览器引擎（删除 Selenium）
2. 保留全部功能：org_id 爬取、股票名查询、多页下载、反序遍历、关键词过滤、跳过已存在文件
3. 保留原有 E2E 测试套件（适配新路径）
4. 每个大阶段结束前 E2E 测试必须 100% 通过
5. 补全文档

---

## 架构设计（新 vs 旧）

```
旧 (29,000 行, 205 类, 32 配置文件):
  src/core/       6 文件 config + 8 文件 exceptions + logger + monitoring + ...
  src/web/        4 个策略实现 + 反爬虫包 + driver pool + proxy + scraper + ...
  src/services/   unified_downloader + 8 个 service + download_helpers
  src/factory/    downloader_factory (300 行)
  src/adapters/   legacy_downloader_adapter
  src/interfaces/ downloader_interface (200 行)
  src/abstracts/  base_downloader (380 行)
  微服务 5 个 Docker 容器

新 (~2,000 行, ~15 类, 2 配置文件):
  src/
    config.py          # 配置加载 + 常量 (~80 行)
    browser.py         # Playwright 包装 (~200 行)
    downloader.py      # 核心下载逻辑 (~350 行)
    mapping.py         # 股票代码 → org_id 映射 (~200 行)
    models.py          # 数据模型 (~60 行)
    storage.py         # JSON 存储 (~50 行)
    orgid.py           # org_id 爬取服务 (~100 行)
    stock.py           # 股票名称查询 (~80 行)
    file_utils.py      # 文件名清理、目录管理 (~60 行)
    logger.py          # 日志 (~30 行)
    exceptions.py      # 异常定义 (~40 行)
  main.py             # CLI 入口 (~100 行)
  config.json         # 运行配置
```

---

## 实施阶段

### Phase 1: 项目骨架 + 配置系统
- 创建目录结构
- config.py: 配置加载（从 JSON 读取，提供默认值）
- constants.py: URL 模板、选择器、超时常量
- logger.py: 简洁日志配置
- exceptions.py: 5-6 个具体异常类

### Phase 2: 数据层 + 单元测试
- models.py: OrgIdMapping, DownloadRequest, DownloadResult dataclass
- storage.py: JsonStorage (load/save JSON)
- mapping.py: MappingManager（从原项目移植，保留全部功能）
  - 本地映射查找
  - 网络爬取 org_id
  - 股票名称获取
  - 映射持久化
- 单元测试：mapping, storage, models

### Phase 3: 浏览器层 + 单元测试
- browser.py: PlaywrightBrowser 类（不抽象，直接封装 Playwright）
  - navigate, execute_script, find_elements, download_file, go_to_next_page, etc.
  - 反爬虫：随机延迟、User-Agent 轮换
- orgid.py: OrgIdCrawler（从原 OrgIdService 移植，仅用 Playwright）
- stock.py: StockNameService（从原 StockService 移植）
- 单元测试

### Phase 4: 核心下载逻辑 + 单元测试
- downloader.py: StockDownloader 类
  - download(): 主入口，接收 DownloadRequest
  - _download_page(): 单页下载
  - _download_file(): 单文件下载
  - _handle_pagination(): 翻页逻辑（正序/反序）
  - keyword matching, skip existing files
  - retry logic
- file_utils.py: clean_filename, ensure_directory
- 单元测试

### Phase 5: 入口点
- main.py: CLI 入口
  - 支持命令行 stock_code
  - 支持 config.json test_cases / companies
  - 支持 --parallel, --workers
  - 兼容 config_e2e_official.json 格式

### Phase 6: E2E 测试迁移 (关键阶段)
- 将 tests/e2e/ 和 end2end_test/ 复制到新项目
- 更新 import 路径指向新模块
- 迁移 tests/utils/ (CleanerTool)
- 迁移 tests/test_config.py (EnvironmentManager)
- 迁移 tests/fake_browser_strategy.py
- 运行 E2E 测试，必须 100% 通过

### Phase 7: 文档
- README.md
- ARCHITECTURE.md
- CONFIGURATION.md
- API.md
- CHANGELOG.md

---

## E2E 测试兼容性分析

E2E 测试期望的接口：
1. `main.py --config config_e2e_official.json` — subprocess 调用
2. `config_e2e_official.json` 格式：test_cases 列表，每个有 stock_code, suffix, allowed_keywords, max_pages, reverse_order
3. 下载文件到 `end2end_test/test_results/{公司名}/` 目录
4. 与 `end2end_test/expected_results/` 比较

直接导入的 E2E 测试：
- `test_pagination_behavior.py` → `PaginationHandler`
- `test_skip_existing_files.py` → `UnifiedDownloader`, `DownloadRequest`
- `test_dual_browser_modes.py` → `DownloadServiceV2Adapter` (需改写或跳过)

解决方案：
- 新代码提供 `src.interfaces` 兼容层（PaginationHandler, DownloadRequest 等）
- `test_dual_browser_modes.py` 涉及 Selenium，标记为 skip 或改写为 Playwright-only
- `official_e2e_test.py` 只需 main.py 兼容即可
