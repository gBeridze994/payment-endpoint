import uuid

from sqlalchemy import text

from shop.payments.models import Payment


def updated_at(engine, user_id):
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT updated_at FROM users WHERE id = :id"), {"id": user_id}
        ).scalar_one()


def update_user_name(engine, user_id, name_sql):
    with engine.begin() as connection:
        connection.execute(
            text(f"UPDATE users SET name = {name_sql} WHERE id = :id"), {"id": user_id}
        )


def test_update_sets_updated_at(engine, make_user):
    user = make_user()
    before = updated_at(engine, user.id)

    update_user_name(engine, user.id, "'Renamed'")

    assert updated_at(engine, user.id) > before


def test_update_that_changes_nothing_keeps_updated_at(engine, make_user):
    user = make_user()
    before = updated_at(engine, user.id)

    update_user_name(engine, user.id, "name")

    assert updated_at(engine, user.id) == before


def test_payment_outcome_sets_payment_updated_at(client, session, make_user, make_cart):
    user = make_user()
    cart = make_cart(user)

    response = client.post(
        f"/carts/{cart.id}/payments",
        headers={"X-User-Id": str(user.id), "Idempotency-Key": "key-1"},
    )

    payment = session.get_one(Payment, uuid.UUID(response.json["id"]))
    assert payment.updated_at > payment.created_at
