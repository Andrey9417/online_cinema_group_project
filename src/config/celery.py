from celery import Celery
from celery.schedules import crontab
from config.settings import settings


celery_app = Celery(
    "cinema", broker=settings.REDIS_URL, include=["tasks.tokens", "tasks.emails", "tasks.avatars"]
)
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "delete-expired-tokens": {
        "task": "tasks.tokens.delete_expired_tokens",
        "schedule": crontab(minute=0)  # hourly
    },
    "delete-orphaned-avatars": {
        "task": "tasks.avatars.delete_orphaned_avatars",
        "schedule": crontab(hour=3, minute=0),  # daily
    }
}
