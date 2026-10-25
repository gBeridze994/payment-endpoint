"""Shared objects that the app factory creates and the request handlers use."""

from flask import Flask, current_app
from sqlalchemy.orm import Session, sessionmaker

from shop.integrations.payment_provider import PaymentProvider

DB_SESSIONS = "shop.db_sessions"
PAYMENT_PROVIDER = "shop.payment_provider"


def init_app(
    app: Flask, db_sessions: sessionmaker[Session], payment_provider: PaymentProvider
) -> None:
    app.extensions[DB_SESSIONS] = db_sessions
    app.extensions[PAYMENT_PROVIDER] = payment_provider


def get_db_sessions() -> sessionmaker[Session]:
    sessions: sessionmaker[Session] = current_app.extensions[DB_SESSIONS]
    return sessions


def get_payment_provider() -> PaymentProvider:
    provider: PaymentProvider = current_app.extensions[PAYMENT_PROVIDER]
    return provider
