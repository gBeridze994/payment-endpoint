import uuid

from shop.carts.errors import CartNotFound
from shop.carts.models import Cart
from shop.carts.repository import CartRepository


class CartService:
    """Cart operations for other parts of the shop. Runs in the caller's transaction."""

    def __init__(self, carts: CartRepository) -> None:
        self._carts = carts

    def lock_users_cart(self, cart_id: uuid.UUID, user_id: uuid.UUID) -> Cart:
        """The user's cart, locked so concurrent changes to it run one at a time."""
        cart = self._carts.get_for_update(cart_id, user_id)
        if cart is None:
            raise CartNotFound("Cart not found.")
        return cart

    def check_out(self, cart: Cart) -> None:
        self._carts.mark_checked_out(cart)
