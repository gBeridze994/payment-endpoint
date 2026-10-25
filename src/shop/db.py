"""Database access shared by every part of the shop."""

from flask import Flask, current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

SESSIONS_EXTENSION = "shop.db_sessions"


class Base(DeclarativeBase):
    pass


def init_app(app: Flask, database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    app.extensions[SESSIONS_EXTENSION] = sessionmaker(engine, expire_on_commit=False)


def get_sessions() -> sessionmaker[Session]:
    """The session factory of the current app. Use `with get_sessions().begin() as session:`."""
    sessions: sessionmaker[Session] = current_app.extensions[SESSIONS_EXTENSION]
    return sessions
