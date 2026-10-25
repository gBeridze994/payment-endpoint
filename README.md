# Payment Endpoint

The payment part of an online shop: a SQL schema for payments and an HTTP endpoint
that starts the payment for a cart.

Built with Python 3.14, Flask, SQLAlchemy 2, Alembic and PostgreSQL. Dependencies are managed with
[uv](https://docs.astral.sh/uv/).

## Quick start (Docker)

```bash
docker compose up -d --build   # PostgreSQL, migrations, API on http://localhost:8000
curl http://localhost:8000/health
```

The base schema has sample data: Alice has an active cart and a default card.

```bash
curl -i -X POST http://localhost:8000/carts/c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1/payments \
  -H "X-User-Id: 11111111-1111-1111-1111-111111111111" \
  -H "Idempotency-Key: $(uuidgen)"
```

`docker compose down -v` stops everything and deletes the database.

## Local development

Requirements: [uv](https://docs.astral.sh/uv/getting-started/installation/) and Docker
(or a local PostgreSQL 13+ with the databases `shop` and `shop_test`).

```bash
make install   # uv sync: install dependencies into .venv
make db        # start only PostgreSQL (creates "shop" and "shop_test")
make migrate   # alembic upgrade head
make run       # Flask dev server on http://localhost:5000
```

`make help` lists all commands. The main ones:

| Command          | What it does                                          |
|------------------|-------------------------------------------------------|
| `make test`      | all tests (needs PostgreSQL, see `make db`)           |
| `make lint`      | ruff lint and format check                            |
| `make format`    | fix lint issues and format the code                   |
| `make typecheck` | mypy in strict mode                                   |
| `make check`     | lint, type check and tests — the same as CI           |

### Configuration

Settings are read from environment variables (`src/shop/config.py`):

| Variable            | Default                                                            | Used by        |
|---------------------|--------------------------------------------------------------------|----------------|
| `DATABASE_URL`      | `postgresql+psycopg://postgres:postgres@localhost:5432/shop`       | app, Alembic   |
| `LOG_LEVEL`         | `INFO`                                                             | app            |
| `TEST_DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/shop_test`  | tests          |

### Tests

```text
tests/
  unit/          # no database needed: uv run pytest tests/unit
  integration/   # HTTP endpoint, health check and migrations against PostgreSQL
```

The integration tests apply the Alembic migrations to the test database and check that they
can be rolled back. **Warning:** they drop and recreate the `public` schema of that database.

### Migrations

```bash
uv run alembic upgrade head                     # apply all migrations
uv run alembic downgrade -1                     # roll back the last one
uv run alembic history                          # list migrations
uv run alembic upgrade head --sql               # print the SQL without running it
uv run alembic revision -m "add refunds table"  # create a new migration
```

Migrations are written by hand. Autogenerate is turned off, because the SQLAlchemy models map only
the columns the application uses, not the full schema.

## Project structure

```text
src/shop/
  app.py                    # create_app(): wires settings, database, provider, routes
  config.py                 # Settings from environment variables
  wsgi.py                   # entry point for gunicorn
  api/                      # HTTP layer
    payments.py             #   POST /carts/{id}/payments: request parsing, response format
    health.py               #   GET /health
    errors.py               #   maps exceptions to JSON error responses
    dependencies.py         #   access to the session factory and provider in a request
  services/                 # business logic, no HTTP knowledge
    payments.py             #   the payment flow
    cart_total.py           #   stand-in for the existing total calculation service
    errors.py               #   domain errors
  db/
    models.py               # SQLAlchemy models
  integrations/
    payment_provider.py     # payment provider interface + mock
migrations/                 # Alembic (settings in pyproject.toml)
  sql/base_schema.sql       #   the base schema from the task, unchanged
  versions/
    0001_base_schema.py     #   applies sql/base_schema.sql
    0002_payments.py        #   the payments table
    0003_one_default_payment_method.py  # at most one default card per user
tests/                      # unit/ and integration/
Dockerfile                  # multi-stage build, runs gunicorn as a non-root user
docker-compose.yml          # db, migrate (one-off) and api services
.github/workflows/ci.yml    # lint, type check and tests on every push and pull request
```

The layers depend in one direction: `api` → `services` → `db` / `integrations`.
The services raise domain errors. `api/errors.py` alone decides which HTTP status each one gets.

## API

### `POST /carts/{cart_id}/payments`

Charges the user's card for the cart total.

| Header            | Required | Description                                                   |
|-------------------|----------|---------------------------------------------------------------|
| `X-User-Id`       | yes      | The id of the logged-in user (see assumptions).               |
| `Idempotency-Key` | yes      | A unique string (1–255 chars) per payment attempt, e.g. a UUID. |

Optional JSON body:

```json
{ "payment_method_id": "<uuid>" }
```

If no payment method is given, the user's default payment method is used.
A user has at most one default payment method (enforced by the database).

**Idempotency:** the `Idempotency-Key` identifies one payment attempt: one cart charged with one
payment method. If the key was used before with the same cart and payment method, the endpoint
returns the first payment and charges nothing. If the cart or the payment method differs, it returns
`422 idempotency_key_reused`. A request without `payment_method_id` means the default payment method,
so it is compared with the user's current default. To pay with another card (for example after a
decline), send a new key.

Response body (for 201, 202 and 402):

```json
{
  "id": "cc889b8b-ad8c-49ea-a51a-449bf7ee807b",
  "cart_id": "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1",
  "payment_method_id": "11111111-2222-3333-4444-555555555555",
  "status": "succeeded",
  "amount": "70.00",
  "currency": "USD",
  "failure_reason": null
}
```

The amount is a string so no precision is lost.

| Status | When                                                                              |
|--------|-----------------------------------------------------------------------------------|
| 201    | The card was charged. The cart is now `checked_out`.                              |
| 402    | The provider declined the card. The cart stays `active`, so the user can retry.  |
| 202    | Replay of a request whose payment is still in progress.                          |
| 400    | Missing or invalid `Idempotency-Key`, or an invalid body.                         |
| 401    | Missing or invalid `X-User-Id`.                                                   |
| 404    | The cart does not exist or belongs to another user.                               |
| 409    | The cart is not active, or a payment for it is already in progress.              |
| 422    | Empty cart, payment method not found, or idempotency key reused for another cart or payment method. |
| 500    | Unexpected error, e.g. the provider is unreachable (the payment stays `pending`). |

Every error, including unknown routes and unexpected failures, has the same JSON shape:
`{"error": {"code": "cart_not_payable", "message": "..."}}`.

### `GET /health`

Returns `200 {"status": "ok"}` when the database is reachable, otherwise `503 {"status": "unavailable"}`.
Meant for load balancer and container health checks.

## Design

### Schema

`payments` (in `migrations/versions/0002_payments.py`) stores one row per attempt to charge a card for a cart.
A cart can have many failed attempts but never more than one `pending` or `succeeded` one.
A partial unique index enforces this in the database.

`(user_id, idempotency_key)` is unique, so a retried request finds its earlier payment.
`amount` and `currency` are copied onto the payment, so the record keeps what was charged even if the cart changes later.

### Payment flow

1. **Transaction 1:** lock the cart row (`SELECT … FOR UPDATE`), then:
   - find the payment method (the one in the request, or the default);
   - return the earlier payment if the idempotency key was seen before with the same cart and
     payment method, or reject the request if either differs;
   - check that the cart is active, not empty and has no payment in progress;
   - get the total and insert a `pending` payment. Then commit.
2. **Call the provider**, outside any transaction, so no lock is held while waiting for the network.
   The payment id is sent as the provider's idempotency key.
3. **Transaction 2:** mark the payment `succeeded` (and the cart `checked_out`) or `failed`.

The pending row is saved before the provider is called. If the process crashes or the provider
call fails, there is a record of the attempt, and the cart cannot be charged a second time.

### Protection against double charging

- A request sent again with the same `Idempotency-Key` returns the first payment and does not charge
  again. If it names a different cart or payment method, it is rejected with `422`.
- Two different requests for the same cart run one at a time because of the cart row lock.
  The second one gets `409`. The partial unique index is a second safeguard in the database.
- A paid cart is `checked_out` and cannot be paid again.

## Assumptions

- **Authentication** is out of scope. An upstream auth layer is assumed to verify the user
  and pass their id in the `X-User-Id` header. A user can only pay for their own carts
  with their own payment methods. Someone else's cart returns `404`, so its existence is not revealed.
- **One default card:** the base schema allows several default payment methods per user, which makes
  "pay with the default card" ambiguous. Revision `0003` adds a unique index so a user has at most one.
- **Total calculation:** the task says this service already exists. `shop/cart_total.py` is a stand-in
  that sums `quantity × unit_price` and assumes one currency per cart.
- **Payment provider:** `MockPaymentProvider` declines any card token that contains `declined`
  (e.g. `tok_declined`). Every other token succeeds. The charge is synchronous.
- **Provider errors** (timeouts, network failures) are not handled with retries. The payment stays
  `pending` and the request returns `500`. A real system would reconcile pending payments with the
  provider, for example with a background job or webhooks. That is out of scope here.
- **Stock and orders:** decreasing `stock_quantity`, creating an order and sending emails happen
  after a successful payment, in other parts of the system. They are out of scope.
- **Base schema migration:** revision `0001` runs the provided SQL file as it is, so it is easy to compare
  with the task. Its sample data is kept for trying the API locally. Revision `0002` uses Alembic
  operations.
- The base schema has no triggers for `updated_at`. The SQLAlchemy models set it when a row is updated.
