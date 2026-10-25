from shop import create_app
from shop.config import Settings


def test_health_reports_ok_when_database_is_reachable(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_health_reports_unavailable_when_database_is_unreachable():
    unreachable = Settings(database_url="postgresql+psycopg://nobody@127.0.0.1:1/none")
    client = create_app(unreachable).test_client()

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json == {"status": "unavailable"}


def test_unknown_route_returns_json_error(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"
