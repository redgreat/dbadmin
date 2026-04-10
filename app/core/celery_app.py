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
        task_ignore_result=True,
        result_expires=settings.CELERY_RESULT_EXPIRES,
        accept_content=["json"],
        task_serializer="json",
        result_serializer="json",
        broker_connection_retry_on_startup=False,
        broker_transport_options={
            "max_retries": 0,
            "socket_connect_timeout": 2,
            "socket_timeout": 2,
        },
    )
    return app


celery_app = _build_celery()
celery_app.autodiscover_tasks(["app.tasks"])
