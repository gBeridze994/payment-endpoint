import logging

from flask import Blueprint, Response, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from shop.api.dependencies import get_db_sessions

logger = logging.getLogger(__name__)

health_blueprint = Blueprint("health", __name__)


@health_blueprint.get("/health")
def health() -> tuple[Response, int]:
    """Reports whether the service can reach its database."""
    try:
        with get_db_sessions()() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Health check failed: database unreachable")
        return jsonify({"status": "unavailable"}), 503
    return jsonify({"status": "ok"}), 200
