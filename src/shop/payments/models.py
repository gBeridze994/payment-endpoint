import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import FetchedValue, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from shop.db import Base


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    cart_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("carts.id"))
    payment_method_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_payment_methods.id"))
    amount: Mapped[Decimal]
    currency: Mapped[str]
    status: Mapped[str] = mapped_column(default=PaymentStatus.PENDING)
    idempotency_key: Mapped[str]
    provider_payment_id: Mapped[str | None]
    failure_reason: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # Set by the database trigger on every update (migration 0004).
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), server_onupdate=FetchedValue()
    )
