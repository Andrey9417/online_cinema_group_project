from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Order, OrderItem, OrderStatusEnum


async def get_order_for_checkout(
        db: AsyncSession,
        order_id: int,
        user_id: int,
) -> Order | None:
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.user_id == user_id)
        .options(selectinload(Order.items).selectinload(OrderItem.movie))
    )
    return await db.scalar(stmt)


async def get_purchased_movie_ids(
        db: AsyncSession,
        user_id: int,
        movie_ids: list[int],
) -> set[int]:
    purchased = await db.scalars(
        select(OrderItem.movie_id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            Order.user_id == user_id,
            Order.status == OrderStatusEnum.PAID,
            OrderItem.movie_id.in_(movie_ids),
        )
    )
    return set(purchased.all())
