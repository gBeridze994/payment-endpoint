import uuid

from shop.payment_methods.errors import PaymentMethodNotFound
from shop.payment_methods.models import UserPaymentMethod
from shop.payment_methods.repository import PaymentMethodRepository


class PaymentMethodService:
    """Saved payment methods for other parts of the shop. Runs in the caller's transaction."""

    def __init__(self, payment_methods: PaymentMethodRepository) -> None:
        self._payment_methods = payment_methods

    def get_users_payment_method(
        self, user_id: uuid.UUID, payment_method_id: uuid.UUID | None
    ) -> UserPaymentMethod:
        """The user's payment method with this id, or their default one when the id is None."""
        if payment_method_id is None:
            payment_method = self._payment_methods.get_default(user_id)
        else:
            payment_method = self._payment_methods.get(payment_method_id, user_id)
        if payment_method is None:
            raise PaymentMethodNotFound("Payment method not found.")
        return payment_method
