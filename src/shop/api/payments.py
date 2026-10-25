import uuid

from flask import Blueprint, Response, jsonify, request

from shop.api.dependencies import get_db_sessions, get_payment_provider
from shop.api.errors import InvalidRequest, Unauthorized
from shop.db.models import Payment, PaymentStatus
from shop.services.payments import start_cart_payment

payments_blueprint = Blueprint("payments", __name__)

MAX_IDEMPOTENCY_KEY_LENGTH = 255

HTTP_STATUS_BY_PAYMENT_STATUS = {
    PaymentStatus.SUCCEEDED: 201,
    PaymentStatus.FAILED: 402,
    PaymentStatus.PENDING: 202,
}


@payments_blueprint.post("/carts/<uuid:cart_id>/payments")
def create_cart_payment(cart_id: uuid.UUID) -> tuple[Response, int]:
    payment = start_cart_payment(
        sessions=get_db_sessions(),
        provider=get_payment_provider(),
        user_id=_current_user_id(),
        cart_id=cart_id,
        idempotency_key=_idempotency_key(),
        payment_method_id=_requested_payment_method_id(),
    )
    return jsonify(_serialize_payment(payment)), HTTP_STATUS_BY_PAYMENT_STATUS[
        PaymentStatus(payment.status)
    ]


def _current_user_id() -> uuid.UUID:
    """Reads the user id that an upstream auth layer would set (see README)."""
    try:
        return uuid.UUID(request.headers["X-User-Id"])
    except KeyError, ValueError:
        raise Unauthorized("A valid X-User-Id header is required.") from None


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
