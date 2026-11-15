from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache

import stripe

from config.settings import settings
from database.models.orders import Order
from exceptions.payments import InvalidWebhook, PaymentGatewayError


@lru_cache
def get_stripe_client() -> stripe.StripeClient:
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)


def to_cents(amount: Decimal) -> int:
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def from_cents(amount: int) -> Decimal:
    return Decimal(amount) / 100


def build_checkout_session_params(order: Order, customer_email: str) -> dict:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.STRIPE_CHECKOUT_TTL_MINUTES)
    return {
        "mode": "payment",
        "line_items": [
            {
                "price_data": {
                    "currency": settings.STRIPE_CURRENCY,
                    "unit_amount": to_cents(item.price_at_order),
                    "product_data": {"name": item.movie.name},
                },
                "quantity": 1,
            }
            for item in order.items
        ],
        "customer_email": customer_email,
        "client_reference_id": str(order.id),
        "metadata": {"order_id": str(order.id), "user_id": str(order.user_id)},
        "success_url": f"{settings.API_URL}/api/v1/payments/success?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{settings.API_URL}/api/v1/payments/cancel?order_id={order.id}",
        "expires_at": int(expires_at.timestamp()),
    }


async def create_checkout_session(
        client: stripe.StripeClient,
        order: Order,
        customer_email: str
) -> stripe.checkout.Session:
    try:
        return await client.v1.checkout.sessions.create_async(
            params=build_checkout_session_params(order, customer_email)
        )
    except stripe.StripeError as e:
        raise PaymentGatewayError("Could not create payment session, try again later") from e


async def retrieve_checkout_session(client: stripe.StripeClient, session_id: str) -> stripe.checkout.Session:
    try:
        return await client.v1.checkout.sessions.retrieve_async(session_id)
    except stripe.StripeError as e:
        raise PaymentGatewayError("Could not retrieve payment session, try again later") from e


async def refund_checkout_session(client: stripe.StripeClient, session_id: str) -> None:
    try:
        checkout_session = await client.v1.checkout.sessions.retrieve_async(session_id)
        await client.v1.refunds.create_async(params={"payment_intent": checkout_session.payment_intent})
    except stripe.StripeError as e:
        raise PaymentGatewayError("Could not refund payment, try again later") from e


def construct_webhook_event(
        client: stripe.StripeClient,
        payload: bytes,
        signature: str | None,
) -> stripe.Event:
    try:
        return client.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError) as e:
        raise InvalidWebhook("Invalid Stripe webhook") from e


def get_order_id(checkout_session: stripe.checkout.Session) -> int | None:
    metadata = checkout_session.to_dict().get("metadata") or {}
    try:
        return int(metadata["order_id"])
    except (KeyError, ValueError):
        return None
