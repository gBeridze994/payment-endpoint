import uuid

from flask import Blueprint, Response, jsonify, request

from shop.carts import CartNotFound
from shop.payment_methods import PaymentMethodNotFound
from shop.payments.dependencies import get_payment_service
from shop.payments.errors import (
    CartNotPayable,
    EmptyCart,
    IdempotencyKeyReused,
    InvalidCartTotal,
    PaymentConflict,
)
from shop.payments.models import PaymentStatus
from shop.payments.schemas import CreatePaymentRequest, PaymentResponse, StartCartPayment
from shop.payments.service import PaymentService
from shop.web.auth import current_user_id
from shop.web.errors import ErrorResponses, register_error_responses
from shop.web.injection import inject
from shop.web.validation import parse_json_body, validate

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
    InvalidCartTotal: (422, "invalid_cart_total"),
    PaymentMethodNotFound: (422, "payment_method_not_found"),
    IdempotencyKeyReused: (422, "idempotency_key_reused"),
}

payments_blueprint = Blueprint("payments", __name__)
register_error_responses(payments_blueprint, PAYMENT_ERROR_RESPONSES)


@payments_blueprint.post("/carts/<uuid:cart_id>/payments")
@inject(service=get_payment_service)
def create_cart_payment(cart_id: uuid.UUID, service: PaymentService) -> tuple[Response, int]:
    user_id = current_user_id()
    body = parse_json_body(CreatePaymentRequest)
    command = validate(
        StartCartPayment,
        {
            "user_id": user_id,
            "cart_id": cart_id,
            "idempotency_key": request.headers.get("Idempotency-Key", ""),
            "payment_method_id": body.payment_method_id,
        },
    )

    payment = PaymentResponse.model_validate(service.start_cart_payment(command))
    return jsonify(payment.model_dump(mode="json")), HTTP_STATUS_BY_PAYMENT_STATUS[payment.status]
