from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Payment


async def payment_exists(db: AsyncSession, external_payment_id: str) -> bool:
    return await db.scalar(
        select(exists().where(Payment.external_payment_id == external_payment_id))
    )
