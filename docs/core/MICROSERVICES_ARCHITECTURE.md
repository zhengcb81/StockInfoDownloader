# 股票下载器微服务架构文档

## 概述

本文档描述了股票下载器项目的微服务架构设计，该架构将原有的单体应用拆分为多个独立的微服务，提高了系统的可扩展性、可维护性和可靠性。

## 架构概览

### 系统组件

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │    │   Nginx LB      │    │   Client        │
│   (Port 8000)   │────│   (Port 80)     │────│   Applications │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         └───────────────────────┘
                               │
         ┌─────────────────────────────────────────────────────────┐
         │                    Microservices Layer                   │
         ├─────────────────┬─────────────────┬─────────────────┬───┤
         │ Download Svc   │  Cache Svc      │  Error Svc      │ C │
         │ (Port 8001)     │  (Port 8002)     │  (Port 8003)     │ o │
         └─────────────────┴─────────────────┴─────────────────┴───┤
         │                 Config Svc      │                       │ n │
         │                 (Port 8004)     │                       │ f │
         └─────────────────────────────────────────────────────────┴───┤
                               │                                   │ i │
         ┌─────────────────────────────────────────────────────────┐   │ g │
         │                Infrastructure Layer                      │   │   │
         ├─────────────────┬─────────────────┬─────────────────┬───┤   │   │
         │    Redis        │  Prometheus     │   Grafana       │ M │   │   │
         │   (Port 6379)   │  (Port 9090)    │  (Port 3000)    │ o │   │   │
         └─────────────────┴─────────────────┴─────────────────┴───┘   │   │
                                                               │ n │   │
                                                               │ i │   │
                                                               │ t │   │
                                                               │ o │   │
                                                               │ r │   │
                                                               │ i │   │
                                                               │ n │   │
                                                               │ g │   │
                                                               └───┘
```

### 核心特性

- **服务拆分**: 将原有单体应用拆分为5个核心微服务
- **异步通信**: 基于Redis的事件驱动架构
- **容器化**: 完整的Docker容器化部署
- **监控告警**: Prometheus + Grafana监控体系
- **负载均衡**: Nginx负载均衡和API网关
- **分布式任务队列**: 基于Redis的异步任务处理
- **健康检查**: 全面的服务健康检查机制
- **配置管理**: 集中化配置管理服务

## 微服务详细说明

### 1. API网关 (api-gateway)

**端口**: 8000
**职责**: 统一API入口，路由分发，负载均衡

**功能特性**:
- 请求路由和转发
- 服务发现和负载均衡
- 请求限流和安全控制
- 响应缓存和压缩
- 统一错误处理
- API文档聚合

**主要端点**:
- `GET /gateway/services` - 获取服务列表
- `GET /gateway/routes` - 获取路由配置
- `GET /gateway/stats` - 获取网关统计
- `GET /gateway/health` - 健康检查

### 2. 下载服务 (download-service)

**端口**: 8001
**职责**: 股票PDF文件下载核心功能

**功能特性**:
- 支持多种浏览器策略 (Selenium/Playwright)
- 异步任务处理
- 优先级队列管理
- 进度跟踪和状态报告
- 失败重试机制
- 资源管理和清理

**主要端点**:
- `POST /api/v1/download` - 创建下载任务
- `GET /api/v1/download/{task_id}` - 获取任务状态
- `GET /api/v1/download` - 获取任务列表
- `DELETE /api/v1/download/{task_id}` - 取消任务
- `POST /api/v1/download/batch` - 批量下载
- `GET /api/v1/download/stats` - 获取下载统计

### 3. 缓存服务 (cache-service)

**端口**: 8002
**职责**: 智能缓存和性能优化

**功能特性**:
- 多级缓存策略
- 缓存失效和更新
- 标签索引和查询
- 缓存统计和监控
- 内存使用优化
- 分布式缓存同步

**主要端点**:
- `POST /api/v1/cache` - 设置缓存
- `GET /api/v1/cache/{key}` - 获取缓存
- `DELETE /api/v1/cache/{key}` - 删除缓存
- `POST /api/v1/cache/invalidate` - 批量失效
- `GET /api/v1/cache/stats` - 缓存统计
- `GET /api/v1/cache/health` - 缓存健康检查

### 4. 错误服务 (error-service)

**端口**: 8003
**职责**: 统一错误处理和告警

**功能特性**:
- 错误收集和聚合
- 智能告警机制
- 多通道通知 (邮件/Slack/Webhook)
- 错误模式分析
- 告警升级策略
- 错误趋势监控

**主要端点**:
- `POST /api/v1/errors` - 报告错误
- `GET /api/v1/errors` - 查询错误
- `GET /api/v1/alerts` - 获取告警
- `POST /api/v1/alerts/{alert_id}/resolve` - 解决告警
- `GET /api/v1/errors/stats` - 错误统计

### 5. 配置服务 (config-service)

**端口**: 8004
**职责**: 分布式配置管理

**功能特性**:
- 集中化配置存储
- 环境隔离管理
- 配置版本控制
- 实时配置推送
- 配置审计日志
- 配置导入导出

**主要端点**:
- `POST /api/v1/config` - 创建配置
- `GET /api/v1/config/{key}` - 获取配置
- `PUT /api/v1/config/{key}` - 更新配置
- `GET /api/v1/config/{key}/history` - 配置历史
- `POST /api/v1/config/export` - 导出配置
- `POST /api/v1/config/import` - 导入配置

## 通信机制

### 服务间通信

#### 1. 服务发现 (Service Discovery)
- 基于Redis的服务注册中心
- 自动服务注册和注销
- 健康检查和故障转移
- 服务元数据管理

#### 2. 事件总线 (Event Bus)
- 基于Redis发布/订阅
- 异步事件驱动架构
- 事件持久化和重放
- 事件过滤和路由

#### 3. REST API通信
- 标准HTTP/REST接口
- JSON数据格式
- 统一错误处理
- 请求/响应日志

### 事件类型

```python
class ServiceEventType(Enum):
    SERVICE_UP = "service_up"          # 服务上线
    SERVICE_DOWN = "service_down"      # 服务下线
    CONFIG_CHANGE = "config_change"    # 配置变更
    ERROR_REPORT = "error_report"      # 错误报告
    CACHE_INVALIDATE = "cache_invalidate"  # 缓存失效
    TASK_COMPLETED = "task_completed"  # 任务完成
    TASK_FAILED = "task_failed"        # 任务失败
```

## 任务队列系统

### 分布式任务处理

#### 1. 任务优先级
- CRITICAL: 关键任务 (最高优先级)
- HIGH: 高优先级任务
- NORMAL: 普通任务
- LOW: 低优先级任务

#### 2. 任务状态
- PENDING: 等待处理
- RUNNING: 正在执行
- COMPLETED: 执行完成
- FAILED: 执行失败
- CANCELLED: 已取消
- RETRYING: 重试中

#### 3. 任务特性
- 异步执行和回调
- 失败自动重试
- 超时控制和取消
- 进度跟踪和报告
- 依赖关系管理

## 监控和告警

### 监控体系

#### 1. 指标收集
- HTTP请求指标
- 任务处理指标
- 缓存性能指标
- 错误率统计
- 资源使用指标

#### 2. 告警规则
- 服务可用性告警
- 高错误率告警
- 响应时间告警
- 资源使用告警
- 业务指标告警

#### 3. 可视化面板
- 服务状态概览
- 请求率趋势
- 响应时间分析
- 错误率监控
- 资源使用情况

### Grafana面板

访问地址: http://localhost:3000
默认账号: admin / admin123

主要面板:
- 服务概览面板
- 性能监控面板
- 错误分析面板
- 任务处理面板
- 缓存性能面板

## 部署架构

### 容器化部署

#### 1. Docker Compose编排
```yaml
# 生产环境
docker-compose up -d

# 开发环境
docker-compose -f docker-compose.dev.yml --profile dev up -d

# 仅监控工具
docker-compose -f docker-compose.dev.yml --profile tools up -d
```

#### 2. 服务端口分配
| 服务 | 端口 | 说明 |
|------|------|------|
| Nginx | 80 | 负载均衡器 |
| API网关 | 8000 | API入口 |
| 下载服务 | 8001 | 文件下载 |
| 缓存服务 | 8002 | 缓存管理 |
| 错误服务 | 8003 | 错误处理 |
| 配置服务 | 8004 | 配置管理 |
| Redis | 6379 | 数据缓存 |
| Prometheus | 9090 | 指标收集 |
| Grafana | 3000 | 可视化 |

#### 3. 网络架构
- 内部网络: 172.20.0.0/16
- 服务发现: 基于DNS和服务名
- 负载均衡: Nginx + 服务发现
- 安全隔离: 网络分段和访问控制

## 配置管理

### 环境变量配置

#### 1. 服务发现配置
```bash
# 服务地址配置 (默认 localhost)
DOWNLOAD_SERVICE_HOST=localhost
DOWNLOAD_SERVICE_PORT=8001

CACHE_SERVICE_HOST=localhost
CACHE_SERVICE_PORT=8002

ERROR_SERVICE_HOST=localhost
ERROR_SERVICE_PORT=8003

CONFIG_SERVICE_HOST=localhost
CONFIG_SERVICE_PORT=8004

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

#### 2. 业务规则配置
业务规则（如 XPath 选择器、URL 模板、反爬参数）已从代码中剥离，统一管理在 `configs/business_rules.json` 文件中。

**`configs/business_rules.json` 示例**:
```json
{
  "urls": {
    "base_url": "https://www.cninfo.com.cn",
    ...
  },
  "selectors": {
    "download_button": "//button[contains(., '公告下载')]",
    ...
  },
  "timeouts": {
    "page_load": 30,
    ...
  }
}
```

#### 3. 基础配置
```bash
# 服务配置
SERVICE_NAME=stock-downloader
SERVICE_PORT=8000
LOG_LEVEL=INFO
```

#### 2. 下载服务配置
```bash
# 浏览器策略
BROWSER_STRATEGY=playwright
HEADLESS=true
MAX_CONCURRENT_DOWNLOADS=3

# 超时配置
DOWNLOAD_TIMEOUT=300
PAGE_LOAD_TIMEOUT=30
```

#### 3. 监控配置
```bash
# 指标收集
ENABLE_METRICS=true
METRICS_PORT=9090

# 告警配置
ERROR_EMAIL_ENABLED=false
ERROR_WEBHOOK_URL=
ERROR_SLACK_WEBHOOK=
```

### 配置文件优先级

1. 环境变量 (最高优先级)
2. 配置文件 (YAML/JSON)
3. 默认配置值 (最低优先级)

## 开发指南

### 本地开发

#### 1. 环境准备
```bash
# 安装依赖
pip install -r microservices/requirements.txt

# 启动Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 启动服务
python microservices/api-gateway/gateway.py
python microservices/download-service/download_service.py
# ... 其他服务
```

#### 2. 开发工具
```bash
# 启动开发环境
docker-compose -f docker-compose.dev.yml --profile dev up -d

# 启动监控工具
docker-compose -f docker-compose.dev.yml --profile tools up -d

# Redis管理界面: http://localhost:8081
```

### 服务测试

#### 1. 单元测试
```bash
# 运行微服务测试
python -m pytest tests/microservices/ -v

# 运行集成测试
python -m pytest tests/integration/ -v
```

#### 2. API测试
```bash
# 健康检查
curl http://localhost:8000/health

# 服务列表
curl http://localhost:8000/gateway/services

# 创建下载任务
curl -X POST http://localhost:8000/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{"stock_code": "000001", "page_types": ["research"]}'
```

### 调试和日志

#### 1. 日志配置
```bash
# 日志级别
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR

# 日志格式
LOG_FORMAT=json  # json, text

# 日志文件
LOG_FILE=/var/log/stock-downloader/app.log
```

#### 2. 调试工具
```bash
# 查看服务日志
docker logs stock-downloader-gateway
docker logs stock-downloader-download

# 实时日志
docker logs -f stock-downloader-gateway

# 进入容器调试
docker exec -it stock-downloader-gateway bash
```

## 生产部署

### 部署步骤

#### 1. 环境准备
```bash
# 创建生产环境配置
cp .env.example .env
# 编辑 .env 文件设置生产环境参数

# 构建Docker镜像
docker-compose build

# 启动服务
docker-compose up -d
```

#### 2. 安全配置
```bash
# SSL证书配置
# 将证书文件放到 nginx/ssl/ 目录

# 防火墙配置
# 仅开放必要端口: 80, 443, 22

# 访问控制
# 配置IP白名单和认证
```

#### 3. 监控配置
```bash
# 配置告警通知
# 编辑 monitoring/alert_rules.yml

# 设置Grafana通知
# http://localhost:3000/alerting/notification

# 配置数据保留
# Prometheus数据保留期: 200小时
# Grafana数据保留期: 永久
```

### 性能优化

#### 1. 资源优化
```yaml
# Docker资源配置
services:
  download-service:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

#### 2. 缓存优化
```bash
# Redis配置
maxmemory 1gb
maxmemory-policy allkeys-lru

# 缓存TTL设置
CACHE_TTL=3600
CACHE_MAX_SIZE=1000
```

#### 3. 并发优化
```bash
# 工作进程数
WORKER_PROCESSES=4

# 连接池大小
REDIS_MAX_CONNECTIONS=50

# 下载并发数
MAX_CONCURRENT_DOWNLOADS=3
```

## 运维手册

### 日常运维

#### 1. 服务管理
```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启特定服务
docker-compose restart download-service

# 查看服务状态
docker-compose ps
```

#### 2. 数据备份
```bash
# Redis数据备份
docker exec stock-downloader-redis redis-cli SAVE
docker cp stock-downloader-redis:/data/dump.rdb ./backup/

# 配置文件备份
cp -r microservices/ ./backup/
cp -r monitoring/ ./backup/
```

#### 3. 日志管理
```bash
# 日志轮转
# 配置logrotate处理日志文件

# 日志收集
# 可以集成ELK stack或类似方案

# 日志清理
find ./logs -name "*.log" -mtime +30 -delete
```

### 故障处理

#### 1. 常见问题
- **服务启动失败**: 检查端口占用和依赖服务
- **Redis连接失败**: 检查Redis服务和网络连接
- **下载任务失败**: 检查浏览器驱动和网络连接
- **内存溢出**: 调整JVM/Python内存配置

#### 2. 故障排查
```bash
# 检查服务状态
docker-compose ps

# 查看错误日志
docker-compose logs --tail=100 download-service

# 检查资源使用
docker stats

# 网络连通性测试
docker exec -it stock-downloader-gateway ping redis
```

#### 3. 应急恢复
```bash
# 服务重启
docker-compose restart

# 数据恢复
docker cp ./backup/dump.rdb stock-downloader-redis:/data/
docker restart stock-downloader-redis

# 配置回滚
git checkout -- microservices/
docker-compose restart
```

## 扩展和定制

### 添加新服务

#### 1. 创建服务模板
```python
# 继承MicroserviceBase类
class NewService(MicroserviceBase):
    def _setup_service(self):
        # 服务初始化逻辑
        pass

    def _register_routes(self):
        # 注册API路由
        pass
```

#### 2. 配置Docker和编排
```dockerfile
# 创建Dockerfile
FROM python:3.11-slim
# ... 构建配置
```

#### 3. 更新网关路由
```python
# 在API网关中添加新服务路由
self.routes["/api/v1/new-service"] = RouteConfig(
    path="/api/v1/new-service",
    target_service="new-service"
)
```

### 自定义扩展

#### 1. 添加新指标
```python
# 在服务中添加自定义指标
custom_metric = self.add_metric(
    "custom_operations_total",
    "counter",
    "Total custom operations"
)
```

#### 2. 扩展任务类型
```python
# 注册新的任务处理器
await task_queue.register_task_handler("custom_task", custom_handler)
```

#### 3. 集成外部系统
```python
# 添加外部服务集成
async def call_external_service():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

## 总结

股票下载器微服务架构提供了:

1. **高可用性**: 多实例部署和故障转移
2. **可扩展性**: 水平扩展和负载均衡
3. **可维护性**: 模块化设计和独立部署
4. **可观测性**: 全面的监控和日志
5. **安全性**: 网络隔离和访问控制
6. **性能**: 缓存优化和异步处理

该架构适合生产环境部署，能够满足大规模股票数据下载的需求。通过Docker容器化和完整的监控体系，简化了运维工作，提高了系统的稳定性和可靠性。