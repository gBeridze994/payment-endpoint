from alembic import command
from sqlalchemy import inspect


def test_migrations_can_be_rolled_back_and_reapplied(engine, alembic_config):
    command.downgrade(alembic_config, "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}

    command.upgrade(alembic_config, "head")
    assert "payments" in inspect(engine).get_table_names()
