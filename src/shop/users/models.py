import uuid

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from shop.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    email: Mapped[str]
    name: Mapped[str]
