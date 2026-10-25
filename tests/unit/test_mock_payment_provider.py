from decimal import Decimal

from shop.integrations.payment_provider import MockPaymentProvider


def charge(card_token):
    return MockPaymentProvider().charge(card_token, Decimal("10.00"), "USD", "key")


def test_mock_provider_charges_regular_card():
    result = charge("tok_visa")

    assert result.succeeded
    assert result.provider_payment_id.startswith("ch_mock_")
    assert result.failure_reason is None


def test_mock_provider_declines_card_with_declined_token():
    result = charge("tok_declined")

    assert not result.succeeded
    assert result.failure_reason == "card_declined"
