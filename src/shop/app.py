import logging

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shop.api import dependencies
from shop.api.errors import register_error_handlers
from shop.api.health import health_blueprint
from shop.api.payments import payments_blueprint
from shop.config import Settings
from shop.integrations.payment_provider import MockPaymentProvider, PaymentProvider

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def create_app(
    settings: Settings | None = None, payment_provider: PaymentProvider | None = None
) -> Flask:
    settings = settings or Settings.from_env()
    logging.basicConfig(level=settings.log_level, format=LOG_FORMAT)

    app = Flask(__name__)
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    dependencies.init_app(
        app,
        db_sessions=sessionmaker(engine, expire_on_commit=False),
        payment_provider=payment_provider or MockPaymentProvider(),
    )

    app.register_blueprint(health_blueprint)
    app.register_blueprint(payments_blueprint)
    register_error_handlers(app)
    return app
