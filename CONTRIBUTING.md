# Contributing to StockInfoDownloader

感谢您对 StockInfoDownloader 项目的关注！本文档将帮助您了解如何参与贡献。

## 开发环境设置

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/StockInfoDownloader.git
cd StockInfoDownloader
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
playwright install
```

### 3. 配置环境

```bash
cp .env.example .env
# 编辑 .env 文件，配置必要的环境变量
```

## 代码规范

### 命名规范

- **类名**: PascalCase (例如: `ConfigManager`, `BrowserStrategy`)
- **函数/方法**: snake_case (例如: `download_stock_pdfs`, `get_org_id`)
- **变量**: snake_case (例如: `stock_code`, `download_count`)
- **常量**: UPPER_SNAKE_CASE (例如: `BASE_URL`, `MAX_RETRIES`)

### 类型注解

所有公共方法必须包含类型注解：

```python
def download_file(
    url: str,
    save_path: Union[str, Path],
    timeout: int = 30
) -> bool:
    """下载文件到指定路径"""
    pass
```

### 文档字符串

所有类和公共方法必须包含 docstring：

```python
class ConfigManager:
    """配置管理器

    提供统一的配置加载和管理功能，支持多环境配置。
    """

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
        pass
```

## 测试要求

### 运行测试

```bash
# 单元测试
pytest tests/unit/ -v

# 集成测试
pytest tests/integration/ -v

# E2E 测试 (Playwright)
python tests/e2e/official_e2e_test.py --browser-strategy=playwright

# E2E 测试 (Selenium)
python tests/e2e/official_e2e_test.py --browser-strategy=selenium

# 覆盖率测试
pytest --cov=src --cov-report=html
```

### E2E 测试要求

**重要**: 所有 E2E 测试必须 100% 通过才能提交代码。

- Playwright 测试: 必须显示 "Perfect match"
- Selenium 测试: 必须显示 "Perfect match"

## 提交规范

### Commit Message 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

- `feat`: 新功能
- `fix`: 修复 Bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

### 示例

```
feat(downloader): 添加并行下载支持

- 实现 ThreadPoolExecutor 并行下载
- 添加并发控制参数
- 更新配置文件格式

Closes #123
```

## Pull Request 流程

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### PR 检查清单

- [ ] 代码符合项目规范
- [ ] 所有单元测试通过
- [ ] 所有 E2E 测试通过 (Playwright + Selenium)
- [ ] 添加了必要的测试用例
- [ ] 更新了相关文档
- [ ] 类型注解完整

## 问题反馈

如果您发现 Bug 或有功能建议，请在 GitHub Issues 中提交。

## 许可证

本项目采用 MIT 许可证。参与贡献即表示您同意您的贡献将采用相同的许可证。
