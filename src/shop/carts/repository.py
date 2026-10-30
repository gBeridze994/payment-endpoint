import uuid

from sqlalchemy import select

from shop.carts.models import Cart, CartStatus
from shop.db import Repository


class CartRepository(Repository):
    def get_for_update(self, cart_id: uuid.UUID, user_id: uuid.UUID) -> Cart | None:
        """The user's cart, locked until the current transaction ends."""
        return self._session.scalar(
            select(Cart).where(Cart.id == cart_id, Cart.user_id == user_id).with_for_update()
        )

    def mark_checked_out(self, cart: Cart) -> None:
        cart.status = CartStatus.CHECKED_OUT
