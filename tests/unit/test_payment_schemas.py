import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from shop.payments.schemas import CreatePaymentRequest, PaymentResponse, StartCartPayment


def start_cart_payment(idempotency_key):
    return StartCartPayment(
        user_id=uuid.uuid4(), cart_id=uuid.uuid4(), idempotency_key=idempotency_key
    )


def test_idempotency_key_is_stripped():
    assert start_cart_payment("  key-1  ").idempotency_key == "key-1"


@pytest.mark.parametrize("idempotency_key", ["", "   ", "x" * 256])
def test_idempotency_key_must_have_1_to_255_characters(idempotency_key):
    with pytest.raises(ValidationError):
        start_cart_payment(idempotency_key)


def test_create_payment_request_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        CreatePaymentRequest.model_validate({"payment_methd_id": str(uuid.uuid4())})


def test_payment_response_serializes_amount_as_string():
    response = PaymentResponse(
        id=uuid.uuid4(),
        cart_id=uuid.uuid4(),
        payment_method_id=uuid.uuid4(),
        status="succeeded",
        amount=Decimal("70.00"),
        currency="USD",
        failure_reason=None,
    )

    assert response.model_dump(mode="json")["amount"] == "70.00"
