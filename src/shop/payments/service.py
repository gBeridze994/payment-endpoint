import logging

import psycopg
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shop.models import Cart, CartStatus, UserPaymentMethod
from shop.payments.cart_total import CartTotalService
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
from shop.payments.repository import PaymentRepository
from shop.payments.schemas import StartCartPayment
from shop.repositories import CartRepository, PaymentMethodRepository

logger = logging.getLogger(__name__)

IDEMPOTENCY_KEY_CONSTRAINT = "uq_payments_user_idempotency_key"


class PaymentService:
    """Charges a user's card for a cart.

    The service owns the transactions; repositories only read and write rows.
    The pending payment is committed before the provider is called, so a crash
    during the call leaves a record to reconcile instead of a lost charge. The
    provider is called outside any transaction, so no database lock is held
    while waiting for the network.
    """

    def __init__(
        self,
        session: Session,
        payments: PaymentRepository,
        carts: CartRepository,
        payment_methods: PaymentMethodRepository,
        cart_total: CartTotalService,
        provider: PaymentProvider,
    ) -> None:
        self._session = session
        self._payments = payments
        self._carts = carts
        self._payment_methods = payment_methods
        self._cart_total = cart_total
        self._provider = provider

    def start_cart_payment(self, command: StartCartPayment) -> Payment:
        """Returns the payment: new, or the earlier one if the idempotency key was seen before."""
        try:
            with self._session.begin():
                cart = self._lock_users_cart(command)
                payment_method = self._find_payment_method(command)

                replayed_payment = self._payments.get_by_idempotency_key(
                    command.user_id, command.idempotency_key
                )
                if replayed_payment is not None:
                    _ensure_replay_matches(replayed_payment, cart, payment_method)
                    logger.info("Replaying payment %s for cart %s", replayed_payment.id, cart.id)
                    return replayed_payment

                payment = self._create_pending_payment(cart, payment_method, command)
        except IntegrityError as error:
            raise _concurrent_request_error(error) from error

        self._charge(payment, payment_method, cart)
        return payment

    def _lock_users_cart(self, command: StartCartPayment) -> Cart:
        """Locks the cart so concurrent payment requests for it run one at a time."""
        cart = self._carts.get_for_update(command.cart_id, command.user_id)
        if cart is None:
            raise CartNotFound("Cart not found.")
        return cart

    def _find_payment_method(self, command: StartCartPayment) -> UserPaymentMethod:
        if command.payment_method_id is None:
            payment_method = self._payment_methods.get_default(command.user_id)
        else:
            payment_method = self._payment_methods.get(command.payment_method_id, command.user_id)
        if payment_method is None:
            raise PaymentMethodNotFound("Payment method not found.")
        return payment_method

    def _create_pending_payment(
        self, cart: Cart, payment_method: UserPaymentMethod, command: StartCartPayment
    ) -> Payment:
        self._ensure_cart_is_payable(cart)
        total = self._cart_total.calculate(cart)
        if total.amount <= 0:
            raise InvalidCartTotal(f"Cart total must be greater than 0, got {total.amount}.")
        payment = Payment(
            user_id=command.user_id,
            cart_id=cart.id,
            payment_method_id=payment_method.id,
            amount=total.amount,
            currency=total.currency,
            idempotency_key=command.idempotency_key,
        )
        self._payments.add(payment)
        return payment

    def _ensure_cart_is_payable(self, cart: Cart) -> None:
        if cart.status != CartStatus.ACTIVE:
            raise CartNotPayable(f"Cart is {cart.status} and cannot be paid.")
        if not cart.items:
            raise EmptyCart("Cart is empty.")
        if self._payments.has_pending_for_cart(cart.id):
            raise PaymentConflict("A payment for this cart is already in progress.")

    def _charge(self, payment: Payment, payment_method: UserPaymentMethod, cart: Cart) -> None:
        logger.info("Charging payment %s for cart %s", payment.id, cart.id)
        charge = self._provider.charge(
            card_token=payment_method.provider_token,
            amount=payment.amount,
            currency=payment.currency,
            idempotency_key=str(payment.id),
        )
        with self._session.begin():
            payment.provider_payment_id = charge.provider_payment_id
            if charge.succeeded:
                payment.status = PaymentStatus.SUCCEEDED
                cart.status = CartStatus.CHECKED_OUT
            else:
                payment.status = PaymentStatus.FAILED
                payment.failure_reason = charge.failure_reason
        logger.info("Payment %s for cart %s %s", payment.id, cart.id, payment.status)


def _ensure_replay_matches(payment: Payment, cart: Cart, payment_method: UserPaymentMethod) -> None:
    """A reused idempotency key must describe the same payment as the first request."""
    if payment.cart_id != cart.id:
        raise IdempotencyKeyReused("This idempotency key was used for another cart.")
    if payment.payment_method_id != payment_method.id:
        raise IdempotencyKeyReused("This idempotency key was used with another payment method.")


def _concurrent_request_error(error: IntegrityError) -> PaymentError:
    """Explains a unique constraint violation caused by a concurrent request."""
    violated = error.orig.diag.constraint_name if isinstance(error.orig, psycopg.Error) else None
    if violated == IDEMPOTENCY_KEY_CONSTRAINT:
        return IdempotencyKeyReused("This idempotency key is used by another request.")
    return PaymentConflict("Another payment request for this cart is in progress.")
