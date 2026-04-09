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
        result_expires=settings.CELERY_RESULT_EXPIRES,
        accept_content=["json"],
        task_serializer="json",
        result_serializer="json",
    )
    return app


celery_app = _build_celery()
celery_app.autodiscover_tasks(["app.tasks"])
