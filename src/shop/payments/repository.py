import uuid
from decimal import Decimal

from sqlalchemy import exists, select

from shop.db import Repository
from shop.payments.models import Payment, PaymentStatus


class PaymentRepository(Repository):
    def create_pending(
        self,
        *,
        user_id: uuid.UUID,
        cart_id: uuid.UUID,
        payment_method_id: uuid.UUID,
        amount: Decimal,
        currency: str,
        idempotency_key: str,
    ) -> Payment:
        """Inserts a pending payment and returns it with its database-generated id."""
        payment = Payment(
            user_id=user_id,
            cart_id=cart_id,
            payment_method_id=payment_method_id,
            amount=amount,
            currency=currency,
            idempotency_key=idempotency_key,
            status=PaymentStatus.PENDING,
        )
        self._session.add(payment)
        self._session.flush()
        return payment

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
