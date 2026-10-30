"""The payment part of the shop: paying for a cart with a saved card.

Other modules use payments only through what this package exports.
"""

from flask import Flask

from shop.payments.dependencies import PROVIDER_EXTENSION
from shop.payments.models import Payment, PaymentStatus
from shop.payments.provider import ChargeResult, MockPaymentProvider, PaymentProvider
from shop.payments.routes import payments_blueprint

__all__ = [
    "ChargeResult",
    "MockPaymentProvider",
    "Payment",
    "PaymentProvider",
    "PaymentStatus",
    "init_app",
]


def init_app(app: Flask, provider: PaymentProvider) -> None:
    app.extensions[PROVIDER_EXTENSION] = provider
    app.register_blueprint(payments_blueprint)
