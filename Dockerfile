# ========================================
# 阶段1: 构建前端
# ========================================
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# 设置npm镜像
RUN npm config set registry https://registry.npmjs.org

# 复制前端源代码
COPY web/package*.json ./

# 安装依赖
RUN npm install

# 复制前端源代码
COPY web/ ./

# 构建前端
RUN npm run build

# ========================================
# 阶段2: 构建最终镜像
# ========================================
FROM python:3.12-slim

WORKDIR /opt/dbadmin

# 设置环境变量
ENV PYTHONPATH=/opt/dbadmin \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    POETRY_VERSION=1.8.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

# 安装系统依赖（包含 nginx）
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    default-libmysqlclient-dev \
    pkg-config \
    tzdata \
    supervisor \
    nginx \
    curl \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

# 设置时区
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装 Poetry
RUN pip install poetry==1.8.2

# 复制项目依赖文件
COPY pyproject.toml poetry.lock ./

# 安装Python依赖
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main -n

# 复制项目文件
COPY . .

# 从前端构建阶段复制构建产物
COPY --from=frontend-builder /app/dist /opt/dbadmin/web/dist

# Supervisor 配置（带 nginx）
COPY deploy/supervisord_with_nginx.conf /etc/supervisor/supervisord.conf
COPY deploy/app_supervisor_with_nginx.conf /etc/supervisor/conf.d/app.conf

# Nginx 配置 - 在构建时从 config.yml 生成
COPY deploy/web.conf /etc/nginx/sites-available/web.conf.template
RUN rm -f /etc/nginx/sites-enabled/default

# 创建启动脚本 - 在启动时从 config.yml 生成 nginx 配置
RUN echo '#!/bin/bash\n\
    # 从 config.yml 读取配置并生成 nginx 配置\n\
    export NGINX_PORT=$(python3 -c "from app.core.config_loader import get_config; print(get_config().nginx.listen_port)")\n\
    export NGINX_SERVER_NAME=$(python3 -c "from app.core.config_loader import get_config; print(get_config().nginx.server_name)")\n\
    export NGINX_STATIC_ROOT=$(python3 -c "from app.core.config_loader import get_config; print(get_config().nginx.static_root)")\n\
    export NGINX_API_PROXY=$(python3 -c "from app.core.config_loader import get_config; print(get_config().nginx.api_proxy_pass)")\n\
    \n\
    # 使用 envsubst 替换模板变量\n\
    envsubst '"'"'${NGINX_PORT} ${NGINX_SERVER_NAME} ${NGINX_STATIC_ROOT} ${NGINX_API_PROXY}'"'"' \\\n\
    < /etc/nginx/sites-available/web.conf.template \\\n\
    > /etc/nginx/sites-available/web.conf\n\
    \n\
    # 创建符号链接\n\
    ln -sf /etc/nginx/sites-available/web.conf /etc/nginx/sites-enabled/\n\
    \n\
    # 启动 supervisor\n\
    exec supervisord -c /etc/supervisor/supervisord.conf\n\
    ' > /opt/dbadmin/docker-entrypoint.sh && chmod +x /opt/dbadmin/docker-entrypoint.sh

# 创建非root用户和必要目录
RUN groupadd -r -g 1000 appuser && useradd -r -u 1000 -g appuser appuser \
    && mkdir -p /opt/dbadmin/log /var/log/supervisor /var/log/nginx /var/lib/nginx /run \
    && chown -R appuser:appuser /opt/dbadmin \
    && chown -R appuser:appuser /var/log/supervisor \
    && chown -R appuser:appuser /var/log/nginx \
    && chown -R appuser:appuser /var/lib/nginx \
    && chown -R appuser:appuser /run

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost/ || exit 1

# 使用启动脚本
CMD ["/opt/dbadmin/docker-entrypoint.sh"]