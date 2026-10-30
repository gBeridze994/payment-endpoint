import logging

from flask import Blueprint, Response, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from shop.db import get_session
from shop.web.injection import inject

logger = logging.getLogger(__name__)

health_blueprint = Blueprint("health", __name__)


@health_blueprint.get("/health")
@inject(session=get_session)
def health(session: Session) -> tuple[Response, int]:
    """Reports whether the service can reach its database."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Health check failed: database unreachable")
        return jsonify({"status": "unavailable"}), 503
    return jsonify({"status": "ok"}), 200
