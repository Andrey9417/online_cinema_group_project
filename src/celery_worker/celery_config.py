from celery import Celery

from config.settings import settings

celery_app = Celery(
    "cinema",
    broker=settings.REDIS_URL,
    include=["celery_worker.tasks"],
)

celery_app.conf.update(
    beat_schedule={
        # Temporary: proves beat works. Replaced by the token cleanup later.
        "ping-every-one-minute": {
            "task": "debug.ping",
            "schedule": 60.0,
        },
    },
)
