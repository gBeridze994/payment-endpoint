"""Database access shared by every part of the shop."""

from collections.abc import Iterator
from contextlib import ExitStack, contextmanager

from flask import Flask, current_app, g
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

SESSION_FACTORY_EXTENSION = "shop.db_session_factory"


class Base(DeclarativeBase):
    pass


class Repository:
    """Base class for repositories. They read and write rows but never commit:
    transactions belong to the service that uses them."""

    def __init__(self, session: Session) -> None:
        self._session = session


def init_app(app: Flask, database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    # Objects stay usable after commit: the payment flow commits before calling the provider.
    app.extensions[SESSION_FACTORY_EXTENSION] = sessionmaker(engine, expire_on_commit=False)
    # Every request runs inside session_scope(): opened before the view, closed after the
    # response. Flask calls teardown_request functions even when the request failed.
    app.before_request(_open_request_session)
    app.teardown_request(_close_request_session)


@contextmanager
def session_scope() -> Iterator[Session]:
    """A session that is closed when the block ends, also after an error.

    Closing rolls back anything not committed and returns the connection to the pool.
    Usable outside requests too, e.g. in scripts: `with session_scope() as session: ...`.
    """
    session_factory: sessionmaker[Session] = current_app.extensions[SESSION_FACTORY_EXTENSION]
    with session_factory() as session:
        yield session


def get_session() -> Session:
    """Provider of the current request's session."""
    session: Session = g.db_session
    return session


def _open_request_session() -> None:
    g.db_request_scope = ExitStack()
    g.db_session = g.db_request_scope.enter_context(session_scope())


def _close_request_session(_: BaseException | None) -> None:
    g.pop("db_session", None)
    request_scope = g.pop("db_request_scope", None)
    if request_scope is not None:
        request_scope.close()
