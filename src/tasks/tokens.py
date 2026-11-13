import asyncio
from datetime import datetime, timezone

from sqlalchemy import NullPool, delete
from sqlalchemy.ext.asyncio import create_async_engine

from config.settings import settings
from config.celery import celery_app
from database.models import ActivationToken, PasswordResetToken, RefreshToken


@celery_app.task
def delete_expired_tokens():
    asyncio.run(_task_delete_expired_token())


async def _task_delete_expired_token():  # Do not call this manually, ever
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    # the above is to avoid >attached to a different loop< error during Celery tasks
    try:
        async with engine.begin() as con:
            the_now = datetime.now(timezone.utc)
            for model in (ActivationToken, PasswordResetToken, RefreshToken):
                await con.execute(delete(model).where(model.expires_at < the_now))
    finally:
        await engine.dispose()
