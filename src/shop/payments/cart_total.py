from dataclasses import dataclass
from decimal import Decimal

from shop.models import Cart


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str


def calculate_cart_total(cart: Cart) -> Money:
    """Stand-in for the existing payment total calculation service.

    The real service owns taxes, shipping and discounts. This stub only sums
    the cart items and assumes all products in a cart share one currency.
    """
    amount = sum((item.unit_price * item.quantity for item in cart.items), Decimal("0"))
    return Money(amount=amount, currency=cart.items[0].product.currency)
