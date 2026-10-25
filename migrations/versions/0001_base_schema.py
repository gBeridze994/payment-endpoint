"""Base schema of the online shop, as given by the task.

Revision ID: 0001
Revises:
Create Date: 2026-10-25

"""

from collections.abc import Sequence
from pathlib import Path

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Kept as the original SQL file so it can be compared with the task 1:1.
BASE_SCHEMA_SQL = Path(__file__).parent.parent / "sql" / "base_schema.sql"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(BASE_SCHEMA_SQL.read_text())


def downgrade() -> None:
    """Downgrade schema. The pgcrypto extension is kept: other schemas may use it."""
    for table in ["user_payment_methods", "cart_items", "carts", "products", "users"]:
        op.drop_table(table)
