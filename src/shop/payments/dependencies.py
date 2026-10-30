"""Provider functions: build the payment part's objects for the current request."""

from flask import current_app

from shop.carts import get_cart_service
from shop.db import get_session
from shop.payment_methods import get_payment_method_service
from shop.payments.cart_total import CartTotalService, StubCartTotalService
from shop.payments.provider import PaymentProvider
from shop.payments.repository import PaymentRepository
from shop.payments.service import PaymentService

PROVIDER_EXTENSION = "shop.payment_provider"


def get_payment_provider() -> PaymentProvider:
    """The provider chosen in create_app(): the mock by default, a fake in tests."""
    provider: PaymentProvider = current_app.extensions[PROVIDER_EXTENSION]
    return provider


def get_cart_total_service() -> CartTotalService:
    return StubCartTotalService()


def get_payment_service() -> PaymentService:
    session = get_session()
    return PaymentService(
        session=session,
        payments=PaymentRepository(session),
        carts=get_cart_service(),
        payment_methods=get_payment_method_service(),
        cart_total=get_cart_total_service(),
        provider=get_payment_provider(),
    )
