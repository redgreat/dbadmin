#!/bin/bash
# Celery Worker 健康检查脚本

# 检查Celery worker进程是否存在
if ! pgrep -f "celery.*worker" > /dev/null; then
    echo "Celery worker process not found"
    exit 1
fi

# 检查Redis连接（如果配置了的话）
if [ -f "/opt/dbadmin/config/config.yml" ]; then
    # 尝试连接Redis
    python3 -c "
import sys
import yaml
import redis

try:
    with open('/opt/dbadmin/config/config.yml', 'r') as f:
        config = yaml.safe_load(f)

    redis_url = config.get('redis', {}).get('url', 'redis://127.0.0.1:6379/0')
    r = redis.from_url(redis_url)
    r.ping()
    print('Redis connection OK')
except Exception as e:
    print(f'Redis connection failed: {e}')
    sys.exit(1)
"
fi

# 检查Celery worker是否能响应ping
python3 -c "
import sys
from celery import Celery

try:
    # 创建Celery应用实例
    app = Celery('dbadmin')
    app.config_from_object('app.core.celery_app')

    # 发送ping命令
    result = app.control.ping(timeout=5)
    if result:
        print('Celery worker ping OK')
        sys.exit(0)
    else:
        print('Celery worker ping failed: no response')
        sys.exit(1)
except Exception as e:
    print(f'Celery ping failed: {e}')
    sys.exit(1)
"