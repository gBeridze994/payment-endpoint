"""The payment part of the shop: paying for a cart with a saved card."""

from flask import Flask

from shop.payments.dependencies import PROVIDER_EXTENSION
from shop.payments.provider import PaymentProvider
from shop.payments.routes import payments_blueprint


def init_app(app: Flask, provider: PaymentProvider) -> None:
    app.extensions[PROVIDER_EXTENSION] = provider
    app.register_blueprint(payments_blueprint)
