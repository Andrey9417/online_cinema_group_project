import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from database.models.accounts import User
    from database.models.orders import Order, OrderItem


class PaymentStatusEnum(enum.StrEnum):
    SUCCESSFUL = "successful"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[PaymentStatusEnum] = mapped_column(
        Enum(PaymentStatusEnum),
        default=PaymentStatusEnum.SUCCESSFUL,
        server_default=PaymentStatusEnum.SUCCESSFUL.name,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    external_payment_id: Mapped[Optional[str]] = mapped_column(String(255))

    user: Mapped["User"] = relationship(back_populates="payments")
    order: Mapped["Order"] = relationship(back_populates="payments")
    items: Mapped[list["PaymentItem"]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PaymentItem(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE")
    )
    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("order_items.id")
    )
    price_at_payment: Mapped[Decimal] = mapped_column(
        Numeric(10, 2)
    )

    payment: Mapped["Payment"] = relationship(back_populates="items")
    order_item: Mapped["OrderItem"] = relationship()
