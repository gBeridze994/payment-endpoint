"""Tables of the base schema, owned by the existing parts of the shop.

Only the columns the payment part needs are mapped.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shop.db import Base


class CartStatus(StrEnum):
    ACTIVE = "active"
    CHECKED_OUT = "checked_out"
    ABANDONED = "abandoned"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    email: Mapped[str]
    name: Mapped[str]


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str]
    price: Mapped[Decimal]
    currency: Mapped[str]
    stock_quantity: Mapped[int]


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(default=CartStatus.ACTIVE)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    items: Mapped[list[CartItem]] = relationship()


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    cart_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("carts.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int]
    unit_price: Mapped[Decimal]

    product: Mapped[Product] = relationship()


class UserPaymentMethod(Base):
    __tablename__ = "user_payment_methods"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    provider_token: Mapped[str]
    last_four: Mapped[str | None]
    is_default: Mapped[bool] = mapped_column(default=False)
