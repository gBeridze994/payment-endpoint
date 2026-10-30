from shop.carts.repository import CartRepository
from shop.carts.service import CartService
from shop.db import get_session


def get_cart_service() -> CartService:
    return CartService(CartRepository(get_session()))
