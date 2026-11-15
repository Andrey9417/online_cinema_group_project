from datetime import datetime
from typing import Annotated

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_current_user
from crud.payments import list_payments
from database import get_db_session
from database.models import Payment, PaymentStatusEnum, User
from exceptions.payments import (
    EmptyOrder,
    InvalidWebhook,
    MoviesAlreadyPurchased,
    OrderNotFound,
    OrderNotPayable,
    OrderNotRefundable,
    PaymentGatewayError,
)
from payments.services import (
    checkout_order_service,
    handle_stripe_event_service,
    payment_success_service,
    refund_order_service,
)
from payments.stripe_gateway import construct_webhook_event, get_stripe_client
from schemas.payments import CheckoutResponseSchema, PaymentMessageSchema, PaymentSchema
from services.users import is_regular_user

router = APIRouter(prefix="/payments", tags=["payments"])

ASession = Annotated[AsyncSession, Depends(get_db_session)]
CUser = Annotated[User, Depends(get_current_user)]
StripeClientDep = Annotated[stripe.StripeClient, Depends(get_stripe_client)]


@router.post(
    "/orders/{order_id}/checkout",
    response_model=CheckoutResponseSchema,
    status_code=status.HTTP_201_CREATED
)
async def checkout_order(
        order_id: int,
        db: ASession,
        current_user: CUser,
        client: StripeClientDep,
) -> CheckoutResponseSchema:
    try:
        return await checkout_order_service(db=db, client=client, user=current_user, order_id=order_id)
    except OrderNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e
    except (OrderNotPayable, MoviesAlreadyPurchased) as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        ) from e
    except EmptyOrder as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except PaymentGatewayError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        ) from e


@router.post("/orders/{order_id}/refund", response_model=PaymentMessageSchema)
async def refund_order(
        order_id: int,
        db: ASession,
        current_user: CUser,
        client: StripeClientDep,
) -> PaymentMessageSchema:
    try:
        return await refund_order_service(db=db, client=client, user=current_user, order_id=order_id)
    except OrderNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e
    except OrderNotRefundable as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        ) from e
    except PaymentGatewayError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        ) from e


@router.post("/webhook/")
async def stripe_webhook(
        request: Request,
        db: ASession,
        client: StripeClientDep,
        stripe_signature: Annotated[str | None, Header()] = None,
) -> dict[str, bool]:
    try:
        event = construct_webhook_event(client, await request.body(), stripe_signature)
    except InvalidWebhook as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e

    await handle_stripe_event_service(db=db, event=event)
    return {"received": True}


@router.get("/success", response_model=PaymentMessageSchema)
async def payment_success(session_id: str, client: StripeClientDep) -> PaymentMessageSchema:
    try:
        return await payment_success_service(client=client, session_id=session_id)
    except PaymentGatewayError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        ) from e


@router.get("/cancel", response_model=PaymentMessageSchema)
async def payment_cancel() -> PaymentMessageSchema:
    return PaymentMessageSchema(message="Payment was not completed. Try again or use a different payment method")


@router.get("", response_model=list[PaymentSchema])
async def get_payments(
        db: ASession,
        current_user: CUser,
        user_id: int | None = None,
        payment_status: PaymentStatusEnum | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
) -> list[Payment]:
    if is_regular_user(current_user):
        user_id = current_user.id
    return await list_payments(
        db=db,
        user_id=user_id,
        status=payment_status,
        start_date=start_date,
        end_date=end_date,
    )
