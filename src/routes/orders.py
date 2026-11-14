from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_current_user
from crud.orders import get_order_with_movies_by_id
from database import get_db_session
from database.models import User, OrderStatusEnum
from exceptions.orders import (
    CartNotFound,
    CartIsEmpty,
    NoAvailableMovies,
    OrderDoNotExist,
    OrderCannotBeCanceled, InvalidDateRange
)
import services
from schemas.orders import (
    OrderListResponseSchema,
    OrderDetailResponseSchema,
    CreateOrderResponseSchema
)
from services import is_regular_user

router = APIRouter(tags=["orders"])

SessionDP = Annotated[AsyncSession, Depends(get_db_session)]
UserDP = Annotated[User, Depends(get_current_user)]


@router.get("/orders", response_model=OrderListResponseSchema)
async def get_orders_list(
    db: SessionDP,
    user: UserDP,
    user_id: int | None = Query(None, ge=1),
    order_status: OrderStatusEnum | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1),
):
    """
    Retrieve a paginated list of orders.

    Regular users can view only their own orders.
    Moderators and admins can view orders belonging to all users.
    """
    if is_regular_user(user):
        user_id = user.id

    skip = per_page * (page - 1)
    try:
        return await services.get_orders_service(
            db=db,
            user_id=user_id,
            skip=skip,
            limit=per_page,
            status=order_status,
            start_date=start_date,
            end_date=end_date,
        )
    except InvalidDateRange:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date range"
        )


@router.get(
    "/orders/{order_id}",
    response_model=OrderDetailResponseSchema,
)
async def get_order_detail(
    order_id: int,
    db: SessionDP,
    user: UserDP,
):
    """
    Retrieve an order by ID.

    Regular users can access only their own orders.
    Moderators and admins can access orders belonging to any user.
    """

    order = await get_order_with_movies_by_id(
        order_id=order_id,
        user_id=user.id if is_regular_user(user) else None,
        db=db,
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/orders", response_model=CreateOrderResponseSchema)
async def create_order(db: SessionDP, user: UserDP):
    """
    Create a new order from the authenticated user's shopping cart.

    Excludes movies that have already been purchased or are included
    in another pending order.
    """
    try:
        return await services.create_order_service(
            db=db,
            user_id=user.id,
        )
    except CartNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    except CartIsEmpty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty"
        )
    except NoAvailableMovies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No available movies"
        )


@router.patch(
    "/orders/{order_id}/cancel",
    response_model=OrderDetailResponseSchema
)
async def cancel_order(
        db: SessionDP,
        order_id: int,
        user: UserDP,
):
    """
    Cancel an order belonging to the authenticated user.

    Only pending orders can be canceled.
    """
    try:
        return await services.cancel_order_service(
            db=db,
            order_id=order_id,
            user_id=user.id
        )
    except OrderDoNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    except OrderCannotBeCanceled as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
