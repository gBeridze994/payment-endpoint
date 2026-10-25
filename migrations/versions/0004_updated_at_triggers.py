"""Keep updated_at current with a database trigger.

The base schema sets updated_at only on insert. A BEFORE UPDATE trigger sets
it on every update that changes the row, whoever writes it: this application,
another service or a manual SQL statement.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-25

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES_WITH_UPDATED_AT = ["users", "products", "carts", "payments"]


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE FUNCTION set_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in TABLES_WITH_UPDATED_AT:
        # The WHEN clause skips updates that change nothing.
        op.execute(
            f"""
            CREATE TRIGGER {table}_set_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                WHEN (OLD IS DISTINCT FROM NEW)
                EXECUTE FUNCTION set_updated_at()
            """
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in TABLES_WITH_UPDATED_AT:
        op.execute(f"DROP TRIGGER {table}_set_updated_at ON {table}")
    op.execute("DROP FUNCTION set_updated_at()")
