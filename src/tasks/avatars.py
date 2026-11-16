import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import NullPool, select
from sqlalchemy.ext.asyncio import create_async_engine

from config.dependencies import get_s3_storage_client
from config.settings import settings
from config.celery import celery_app
from database.models import UserProfile


logger = logging.getLogger(__name__)


@celery_app.task
def delete_orphaned_avatars():
    asyncio.run(_task_delete_orphaned_avatars())


async def _task_delete_orphaned_avatars():
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    # the above is to avoid >attached to a different loop< error during Celery tasks
    try:
        s3 = get_s3_storage_client()
        files = await s3.list_files("avatars/")
        async with engine.connect() as con:
            referenced = set(await con.scalars(
                select(UserProfile.avatar)
                .where(UserProfile.avatar.is_not(None))
            ))
        cut = datetime.now(timezone.utc) - timedelta(
            minutes=settings.AVATAR_ORPHAN_GRACE_MINUTES
        )
        to_delete = [key for key, mod in files
                     if key not in referenced and mod < cut]
        await s3.delete_files(to_delete)
        logger.info("Deleted %s orphaned avatars", len(to_delete))
    finally:
        await engine.dispose()
