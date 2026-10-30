from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from shop.models import Cart


class Money(BaseModel):
    model_config = ConfigDict(frozen=True)

    amount: Decimal
    currency: str


class CartTotalService(Protocol):
    """The existing payment total calculation service. It owns taxes, shipping and discounts."""

    def calculate(self, cart: Cart) -> Money: ...


class StubCartTotalService:
    """Stand-in for the real service: sums the cart items, assumes one currency per cart."""

    def calculate(self, cart: Cart) -> Money:
        amount = sum((item.unit_price * item.quantity for item in cart.items), Decimal("0"))
        return Money(amount=amount, currency=cart.items[0].product.currency)
