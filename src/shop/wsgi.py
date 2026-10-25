"""Entry point for WSGI servers, e.g. `gunicorn shop.wsgi:app`."""

from shop.app import create_app

app = create_app()
