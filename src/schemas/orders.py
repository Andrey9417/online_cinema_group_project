import decimal
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from database.models import OrderStatusEnum


class OrderItemResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie_id: int
    price_at_order: decimal.Decimal


class OrderResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    status: OrderStatusEnum
    total_amount: decimal.Decimal
    items: list[OrderItemResponseSchema]


class ExcludedMovieReasonEnum(StrEnum):
    ALREADY_PURCHASED = "already_purchased"
    ALREADY_IN_PENDING_ORDER = "already_in_pending_order"


class ExcludedMovieSchema(BaseModel):
    movie_id: int
    reason: ExcludedMovieReasonEnum


class CreateOrderResponseSchema(BaseModel):
    order: OrderResponseSchema
    excluded_movies: list[ExcludedMovieSchema]


class OrderListResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    orders: list[OrderResponseSchema]
