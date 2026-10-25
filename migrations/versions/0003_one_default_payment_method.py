"""A user can have at most one default payment method.

The base schema allows several default payment methods per user, which makes
"charge the default card" ambiguous. Fails if existing data already has a user
with more than one default payment method.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "uq_user_payment_methods_one_default",
        "user_payment_methods",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_user_payment_methods_one_default", table_name="user_payment_methods")
