# StockInfoDownloader 部署指南

本文档提供 StockInfoDownloader 的生产环境部署指南。

## 系统要求

- Python 3.10+
- Chrome/Chromium 浏览器
- 4GB+ RAM
- 10GB+ 磁盘空间

## 部署方式

### 方式 1: 直接部署

#### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

#### 2. 配置环境

```bash
cp .env.example .env
```

编辑 `.env` 文件:

```env
# 基础配置
SAVE_DIR=downloads
HEADLESS=true
MAX_RETRIES=3

# 浏览器策略 (playwright/selenium)
BROWSER_STRATEGY=playwright

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/downloader.log

# 反爬虫配置
ANTI_CRAWLER_ENABLED=true
BASE_DELAY=1.0
RANDOM_DELAY_MIN=0.5
RANDOM_DELAY_MAX=2.0
```

#### 3. 运行

```bash
# 下载单个公司
python main.py 000001

# 并行下载多个公司
python main.py --parallel --workers 3

# 使用配置文件
python main.py --config config.json
```

### 方式 2: Docker 部署

#### 1. 构建镜像

```bash
docker build -t stock-info-downloader .
```

#### 2. 运行容器

```bash
docker run -d \
  --name stock-downloader \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config.json:/app/config.json \
  stock-info-downloader
```

### 方式 3: Docker Compose 部署

#### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

#### 2. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f download-service
```

## 微服务部署

StockInfoDownloader 支持微服务架构部署：

| 服务 | 端口 | 描述 |
|------|------|------|
| API Gateway | 8000 | API 网关 |
| Download Service | 8001 | 下载服务 |
| Cache Service | 8002 | 缓存服务 |
| Error Service | 8003 | 错误处理服务 |
| Config Service | 8004 | 配置服务 |
| Prometheus | 9090 | 监控 |
| Grafana | 3000 | 可视化 |

### 启动微服务

```bash
docker-compose -f docker-compose.yml up -d
```

## 监控配置

### Prometheus

Prometheus 配置位于 `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'download-service'
    static_configs:
      - targets: ['download-service:8001']
```

### Grafana

Grafana 默认访问地址: http://localhost:3000

默认凭据:
- 用户名: admin
- 密码: 通过环境变量 `GF_SECURITY_ADMIN_PASSWORD` 配置

## 性能优化

### 1. 并行下载

```bash
python main.py --parallel --workers 5
```

### 2. 浏览器池

在 `config.json` 中配置:

```json
{
  "browser": {
    "pool_size": 3,
    "max_session_downloads": 20
  }
}
```

### 3. 反爬虫配置

```json
{
  "anti_crawler": {
    "enabled": true,
    "base_delay": 1.0,
    "random_delay_range": [0.5, 2.0],
    "session_limit": 50
  }
}
```

## 故障排除

### 常见问题

#### 1. Chrome 启动失败

```bash
# 检查 Chrome 是否安装
google-chrome --version

# 安装 Chrome (Ubuntu)
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list
apt-get update
apt-get install -y google-chrome-stable
```

#### 2. 下载超时

增加超时配置:

```json
{
  "timeout": {
    "page_load": 60,
    "element_wait": 60,
    "download": 300
  }
}
```

#### 3. 内存不足

减少并行工作数:

```bash
python main.py --parallel --workers 2
```

## 安全建议

1. **不要提交敏感信息**: 确保 `.env` 文件不被提交到版本控制
2. **使用环境变量**: 所有敏感配置通过环境变量传递
3. **定期更新依赖**: 保持依赖库最新
4. **监控日志**: 定期检查日志文件，发现异常行为

## 备份与恢复

### 备份

```bash
# 备份下载文件
tar -czf downloads_backup.tar.gz downloads/

# 备份配置
tar -czf config_backup.tar.gz config.json configs/
```

### 恢复

```bash
# 恢复下载文件
tar -xzf downloads_backup.tar.gz

# 恢复配置
tar -xzf config_backup.tar.gz
```
