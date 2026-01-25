# 浏览器测试指南

## 📋 概述

本指南详细介绍了StockInfoDownloader项目中Selenium和Playwright两种浏览器自动化框架的测试方法、配置和最佳实践。

## 🎯 测试架构

### 双浏览器策略测试
- **Selenium Strategy**: 传统浏览器自动化方案
- **Playwright Strategy**: 现代浏览器自动化方案
- **参数化测试**: 自动测试两种策略的一致性
- **集成测试**: 验证策略与下载服务的完整集成

## 🧪 测试类型

### 1. 单元测试
**位置**: `tests/unit/test_browser_strategy.py`

测试浏览器策略的基础功能：
- 策略接口定义验证
- 策略创建和初始化
- 基本方法调用测试

```bash
# 运行浏览器策略单元测试
python -m pytest tests/unit/test_browser_strategy.py -v
```

### 2. 集成测试
**位置**: `tests/integration/test_downloader_integration.py`

参数化测试两种浏览器策略：
- 验证策略初始化
- 测试下载服务集成
- 确保功能一致性

```bash
# 运行参数化集成测试
python -m pytest tests/integration/test_downloader_integration.py -v
```

### 3. 策略对比测试
**位置**: `tests/integration/test_browser_strategies.py`

专门测试两种策略的对比：
- 策略工厂创建测试
- 性能对比分析
- 错误处理一致性
- 兼容性验证

```bash
# 运行策略对比测试
python -m pytest tests/integration/test_browser_strategies.py -v
```

### 4. 端到端测试
**位置**: `tests/e2e/test_dual_browser_modes.py`

完整的工作流程测试：
- 双浏览器模式E2E测试
- 下载流程一致性验证
- 错误处理和恢复测试

```bash
# 运行双浏览器E2E测试
python -m pytest tests/e2e/test_dual_browser_modes.py -v
```

## 🔧 测试配置

### 1. 测试环境配置
创建 `tests/browser_test_config.json`:

```json
{
  "browser_strategies": ["selenium", "playwright"],
  "test_stocks": ["300470", "000001"],
  "test_config": {
    "headless": true,
    "max_retries": 2,
    "timeout": 30
  },
  "performance_thresholds": {
    "max_creation_time": 5.0,
    "max_memory_usage": 100
  }
}
```

### 2. 依赖配置
确保安装必要的测试依赖：

```bash
# 安装Selenium依赖
pip install selenium webdriver-manager

# 安装Playwright依赖
pip install playwright
playwright install

# 安装测试框架
pip install pytest pytest-mock pytest-cov
```

## 🚀 运行测试

### 1. 运行所有浏览器测试
```bash
# 运行所有浏览器相关测试
python -m pytest tests/ -k "browser" -v

# 生成覆盖率报告
python -m pytest tests/ -k "browser" --cov=src.web --cov-report=html
```

### 2. 运行特定策略测试
```bash
# 仅测试Selenium策略
python -m pytest tests/ -k "selenium" -v

# 仅测试Playwright策略
python -m pytest tests/ -k "playwright" -v
```

### 3. 性能测试
```bash
# 运行性能对比测试
python -m pytest tests/integration/test_browser_strategies.py::TestBrowserStrategiesIntegration::test_strategy_performance_comparison -v -s
```

## 📊 测试用例详解

### 1. 策略初始化测试
```python
def test_browser_strategy_initialization(self):
    """测试浏览器策略初始化"""
    # 验证下载器使用了正确的浏览器策略
    assert self.downloader.browser_strategy is not None

    # 验证策略类型
    if self.browser_strategy == "selenium":
        from src.web.selenium_strategy import SeleniumStrategy
        assert isinstance(self.downloader.browser_strategy, SeleniumStrategy)
    elif self.browser_strategy == "playwright":
        from src.web.playwright_strategy import PlaywrightStrategy
        assert isinstance(self.downloader.browser_strategy, PlaywrightStrategy)
```

### 2. 策略一致性测试
```python
def test_download_workflow_consistency(self):
    """测试不同策略下的下载工作流程一致性"""
    # 模拟成功的下载流程
    mock_strategy.navigate.return_value = True
    mock_strategy.find_elements.return_value = []

    # 执行下载
    download_records = downloader.download_stock_pdfs(...)

    # 验证下载结果一致性
    assert isinstance(download_records, list)

    # 验证策略方法调用一致性
    mock_strategy.navigate.assert_called()
    mock_strategy.find_elements.assert_called()
```

### 3. 错误处理测试
```python
def test_error_handling_consistency(self):
    """测试不同策略下的错误处理一致性"""
    # 设置mock策略来模拟错误
    mock_strategy.navigate.side_effect = Exception("Navigation failed")

    # 执行下载（应该处理错误）
    download_records = downloader.download_stock_pdfs(...)

    # 验证错误处理一致性
    assert isinstance(download_records, list)
    mock_strategy.navigate.assert_called()
```

## 🔍 测试最佳实践

### 1. Mock使用
- 使用mock避免真实浏览器操作
- 模拟成功和失败场景
- 验证方法调用和参数

### 2. 参数化测试
- 使用 `@pytest.mark.parametrize` 测试多种策略
- 确保测试覆盖所有浏览器类型
- 验证策略间的一致性

### 3. 资源管理
- 在 `setup_method` 中创建测试资源
- 在 `teardown_method` 中清理资源
- 避免测试间的资源泄露

### 4. 错误处理
- 测试策略创建失败场景
- 验证优雅降级机制
- 确保测试稳定性

## 📈 性能测试

### 1. 策略创建性能
```python
def test_strategy_performance_comparison(self):
    """测试策略性能对比"""
    creation_times = {}

    for strategy_type in ["selenium", "playwright"]:
        start_time = time.time()
        strategy = BrowserStrategyFactory.create_strategy(...)
        creation_time = time.time() - start_time

        creation_times[strategy_type] = creation_time
        strategy.close()

    # 验证性能在可接受范围内
    for strategy_type, creation_time in creation_times.items():
        assert creation_time < 5.0, f"{strategy_type} 创建时间过长: {creation_time}s"
```

### 2. 内存使用测试
```python
def test_strategy_memory_usage(self):
    """测试策略内存使用"""
    import psutil
    import os

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # 创建策略
    strategy = BrowserStrategyFactory.create_strategy(...)

    # 测量内存使用
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    # 验证内存使用在合理范围内
    assert memory_increase < 50, f"内存使用增加过多: {memory_increase}MB"

    strategy.close()
```

## 🐛 常见问题

### 1. 依赖缺失
**问题**: `ModuleNotFoundError: No module named 'playwright'`
**解决**: 安装Playwright依赖
```bash
pip install playwright
playwright install
```

### 2. WebDriver问题
**问题**: Selenium WebDriver无法启动
**解决**: 检查Chrome版本和WebDriver版本匹配
```bash
# 检查Chrome版本
google-chrome --version

# 更新WebDriver
pip install --upgrade webdriver-manager
```

### 3. 权限问题
**问题**: 测试无法创建临时文件
**解决**: 检查文件系统权限
```bash
# 检查权限
ls -la /tmp

# 手动创建测试目录
mkdir -p /tmp/test_downloads
chmod 755 /tmp/test_downloads
```

### 4. 网络问题
**问题**: 测试因网络超时失败
**解决**: 调整测试配置或使用mock
```json
{
  "test_config": {
    "timeout": 60,
    "use_mock": true
  }
}
```

## 📋 测试检查清单

### 开发新功能时
- [ ] 为新功能添加单元测试
- [ ] 验证在两种浏览器策略下工作正常
- [ ] 添加集成测试验证功能完整性
- [ ] 运行完整的测试套件

### 发布前
- [ ] 运行所有浏览器相关测试
- [ ] 验证测试覆盖率
- [ ] 检查性能测试结果
- [ ] 确保没有测试失败

### 持续集成
- [ ] 配置CI/CD运行浏览器测试
- [ ] 设置测试失败时的通知
- [ ] 定期检查测试稳定性
- [ ] 维护测试环境

## 📚 相关文档

- [浏览器策略指南](BROWSER_STRATEGY_GUIDE.md)
- [项目清理指南](PROJECT_CLEANUP_GUIDE.md)
- [测试工具文档](TESTING_TOOLS.md)

---

**维护说明**: 本文档应随浏览器策略和测试框架的更新而维护。

**最后更新**: 2025年9月13日