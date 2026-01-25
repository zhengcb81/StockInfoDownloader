# 股票下载器微服务快速启动指南

## 快速开始

### 1. 环境要求

- Docker >= 20.10
- Docker Compose >= 2.0
- Python >= 3.8 (可选，用于本地开发)

### 2. 一键启动

```bash
# 克隆项目
git clone <repository-url>
cd StockInfoDownloader

# 启动生产环境
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 3. 验证部署

```bash
# 检查服务健康状态
curl http://localhost/health

# 查看服务列表
curl http://localhost:8000/gateway/services

# 访问监控面板
# Grafana: http://localhost:3000 (admin/admin123)
# Prometheus: http://localhost:9090
```

## 开发环境

### 1. 启动开发环境

```bash
# 启动所有开发服务
docker-compose -f docker-compose.dev.yml --profile dev up -d

# 启动开发工具 (Redis管理器等)
docker-compose -f docker-compose.dev.yml --profile tools up -d
```

### 2. 本地开发

```bash
# 安装依赖
pip install -r microservices/requirements.txt

# 启动Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 启动单个服务
python microservices/api-gateway/gateway.py
python microservices/download-service/download_service.py
```

## 基本使用

### 1. 创建下载任务

```bash
curl -X POST http://localhost:8000/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{
    "stock_code": "000001",
    "stock_name": "平安银行",
    "page_types": ["research", "periodicReports"],
    "keywords": ["2023", "年报"],
    "max_pages": 5
  }'
```

### 2. 查看任务状态

```bash
# 获取任务列表
curl http://localhost:8000/api/v1/download

# 获取特定任务
curl http://localhost:8000/api/v1/download/{task_id}
```

### 3. 缓存操作

```bash
# 设置缓存
curl -X POST http://localhost:8000/api/v1/cache \
  -H "Content-Type: application/json" \
  -d '{
    "key": "test_key",
    "value": "test_value",
    "ttl": 3600
  }'

# 获取缓存
curl http://localhost:8000/api/v1/cache/test_key
```

## 监控和调试

### 1. 服务监控

```bash
# 查看实时日志
docker-compose logs -f download-service

# 查看服务状态
curl http://localhost:8000/gateway/health

# 查看队列统计
curl http://localhost:8000/api/v1/download/stats
```

### 2. 性能监控

访问 Grafana 面板: http://localhost:3000
- 默认用户: admin
- 默认密码: admin123

### 3. Redis管理

访问 Redis 管理界面: http://localhost:8081
- 连接地址: redis:6379
- 可视化管理缓存数据

## 常用命令

### 服务管理

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart download-service

# 更新并重启
docker-compose up -d --build
```

### 日志和调试

```bash
# 查看所有日志
docker-compose logs

# 查看特定服务日志
docker-compose logs download-service

# 实时查看日志
docker-compose logs -f api-gateway

# 查看错误日志
docker-compose logs --tail=100 | grep ERROR
```

### 数据和备份

```bash
# 备份Redis数据
docker exec stock-downloader-redis redis-cli SAVE
docker cp stock-downloader-redis:/data/dump.rdb ./backup/

# 清理日志
find ./logs -name "*.log" -mtime +7 -delete
```

## 故障排除

### 1. 端口冲突

```bash
# 检查端口占用
netstat -tulpn | grep :8000
netstat -tulpn | grep :6379

# 修改端口配置
编辑 docker-compose.yml 文件中的端口映射
```

### 2. 服务启动失败

```bash
# 查看详细错误
docker-compose logs --tail=50 download-service

# 检查依赖服务
docker-compose ps

# 重新构建服务
docker-compose build download-service
```

### 3. 网络问题

```bash
# 测试网络连通性
docker exec -it stock-downloader-gateway ping redis

# 检查DNS解析
docker exec -it stock-downloader-gateway nslookup redis
```

## 配置说明

### 环境变量

复制 `.env.example` 到 `.env` 并根据需要修改:

```bash
# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379

# 下载服务配置
BROWSER_STRATEGY=playwright
HEADLESS=true
MAX_CONCURRENT_DOWNLOADS=3

# 监控配置
ENABLE_METRICS=true
LOG_LEVEL=INFO
```

### 服务端口

| 服务 | 端口 | 用途 |
|------|------|------|
| 80 | Nginx | 主入口 |
| 8000 | API网关 | API路由 |
| 8001 | 下载服务 | 文件下载 |
| 8002 | 缓存服务 | 缓存管理 |
| 8003 | 错误服务 | 错误处理 |
| 8004 | 配置服务 | 配置管理 |
| 3000 | Grafana | 监控面板 |
| 9090 | Prometheus | 指标收集 |

## API文档

### 认证

目前所有API都是开放的，生产环境建议添加认证:

```bash
# API密钥认证
curl -H "Authorization: Bearer your-api-key" \
  http://localhost:8000/api/v1/download
```

### 请求格式

所有API请求使用JSON格式:

```bash
curl -X POST http://localhost:8000/api/v1/download \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

### 响应格式

统一响应格式:

```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2023-01-01T00:00:00Z"
}
```

## 性能优化

### 1. 资源限制

```yaml
# 在docker-compose.yml中添加
services:
  download-service:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
```

### 2. 缓存优化

```bash
# 调整Redis配置
maxmemory 1gb
maxmemory-policy allkeys-lru
```

### 3. 并发控制

```bash
# 限制并发下载任务
MAX_CONCURRENT_DOWNLOADS=3
```

## 安全建议

### 1. 网络安全

```bash
# 仅开放必要端口
ufw allow 80
ufw allow 443
ufw allow 22
```

### 2. 访问控制

```bash
# 配置Nginx访问控制
location /api/ {
    allow 192.168.1.0/24;
    deny all;
}
```

### 3. 数据保护

```bash
# 启用SSL/TLS
# 配置证书文件
nginx/ssl/cert.pem
nginx/ssl/key.pem
```

## 获取帮助

### 文档资源

- [完整架构文档](./MICROSERVICES_ARCHITECTURE.md)
- [API文档](http://localhost:8000/docs)
- [监控面板](http://localhost:3000)

### 常见问题

1. **服务无法启动**: 检查Docker和端口占用
2. **Redis连接失败**: 确认Redis服务运行
3. **下载任务失败**: 检查网络连接和浏览器驱动
4. **内存不足**: 调整Docker内存限制

### 技术支持

- 查看日志: `docker-compose logs`
- 检查状态: `docker-compose ps`
- 重启服务: `docker-compose restart`

---

**提示**: 建议先在开发环境测试，确认无误后再部署到生产环境。