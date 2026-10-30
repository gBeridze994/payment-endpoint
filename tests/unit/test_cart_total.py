from decimal import Decimal

from shop.models import Cart, CartItem, Product
from shop.payments.cart_total import Money, StubCartTotalService


def test_cart_total_sums_unit_price_times_quantity():
    product = Product(name="Mug", price=Decimal("99.00"), currency="EUR", stock_quantity=1)
    cart = Cart(
        items=[
            CartItem(product=product, quantity=3, unit_price=Decimal("12.50")),
            CartItem(product=product, quantity=1, unit_price=Decimal("0.99")),
        ]
    )

    assert StubCartTotalService().calculate(cart) == Money(amount=Decimal("38.49"), currency="EUR")
