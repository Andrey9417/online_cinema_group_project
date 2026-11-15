from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from database.models import PaymentStatusEnum


class CheckoutResponseSchema(BaseModel):
    session_id: str
    payment_url: str


class PaymentMessageSchema(BaseModel):
    message: str


class PaymentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    amount: Decimal
    status: PaymentStatusEnum
