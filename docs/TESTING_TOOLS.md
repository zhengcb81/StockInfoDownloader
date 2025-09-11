# 测试工具文档

本文档描述了股票信息下载器项目中可用的测试工具和框架。

## 🧪 测试框架概述

项目包含多层次的测试体系：

### 1. 单元测试 (`tests/unit/`)
测试各个模块的独立功能
- `test_config.py` - 配置管理测试
- `test_driver.py` - WebDriver管理测试  
- `test_downloader.py` - 下载服务测试
- `test_pagination.py` - 分页功能测试
- 其他模块测试...

### 2. 集成测试 (`tests/integration/`)
测试模块间的协作功能
- `test_integration.py` - 整体集成测试
- `test_pagination_integration.py` - 分页集成测试
- `test_downloader_integration.py` - 下载器集成测试

### 3. 端到端测试 (`e2e_test.py`)
完整的用户场景测试，验证整个下载流程

### 4. 回归测试 (`tests/regression/`)
确保新功能不影响现有功能

## 🛠️ 专用测试工具

### 内容验证工具 (`tools/content_validator.py`)

**用途**: 快速验证分页功能是否正常

**适用场景**:
- 日常健康检查
- 分页功能故障排查
- 网站结构变化检测

**示例**:
```bash
# 基础验证
python tools/content_validator.py --stock-code 300470 --org-id 9900023856

# 详细验证多页
python tools/content_validator.py --stock-code 300470 --org-id 9900023856 --max-pages 5 --headless
```

**输出解读**:
- `healthy`: 分页功能正常
- `suspicious`: 分页功能异常
- `error`: 验证过程出错

### 页面监控工具 (`tools/page_monitor.py`)

**用途**: 详细监控所有页面内容

**适用场景**:
- 深度问题诊断
- 内容变化分析
- 详细文档清单获取

**示例**:
```bash
# 基础监控
python tools/page_monitor.py --stock-code 300470 --org-id 9900023856

# 详细监控并导出CSV
python tools/page_monitor.py --stock-code 300470 --org-id 9900023856 --max-pages 5 --export-format csv
```

**输出特点**:
- 每页文档详细列表
- 日期分布分析
- 跨页面对比
- 支持JSON/CSV导出

## 🔄 测试执行流程

### 1. 开发阶段测试
```bash
# 运行单元测试
python tests/run_unit_tests.py

# 运行集成测试  
python tests/run_integration_tests.py

# 运行特定模块测试
python -m pytest tests/unit/test_pagination.py -v
```

### 2. 发布前测试
```bash
# 运行完整的端到端测试
python e2e_test.py

# 运行回归测试
python tests/run_regression_tests.py

# 运行综合测试套件
python tests/run_comprehensive_tests.py
```

### 3. 生产环境验证
```bash
# 使用内容验证工具检查分页功能
python tools/content_validator.py --stock-code 300470 --org-id 9900023856

# 使用页面监控工具进行详细检查
python tools/page_monitor.py --stock-code 300470 --org-id 9900023856 --max-pages 3
```

## 📊 测试数据管理

### 测试配置
- `config_test.json` - 基础测试配置
- `config_end2end_test.json` - 端到端测试配置
- `tests/integration/test_config.json` - 集成测试配置

### 测试数据
- `tests/test_data/` - 测试用数据文件
- `tests/expected_results/` - 预期结果文件
- `stock_orgid_mapping.json` - 股票代码映射（共享）

### 测试报告
- `test_reports/unit/` - 单元测试报告
- `test_reports/integration/` - 集成测试报告  
- `test_reports/e2e/` - 端到端测试报告

## 🎯 测试策略

### 分层测试策略
1. **快速反馈层**: 单元测试（秒级）
2. **功能验证层**: 集成测试（分钟级）
3. **端到端层**: 完整流程测试（10分钟级）
4. **回归验证层**: 全量测试（30分钟级）

### 关键测试场景

#### 分页功能测试
- 多页导航成功率
- 内容真实性验证
- 边界情况处理（首页、末页）
- 异常恢复能力

#### 下载功能测试
- 文件完整性验证
- 重复下载处理
- 错误重试机制
- 多格式支持

#### 稳定性测试
- Chrome崩溃恢复
- 网络异常处理
- 超时机制验证
- 资源清理验证

## 📈 测试质量指标

### 覆盖率目标
- **单元测试覆盖率**: ≥80%
- **集成测试覆盖率**: ≥70%  
- **关键路径覆盖**: 100%

### 性能指标
- **单元测试执行时间**: ≤2分钟
- **集成测试执行时间**: ≤5分钟
- **端到端测试执行时间**: ≤15分钟

### 稳定性指标
- **测试通过率**: ≥95%
- **假失败率**: ≤5%
- **平均修复时间**: ≤4小时

## 🔧 测试工具开发指南

### 工具开发原则
1. **单一职责**: 每个工具专注一个核心功能
2. **命令行友好**: 支持参数化配置
3. **输出清晰**: 提供人类可读的输出格式
4. **错误处理**: 完善的异常处理机制
5. **文档完整**: 包含使用说明和示例

### 工具模板
```python
#!/usr/bin/env python3
"""
工具名称和用途说明
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logger import get_logger

logger = get_logger(__name__)

class ToolName:
    """工具类说明"""
    
    def __init__(self, param1, param2):
        self.param1 = param1
        self.param2 = param2
    
    def main_function(self):
        """主要功能实现"""
        pass
    
    def validate_input(self):
        """输入验证"""
        pass

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='工具描述')
    parser.add_argument('--required-param', required=True, help='参数说明')
    parser.add_argument('--optional-param', default='default', help='参数说明')
    
    args = parser.parse_args()
    
    # 工具逻辑
    tool = ToolName(args.required_param, args.optional_param)
    result = tool.main_function()
    
    sys.exit(0 if result else 1)

if __name__ == "__main__":
    main()
```

## 📋 常见测试场景

### 1. 新功能测试
- 编写对应的单元测试
- 添加集成测试验证模块协作
- 更新端到端测试覆盖新场景
- 运行回归测试确保兼容性

### 2. Bug修复验证
- 编写重现bug的测试用例
- 验证修复后的正确性
- 添加边界情况测试
- 更新相关文档

### 3. 性能优化测试
- 基准性能测试
- 优化前后对比测试
- 长时间稳定性测试
- 资源使用监控

### 4. 环境变化测试
- 不同Python版本测试
- 不同操作系统测试
- 网络环境变化测试
- 网站结构变化测试

## 🚨 测试失败处理

### 失败分类
1. **环境问题**: 网络、权限、资源等
2. **代码问题**: 逻辑错误、边界情况
3. **外部变化**: 网站结构变化、反爬升级
4. **随机失败**: 时序、并发、资源竞争

### 处理流程
1. **日志分析**: 查看详细错误信息
2. **重现测试**: 手动重现问题
3. **根因分析**: 确定问题来源
4. **修复验证**: 实施修复并验证
5. **回归测试**: 确保不引入新问题

## 📚 相关文档

- [PAGINATION_FIX_SUMMARY.md](PAGINATION_FIX_SUMMARY.md) - 分页功能修复详细过程
- [CHANGELOG.md](CHANGELOG.md) - 测试框架变更记录
- [README.md](../README.md) - 项目总体说明

## 💡 最佳实践

### 1. 测试设计
- 测试行为而非实现
- 保持测试的独立性和可重复性
- 使用描述性的测试名称
- 一个测试专注一个概念

### 2. 测试数据
- 使用真实但脱敏的数据
- 保持测试数据的稳定性
- 定期更新测试数据
- 文档化测试数据来源

### 3. 测试环境
- 与生产环境隔离
- 可重复的环境配置
- 环境状态可重置
- 资源使用可监控

### 4. 持续改进
- 定期评审测试用例
- 更新过时的测试
- 优化测试执行时间
- 分享测试经验

测试是确保软件质量的重要手段，但更重要的是建立质量文化，让每个团队成员都重视测试、参与测试、改进测试。通过这些工具和流程，我们能够持续交付高质量的软件产品。🚀