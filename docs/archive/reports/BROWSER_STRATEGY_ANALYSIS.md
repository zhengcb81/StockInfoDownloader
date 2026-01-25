# Selenium vs Playwright 策略相似性分析

## 概述

本文档分析了 `SeleniumStrategy` 和 `PlaywrightStrategy` 的相似性和差异，为创建通用浏览器操作模块提供依据。

## 1. 共同的接口方法

两个策略都实现了 `BrowserAutomationStrategy` 接口，具有以下共同方法：

| 方法名 | 功能 | Selenium实现 | Playwright实现 |
|--------|------|--------------|----------------|
| `initialize()` | 初始化浏览器 | ✅ | ✅ |
| `create_driver()` | 创建驱动实例 | ✅ | ✅ |
| `navigate_to_page(url)` | 导航到页面 | ✅ | ✅ |
| `navigate(url)` | 导航（内部） | ✅ | ✅ |
| `find_elements(selector, by)` | 查找元素 | ✅ | ✅ |
| `click(element)` | 点击元素 | ✅ | ✅ |
| `get_text(element)` | 获取文本 | ✅ | ✅ |
| `get_attribute(element, attr)` | 获取属性 | ✅ | ✅ |
| `wait_for_element(selector, timeout)` | 等待元素 | ✅ | ✅ |
| `get_current_url()` | 获取当前URL | ✅ | ✅ |
| `get_page_title()` | 获取页面标题 | ✅ | ✅ |
| `close()` | 关闭浏览器 | ✅ | ✅ |
| `cleanup()` | 清理资源 | ✅ | ✅ |

## 2. 核心差异分析

### 2.1 初始化和配置

**Selenium:**
```python
# 使用ChromeOptions对象
chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_experimental_option("prefs", prefs)
self.driver = webdriver.Chrome(options=chrome_options)
```

**Playwright:**
```python
# 使用字典参数
launch_options = {
    'headless': True,
    'args': ['--no-sandbox', '--disable-dev-shm-usage']
}
context_options = {
    'viewport': {'width': 1920, 'height': 1080},
    'user_agent': '...'
}
self.playwright = sync_playwright().start()
self.browser = self.playwright.chromium.launch(**launch_options)
```

**相似性:** 都需要配置浏览器启动参数、窗口大小、User-Agent等
**差异:** Selenium使用对象+方法，Playwright使用字典参数

### 2.2 元素查找

**Selenium:**
```python
def find_elements(self, selector: str, by: str = "css") -> List[Any]:
    if by == "css":
        return self.driver.find_elements(By.CSS_SELECTOR, selector)
    elif by == "xpath":
        return self.driver.find_elements(By.XPATH, selector)
    else:
        return self.driver.find_elements(By.ID, selector)
```

**Playwright:**
```python
def find_elements(self, selector: str, by: str = "css") -> List[Any]:
    if by == "css":
        return self.page.query_selector_all(selector)
    elif by == "xpath":
        return self.page.query_selector_all(f"xpath={selector}")
    else:
        return self.page.query_selector_all(f"css=#{selector}")
```

**相似性:** 都支持CSS选择器、XPath等
**差异:** 方法名不同，Playwright使用 `query_selector_all`

### 2.3 等待机制

**Selenium:**
```python
def wait_for_element(self, selector: str, timeout: int = 10, by: str = "css"):
    wait = WebDriverWait(self.driver, timeout)
    if by == "css":
        return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
```

**Playwright:**
```python
def wait_for_element(self, selector: str, timeout: int = 10, by: str = "css"):
    if by == "css":
        return self.page.wait_for_selector(selector, timeout=timeout * 1000)
    elif by == "xpath":
        return self.page.wait_for_selector(f"xpath={selector}", timeout=timeout * 1000)
```

**相似性:** 都支持超时等待
**差异:** Selenium使用ExpectedConditions，Playwright内置wait_for_selector

### 2.4 下载处理

**Selenium:**
```python
# 通过Chrome preferences设置下载目录
prefs = {
    "download.default_directory": abs_download_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
}
chrome_options.add_experimental_option("prefs", prefs)
```

**Playwright:**
```python
# 使用持久化上下文或监听下载事件
if self.download_dir:
    context_options['downloads_path'] = abs_download_dir
    self.context = self.playwright.chromium.launch_persistent_context(...)
```

**相似性:** 都需要设置下载目录
**差异:** Selenium通过preferences，Playwright通过downloads_path参数

## 3. 通用操作模式识别

### 3.1 浏览器生命周期管理

两个策略都需要：
1. 创建浏览器实例
2. 配置选项
3. 导航到页面
4. 执行操作
5. 关闭/清理

### 3.2 页面交互模式

两个策略都支持：
- 元素查找（CSS/XPath）
- 元素点击
- 文本获取
- 属性获取
- 等待元素出现

### 3.3 配置管理

两个策略都接受：
- headless模式
- 下载目录
- 窗口大小
- User-Agent
- 超时设置

## 4. 创建通用模块的建议

### 4.1 抽象共同操作

可以创建一个 `CommonBrowserOperations` 类，包含：

```python
class CommonBrowserOperations:
    """通用浏览器操作 - 与具体框架无关"""

    def __init__(self, strategy):
        self.strategy = strategy

    def find_and_click(self, selector, by="css", timeout=10):
        """查找并点击元素"""
        element = self.strategy.wait_for_element(selector, timeout, by)
        if element:
            return self.strategy.click(element)
        return False

    def get_element_text(self, selector, by="css", timeout=10):
        """获取元素文本"""
        element = self.strategy.wait_for_element(selector, timeout, by)
        if element:
            return self.strategy.get_text(element)
        return ""

    def navigate_and_wait(self, url, wait_selector="body", timeout=30):
        """导航并等待页面加载"""
        if self.strategy.navigate_to_page(url):
            return self.strategy.wait_for_element(wait_selector, timeout)
        return False
```

### 4.2 统一配置接口

创建统一的配置转换器：

```python
def normalize_config(config):
    """将配置转换为统一格式"""
    return {
        'headless': config.get('headless', True),
        'download_dir': config.get('download_dir'),
        'window_size': config.get('window_size', '1920,1080'),
        'timeout': config.get('timeout', 180),
        'user_agent': config.get('user_agent')
    }
```

### 4.3 策略适配器模式

```python
class UnifiedBrowserStrategy:
    """统一浏览器策略接口"""

    def __init__(self, engine="playwright", config=None):
        if engine == "playwright":
            self._strategy = PlaywrightStrategy(**config)
        elif engine == "selenium":
            self._strategy = SeleniumStrategy(**config)

        self._common_ops = CommonBrowserOperations(self._strategy)

    # 暴露通用操作方法
    def find_and_click(self, selector, **kwargs):
        return self._common_ops.find_and_click(selector, **kwargs)
```

## 5. 重构建议

### 5.1 提取共同配置

```python
# config/browser_config.py
BROWSER_BASE_ARGS = [
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--disable-extensions',
    '--disable-blink-features=AutomationControlled',
    '--remote-debugging-port=0',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-background-timer-throttling',
    '--disable-backgrounding-occluded-windows',
    '--disable-renderer-backgrounding',
    '--disable-sync',
    '--disable-translate',
    '--disable-default-apps',
    '--disable-notifications',
    '--disable-popup-blocking',
    '--log-level=3',
    '--disable-features=TranslateUI',
    '--disable-component-extensions-with-background-pages',
    '--disable-domain-reliability',
    '--disable-setuid-sandbox',
    '--disable-features=VizDisplayCompositor',
    '--disable-ipc-flooding-protection',
]
```

### 5.2 创建通用操作模块

```python
# src/web/common_browser_ops.py
class CommonBrowserOperations:
    """通用浏览器操作模块"""

    @staticmethod
    def build_base_args():
        """获取基础浏览器参数"""
        return BROWSER_BASE_ARGS

    @staticmethod
    def build_user_agents():
        """获取默认User-Agent列表"""
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        ]

    @staticmethod
    def normalize_window_size(size):
        """标准化窗口大小配置"""
        if isinstance(size, str):
            # "1920,1080" -> {'width': 1920, 'height': 1080}
            w, h = size.split(',')
            return {'width': int(w), 'height': int(h)}
        elif isinstance(size, dict):
            return size
        else:
            return {'width': 1920, 'height': 1080}
```

### 5.3 重构Selenium策略

使用通用模块：

```python
from src.web.common_browser_ops import CommonBrowserOperations

class SeleniumStrategy(BrowserAutomationStrategy):
    def __init__(self, headless=True, download_dir=None, config=None):
        # 使用通用配置
        self.common = CommonBrowserOperations()
        self.headless = headless
        self.download_dir = download_dir
        self.config = config or {}

        # 使用通用方法标准化配置
        self.window_size = self.common.normalize_window_size(
            self.config.get('window_size', '1920,1080')
        )
        self._user_agents = self.config.get('user_agents', self.common.build_user_agents())
```

## 6. 总结

### 相似性（可复用部分）
1. ✅ 浏览器生命周期管理
2. ✅ 页面导航和等待
3. ✅ 元素查找和交互
4. ✅ 配置管理
5. ✅ 错误处理模式

### 差异（需要适配部分）
1. ❌ 初始化API（对象 vs 字典）
2. ❌ 元素查找方法名
3. ❌ 等待机制实现
4. ❌ 下载处理方式
5. ❌ 上下文管理

### 重构价值
- 减少代码重复 ✅
- 提高可维护性 ✅
- 统一行为标准 ✅
- 便于测试 ✅

### 建议优先级
1. 创建 `common_browser_ops.py` - 提取共同配置和工具函数
2. 重构 `SeleniumStrategy` - 使用通用模块
3. 重构 `PlaywrightStrategy` - 使用通用模块
4. 创建策略适配器 - 提供统一接口

## 7. 下一步行动计划

1. **创建通用浏览器操作模块** (`src/web/common_browser_ops.py`)
   - 提取共同配置
   - 提供工具函数
   - 标准化数据格式

2. **重构Selenium策略**
   - 导入通用模块
   - 简化配置逻辑
   - 统一方法实现

3. **创建策略适配器**
   - 提供统一接口
   - 支持运行时切换
   - 保持向后兼容

4. **更新测试**
   - 添加通用模块测试
   - 更新策略测试
   - 验证兼容性