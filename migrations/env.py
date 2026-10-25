from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from shop.config import Settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Revisions are written by hand, so autogenerate is not used: the models map
# only the columns the application needs, not the full schema.
target_metadata = None


def get_url() -> str:
    """The URL set by the caller (e.g. the tests), else the application's URL."""
    return config.get_main_option("sqlalchemy.url") or Settings.from_env().database_url


def run_migrations_offline() -> None:
    """Renders the migrations as SQL (`alembic upgrade head --sql`) without a database."""
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(get_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
