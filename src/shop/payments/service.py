import logging
import uuid

import psycopg
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from shop.models import Cart, CartStatus, UserPaymentMethod
from shop.payments.cart_total import calculate_cart_total
from shop.payments.errors import (
    CartNotFound,
    CartNotPayable,
    EmptyCart,
    IdempotencyKeyReused,
    InvalidCartTotal,
    PaymentConflict,
    PaymentError,
    PaymentMethodNotFound,
)
from shop.payments.models import Payment, PaymentStatus
from shop.payments.provider import PaymentProvider

logger = logging.getLogger(__name__)

IDEMPOTENCY_KEY_CONSTRAINT = "uq_payments_user_idempotency_key"


def start_cart_payment(
    sessions: sessionmaker[Session],
    provider: PaymentProvider,
    user_id: uuid.UUID,
    cart_id: uuid.UUID,
    idempotency_key: str,
    payment_method_id: uuid.UUID | None = None,
) -> Payment:
    """Charges the user's card for the cart and returns the payment.

    The pending payment is committed before the provider is called, so a crash
    during the call leaves a record to reconcile instead of a lost charge.
    The provider is called outside any transaction, so no database lock is
    held while waiting for the network.
    """
    try:
        with sessions.begin() as session:
            cart = _lock_users_cart(session, user_id, cart_id)
            payment_method = _find_payment_method(session, user_id, payment_method_id)

            replayed_payment = _find_payment_by_idempotency_key(session, user_id, idempotency_key)
            if replayed_payment is not None:
                _ensure_replay_matches(replayed_payment, cart_id, payment_method.id)
                logger.info("Replaying payment %s for cart %s", replayed_payment.id, cart_id)
                return replayed_payment

            _ensure_cart_is_payable(session, cart)
            total = calculate_cart_total(cart)
            if total.amount <= 0:
                raise InvalidCartTotal(f"Cart total must be greater than 0, got {total.amount}.")
            payment = Payment(
                user_id=user_id,
                cart_id=cart_id,
                payment_method_id=payment_method.id,
                amount=total.amount,
                currency=total.currency,
                idempotency_key=idempotency_key,
            )
            session.add(payment)
    except IntegrityError as error:
        raise _concurrent_request_error(error) from error

    logger.info("Charging payment %s for cart %s", payment.id, cart_id)
    charge = provider.charge(
        card_token=payment_method.provider_token,
        amount=payment.amount,
        currency=payment.currency,
        idempotency_key=str(payment.id),
    )

    with sessions.begin() as session:
        payment = session.get_one(Payment, payment.id)
        payment.provider_payment_id = charge.provider_payment_id
        if charge.succeeded:
            payment.status = PaymentStatus.SUCCEEDED
            session.get_one(Cart, cart_id).status = CartStatus.CHECKED_OUT
        else:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = charge.failure_reason
    logger.info("Payment %s for cart %s %s", payment.id, cart_id, payment.status)
    return payment


def _concurrent_request_error(error: IntegrityError) -> PaymentError:
    """Explains a unique constraint violation caused by a concurrent request."""
    violated = error.orig.diag.constraint_name if isinstance(error.orig, psycopg.Error) else None
    if violated == IDEMPOTENCY_KEY_CONSTRAINT:
        return IdempotencyKeyReused("This idempotency key is used by another request.")
    return PaymentConflict("Another payment request for this cart is in progress.")


def _lock_users_cart(session: Session, user_id: uuid.UUID, cart_id: uuid.UUID) -> Cart:
    """Locks the cart row so concurrent payment requests for it run one at a time."""
    cart = session.scalar(
        select(Cart).where(Cart.id == cart_id, Cart.user_id == user_id).with_for_update()
    )
    if cart is None:
        raise CartNotFound("Cart not found.")
    return cart


def _find_payment_by_idempotency_key(
    session: Session, user_id: uuid.UUID, idempotency_key: str
) -> Payment | None:
    return session.scalar(
        select(Payment).where(
            Payment.user_id == user_id, Payment.idempotency_key == idempotency_key
        )
    )


def _ensure_replay_matches(
    payment: Payment, cart_id: uuid.UUID, payment_method_id: uuid.UUID
) -> None:
    """A reused idempotency key must describe the same payment as the first request."""
    if payment.cart_id != cart_id:
        raise IdempotencyKeyReused("This idempotency key was used for another cart.")
    if payment.payment_method_id != payment_method_id:
        raise IdempotencyKeyReused("This idempotency key was used with another payment method.")


def _ensure_cart_is_payable(session: Session, cart: Cart) -> None:
    if cart.status != CartStatus.ACTIVE:
        raise CartNotPayable(f"Cart is {cart.status} and cannot be paid.")
    if not cart.items:
        raise EmptyCart("Cart is empty.")
    pending_payment_id = session.scalar(
        select(Payment.id).where(
            Payment.cart_id == cart.id, Payment.status == PaymentStatus.PENDING
        )
    )
    if pending_payment_id is not None:
        raise PaymentConflict("A payment for this cart is already in progress.")


def _find_payment_method(
    session: Session, user_id: uuid.UUID, payment_method_id: uuid.UUID | None
) -> UserPaymentMethod:
    query = select(UserPaymentMethod).where(UserPaymentMethod.user_id == user_id)
    if payment_method_id is None:
        query = query.where(UserPaymentMethod.is_default)
    else:
        query = query.where(UserPaymentMethod.id == payment_method_id)

    payment_method = session.scalar(query)
    if payment_method is None:
        raise PaymentMethodNotFound("Payment method not found.")
    return payment_method
