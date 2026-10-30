import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from shop.carts import Cart, CartItem, CartStatus
from shop.payment_methods import UserPaymentMethod
from shop.payments import Payment, PaymentStatus
from shop.products import Product


def pay(client, cart_id, user_id, idempotency_key=None, json=None):
    headers = {
        "X-User-Id": str(user_id),
        "Idempotency-Key": idempotency_key or str(uuid.uuid4()),
    }
    return client.post(f"/carts/{cart_id}/payments", headers=headers, json=json)


def test_successful_payment_charges_cart_total_and_checks_out_cart(
    client, provider, session, make_user, make_cart
):
    user = make_user(card_token="tok_visa")
    cart = make_cart(user)

    response = pay(client, cart.id, user.id)

    assert response.status_code == 201
    assert response.json["status"] == "succeeded"
    assert response.json["amount"] == "70.00"
    assert response.json["currency"] == "USD"
    assert provider.charges == [
        {"card_token": "tok_visa", "amount": Decimal("70.00"), "currency": "USD"}
    ]
    payment = session.get_one(Payment, uuid.UUID(response.json["id"]), populate_existing=True)
    assert payment.status == PaymentStatus.SUCCEEDED
    assert payment.provider_payment_id.startswith("ch_mock_")
    assert session.get_one(Cart, cart.id, populate_existing=True).status == CartStatus.CHECKED_OUT


def test_declined_card_fails_payment_and_keeps_cart_active(client, session, make_user, make_cart):
    user = make_user(card_token="tok_declined")
    cart = make_cart(user)

    response = pay(client, cart.id, user.id)

    assert response.status_code == 402
    assert response.json["status"] == "failed"
    assert response.json["failure_reason"] == "card_declined"
    assert session.get_one(Cart, cart.id, populate_existing=True).status == CartStatus.ACTIVE


def test_cart_can_be_paid_with_another_card_after_decline(client, session, make_user, make_cart):
    user = make_user(card_token="tok_declined")
    cart = make_cart(user)
    pay(client, cart.id, user.id)
    working_card = UserPaymentMethod(user_id=user.id, provider_token="tok_visa")
    session.add(working_card)
    session.commit()

    response = pay(client, cart.id, user.id, json={"payment_method_id": str(working_card.id)})

    assert response.status_code == 201
    assert response.json["payment_method_id"] == str(working_card.id)


def test_retry_with_same_idempotency_key_returns_same_payment_without_charging_again(
    client, provider, make_user, make_cart
):
    user = make_user()
    cart = make_cart(user)

    first = pay(client, cart.id, user.id, idempotency_key="key-1")
    retry = pay(client, cart.id, user.id, idempotency_key="key-1")

    assert retry.status_code == 201
    assert retry.json == first.json
    assert len(provider.charges) == 1


def test_idempotency_key_cannot_be_reused_with_another_card(
    client, provider, session, make_user, make_cart
):
    user = make_user(card_token="tok_visa")
    cart = make_cart(user)
    other_card = UserPaymentMethod(user_id=user.id, provider_token="tok_amex")
    session.add(other_card)
    session.commit()

    first = pay(client, cart.id, user.id, idempotency_key="key-1")
    retry = pay(
        client,
        cart.id,
        user.id,
        idempotency_key="key-1",
        json={"payment_method_id": str(other_card.id)},
    )

    assert first.status_code == 201
    assert retry.status_code == 422
    assert retry.json["error"]["code"] == "idempotency_key_reused"
    assert [charge["card_token"] for charge in provider.charges] == ["tok_visa"]


def test_idempotency_key_cannot_be_reused_for_another_cart(client, make_user, make_cart):
    user = make_user()
    pay(client, make_cart(user).id, user.id, idempotency_key="key-1")

    response = pay(client, make_cart(user).id, user.id, idempotency_key="key-1")

    assert response.status_code == 422
    assert response.json["error"]["code"] == "idempotency_key_reused"


def test_checked_out_cart_cannot_be_paid_again(client, provider, make_user, make_cart):
    user = make_user()
    cart = make_cart(user)
    pay(client, cart.id, user.id)

    response = pay(client, cart.id, user.id)

    assert response.status_code == 409
    assert response.json["error"]["code"] == "cart_not_payable"
    assert len(provider.charges) == 1


def test_cart_with_payment_in_progress_cannot_be_paid(
    client, provider, session, make_user, make_cart
):
    user = make_user()
    cart = make_cart(user)
    payment_method = session.query(UserPaymentMethod).filter_by(user_id=user.id).one()
    session.add(
        Payment(
            user_id=user.id,
            cart_id=cart.id,
            payment_method_id=payment_method.id,
            amount=Decimal("70.00"),
            currency="USD",
            idempotency_key="in-flight",
        )
    )
    session.commit()

    response = pay(client, cart.id, user.id)

    assert response.status_code == 409
    assert response.json["error"]["code"] == "payment_conflict"
    assert provider.charges == []


def test_provider_error_leaves_payment_pending_for_reconciliation(
    client, provider, session, make_user, make_cart, monkeypatch
):
    user = make_user()
    cart = make_cart(user)

    def provider_unreachable(**_):
        raise ConnectionError("provider timeout")

    monkeypatch.setattr(provider, "charge", provider_unreachable)

    response = pay(client, cart.id, user.id)

    assert response.status_code == 500
    assert response.json["error"]["code"] == "internal_error"
    payment = session.query(Payment).filter_by(cart_id=cart.id).one()
    assert payment.status == PaymentStatus.PENDING
    assert session.get_one(Cart, cart.id, populate_existing=True).status == CartStatus.ACTIVE


@pytest.mark.parametrize("status", [CartStatus.CHECKED_OUT, CartStatus.ABANDONED])
def test_inactive_cart_cannot_be_paid(client, make_user, make_cart, status):
    user = make_user()
    cart = make_cart(user, status=status)

    response = pay(client, cart.id, user.id)

    assert response.status_code == 409
    assert response.json["error"]["code"] == "cart_not_payable"


@pytest.mark.parametrize("unit_price", ["0.00", "-5.00"])
def test_cart_with_total_not_above_zero_cannot_be_paid(
    client, provider, session, make_user, unit_price
):
    user = make_user()
    product = Product(name="Sticker", price=Decimal("0.00"), currency="USD", stock_quantity=1)
    cart = Cart(
        user_id=user.id,
        items=[CartItem(product=product, quantity=1, unit_price=Decimal(unit_price))],
    )
    session.add(cart)
    session.commit()

    response = pay(client, cart.id, user.id)

    assert response.status_code == 422
    assert response.json["error"]["code"] == "invalid_cart_total"
    assert provider.charges == []


def test_empty_cart_cannot_be_paid(client, make_user, make_cart):
    user = make_user()
    cart = make_cart(user, with_items=False)

    response = pay(client, cart.id, user.id)

    assert response.status_code == 422
    assert response.json["error"]["code"] == "empty_cart"


def test_user_cannot_pay_for_another_users_cart(client, provider, make_user, make_cart):
    owner = make_user()
    other_user = make_user()
    cart = make_cart(owner)

    response = pay(client, cart.id, other_user.id)

    assert response.status_code == 404
    assert response.json["error"]["code"] == "cart_not_found"
    assert provider.charges == []


def test_unknown_cart_returns_not_found(client, make_user):
    user = make_user()

    response = pay(client, uuid.uuid4(), user.id)

    assert response.status_code == 404


def test_user_without_default_payment_method_cannot_pay(client, make_user, make_cart):
    user = make_user(card_token=None)
    cart = make_cart(user)

    response = pay(client, cart.id, user.id)

    assert response.status_code == 422
    assert response.json["error"]["code"] == "payment_method_not_found"


def test_user_cannot_have_two_default_payment_methods(session, make_user):
    user = make_user(card_token="tok_visa")
    session.add(UserPaymentMethod(user_id=user.id, provider_token="tok_amex", is_default=True))

    with pytest.raises(IntegrityError):
        session.commit()


def test_user_cannot_pay_with_another_users_card(client, session, make_user, make_cart):
    user = make_user()
    other_user = make_user()
    other_users_card = session.query(UserPaymentMethod).filter_by(user_id=other_user.id).one()
    cart = make_cart(user)

    response = pay(client, cart.id, user.id, json={"payment_method_id": str(other_users_card.id)})

    assert response.status_code == 422
    assert response.json["error"]["code"] == "payment_method_not_found"


@pytest.mark.parametrize("user_id_header", [None, "not-a-uuid"])
def test_request_without_valid_user_is_unauthorized(client, make_user, make_cart, user_id_header):
    cart = make_cart(make_user())
    headers = {"Idempotency-Key": "key-1"}
    if user_id_header is not None:
        headers["X-User-Id"] = user_id_header

    response = client.post(f"/carts/{cart.id}/payments", headers=headers)

    assert response.status_code == 401


@pytest.mark.parametrize("idempotency_key", [None, "", "x" * 256])
def test_request_without_valid_idempotency_key_is_rejected(
    client, make_user, make_cart, idempotency_key
):
    user = make_user()
    cart = make_cart(user)
    headers = {"X-User-Id": str(user.id)}
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key

    response = client.post(f"/carts/{cart.id}/payments", headers=headers)

    assert response.status_code == 400


@pytest.mark.parametrize(
    "body",
    [
        {"payment_method_id": "not-a-uuid"},
        ["not", "an", "object"],
        {"payment_methd_id": "11111111-2222-3333-4444-555555555555"},
    ],
)
def test_invalid_request_body_is_rejected(client, make_user, make_cart, body):
    user = make_user()
    cart = make_cart(user)

    response = pay(client, cart.id, user.id, json=body)

    assert response.status_code == 400


def test_concurrent_requests_for_same_cart_charge_card_once(client, provider, make_user, make_cart):
    user = make_user()
    cart = make_cart(user)
    start_together = threading.Barrier(2)

    def pay_concurrently(_):
        start_together.wait()
        return pay(client.application.test_client(), cart.id, user.id).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        status_codes = sorted(executor.map(pay_concurrently, range(2)))

    assert status_codes == [201, 409]
    assert len(provider.charges) == 1


def test_concurrent_requests_with_same_key_for_different_carts_charge_once(
    client, provider, make_user, make_cart
):
    user = make_user()
    carts = [make_cart(user), make_cart(user)]
    start_together = threading.Barrier(2)

    def pay_concurrently(cart):
        start_together.wait()
        response = pay(client.application.test_client(), cart.id, user.id, idempotency_key="k")
        return response.status_code, response.json.get("error", {}).get("code")

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = sorted(executor.map(pay_concurrently, carts))

    assert results == [(201, None), (422, "idempotency_key_reused")]
    assert len(provider.charges) == 1
