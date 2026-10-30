import uuid

from sqlalchemy import exists, select

from shop.db import Repository
from shop.payments.models import Payment, PaymentStatus


class PaymentRepository(Repository):
    def add(self, payment: Payment) -> None:
        self._session.add(payment)

    def get_by_idempotency_key(self, user_id: uuid.UUID, idempotency_key: str) -> Payment | None:
        return self._session.scalar(
            select(Payment).where(
                Payment.user_id == user_id, Payment.idempotency_key == idempotency_key
            )
        )

    def has_pending_for_cart(self, cart_id: uuid.UUID) -> bool:
        pending = exists().where(
            Payment.cart_id == cart_id, Payment.status == PaymentStatus.PENDING
        )
        return bool(self._session.scalar(select(pending)))
