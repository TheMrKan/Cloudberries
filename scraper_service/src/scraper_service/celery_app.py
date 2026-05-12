from celery import Celery
from scraper_service import tasks
from scraper_service.config import Settings

settings = Settings()

celery_app = Celery(
    "scraper_service",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["scraper_service.tasks"], related_name="pipeline")

celery_app.conf.beat_schedule = {
    "daily-full-pipeline": {
        "task": "scraper_service.tasks.pipeline.run_full_pipeline",
        "schedule": crontab(hour=3, minute=0),
    },
    "check-batch-pipeline": {
        "task": "scraper_service.tasks.pipeline.run_batch_pipeline",
        "schedule": 900.0, 
    },
}