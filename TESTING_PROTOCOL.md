# 下载器测试协议

## 概述
本文档定义了下载器每个组件在真实网页环境下的完整测试协议。涵盖单元测试、集成测试、端到端测试和回归测试，确保下载器在各种环境下都能正常工作。

## 测试框架架构

### 1. 测试层级结构
```
tests/
├── unit/           # 单元测试 - 测试单个函数/方法
├── integration/    # 集成测试 - 测试模块间协作
├── e2e/           # 端到端测试 - 完整业务流程
└── regression/    # 回归测试 - 验证历史功能
```

### 2. 测试覆盖率目标
- 单元测试: >90%
- 集成测试: >70% 
- 端到端测试: 关键路径100%
- 回归测试: 所有已修复bug

## 测试环境要求

### 基础环境
- 网络连接正常（可访问 cninfo.com.cn）
- Chrome 浏览器及 ChromeDriver 已安装
- Python 3.8+ 环境
- 必要依赖包: selenium, pytest, requests

### 测试数据
- 主要测试股票：300470（中密控股）
- 预期组织ID：9900023856
- 备用测试股票：301611（珂玛科技）、000001（平安银行）

## 详细测试协议

### A. 单元测试协议

#### A.1 组织ID映射测试
**文件**: `tests/unit/test_mapping.py`
**目标**: 验证组织ID映射功能
```python
def test_org_id_mapping():
    mapping_manager = MappingManager("stock_orgid_mapping.json")
    org_id = mapping_manager.get_org_id("300470")
    assert org_id == "9900023856"
```

#### A.2 文件工具测试
**文件**: `tests/unit/test_file_utils.py`
**目标**: 验证文件名清理、目录创建等功能

#### A.3 关键词匹配测试
**文件**: `tests/unit/test_keyword_matcher.py`
**目标**: 验证关键词过滤逻辑

#### A.4 配置解析测试
**文件**: `tests/unit/test_config.py`
**目标**: 验证配置文件解析和验证

### B. 集成测试协议

#### B.1 下载服务集成测试
**文件**: `tests/integration/test_download_service.py`
**目标**: 验证下载服务各组件协作

#### B.2 分页功能集成测试
**文件**: `tests/integration/test_pagination_integration.py`
**目标**: 验证分页逻辑与页面解析集成

#### B.3 Web爬虫集成测试
**文件**: `tests/integration/test_web_scraper_integration.py`
**目标**: 验证网页抓取与数据处理集成

### C. 端到端测试协议

#### C.1 核心功能测试
**文件**: `tests/e2e/test_e2e_downloader.py`
**目标**: 验证完整下载流程
**测试方法**:
1. 加载测试配置
2. 初始化下载器
3. 执行完整下载流程
4. 验证下载结果

#### C.2 多下载器对比测试
**文件**: `test_end_to_end_final.py`
**目标**: 验证新旧下载器功能一致性
**测试方法**:
1. 使用相同配置测试新旧下载器
2. 比较下载结果一致性
3. 验证性能差异

#### C.3 逐步验证测试
**文件**: `test_step_by_step.py`
**目标**: 逐步验证每个关键环节
**测试步骤**:

**Step 1: 组织ID获取测试**
```python
mapping_manager = MappingManager("stock_orgid_mapping.json")
org_id = mapping_manager.get_org_id("300470")
assert org_id == "9900023856"
```
**成功标准**: 返回正确的组织ID `9900023856`
**失败处理**: 检查映射文件是否存在，股票代码是否正确

**Step 2: 页面访问测试**
```python
url = f"https://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#research"
driver.get(url)
assert "cninfo.com.cn/new/index" not in driver.current_url
assert driver.title == "巨潮资讯网"
```
**成功标准**: 
- 当前URL包含股票代码和组织ID
- 页面标题为"巨潮资讯网"
- 找到内容表格元素

**失败处理**: 
- 检查组织ID是否正确
- 检查URL格式是否最新
- 检查网络连接

**Step 3: 链接发现测试**
```python
all_links = driver.find_elements(By.TAG_NAME, 'a')
detail_links = []
for link in all_links:
    text = link.text.strip()
    href = link.get_attribute('href')
    if (href and '/new/disclosure/detail' in href 
        and f'stockCode={stock_code}' in href):
        detail_links.append({'text': text, 'href': href})
assert len(detail_links) > 0
```
**成功标准**: 
- 找到至少10个详情链接
- 链接文本包含投资者关系相关信息

**失败处理**:
- 检查页面是否完全加载
- 检查链接选择器是否需要更新
- 检查股票代码参数是否正确

**Step 4: 关键词过滤测试**
```python
allowed_keywords = ["投资者关系", "调研", "活动记录"]
filtered_links = []
for link_data in detail_links:
    text = link_data['text']
    if any(keyword in text for keyword in allowed_keywords):
        filtered_links.append(link_data)
assert len(filtered_links) > 0
```
**成功标准**: 
- 关键词过滤后至少剩下5个链接
- 过滤后的链接包含投资者关系相关内容

**失败处理**:
- 检查关键词列表是否合适
- 检查页面内容是否变化

**Step 5: 详情页访问测试**
```python
test_link = filtered_links[0]
driver.get(test_link['href'])
download_btn = driver.find_element(By.XPATH, "//button[contains(., '公告下载')]")
assert download_btn.is_displayed()
```
**成功标准**: 
- 成功访问详情页
- 找到可见的下载按钮

**失败处理**:
- 检查详情页URL格式
- 检查下载按钮选择器
- 检查页面加载时间

**Step 6: 分页测试**
```python
try:
    next_btn = driver.find_element(By.XPATH, 
        "//button[contains(@class, 'el-pagination__next')]")
    print(f"下一页状态: {'可用' if next_btn.is_enabled() else '不可用'}")
except:
    print("单页内容，无需分页")
```
**成功标准**: 
- 如果存在多页内容，下一页按钮应可点击
- 如果是单页内容，无分页按钮属正常情况

**失败处理**:
- 检查当前页码
- 检查总页数

### D. 回归测试协议

#### D.1 Bug修复验证
**文件**: `tests/regression/test_regression.py`
**目标**: 确保已修复的bug不会重新出现
**测试方法**:
1. 针对每个已修复的bug创建测试用例
2. 重现bug场景
3. 验证修复效果

#### D.2 性能回归测试
**目标**: 确保性能不会随时间退化
**测试指标**:
- 页面加载时间
- 文件下载速度
- 内存使用情况

## 测试执行流程

### 1. 开发阶段测试
```bash
# 单元测试
python -m pytest tests/unit/ -v

# 集成测试
python -m pytest tests/integration/ -v

# 端到端测试
python test_end_to_end_final.py
```

### 2. 代码提交前测试
```bash
# 完整测试套件
python tests/run_comprehensive_tests.py

# 逐步验证
python test_step_by_step.py
```

### 3. 发布前测试
```bash
# 完整回归测试
python tests/regression/test_regression.py

# 性能测试
python tests/test_performance.py
```

## CI/CD 自动化测试

### 工作流配置
**文件**: `.github/workflows/ci_cd.yml`
**目标**: 自动化测试流程，确保代码质量

### 测试触发时机

#### 每次提交 (Push/Pull Request)
- **执行内容**: 单元测试 + 集成测试
- **预期时间**: 15分钟
- **失败处理**: 阻止合并

#### 每日构建 (UTC+1 01:00)
- **执行内容**: 
  - 所有快速测试
  - 端到端测试
  - 性能测试
- **预期时间**: 60分钟
- **报告生成**: 综合测试报告

#### 每周构建 (周日 UTC+1 01:00)
- **执行内容**:
  - 完整测试套件
  - 回归测试
  - 综合报告生成
- **预期时间**: 90分钟
- **风险评估**: 回归风险等级

#### 发布前测试 (手动触发)
- **执行内容**:
  - 完整测试套件
  - 覆盖率测试
  - 安全扫描
  - 代码质量检查
  - 发布报告生成
- **预期时间**: 120分钟
- **发布标准**: 所有检查通过

### 测试运行器

#### 单元测试运行器
```bash
python tests/run_unit_tests.py
```

#### 集成测试运行器
```bash
python tests/run_integration_tests.py
```

#### 回归测试运行器
```bash
python tests/run_regression_tests.py
```

#### 性能测试运行器
```bash
python tests/performance_test_runner.py
```

### CI/CD 报告生成

#### 报告类型
1. **快速测试报告**: `reports/quick_test_*.json`
2. **每日构建报告**: `reports/daily_build_*.json`
3. **回归测试报告**: `reports/weekly_regression_*.json`
4. **发布测试报告**: `reports/release_test_*.json`
5. **HTML汇总报告**: `test_summary_*.html`

#### 报告生成器
- `TestReportGenerator`: 基础测试报告生成
- `CICDReportGenerator`: CI/CD专用报告生成

### 性能基准

#### 内存使用
- 内存增长阈值: < 50MB
- 内存泄漏阈值: < 5MB

#### CPU使用
- CPU使用率阈值: < 80%
- 执行时间阈值: < 5秒

#### 响应时间
- 关键词匹配: < 1ms/条
- 文件操作: < 2秒/100文件
- 映射查询: < 1ms/查询

### 发布就绪标准

发布需要满足以下所有条件：
- ✅ 测试通过率 ≥ 95%
- ✅ 代码覆盖率 ≥ 80%
- ✅ 安全检查通过
- ✅ 代码质量检查通过
- ✅ 性能基准达标

### 监控和告警

#### 关键指标
- 测试通过率趋势
- 执行时间变化
- 覆盖率变化
- 性能指标变化

#### 告警设置
- 连续失败超过3次
- 覆盖率下降超过5%
- 性能指标下降超过10%
- 执行时间增长超过50%

### 故障排除

#### 常见问题
1. **测试超时**: 检查网络连接和WebDriver配置
2. **依赖问题**: 更新依赖包版本，清理pip缓存
3. **环境问题**: 验证Chrome和ChromeDriver版本匹配

#### 调试命令
```bash
# 运行单个测试
pytest tests/unit/test_mapping.py::TestMapping::test_get_org_id_success -v -s

# 生成覆盖率报告
pytest --cov=src --cov-report=html

# 并行测试
pytest -n auto tests/
```

## 测试报告规范

### 报告目录结构
```
test_reports/
├── e2e/                    # 端到端测试报告
├── unit/                   # 单元测试报告
├── integration/            # 集成测试报告
├── regression/             # 回归测试报告
└── summary/                # 综合测试报告
```

### 报告命名规范
- 端到端测试: `e2e_report_YYYYMMDD_HHMMSS.json`
- 单元测试: `unit_report_YYYYMMDD_HHMMSS.json`
- 集成测试: `integration_report_YYYYMMDD_HHMMSS.json`
- 回归测试: `regression_report_YYYYMMDD_HHMMSS.json`
- 综合报告: `summary_report_YYYYMMDD_HHMMSS.json`

### 报告内容要求
```json
{
  "test_info": {
    "timestamp": "2025-09-06T14:30:00",
    "test_type": "e2e|unit|integration|regression",
    "description": "测试描述"
  },
  "test_environment": {
    "python_version": "3.8.0",
    "chrome_version": "128.0.6613.85",
    "test_data": "300470,301611"
  },
  "results": [],
  "summary": {
    "total": 10,
    "passed": 8,
    "failed": 2,
    "success_rate": "80.0%"
  }
}
```

## 测试结果记录

每次测试后必须记录:
1. **测试时间**: YYYY-MM-DD HH:MM:SS
2. **测试类型**: unit/integration/e2e/regression
3. **测试环境**: Python版本、Chrome版本、网络状态
4. **测试数据**: 使用的股票代码和配置
5. **各步骤结果**: ✅/❌
6. **失败详情**: 如果有任何步骤失败，记录具体错误信息
7. **处理措施**: 采取的修复措施
8. **报告位置**: 测试报告文件路径

## 自动化测试集成

### CI/CD 流程
1. **代码提交**: 触发单元测试和集成测试
2. **测试失败**: 阻止合并，发送通知
3. **测试通过**: 合并到开发分支
4. **部署测试**: 运行端到端测试和回归测试
5. **发布准备**: 生成综合测试报告

### 测试调度
- **每次提交**: 单元测试 + 集成测试
- **每日构建**: 端到端测试 + 性能测试
- **每周构建**: 完整回归测试
- **发布前**: 完整测试套件

## 注意事项

### 网络依赖
- 测试依赖外部网站，网络不稳定可能导致失败
- 设置合理的超时时间和重试机制
- 考虑使用本地缓存减少网络依赖

### 反爬虫机制
- 网站可能有访问频率限制，需要适当延迟
- 使用不同的User-Agent和IP地址
- 遵守robots.txt规则

### 页面结构变化
- 目标网站结构可能变化，需要定期更新测试
- 使用灵活的选择器策略
- 建立页面结构监控机制

### 数据时效性
- 测试数据可能随时间变化，需要定期验证
- 使用固定的测试时间段数据
- 建立数据备份机制

## 测试维护

### 定期维护任务
1. **每周**: 检查测试用例有效性
2. **每月**: 更新测试数据和预期结果
3. **每季度**: 重构和优化测试代码
4. **每年**: 评估测试策略和工具

### 测试用例更新
- 新功能开发时添加对应测试
- Bug修复时添加回归测试
- 页面结构变化时更新选择器
- 性能要求变化时调整测试标准

## 更新记录

- 2025-09-06: 创建完整测试协议
- 2025-09-06: 添加测试报告规范和自动化集成
- 测试验证: 核心功能测试通过，性能测试待优化