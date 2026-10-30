"""Data transfer objects of the payment part."""

import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from shop.payments.models import PaymentStatus

MAX_IDEMPOTENCY_KEY_LENGTH = 255

IdempotencyKey = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_IDEMPOTENCY_KEY_LENGTH),
]


class CreatePaymentRequest(BaseModel):
    """JSON body of POST /carts/{cart_id}/payments.

    Unknown fields are rejected, so a typo such as "payment_methd_id" cannot
    silently charge the default card.
    """

    model_config = ConfigDict(extra="forbid")

    payment_method_id: uuid.UUID | None = None


class StartCartPayment(BaseModel):
    """Everything PaymentService needs to start a payment for a cart."""

    model_config = ConfigDict(frozen=True)

    user_id: uuid.UUID
    cart_id: uuid.UUID
    idempotency_key: IdempotencyKey
    # None means the user's default payment method.
    payment_method_id: uuid.UUID | None = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cart_id: uuid.UUID
    payment_method_id: uuid.UUID
    status: PaymentStatus
    # Serialized as a string, so no precision is lost.
    amount: Decimal
    currency: str
    failure_reason: str | None
