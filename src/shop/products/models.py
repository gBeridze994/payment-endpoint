import uuid
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from shop.db import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str]
    price: Mapped[Decimal]
    currency: Mapped[str]
    stock_quantity: Mapped[int]
