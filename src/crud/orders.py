from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Order, OrderStatusEnum, OrderItem
from exceptions.orders import InvalidDateRange


async def get_orders(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        user_id: int | None = None,
        status: OrderStatusEnum | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
) -> list[Order]:

    stmt = select(Order)
    if user_id is not None:
        stmt = stmt.where(Order.user_id == user_id)

    if status is not None:
        stmt = stmt.where(Order.status == status)

    if start_date is not None:
        stmt = stmt.where(Order.created_at >= start_date)

    if end_date is not None:
        stmt = stmt.where(Order.created_at <= end_date)

    stmt = (
        stmt
        .order_by(Order.created_at.desc())
        .offset(skip).limit(limit)
        .options(selectinload(Order.items))
    )

    orders = await db.scalars(stmt)
    return list(orders.all())


async def get_order_by_id(
        db: AsyncSession,
        order_id: int,
        user_id: int | None = None,
        for_update: bool = False,
) -> Order | None:
    stmt = (
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
    )

    if user_id is not None:
        stmt = stmt.where(Order.user_id == user_id)

    if for_update:
        stmt = stmt.with_for_update()

    order = await db.scalar(stmt)

    return order


async def get_order_list_by_user_id(
        db: AsyncSession, user_id: int, skip: int = 0, limit: int = 20,
) -> list[Order]:
    stmt = (
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .offset(skip).limit(limit)
        .options(selectinload(Order.items))
    )
    orders = await db.scalars(stmt)
    return list(orders.all())


async def create_db_order(
        db: AsyncSession,
        order: Order
) -> Order:
    db.add(order)
    await db.flush()
    return order


async def cancel_order(
        db: AsyncSession,
        order: Order,
) -> Order:
    order.status = OrderStatusEnum.CANCELED
    await db.flush()
    return order


async def get_movies_by_user_id_and_order_status(
        db: AsyncSession,
        order_status: OrderStatusEnum,
        user_id: int,
) -> set[int]:
    movie_ids = await db.scalars(
        select(OrderItem.movie_id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.user_id == user_id, Order.status == order_status)
    )
    return set(movie_ids.all())