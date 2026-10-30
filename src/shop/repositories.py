"""Data access for the base-schema tables.

Repositories only read and write rows. They never commit: transactions belong
to the service that uses them.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from shop.models import Cart, UserPaymentMethod


class Repository:
    def __init__(self, session: Session) -> None:
        self._session = session


class CartRepository(Repository):
    def get_for_update(self, cart_id: uuid.UUID, user_id: uuid.UUID) -> Cart | None:
        """The user's cart, locked until the current transaction ends."""
        return self._session.scalar(
            select(Cart).where(Cart.id == cart_id, Cart.user_id == user_id).with_for_update()
        )


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
