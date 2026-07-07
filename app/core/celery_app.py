from celery import Celery

from app.settings.config import settings


def _build_celery() -> Celery:
    app = Celery(
        "dbadmin",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )
    app.conf.update(
        timezone=settings.CELERY_TIMEZONE,
        task_default_queue=settings.CELERY_TASK_DEFAULT_QUEUE,
        task_track_started=True,
        task_ignore_result=False,
        result_expires=settings.CELERY_RESULT_EXPIRES,
        accept_content=["json"],
        task_serializer="json",
        result_serializer="json",
        broker_connection_retry_on_startup=True,
        broker_transport_options={
            "max_retries": 10,
            "socket_connect_timeout": 2,
            "socket_timeout": 2,
        },
        # 低配机器上导入可能很慢，不用全局硬超时杀任务；具体任务需要时单独设置。
        task_time_limit=None,
        task_soft_time_limit=None,
        task_acks_late=True,
        task_acks_on_failure_or_timeout=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,  # 每次只处理一个任务
        worker_max_tasks_per_child=1,  # 每个worker进程只处理一个任务后重启
        worker_disable_rate_limits=True,  # 禁用速率限制
    )
    return app


celery_app = _build_celery()
celery_app.conf.update(
    imports=(
        "app.tasks.celery_tasks",
    )
)
