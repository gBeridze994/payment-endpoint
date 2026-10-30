"""Database access shared by every part of the shop."""

from flask import Flask, current_app, g
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

SESSION_FACTORY_EXTENSION = "shop.db_session_factory"


class Base(DeclarativeBase):
    pass


def init_app(app: Flask, database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    # Objects stay usable after commit: the payment flow commits before calling the provider.
    app.extensions[SESSION_FACTORY_EXTENSION] = sessionmaker(engine, expire_on_commit=False)
    app.teardown_appcontext(_close_session)


def get_session() -> Session:
    """Provider of the request's session: created on first use, closed when the request ends."""
    if "db_session" not in g:
        session_factory: sessionmaker[Session] = current_app.extensions[SESSION_FACTORY_EXTENSION]
        g.db_session = session_factory()
    session: Session = g.db_session
    return session


def _close_session(_: BaseException | None) -> None:
    session = g.pop("db_session", None)
    if session is not None:
        session.close()
