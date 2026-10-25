import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class ChargeResult:
    succeeded: bool
    provider_payment_id: str
    failure_reason: str | None = None


class PaymentProvider(Protocol):
    def charge(
        self, card_token: str, amount: Decimal, currency: str, idempotency_key: str
    ) -> ChargeResult: ...


class MockPaymentProvider:
    """Fake provider: declines every card whose token contains "declined"."""

    DECLINED_TOKEN_MARKER = "declined"

    def charge(
        self, card_token: str, amount: Decimal, currency: str, idempotency_key: str
    ) -> ChargeResult:
        provider_payment_id = f"ch_mock_{uuid.uuid4().hex}"
        if self.DECLINED_TOKEN_MARKER in card_token:
            return ChargeResult(False, provider_payment_id, failure_reason="card_declined")
        return ChargeResult(True, provider_payment_id)
