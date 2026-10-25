import os
from dataclasses import dataclass
from typing import Self

DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/shop"


@dataclass(frozen=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Self:
        return cls(
            database_url=os.environ.get("DATABASE_URL", cls.database_url),
            log_level=os.environ.get("LOG_LEVEL", cls.log_level),
        )
