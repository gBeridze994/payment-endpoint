import os
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from shop import create_app
from shop.carts import Cart, CartItem, CartStatus
from shop.config import Settings
from shop.payment_methods import UserPaymentMethod
from shop.payments import MockPaymentProvider
from shop.products import Product
from shop.users import User

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/shop_test"
)
PROJECT_ROOT = Path(__file__).parents[2]
TABLES = ["payments", "cart_items", "carts", "user_payment_methods", "products", "users"]


class RecordingPaymentProvider(MockPaymentProvider):
    """Mock provider that remembers every charge, so tests can count them."""

    def __init__(self):
        self.charges = []

    def charge(self, card_token, amount, currency, idempotency_key):
        self.charges.append({"card_token": card_token, "amount": amount, "currency": currency})
        return super().charge(card_token, amount, currency, idempotency_key)


@pytest.fixture(scope="session")
def alembic_config():
    config = Config(toml_file=PROJECT_ROOT / "pyproject.toml")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return config


@pytest.fixture(scope="session")
def engine(alembic_config):
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    command.upgrade(alembic_config, "head")
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables(engine):
    yield
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {', '.join(TABLES)} CASCADE"))


@pytest.fixture
def session(engine):
    with Session(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def provider():
    return RecordingPaymentProvider()


@pytest.fixture
def client(provider):
    app = create_app(Settings(database_url=TEST_DATABASE_URL), payment_provider=provider)
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def make_user(session):
    def make(card_token: str | None = "tok_visa") -> User:
        user = User(email=f"{uuid.uuid4()}@example.com", name="Test User")
        session.add(user)
        session.flush()
        if card_token is not None:
            session.add(
                UserPaymentMethod(user_id=user.id, provider_token=card_token, is_default=True)
            )
        session.commit()
        return user

    return make


@pytest.fixture
def make_cart(session):
    def make(user: User, status: CartStatus = CartStatus.ACTIVE, with_items: bool = True) -> Cart:
        cart = Cart(user_id=user.id, status=status)
        if with_items:
            kettle = Product(
                name="Kettle", price=Decimal("45.00"), currency="USD", stock_quantity=10
            )
            mug = Product(name="Mug", price=Decimal("12.50"), currency="USD", stock_quantity=100)
            cart.items = [
                CartItem(product=kettle, quantity=1, unit_price=kettle.price),
                CartItem(product=mug, quantity=2, unit_price=mug.price),
            ]
        session.add(cart)
        session.commit()
        return cart

    return make
