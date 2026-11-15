from decimal import Decimal

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from crud.orders import get_movies_by_user_id_and_order_status, get_order_with_movies_by_id
from crud.payments import payment_exists
from database.models import OrderStatusEnum, Payment, PaymentItem, PaymentStatusEnum, User
from exceptions.payments import EmptyOrder, MoviesAlreadyPurchased, OrderNotFound, OrderNotPayable
from payments.stripe_gateway import create_checkout_session, from_cents, get_order_id, retrieve_checkout_session
from schemas.payments import CheckoutResponseSchema, PaymentMessageSchema


async def checkout_order_service(
        db: AsyncSession,
        client: stripe.StripeClient,
        user: User,
        order_id: int,
) -> CheckoutResponseSchema:
    order = await get_order_with_movies_by_id(db=db, order_id=order_id, user_id=user.id)
    if order is None:
        raise OrderNotFound("Order not found")

    if order.status != OrderStatusEnum.PENDING:
        raise OrderNotPayable(f"Order with status '{order.status}' cannot be paid")

    if not order.items:
        raise EmptyOrder("Order has no movies to pay for")

    paid_movie_ids = await get_movies_by_user_id_and_order_status(
        db=db,
        order_status=OrderStatusEnum.PAID,
        user_id=user.id,
    )
    purchased_movie_ids = paid_movie_ids & {item.movie_id for item in order.items}
    if purchased_movie_ids:
        raise MoviesAlreadyPurchased(
            f"Movies already purchased: {', '.join(map(str, sorted(purchased_movie_ids)))}"
        )

    total_amount = sum((item.price_at_order for item in order.items), start=Decimal("0.00"))
    if order.total_amount != total_amount:
        order.total_amount = total_amount
        await db.commit()

    checkout_session = await create_checkout_session(client, order, user.email)
    return CheckoutResponseSchema(session_id=checkout_session.id, payment_url=checkout_session.url)


async def record_payment(
        db: AsyncSession,
        checkout_session: stripe.checkout.Session,
        payment_status: PaymentStatusEnum,
) -> None:
    order_id = get_order_id(checkout_session)
    if order_id is None:
        return

    order = await get_order_with_movies_by_id(db=db, order_id=order_id, for_update=True)
    if order is None or await payment_exists(db=db, external_payment_id=checkout_session.id):
        return

    db.add(
        Payment(
            user_id=order.user_id,
            order_id=order.id,
            status=payment_status,
            amount=from_cents(checkout_session.amount_total),
            external_payment_id=checkout_session.id,
            items=[
                PaymentItem(order_item_id=item.id, price_at_payment=item.price_at_order)
                for item in order.items
            ],
        )
    )
    if payment_status == PaymentStatusEnum.SUCCESSFUL:
        order.status = OrderStatusEnum.PAID
    await db.commit()


async def handle_stripe_event_service(db: AsyncSession, event: stripe.Event) -> None:
    checkout_session = event.data.object
    if event.type == "checkout.session.completed" and checkout_session.payment_status == "paid":
        await record_payment(db, checkout_session, PaymentStatusEnum.SUCCESSFUL)
    elif event.type == "checkout.session.expired":
        await record_payment(db, checkout_session, PaymentStatusEnum.CANCELED)


async def payment_success_service(client: stripe.StripeClient, session_id: str) -> PaymentMessageSchema:
    checkout_session = await retrieve_checkout_session(client, session_id)
    if checkout_session.payment_status == "paid":
        return PaymentMessageSchema(message="Payment completed successfully")
    return PaymentMessageSchema(message="Payment is not completed yet")
