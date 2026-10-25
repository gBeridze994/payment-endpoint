import logging

from flask import Flask

from shop import db, payments
from shop.config import Settings
from shop.payments.provider import MockPaymentProvider, PaymentProvider
from shop.web.errors import register_error_handlers
from shop.web.health import health_blueprint

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def create_app(
    settings: Settings | None = None, payment_provider: PaymentProvider | None = None
) -> Flask:
    settings = settings or Settings.from_env()
    logging.basicConfig(level=settings.log_level, format=LOG_FORMAT)

    app = Flask(__name__)
    db.init_app(app, settings.database_url)
    register_error_handlers(app)
    app.register_blueprint(health_blueprint)
    payments.init_app(app, provider=payment_provider or MockPaymentProvider())
    return app
