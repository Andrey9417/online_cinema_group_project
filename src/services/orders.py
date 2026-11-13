from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crud.orders import (
    get_movies_by_user_id_and_order_status,
    create_db_order,
    cancel_order,
    get_order_by_id,
    get_orders
)
from database.models import Order, Cart, OrderItem, OrderStatusEnum, CartItem
from exceptions.orders import (
    CartNotFound,
    CartIsEmpty,
    NoAvailableMovies,
    OrderCannotBeCanceled,
    OrderDoNotExist,
    InvalidDateRange
)
from schemas.orders import (
    CreateOrderResponseSchema,
    ExcludedMovieReasonEnum,
    OrderResponseSchema,
    OrderListResponseSchema
)


async def create_order_service(db: AsyncSession, user_id: int) -> CreateOrderResponseSchema:
    cart = await db.scalar(
        select(Cart)
        .where(Cart.user_id == user_id)
        .options(selectinload(Cart.items).selectinload(CartItem.movie))
    )
    if cart is None:
        raise CartNotFound

    if not cart.items:
        raise CartIsEmpty

    # Already purchased movies
    purchased_movie_ids = await get_movies_by_user_id_and_order_status(
        db=db, user_id=user_id, order_status=OrderStatusEnum.PAID
    )

    # Movies in pending orders
    pending_movie_ids = await get_movies_by_user_id_and_order_status(
        db=db, user_id=user_id, order_status=OrderStatusEnum.PENDING
    )

    excluded_movies = []
    available_items = []

    for item in cart.items:
        if item.movie_id in purchased_movie_ids:
            excluded_movies.append({
                "movie_id": item.movie_id,
                "reason": ExcludedMovieReasonEnum.ALREADY_PURCHASED,
            })
            continue

        if item.movie_id in pending_movie_ids:
            excluded_movies.append({
                "movie_id": item.movie_id,
                "reason": ExcludedMovieReasonEnum.ALREADY_IN_PENDING_ORDER,
            })
            continue

        available_items.append(item)

    if not available_items:
        raise NoAvailableMovies

    total_amount = count_total_amount([item.movie.price for item in available_items])

    order = Order(user_id=user_id, total_amount=total_amount)
    order.items = [
        OrderItem(
            movie_id=item.movie_id,
            price_at_order=item.movie.price,
        )
        for item in available_items
    ]
    try:
        db_order = await create_db_order(db=db, order=order)

        # Remove successfully ordered movies from the cart.
        # Excluded movies remain so the user can decide what to do with them.
        for item in available_items:
            await db.delete(item)

        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return CreateOrderResponseSchema(
        order=OrderResponseSchema.model_validate(db_order),
        excluded_movies=excluded_movies,
    )


def count_total_amount(prices: list[Decimal]) -> Decimal:
    return sum(prices, start=Decimal("0.00"))


async def cancel_order_service(order_id: int, user_id: int, db: AsyncSession) -> None:
    try:
        order = await get_order_by_id(
            db=db,
            order_id=order_id,
            user_id=user_id,
            for_update=True
        )
        if order is None:
            raise OrderDoNotExist

        if order.status != OrderStatusEnum.PENDING:
            raise OrderCannotBeCanceled("Only pending orders can be canceled.")
        await cancel_order(db=db, order=order)
        await db.commit()

    except Exception:
        await db.rollback()
        raise


async def get_orders_service(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        user_id: int | None = None,
        status: OrderStatusEnum | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
) -> OrderListResponseSchema:
    if (
            start_date is not None
            and end_date is not None
            and start_date > end_date
    ):
        raise InvalidDateRange

    orders = await get_orders(
        db=db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )

    return OrderListResponseSchema(orders=orders)

