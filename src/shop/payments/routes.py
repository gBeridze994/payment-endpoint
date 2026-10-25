import uuid

from flask import Blueprint, Response, current_app, jsonify, request

from shop.db import get_sessions
from shop.payments.errors import (
    CartNotFound,
    CartNotPayable,
    EmptyCart,
    IdempotencyKeyReused,
    PaymentConflict,
    PaymentMethodNotFound,
)
from shop.payments.models import Payment, PaymentStatus
from shop.payments.provider import PaymentProvider
from shop.payments.service import start_cart_payment
from shop.web.auth import current_user_id
from shop.web.errors import ErrorResponses, InvalidRequest, register_error_responses

PROVIDER_EXTENSION = "shop.payment_provider"
MAX_IDEMPOTENCY_KEY_LENGTH = 255

HTTP_STATUS_BY_PAYMENT_STATUS = {
    PaymentStatus.SUCCEEDED: 201,
    PaymentStatus.FAILED: 402,
    PaymentStatus.PENDING: 202,
}

PAYMENT_ERROR_RESPONSES: ErrorResponses = {
    CartNotFound: (404, "cart_not_found"),
    CartNotPayable: (409, "cart_not_payable"),
    PaymentConflict: (409, "payment_conflict"),
    EmptyCart: (422, "empty_cart"),
    PaymentMethodNotFound: (422, "payment_method_not_found"),
    IdempotencyKeyReused: (422, "idempotency_key_reused"),
}

payments_blueprint = Blueprint("payments", __name__)
register_error_responses(payments_blueprint, PAYMENT_ERROR_RESPONSES)


@payments_blueprint.post("/carts/<uuid:cart_id>/payments")
def create_cart_payment(cart_id: uuid.UUID) -> tuple[Response, int]:
    payment = start_cart_payment(
        sessions=get_sessions(),
        provider=_payment_provider(),
        user_id=current_user_id(),
        cart_id=cart_id,
        idempotency_key=_idempotency_key(),
        payment_method_id=_requested_payment_method_id(),
    )
    status_code = HTTP_STATUS_BY_PAYMENT_STATUS[PaymentStatus(payment.status)]
    return jsonify(_serialize_payment(payment)), status_code


def _payment_provider() -> PaymentProvider:
    provider: PaymentProvider = current_app.extensions[PROVIDER_EXTENSION]
    return provider


def _idempotency_key() -> str:
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key or len(key) > MAX_IDEMPOTENCY_KEY_LENGTH:
        raise InvalidRequest(
            f"An Idempotency-Key header of 1 to {MAX_IDEMPOTENCY_KEY_LENGTH} characters "
            "is required."
        )
    return key


def _requested_payment_method_id() -> uuid.UUID | None:
    if not request.data:
        return None
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise InvalidRequest("The request body must be a JSON object.")
    if body.get("payment_method_id") is None:
        return None
    try:
        return uuid.UUID(str(body["payment_method_id"]))
    except ValueError:
        raise InvalidRequest("payment_method_id must be a UUID.") from None


def _serialize_payment(payment: Payment) -> dict[str, str | None]:
    return {
        "id": str(payment.id),
        "cart_id": str(payment.cart_id),
        "payment_method_id": str(payment.payment_method_id),
        "status": payment.status,
        "amount": str(payment.amount),
        "currency": payment.currency,
        "failure_reason": payment.failure_reason,
    }
