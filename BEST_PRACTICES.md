# StockInfoDownloader 最佳实践

本文档提供使用 StockInfoDownloader 的最佳实践建议。

## 配置管理

### 1. 使用环境变量

敏感信息（如密码、API密钥）应该通过环境变量传递，而不是硬编码在配置文件中：

```bash
# .env 文件
GF_SECURITY_ADMIN_PASSWORD=your_secure_password
PROXY_PASSWORD=your_proxy_password
```

```json
// config.json - 使用环境变量引用
{
  "proxy": {
    "password": "${PROXY_PASSWORD}"
  }
}
```

### 2. 配置文件分层

建议将配置分为多个层次：

```
configs/
├── base.json          # 基础配置
├── development.json   # 开发环境配置
├── production.json    # 生产环境配置
└── test.json          # 测试环境配置
```

### 3. 配置验证

在应用启动前验证配置：

```python
from src.core.config import ConfigManager

config_manager = ConfigManager()
config = config_manager.load_config("config.json")

# 验证关键配置
assert config.get("save_dir"), "save_dir is required"
assert config.get("browser", {}).get("strategy"), "browser strategy is required"
```

## 下载策略

### 1. 选择合适的浏览器策略

| 策略 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| Playwright | 速度快、API现代 | 依赖较多 | 生产环境、并行下载 |
| Selenium | 兼容性好、社区成熟 | 速度较慢 | 兼容性要求高 |

```python
# 使用 Playwright (推荐)
python main.py --browser-strategy=playwright

# 使用 Selenium
python main.py --browser-strategy=selenium
```

### 2. 并行下载配置

```bash
# 根据系统资源调整 worker 数量
# CPU 密集型: workers = CPU 核心数
# IO 密集型: workers = 2 * CPU 核心数

python main.py --parallel --workers 3
```

### 3. 反爬虫策略

```json
{
  "anti_crawler": {
    "enabled": true,
    "base_delay": 1.0,
    "random_delay_range": [0.5, 2.0],
    "session_limit": 50,
    "max_retries": 3
  }
}
```

## 错误处理

### 1. 使用自定义异常

```python
from src.core.exceptions import DownloadError, BrowserError, ConfigError

try:
    downloader.download_stock_pdfs(request)
except DownloadError as e:
    logger.error(f"下载失败: {e}")
except BrowserError as e:
    logger.error(f"浏览器错误: {e}")
except ConfigError as e:
    logger.error(f"配置错误: {e}")
```

### 2. 重试机制

```python
from src.core.exceptions import with_error_handling, RecoveryStrategy

@with_error_handling(
    error_code=ErrorCode.DOWNLOAD_NETWORK_ERROR,
    recovery_strategy=RecoveryStrategy.RETRY
)
def download_with_retry(url: str, max_retries: int = 3) -> bool:
    # 实现重试逻辑
    pass
```

### 3. 资源清理

```python
# 使用 context manager
with downloader_factory.create_downloader() as downloader:
    downloader.download_stock_pdfs(request)
# 自动清理资源

# 或者手动清理
try:
    downloader.download_stock_pdfs(request)
finally:
    downloader.cleanup()
```

## 日志管理

### 1. 日志级别配置

```json
{
  "logging": {
    "level": "INFO",
    "log_to_file": true,
    "log_file": "logs/downloader.log",
    "max_file_size": 10485760,
    "backup_count": 5
  }
}
```

### 2. 结构化日志

```python
from src.core.logger import get_logger

logger = get_logger(__name__)

# 使用结构化日志
logger.info("下载完成", extra={
    "stock_code": "000001",
    "files_count": 10,
    "duration": 120.5
})
```

## 性能优化

### 1. 浏览器池

```json
{
  "browser": {
    "pool_size": 3,
    "max_session_downloads": 20
  }
}
```

### 2. 缓存策略

```json
{
  "cache": {
    "enabled": true,
    "ttl": 3600,
    "max_size": 1000
  }
}
```

### 3. 增量下载

```json
{
  "download": {
    "skip_existing": true,
    "validate_downloads": true
  }
}
```

## 测试策略

### 1. 单元测试

```python
import pytest
from unittest.mock import MagicMock, patch

def test_download_stock_pdfs():
    with patch("src.web.browser_strategy.BrowserStrategyFactory") as mock:
        downloader = UnifiedDownloader(config={"skip_browser_init": True})
        # 测试逻辑
```

### 2. E2E 测试

```bash
# 每次代码变更后运行 E2E 测试
python tests/e2e/official_e2e_test.py --browser-strategy=playwright
python tests/e2e/official_e2e_test.py --browser-strategy=selenium
```

## 常见陷阱

### 1. 不要在循环中创建浏览器实例

```python
# ❌ 错误
for stock_code in stock_codes:
    downloader = UnifiedDownloader()
    downloader.download_stock_pdfs(stock_code)

# ✅ 正确
downloader = UnifiedDownloader()
for stock_code in stock_codes:
    downloader.download_stock_pdfs(stock_code)
downloader.cleanup()
```

### 2. 不要忽略异常

```python
# ❌ 错误
try:
    risky_operation()
except:
    pass

# ✅ 正确
try:
    risky_operation()
except SpecificError as e:
    logger.error(f"操作失败: {e}")
    # 适当的恢复逻辑
```

### 3. 不要硬编码配置

```python
# ❌ 错误
BASE_URL = "https://www.cninfo.com.cn"
TIMEOUT = 30

# ✅ 正确
from src.core.config_constants import ConfigConstants

BASE_URL = ConfigConstants.BASE_URL
TIMEOUT = ConfigConstants.TIMEOUT_CONFIG["page_load"]
```
