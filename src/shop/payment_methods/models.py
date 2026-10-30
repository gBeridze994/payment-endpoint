import uuid

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from shop.db import Base


class UserPaymentMethod(Base):
    __tablename__ = "user_payment_methods"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    # Token from the payment provider; the card number is never stored.
    provider_token: Mapped[str]
    last_four: Mapped[str | None]
    is_default: Mapped[bool] = mapped_column(default=False)
