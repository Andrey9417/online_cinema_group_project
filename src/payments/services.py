from decimal import Decimal

import stripe
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from crud.payments import get_order_for_checkout, get_purchased_movie_ids
from database.models import OrderStatusEnum, User
from exceptions.payments import EmptyOrder, MoviesAlreadyPurchased, OrderNotFound, OrderNotPayable
from payments.stripe_gateway import create_checkout_session
from schemas.payments import CheckoutResponseSchema


async def checkout_order_service(
        db: AsyncSession,
        client: stripe.StripeClient,
        user: User,
        order_id: int,
) -> CheckoutResponseSchema:
    order = await get_order_for_checkout(db=db, order_id=order_id, user_id=user.id)
    if order is None:
        raise OrderNotFound("Order not found")

    if order.status != OrderStatusEnum.PENDING:
        raise OrderNotPayable(f"Order with status '{order.status}' cannot be paid")

    if not order.items:
        raise EmptyOrder("Order has no movies to pay for")

    purchased_movie_ids = await get_purchased_movie_ids(
        db=db,
        user_id=user.id,
        movie_ids=[item.movie_id for item in order.items],
    )
    if purchased_movie_ids:
        raise MoviesAlreadyPurchased(
            f"Movies already purchased: {', '.join(map(str, sorted(purchased_movie_ids)))}"
        )

    total_amount = sum((item.price_at_order for item in order.items), start=Decimal("0.00"))
    if order.total_amount != total_amount:
        order.total_amount = total_amount
        try:
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            raise

    checkout_session = await create_checkout_session(client, order, user.email)
    return CheckoutResponseSchema(session_id=checkout_session.id, payment_url=checkout_session.url)
