from celery_worker.celery_config import celery_app


@celery_app.task(name="debug.ping")
def ping() -> str:
    print("pong")
    return "pong"
