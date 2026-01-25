# StockInfoDownloader 代码规范指南

## 📝 代码规范概述

本项目遵循以下代码规范，确保代码质量和一致性。

## 🔧 编码风格

### 1. 命名规范

#### 类名
- 使用 `PascalCase`
- 应该是名词或名词短语
- 示例：`ConfigManager`, `BrowserService`, `FileService`

#### 函数和方法名
- 使用 `snake_case`
- 应该是动词或动词短语
- 示例：`download_stock_pdfs`, `setup_driver`, `validate_params`

#### 变量名
- 使用 `snake_case`
- 应该是有意义的名称
- 示例：`stock_code`, `download_count`, `config_manager`

#### 常量
- 使用 `UPPER_SNAKE_CASE`
- 示例：`BASE_URL`, `DEFAULT_TIMEOUTS`, `MAX_RETRIES`

### 2. 文档字符串

#### 类文档
```python
class ConfigManager:
    """配置管理器

    提供统一的配置加载和管理功能，支持多环境配置。
    """
```

#### 方法文档
```python
def load_config(self, config_path: str = "config.json") -> Dict[str, Any]:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        Dict[str, Any]: 配置字典

    Raises:
        ConfigError: 配置文件加载失败
    """
```

### 3. 类型注解

- 所有公共方法都应该有类型注解
- 使用 `typing` 模块中的类型
- 示例：
```python
from typing import Dict, Any, Optional, List

def get_test_stock(self, stock_code: str) -> Dict[str, str]:
    pass
```

## 🚨 异常处理规范

### 1. 异常类型层次

```python
# 自定义异常基类
class StockDownloaderError(Exception):
    """股票下载器异常基类"""
    pass

class ConfigError(StockDownloaderError):
    """配置相关异常"""
    pass

class DownloadError(StockDownloaderError):
    """下载相关异常"""
    pass

class BrowserError(StockDownloaderError):
    """浏览器相关异常"""
    pass
```

### 2. 异常处理原则

#### 捕获特定异常
```python
# ❌ 不好的做法
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"操作失败: {e}")

# ✅ 好的做法
try:
    result = risky_operation()
except ConfigError as e:
    logger.error(f"配置错误: {e}")
except DownloadError as e:
    logger.error(f"下载错误: {e}")
except TimeoutError as e:
    logger.warning(f"操作超时: {e}")
```

#### 记录足够的上下文
```python
try:
    result = download_file(url)
except Exception as e:
    logger.error(f"下载文件失败: URL={url}, 错误={str(e)}, 类型={type(e).__name__}")
    raise DownloadError(f"下载文件失败: {url}") from e
```

#### 避免空的 except 块
```python
# ❌ 不好的做法
try:
    operation()
except:
    pass

# ✅ 好的做法
try:
    operation()
except Exception as e:
    logger.debug(f"操作失败但可忽略: {e}")
```

### 3. 资源管理

#### 使用上下文管理器
```python
# ✅ 好的做法
with BrowserService() as browser:
    result = browser.download_files()

# ✅ 好的做法（自定义上下文管理器）
class DownloaderContext:
    def __enter__(self):
        self.driver = setup_driver()
        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()

# 使用
with DownloaderContext() as driver:
    driver.get(url)
```

#### finally 块确保清理
```python
driver = None
try:
    driver = setup_driver()
    result = perform_operation(driver)
finally:
    if driver:
        driver.quit()
```

## 📁 文件组织规范

### 1. 目录结构

```
src/
├── core/                    # 核心模块
│   ├── config.py           # 配置管理
│   ├── exceptions.py       # 异常定义
│   ├── logger.py          # 日志管理
│   └── config_constants.py # 配置常量
├── services/              # 服务层
│   ├── browser_service.py # 浏览器服务
│   ├── file_service.py    # 文件服务
│   └── downloader.py     # 下载服务
├── web/                   # Web相关
│   ├── driver.py          # 驱动管理
│   ├── scraper.py         # 页面抓取
│   └── anti_crawler.py    # 反爬虫
├── data/                  # 数据层
│   ├── models.py          # 数据模型
│   ├── mapping.py         # 数据映射
│   └── storage.py         # 数据存储
└── utils/                 # 工具层
    ├── validation.py      # 验证工具
    └── keyword_matcher.py # 关键词匹配
```

### 2. 文件命名

- 使用 `snake_case`
- 模块文件名应该简短且描述性强
- 示例：`config_manager.py`, `browser_service.py`, `file_validator.py`

### 3. 导入规范

#### 标准库导入
```python
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
```

#### 第三方库导入
```python
from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
```

#### 本地模块导入
```python
from ..core.logger import get_logger
from ..core.config import ConfigManager
from ..services.browser_service import BrowserService
```

#### 避免循环导入
- 使用延迟导入解决循环依赖
- 在函数内部导入而不是在文件顶部

## 🧪 测试规范

### 1. 测试文件命名

- 单元测试：`test_<module_name>.py`
- 集成测试：`test_<feature>_integration.py`
- 端到端测试：`test_<feature>_e2e.py`

### 2. 测试类和方法

```python
import unittest
from unittest.mock import Mock, patch

class TestConfigManager(unittest.TestCase):
    """配置管理器测试"""

    def setUp(self):
        """测试前置设置"""
        self.config_manager = ConfigManager()

    def tearDown(self):
        """测试后置清理"""
        # 清理测试数据
        pass

    def test_load_config_success(self):
        """测试配置文件加载成功"""
        # 测试逻辑
        pass

    @patch('os.path.exists')
    def test_load_config_file_not_found(self, mock_exists):
        """测试配置文件不存在的情况"""
        mock_exists.return_value = False
        # 测试逻辑
        pass
```

### 3. 测试数据管理

- 使用配置文件管理测试数据
- 避免在测试代码中硬编码
- 示例：
```python
def test_download_with_test_data(self):
    test_config = test_config_manager.get_test_stock("300470")
    stock_code = test_config['code']
    org_id = test_config['org_id']
    # 使用测试数据进行测试
```

## 🔧 配置管理规范

### 1. 配置文件结构

```json
{
  "environment": "production",
  "base_url": "https://www.cninfo.com.cn",
  "timeout": {
    "page_load": 30,
    "element_wait": 10,
    "download": 180
  },
  "browser": {
    "strategy": "playwright",
    "headless": true,
    "window_size": "1920,1080"
  }
}
```

### 2. 配置访问方式

```python
# ✅ 好的做法 - 使用配置管理器
config_manager = ConfigManager()
timeout = config_manager.get('timeout.page_load', 30)
base_url = config_manager.get('base_url')

# ❌ 不好的做法 - 直接硬编码
timeout = 30
base_url = "https://www.cninfo.com.cn"
```

## 📊 日志规范

### 1. 日志级别使用

- **DEBUG**: 详细的调试信息
- **INFO**: 一般信息（操作开始、成功等）
- **WARNING**: 警告信息（可恢复的错误）
- **ERROR**: 错误信息（需要关注的错误）
- **CRITICAL**: 严重错误（系统级别的错误）

### 2. 日志格式

```python
import logging

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# 记录日志
logger.info(f"开始下载股票 {stock_code} 的文件")
logger.error(f"下载失败: {error_message}")
logger.debug(f"详细调试信息: {debug_data}")
```

## 🔄 代码审查清单

### 提交前检查

- [ ] 代码符合命名规范
- [ ] 所有公共方法都有类型注解
- [ ] 所有公共方法都有文档字符串
- [ ] 异常处理恰当且不捕获过宽的异常
- [ ] 资源正确释放（使用上下文管理器或 finally）
- [ ] 没有硬编码的值（使用配置文件）
- [ ] 日志记录适当且信息充分
- [ ] 测试覆盖主要功能
- [ ] 代码简洁且易于理解

### 性能考虑

- [ ] 避免在循环中进行昂贵的操作
- [ ] 使用生成器处理大数据集
- [ ] 缓存重复计算的结果
- [ ] 合理使用并发（如果适用）

### 安全考虑

- [ ] 不记录敏感信息（密码、密钥等）
- [ ] 输入验证充分
- [ ] 文件路径安全性检查
- [ ] 网络请求超时设置

---

遵循这些规范将确保代码的一致性、可维护性和质量。请所有开发者在编写代码时参考此指南。