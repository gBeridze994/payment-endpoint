"""Every request's database session is closed when the request ends, whatever happened."""

from types import SimpleNamespace

import pytest

from shop.carts import CartStatus
from shop.db import SESSION_FACTORY_EXTENSION


@pytest.fixture
def sessions(client, monkeypatch):
    """Records each session the app opens, and each one it closes.

    It also records how many were closed while the app context was still alive. Without
    that, the test could pass by luck: when the request's objects are garbage-collected,
    Python closes the suspended session_scope() generator, which closes the session too.
    """
    app = client.application
    session_factory = app.extensions[SESSION_FACTORY_EXTENSION]
    opened, closed, closed_before_context_ended = [], [], []
    app.teardown_appcontext(lambda _: closed_before_context_ended.append(len(closed)))

    def tracking_session_factory():
        session = session_factory()
        close = session.close

        def tracked_close():
            closed.append(session)
            close()

        session.close = tracked_close
        opened.append(session)
        return session

    monkeypatch.setitem(app.extensions, SESSION_FACTORY_EXTENSION, tracking_session_factory)
    return SimpleNamespace(
        opened=opened, closed=closed, closed_before_context_ended=closed_before_context_ended
    )


def pay(client, cart, user):
    return client.post(
        f"/carts/{cart.id}/payments",
        headers={"X-User-Id": str(user.id), "Idempotency-Key": "key-1"},
    )


def assert_one_session_opened_and_closed(sessions):
    assert len(sessions.opened) == 1
    assert sessions.closed == sessions.opened
    assert sessions.closed_before_context_ended == [1]


def test_session_is_closed_after_successful_payment(client, sessions, make_user, make_cart):
    user = make_user()

    assert pay(client, make_cart(user), user).status_code == 201
    assert_one_session_opened_and_closed(sessions)


def test_session_is_closed_after_declined_payment(client, sessions, make_user, make_cart):
    user = make_user(card_token="tok_declined")

    assert pay(client, make_cart(user), user).status_code == 402
    assert_one_session_opened_and_closed(sessions)


def test_session_is_closed_after_error_inside_transaction(client, sessions, make_user, make_cart):
    user = make_user()
    cart = make_cart(user, status=CartStatus.CHECKED_OUT)

    assert pay(client, cart, user).status_code == 409
    assert_one_session_opened_and_closed(sessions)


def test_session_is_closed_after_unexpected_error(
    client, provider, sessions, make_user, make_cart, monkeypatch
):
    def provider_unreachable(**_):
        raise ConnectionError("provider timeout")

    monkeypatch.setattr(provider, "charge", provider_unreachable)
    user = make_user()

    assert pay(client, make_cart(user), user).status_code == 500
    assert_one_session_opened_and_closed(sessions)


def test_session_is_closed_after_health_check(client, sessions):
    assert client.get("/health").status_code == 200
    assert_one_session_opened_and_closed(sessions)
