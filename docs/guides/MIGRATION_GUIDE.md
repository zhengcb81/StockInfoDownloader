# 迁移指南 (Migration Guide)

本指南旨在帮助开发者、运维人员和用户适应 StockInfoDownloader 的最新变更。

---

## 目录

1. [代码架构迁移](#1-代码架构迁移)
2. [配置外置化](#2-配置外置化)
3. [微服务网关配置](#3-微服务网关配置)
4. [绝对路径清理](#4-绝对路径清理)
5. [常见问题](#5-常见问题)

---

## 1. 代码架构迁移

### 背景
项目已从早期的单文件脚本架构（如 `cninfo_activity_downloader.py`）迁移到了模块化的服务架构。

### 主要变更

#### 1.1 下载器接口
- **旧模式**: 实例化 `CninfoDownloader` 或 `DownloadServiceV1/V2`。
- **新模式**: 使用 `UnifiedDownloader` 或 `DownloaderFactory`。

```python
# 推荐：直接使用 UnifiedDownloader
from src.services.unified_downloader import UnifiedDownloader
from src.interfaces.downloader_interface import DownloadRequest

downloader = UnifiedDownloader({"save_dir": "downloads", "browser_strategy": "playwright"})
request = DownloadRequest(stock_code="300470", stock_name="中密控股")
result = downloader.download_stock_pdfs(request)

# 或使用工厂类
from src.factory.downloader_factory import downloader_factory
result = downloader_factory.create_downloader("unified", save_dir="downloads")
```

#### 1.2 配置管理
- **旧模式**: 直接读取 `config.json` 字典或硬编码。
- **新模式**: 使用 `ConfigManager` 和 `ConfigConstants`。

```python
from src.core.config import ConfigManager

config_manager = ConfigManager()
config = config_manager.get_all_config()
timeout = config.get("timeout", 30)
```

#### 1.3 适配器（向后兼容）
如果暂时不想修改调用方代码，可以使用适配器：

```python
from src.adapters.legacy_downloader_adapter import DownloadServiceV2Adapter

# 注意：适配器已标记为废弃，建议尽快迁移到 UnifiedDownloader
downloader = DownloadServiceV2Adapter(save_dir="downloads", browser_strategy="playwright")
```

---

## 2. 配置外置化 (Configuration Externalization)

### 变更说明
为了提高系统的灵活性，我们将原先硬编码在 Python 代码中的业务规则（如 URL、XPath 选择器、超时时间）移动到了外部 JSON 配置文件中。

*   **旧方式**: 修改 `src/core/config_constants.py` 中的 Python 常量。
*   **新方式**: 修改 `configs/business_rules.json` 文件。

### 如何迁移
如果您之前修改过源码中的选择器或超时时间，请检查 `configs/business_rules.json` 并确保您的自定义值已应用。

**`configs/business_rules.json` 结构**:

```json
{
  "urls": { ... },       // 基础 URL 和模板
  "selectors": { ... },  // XPath 选择器
  "anti_crawler": { ... }, // 反爬虫延迟配置
  "timeouts": { ... }    // 各类操作超时时间 (秒)
}
```

### 优势
*   **热更新**: 修改 JSON 文件后重启服务即可生效，无需重新打包代码。
*   **维护性**: 即使是不熟悉 Python 的运维人员也可以调整爬虫参数。

---

## 3. 微服务网关配置 (Gateway Configuration)

### 变更说明
API 网关 (`microservices/api-gateway/gateway.py`) 不再将子服务地址硬编码为 `localhost`。它现在优先读取环境变量，这使得在 Docker/K8s 环境中的部署变得极其简单。

### 环境变量清单

| 变量名 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `DOWNLOAD_SERVICE_HOST` | `localhost` | 下载服务主机地址 |
| `DOWNLOAD_SERVICE_PORT` | `8001` | 下载服务端口 |
| `CACHE_SERVICE_HOST` | `localhost` | 缓存服务主机地址 |
| `CACHE_SERVICE_PORT` | `8002` | 缓存服务端口 |
| `ERROR_SERVICE_HOST` | `localhost` | 错误服务主机地址 |
| `ERROR_SERVICE_PORT` | `8003` | 错误服务端口 |
| `CONFIG_SERVICE_HOST` | `localhost` | 配置服务主机地址 |
| `CONFIG_SERVICE_PORT` | `8004` | 配置服务端口 |

### Docker Compose 示例

在 `docker-compose.yml` 中，您现在可以这样配置网关：

```yaml
services:
  api-gateway:
    environment:
      - DOWNLOAD_SERVICE_HOST=download-service
      - CACHE_SERVICE_HOST=cache-service
      ...
```

---

## 4. 绝对路径清理

### 变更说明
项目文档和脚本中移除了所有特定用户的绝对路径（如 `C:\Users\...`）。现在使用相对路径或 `<PROJECT_ROOT>` 占位符。

### 影响
*   **新用户**: `git clone` 后无需修改文档中的路径即可运行命令。
*   **现有脚本**: 如果您有依赖绝对路径的个人脚本，请更新为使用相对路径。

---

## 5. 常见问题 (FAQ)

**Q: 我修改了 `business_rules.json` 但没生效？**
A: 请确保您修改的是 `configs/business_rules.json`，并且重启了应用程序。`ConfigConstants` 仅在模块初始化时加载一次配置。

**Q: 如果 `business_rules.json` 丢失了怎么办？**
A: 代码中保留了默认的硬编码值作为后备（Fallback），但建议保持该文件存在以确保配置的可见性。

**Q: E2E 测试失败，提示 "Element not interactable"？**
A: 尝试增加 `business_rules.json` 中的 `timeouts.element_wait` 值，或者检查 `selectors` 是否需要针对目标网站的更新进行调整。

**Q: 如何验证迁移是否成功？**
A: 运行以下命令验证：
```bash
# 类型检查
mypy src/ --ignore-missing-imports

# E2E 测试
python tests/e2e/official_e2e_test.py --browser-strategy=playwright
python tests/e2e/official_e2e_test.py --browser-strategy=selenium
```

---

## 已移除的文件 (Obsolete)

以下文件在重构过程中已被移除或替换：
- `src/core/config_backup.py`
- `tests/unit/test_cninfo_downloader.py` (已由 `test_basic.py` 覆盖)
- `tests/integration/test_web_scraper_integration.py` (已由 E2E 覆盖)

---

*最后更新: 2026-01-29*
