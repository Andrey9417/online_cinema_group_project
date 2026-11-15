from datetime import datetime

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Payment, PaymentStatusEnum


async def payment_exists(db: AsyncSession, external_payment_id: str) -> bool:
    return await db.scalar(
        select(exists().where(Payment.external_payment_id == external_payment_id))
    )


async def list_payments(
        db: AsyncSession,
        user_id: int | None = None,
        status: PaymentStatusEnum | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
) -> list[Payment]:
    stmt = select(Payment).order_by(Payment.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(Payment.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Payment.status == status)
    if start_date is not None:
        stmt = stmt.where(Payment.created_at >= start_date)
    if end_date is not None:
        stmt = stmt.where(Payment.created_at <= end_date)
    payments = await db.scalars(stmt)
    return list(payments.all())
