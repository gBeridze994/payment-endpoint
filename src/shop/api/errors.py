"""Turns exceptions into JSON error responses: {"error": {"code": ..., "message": ...}}."""

import logging
from collections.abc import Callable

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException

from shop.services.errors import (
    CartNotFound,
    CartNotPayable,
    EmptyCart,
    IdempotencyKeyReused,
    PaymentConflict,
    PaymentMethodNotFound,
)

logger = logging.getLogger(__name__)


class InvalidRequest(Exception):
    pass


class Unauthorized(Exception):
    pass


# Exception class -> (HTTP status, error code shown to the client).
ERROR_RESPONSES: dict[type[Exception], tuple[int, str]] = {
    InvalidRequest: (400, "invalid_request"),
    Unauthorized: (401, "unauthorized"),
    CartNotFound: (404, "cart_not_found"),
    CartNotPayable: (409, "cart_not_payable"),
    PaymentConflict: (409, "payment_conflict"),
    EmptyCart: (422, "empty_cart"),
    PaymentMethodNotFound: (422, "payment_method_not_found"),
    IdempotencyKeyReused: (422, "idempotency_key_reused"),
}


def register_error_handlers(app: Flask) -> None:
    for error_class, (status_code, code) in ERROR_RESPONSES.items():
        app.register_error_handler(error_class, _error_handler(status_code, code))
    app.register_error_handler(HTTPException, _handle_http_exception)
    app.register_error_handler(Exception, _handle_unexpected_error)


def error_response(status_code: int, code: str, message: str) -> tuple[Response, int]:
    return jsonify({"error": {"code": code, "message": message}}), status_code


def _error_handler(status_code: int, code: str) -> Callable[[Exception], tuple[Response, int]]:
    def handle(error: Exception) -> tuple[Response, int]:
        return error_response(status_code, code, str(error))

    return handle


def _handle_http_exception(error: HTTPException) -> tuple[Response, int]:
    status_code = error.code or 500
    code = (error.name or "error").lower().replace(" ", "_")
    return error_response(status_code, code, error.description or "")


def _handle_unexpected_error(error: Exception) -> tuple[Response, int]:
    logger.exception("Unhandled error", exc_info=error)
    return error_response(500, "internal_error", "An unexpected error occurred.")
