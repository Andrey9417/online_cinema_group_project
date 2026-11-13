import decimal
from datetime import datetime

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
    items: list[OrderItemResponseSchema] # or list[int]
