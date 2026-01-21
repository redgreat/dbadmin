#!/bin/bash
# Nginx 配置文件生成脚本
# 从 config.yml 读取配置并生成 nginx 配置文件

# 使用 Python 读取配置并导出为环境变量
eval $(python3 -c "
from app.core.config_loader import get_config
config = get_config()
print(f'export NGINX_PORT={config.nginx.listen_port}')
print(f'export NGINX_SERVER_NAME=\"{config.nginx.server_name}\"')
print(f'export NGINX_STATIC_ROOT=\"{config.nginx.static_root}\"')
print(f'export NGINX_API_PROXY=\"{config.nginx.api_proxy_pass}\"')
")

# 使用 envsubst 替换模板中的变量
envsubst '${NGINX_PORT} ${NGINX_SERVER_NAME} ${NGINX_STATIC_ROOT} ${NGINX_API_PROXY}' \
    < /opt/dbadmin/deploy/web.conf.template \
    > /etc/nginx/sites-available/web.conf

echo "Nginx 配置已生成："
cat /etc/nginx/sites-available/web.conf
