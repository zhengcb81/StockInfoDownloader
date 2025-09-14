FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 复制requirements文件
COPY ../requirements.txt .
COPY ../cache-service/requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY ../common/ ./common/
COPY ../cache-service/ ./cache-service/
COPY ../src/ ./src/

# 创建日志目录
RUN mkdir -p /app/logs

# 创建app用户
RUN useradd -m -u 1000 app && chown -R app:app /app
USER app

# 暴露端口
EXPOSE 8002

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/api/v1/cache/health || exit 1

# 启动命令
CMD ["python", "cache-service/cache_service.py"]