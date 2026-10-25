"""Payments: one row per attempt to charge a user's card for a cart.

A cart can have many failed attempts, but at most one that is in progress
or succeeded (see uq_payments_cart_not_failed).

Status values:
  pending    — the row is saved and the provider is being called.
               A row that stays pending means the outcome is unknown
               and must be reconciled with the provider.
  succeeded  — the provider charged the card.
  failed     — the provider declined the charge.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column("user_id", sa.Uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("cart_id", sa.Uuid, sa.ForeignKey("carts.id"), nullable=False),
        sa.Column(
            "payment_method_id",
            sa.Uuid,
            sa.ForeignKey("user_payment_methods.id"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        # Sent by the client so a retried request does not charge the card twice.
        sa.Column("idempotency_key", sa.Text, nullable=False),
        # The charge id from the payment provider. Set once the provider answers.
        sa.Column("provider_payment_id", sa.Text, unique=True),
        sa.Column("failure_reason", sa.Text),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        sa.CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed')", name="ck_payments_status"
        ),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_payments_user_idempotency_key"),
    )
    op.create_index("idx_payments_cart_id", "payments", ["cart_id"])
    # A cart must never be charged twice.
    op.create_index(
        "uq_payments_cart_not_failed",
        "payments",
        ["cart_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'succeeded')"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("payments")
