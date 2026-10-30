"""PaymentService with in-memory fakes injected in place of the database and the provider."""

import contextlib
import uuid
from decimal import Decimal

import pytest

from shop.models import Cart, CartItem, CartStatus, Product, UserPaymentMethod
from shop.payments.cart_total import StubCartTotalService
from shop.payments.errors import IdempotencyKeyReused, InvalidCartTotal
from shop.payments.models import PaymentStatus
from shop.payments.provider import MockPaymentProvider
from shop.payments.schemas import StartCartPayment
from shop.payments.service import PaymentService


class FakeSession:
    def begin(self):
        return contextlib.nullcontext()


class FakeCarts:
    def __init__(self, cart):
        self.cart = cart

    def get_for_update(self, cart_id, user_id):
        return self.cart if (self.cart.id, self.cart.user_id) == (cart_id, user_id) else None


class FakePaymentMethods:
    def __init__(self, *payment_methods):
        self.payment_methods = payment_methods

    def get(self, payment_method_id, user_id):
        return next((m for m in self.payment_methods if m.id == payment_method_id), None)

    def get_default(self, user_id):
        return next((m for m in self.payment_methods if m.is_default), None)


class FakePayments:
    def __init__(self):
        self.payments = []

    def add(self, payment):
        payment.id = uuid.uuid4()
        self.payments.append(payment)

    def get_by_idempotency_key(self, user_id, idempotency_key):
        return next((p for p in self.payments if p.idempotency_key == idempotency_key), None)

    def has_pending_for_cart(self, cart_id):
        return any(p.status == PaymentStatus.PENDING for p in self.payments)


class SpyProvider(MockPaymentProvider):
    def __init__(self):
        self.charged_tokens = []

    def charge(self, card_token, amount, currency, idempotency_key):
        self.charged_tokens.append(card_token)
        return super().charge(card_token, amount, currency, idempotency_key)


USER_ID = uuid.uuid4()


def make_cart(unit_price="10.00"):
    product = Product(name="Mug", price=Decimal("10.00"), currency="USD", stock_quantity=1)
    return Cart(
        id=uuid.uuid4(),
        user_id=USER_ID,
        status=CartStatus.ACTIVE,
        items=[CartItem(product=product, quantity=2, unit_price=Decimal(unit_price))],
    )


def make_card(token, is_default=False):
    return UserPaymentMethod(
        id=uuid.uuid4(), user_id=USER_ID, provider_token=token, is_default=is_default
    )


def make_service(cart, *cards):
    provider = SpyProvider()
    service = PaymentService(
        session=FakeSession(),
        payments=FakePayments(),
        carts=FakeCarts(cart),
        payment_methods=FakePaymentMethods(*cards),
        cart_total=StubCartTotalService(),
        provider=provider,
    )
    return service, provider


def command(cart, idempotency_key="key-1", payment_method_id=None):
    return StartCartPayment(
        user_id=USER_ID,
        cart_id=cart.id,
        idempotency_key=idempotency_key,
        payment_method_id=payment_method_id,
    )


def test_successful_charge_checks_out_cart():
    cart = make_cart()
    service, provider = make_service(cart, make_card("tok_visa", is_default=True))

    payment = service.start_cart_payment(command(cart))

    assert payment.status == PaymentStatus.SUCCEEDED
    assert payment.amount == Decimal("20.00")
    assert cart.status == CartStatus.CHECKED_OUT
    assert provider.charged_tokens == ["tok_visa"]


def test_declined_charge_fails_payment_and_keeps_cart_active():
    cart = make_cart()
    service, _ = make_service(cart, make_card("tok_declined", is_default=True))

    payment = service.start_cart_payment(command(cart))

    assert payment.status == PaymentStatus.FAILED
    assert payment.failure_reason == "card_declined"
    assert cart.status == CartStatus.ACTIVE


def test_cart_total_of_zero_is_rejected_before_charging():
    cart = make_cart(unit_price="0.00")
    service, provider = make_service(cart, make_card("tok_visa", is_default=True))

    with pytest.raises(InvalidCartTotal):
        service.start_cart_payment(command(cart))
    assert provider.charged_tokens == []


def test_reused_idempotency_key_with_another_card_is_rejected():
    cart = make_cart()
    default_card, other_card = make_card("tok_declined", is_default=True), make_card("tok_visa")
    service, provider = make_service(cart, default_card, other_card)
    service.start_cart_payment(command(cart))

    with pytest.raises(IdempotencyKeyReused):
        service.start_cart_payment(command(cart, payment_method_id=other_card.id))
    assert provider.charged_tokens == ["tok_declined"]
