# 浏览器策略选择指南

## 📋 概述

本项目支持两种浏览器自动化框架：**Selenium** 和 **Playwright**。本文档提供两种策略的详细对比和使用指南。

## 🎯 策略对比

| 特性 | Selenium | Playwright |
|------|----------|------------|
| **安装复杂度** | ⭐⭐⭐⭐⭐ (简单) | ⭐⭐⭐⭐ (中等) |
| **稳定性** | ⭐⭐⭐⭐ (稳定) | ⭐⭐⭐⭐⭐ (非常稳定) |
| **性能** | ⭐⭐⭐⭐ (良好) | ⭐⭐⭐⭐⭐ (优秀) |
| **下载可靠性** | ⭐⭐⭐⭐ (可靠) | ⭐⭐⭐⭐⭐ (非常可靠) |
| **错误恢复** | ⭐⭐⭐ (一般) | ⭐⭐⭐⭐⭐ (优秀) |
| **社区支持** | ⭐⭐⭐⭐⭐ (丰富) | ⭐⭐⭐⭐ (良好) |

## 🔧 配置方式

### 1. 配置文件设置

在 `config.json` 中设置浏览器策略：

```json
{
  "browser": {
    "strategy": "selenium",  // 或 "playwright"
    "headless": true,
    "window_size": "1920,1080"
  },
  "download": {
    "max_retries": 3,
    "max_downloads_per_session": 5
  }
}
```

### 2. 代码中指定

```python
# 使用Selenium策略
downloader = DownloadServiceV2(browser_strategy="selenium")

# 使用Playwright策略  
downloader = DownloadServiceV2(browser_strategy="playwright")
```

### 3. 运行时切换

```python
# 运行时切换策略
downloader.switch_browser_strategy("playwright")
```

## 🚀 安装要求

### Selenium 策略
```bash
# 基础依赖
pip install selenium

# 需要Chrome浏览器和ChromeDriver
# 下载地址: https://chromedriver.chromium.org/
```

### Playwright 策略
```bash
# 安装Playwright
pip install playwright

# 安装浏览器二进制文件
playwright install chromium
```

## 📊 性能基准测试

### 测试结果（平均）

| 指标 | Selenium | Playwright |
|------|----------|------------|
| **初始化时间** | 2-3秒 | 1-2秒 |
| **页面加载时间** | 3-5秒 | 2-3秒 |
| **下载成功率** | 95% | 98% |
| **内存使用** | 中等 | 较低 |
| **崩溃率** | <5% | <1% |

## 🛠️ 使用场景推荐

### 推荐使用 Selenium 当：
- 项目已有Selenium基础架构
- 需要最大兼容性
- 开发团队熟悉Selenium
- 对性能要求不是极致

### 推荐使用 Playwright 当：
- 需要最高稳定性和性能
- 处理复杂JavaScript页面
- 需要更好的错误恢复机制
- 项目从零开始构建

## 🔍 详细功能对比

### 元素定位能力

**Selenium**:
- 支持CSS选择器、XPath、ID等
- 成熟的元素等待机制
- 广泛的社区支持

**Playwright**:
- 更快的元素定位速度
- 更好的动态内容处理
- 内置的智能等待机制

### 下载处理

**Selenium**:
- 自动下载到配置目录
- 需要手动检查文件完整性
- 依赖浏览器下载设置

**Playwright**:
- 精确的下载事件监听
- 直接文件保存控制
- 更好的下载状态监控

### 错误处理

**Selenium**:
- 基本的异常捕获
- 需要手动实现重试逻辑
- 浏览器崩溃恢复较复杂

**Playwright**:
- 内置的错误恢复机制
- 自动浏览器重启
- 详细的错误上下文信息

## 🧪 测试策略选择

### 端到端测试配置

在 `config_end2end_test.json` 中配置测试策略：

```json
{
  "test_cases": [
    {
      "stock_code": "300470",
      "suffix": "research",
      "browser_strategy": "selenium"  // 指定测试策略
    }
  ],
  "strategies_to_test": ["selenium", "playwright"]  // 测试所有策略
}
```

### 运行性能比较测试

```bash
# 测试所有策略
python e2e_test.py

# 输出示例:
浏览器策略性能比较:
  - SELENIUM:
      成功率: 95.0% (19/20)
      失败率: 5.0% (1/20)
      平均耗时: 45.2s
      平均文件数: 2.8 个/成功测试
  - PLAYWRIGHT:
      成功率: 98.0% (49/50)
      失败率: 2.0% (1/50)
      平均耗时: 32.1s
      平均文件数: 3.1 个/成功测试
```

## 🐛 常见问题排查

### Selenium 常见问题

1. **ChromeDriver版本不匹配**
   ```bash
   # 检查版本
   chromedriver --version
   google-chrome --version
   ```

2. **浏览器崩溃**
   - 增加内存参数
   - 减少并发下载数量
   - 启用无头模式

3. **元素定位失败**
   - 增加等待时间
   - 使用更稳定的选择器

### Playwright 常见问题

1. **浏览器安装失败**
   ```bash
   # 重新安装
   playwright install --force chromium
   ```

2. **下载事件超时**
   - 增加下载超时时间
   - 检查网络连接

3. **内存泄漏**
   - 定期重启浏览器
   - 监控内存使用情况

## 🔧 高级配置

### Selenium 高级配置

```python
# 自定义Chrome选项
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--no-sandbox')

# 自定义下载目录
prefs = {
    "download.default_directory": "/path/to/downloads",
    "download.prompt_for_download": False
}
chrome_options.add_experimental_option("prefs", prefs)
```

### Playwright 高级配置

```python
# 自定义启动选项
launch_options = {
    'headless': True,
    'args': [
        '--disable-dev-shm-usage',
        '--no-sandbox'
    ]
}

# 自定义上下文选项
context_options = {
    'viewport': {'width': 1920, 'height': 1080},
    'user_agent': 'Custom User Agent'
}
```

## 📈 监控和日志

### 策略性能监控

启用性能监控来跟踪各策略的表现：

```python
from src.core.performance_monitor import monitor_performance

@monitor_performance("strategy.operation")
def some_operation():
    # 操作代码
    pass
```

### 日志分析

查看策略相关的日志信息：

```bash
# 查看Selenium日志
grep "Selenium" logs/app.log

# 查看Playwright日志  
grep "Playwright" logs/app.log

# 查看性能指标
grep "performance" logs/app.log
```

## 🎯 最佳实践

1. **生产环境推荐**: 使用 Playwright，提供更好的稳定性和性能
2. **开发环境**: 可以根据熟悉程度选择 Selenium 或 Playwright
3. **测试策略**: 在CI/CD中测试所有策略确保兼容性
4. **监控**: 持续监控各策略的性能指标
5. **备份策略**: 实现策略故障时的自动切换

## 🔄 策略切换机制

项目支持运行时策略切换，当检测到当前策略频繁失败时：

```python
# 自动策略切换示例
if downloader.get_failure_count() > 3:
    current_strategy = downloader.get_current_strategy()
    alternative = "playwright" if current_strategy == "selenium" else "selenium"
    if downloader.switch_browser_strategy(alternative):
        logger.info(f"已自动切换到 {alternative} 策略")
```

## 📚 相关资源

- [Selenium 文档](https://www.selenium.dev/documentation/)
- [Playwright 文档](https://playwright.dev/python/docs/intro)
- [浏览器策略源码](src/web/)
- [性能监控模块](src/core/performance_monitor.py)

---

**最后更新**: 2025年9月13日 - 添加浏览器策略选择指南 🚀

如有策略相关的问题，请查看详细日志或提交Issue！