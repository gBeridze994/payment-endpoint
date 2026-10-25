import uuid

from flask import request

from shop.web.errors import Unauthorized


def current_user_id() -> uuid.UUID:
    """The id of the user making the request.

    Authentication is out of scope: an upstream auth layer is assumed to verify
    the user and pass their id in the X-User-Id header (see README).
    """
    try:
        return uuid.UUID(request.headers["X-User-Id"])
    except KeyError, ValueError:
        raise Unauthorized("A valid X-User-Id header is required.") from None
