import logging
from typing import Annotated

import stripe
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_current_user
from database import get_db_session
from database.models import User
from exceptions.payments import (
    EmptyOrder,
    MoviesAlreadyPurchased,
    OrderNotFound,
    OrderNotPayable,
    PaymentGatewayError,
)
from payments.services import checkout_order_service
from payments.stripe_gateway import get_stripe_client
from schemas.payments import CheckoutResponseSchema

logger = logging.getLogger(__name__)

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
        logger.exception("Stripe checkout failed for order %s", order_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        ) from e
