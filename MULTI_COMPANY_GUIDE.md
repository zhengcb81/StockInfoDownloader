# 多公司并行下载使用指南

## 📋 概述

多公司并行下载功能允许用户同时下载多个公司的股票信息，通过并行处理和智能代理管理，大幅提高下载效率并降低被反爬虫机制检测的风险。

## 🚀 主要特性

### 1. 多公司配置支持
- 支持在配置文件中配置多个公司
- 每个公司可独立设置启用状态、优先级和自定义页面
- 自动按优先级排序和处理

### 2. 并行下载
- 多线程并行处理多个公司
- 可配置最大工作线程数
- 智能任务调度和资源管理

### 3. 智能代理管理
- 支持多个代理池
- 自动健康检查和故障转移
- 负载均衡和IP轮换

### 4. 增强反爬虫保护
- 行为模拟和指纹随机化
- 自适应请求频率控制
- 多层异常恢复机制

## 📝 配置说明

### 基本配置结构

```json
{
  "environment": "production",
  "save_dir": "downloads",
  "companies": [
    {
      "stock_code": "300470",
      "company_name": "中密控股",
      "enabled": true,
      "priority": 1,
      "custom_pages": null
    }
  ],
  "parallel_download": {
    "enabled": true,
    "max_workers": 5,
    "task_timeout": 300
  },
  "proxy_management": {
    "enabled": true,
    "pools": {
      "main_pool": {
        "enabled": true,
        "proxies": [
          {
            "host": "proxy1.example.com",
            "port": 8080,
            "type": "http"
          }
        ]
      }
    }
  },
  "anti_crawler": {
    "enabled": true,
    "random_delay": {
      "min": 2,
      "max": 5
    },
    "behavior_simulation": true,
    "fingerprint_randomization": true
  }
}
```

### 详细配置参数

#### 公司配置 (companies)

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `stock_code` | String | 是 | - | 股票代码 |
| `company_name` | String | 否 | 自动获取 | 公司名称 |
| `enabled` | Boolean | 否 | true | 是否启用下载 |
| `priority` | Integer | 否 | 1 | 下载优先级(1-10) |
| `custom_pages` | Array | 否 | null | 自定义页面配置 |

#### 并行下载配置 (parallel_download)

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `enabled` | Boolean | 否 | false | 是否启用并行下载 |
| `max_workers` | Integer | 否 | 3 | 最大工作线程数 |
| `task_timeout` | Integer | 否 | 300 | 任务超时时间(秒) |

#### 代理管理配置 (proxy_management)

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `enabled` | Boolean | 否 | false | 是否启用代理 |
| `pools` | Object | 否 | {} | 代理池配置 |

#### 反爬虫配置 (anti_crawler)

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `enabled` | Boolean | 否 | true | 是否启用反爬虫 |
| `random_delay` | Object | 否 | {min:1, max:3} | 随机延迟配置 |
| `behavior_simulation` | Boolean | 否 | true | 行为模拟 |
| `fingerprint_randomization` | Boolean | 否 | true | 指纹随机化 |

## 🛠️ 使用方法

### 1. 基本使用

```bash
# 使用默认配置运行
python main_parallel.py

# 指定配置文件
python main_parallel.py --config custom_config.json

# 仅下载特定公司
python main_parallel.py --companies 300470,301611

# 查看帮助信息
python main_parallel.py --help
```

### 2. 高级用法

```bash
# 启用详细日志
python main_parallel.py --verbose

# 指定下载目录
python main_parallel.py --save-dir /path/to/downloads

# 设置最大工作线程数
python main_parallel.py --max-workers 8

# 运行特定模式
python main_parallel.py --mode parallel  # 并行模式
python main_parallel.py --mode sequential  # 顺序模式
```

### 3. 配置文件示例

#### 示例1：基础多公司配置
```json
{
  "companies": [
    {
      "stock_code": "300470",
      "company_name": "中密控股",
      "enabled": true,
      "priority": 1
    },
    {
      "stock_code": "301611",
      "company_name": "珂玛科技",
      "enabled": true,
      "priority": 2
    }
  ],
  "parallel_download": {
    "enabled": true,
    "max_workers": 3
  }
}
```

#### 示例2：带代理和反爬虫配置
```json
{
  "companies": [
    {
      "stock_code": "300470",
      "enabled": true,
      "priority": 1
    }
  ],
  "parallel_download": {
    "enabled": true,
    "max_workers": 5,
    "task_timeout": 600
  },
  "proxy_management": {
    "enabled": true,
    "pools": {
      "pool1": {
        "enabled": true,
        "proxies": [
          {
            "host": "proxy1.example.com",
            "port": 8080,
            "type": "http",
            "username": "user1",
            "password": "pass1"
          },
          {
            "host": "proxy2.example.com",
            "port": 8080,
            "type": "socks5"
          }
        ],
        "health_check_interval": 60,
        "max_failures": 3
      }
    }
  },
  "anti_crawler": {
    "enabled": true,
    "random_delay": {
      "min": 3,
      "max": 8
    },
    "behavior_simulation": true,
    "fingerprint_randomization": true,
    "adaptive_rate_limiting": true
  }
}
```

## 🔧 最佳实践

### 1. 代理配置建议

- **使用高质量代理**: 选择稳定、低延迟的代理服务
- **合理设置代理池**: 每个代理池建议包含3-5个代理
- **定期健康检查**: 设置合理的健康检查间隔
- **负载均衡**: 避免单个代理过载

### 2. 反爬虫配置建议

- **随机延迟**: 设置2-10秒的随机延迟
- **行为模拟**: 启用鼠标移动和滚动模拟
- **请求频率**: 根据目标网站调整请求频率
- **异常处理**: 启用多层异常恢复机制

### 3. 性能优化建议

- **合理设置工作线程**: 根据系统资源和网络带宽调整
- **任务超时**: 设置合理的任务超时时间
- **内存管理**: 监控内存使用情况
- **日志级别**: 生产环境建议使用INFO级别

## 🧪 测试验证

### 1. 单元测试
```bash
# 运行多公司相关单元测试
python -m pytest tests/unit/test_config.py -v
python -m pytest tests/unit/test_multi_company.py -v
```

### 2. 集成测试
```bash
# 运行多公司集成测试
python -m pytest tests/integration/test_multi_company_parallel.py -v
```

### 3. 性能测试
```bash
# 运行性能测试
python -m pytest tests/performance/test_parallel_performance.py -v
```

## 🚨 故障排除

### 常见问题

1. **代理连接失败**
   - 检查代理服务器是否可用
   - 验证代理认证信息
   - 检查网络连接

2. **下载超时**
   - 增加任务超时时间
   - 减少并行工作线程数
   - 检查网络稳定性

3. **反爬虫触发**
   - 增加随机延迟时间
   - 启用更多反爬虫保护机制
   - 考虑使用代理轮换

4. **内存不足**
   - 减少并行工作线程数
   - 增加系统内存
   - 优化任务调度

### 日志分析

启用详细日志进行问题诊断：
```bash
python main_parallel.py --verbose --log-level DEBUG
```

查看特定类型的日志：
```bash
python main_parallel.py --verbose 2>&1 | grep "ERROR"
python main_parallel.py --verbose 2>&1 | grep "PROXY"
```

## 📊 性能监控

### 关键指标

- **下载成功率**: 成功下载的文档数 / 总尝试数
- **平均下载时间**: 单个文档的平均下载耗时
- **代理健康度**: 代理可用性和响应时间
- **系统资源使用**: CPU、内存、网络使用情况

### 监控命令

```bash
# 查看下载统计
python main_parallel.py --stats

# 实时监控
python main_parallel.py --monitor

# 性能报告
python main_parallel.py --report
```

## 🔒 安全注意事项

1. **代理安全**:
   - 使用加密连接(HTTPS/SOCKS5)
   - 定期更换代理认证信息
   - 避免使用免费公共代理

2. **数据安全**:
   - 敏感信息不要记录在日志中
   - 定期清理临时文件
   - 使用安全的文件权限

3. **合规使用**:
   - 遵守目标网站的使用条款
   - 合理设置请求频率
   - 尊重robots.txt规则

## 📞 技术支持

如果遇到问题，请：

1. 查看日志文件获取详细错误信息
2. 检查配置文件格式是否正确
3. 参考本文档的故障排除部分
4. 提交Issue时请提供：
   - 详细的错误信息
   - 配置文件内容(敏感信息脱敏)
   - 运行环境信息
   - 相关日志片段

---

*最后更新: 2025年9月14日*