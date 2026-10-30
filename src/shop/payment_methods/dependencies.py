from shop.db import get_session
from shop.payment_methods.repository import PaymentMethodRepository
from shop.payment_methods.service import PaymentMethodService


def get_payment_method_service() -> PaymentMethodService:
    return PaymentMethodService(PaymentMethodRepository(get_session()))
