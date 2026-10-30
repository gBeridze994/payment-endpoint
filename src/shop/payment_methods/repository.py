import uuid

from sqlalchemy import select

from shop.db import Repository
from shop.payment_methods.models import UserPaymentMethod


class PaymentMethodRepository(Repository):
    def get(self, payment_method_id: uuid.UUID, user_id: uuid.UUID) -> UserPaymentMethod | None:
        return self._session.scalar(
            select(UserPaymentMethod).where(
                UserPaymentMethod.id == payment_method_id, UserPaymentMethod.user_id == user_id
            )
        )

    def get_default(self, user_id: uuid.UUID) -> UserPaymentMethod | None:
        return self._session.scalar(
            select(UserPaymentMethod).where(
                UserPaymentMethod.user_id == user_id, UserPaymentMethod.is_default
            )
        )
