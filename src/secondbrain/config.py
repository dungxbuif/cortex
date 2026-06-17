from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PostgresSettings:
    host: str
    port: int
    database: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "PostgresSettings":
        return cls(
            host=os.getenv("SECOND_BRAIN_PGHOST", os.getenv("PGHOST", "localhost")),
            port=int(os.getenv("SECOND_BRAIN_PGPORT", os.getenv("PGPORT", "5432"))),
            database=os.getenv("SECOND_BRAIN_PGDATABASE", os.getenv("PGDATABASE", "cortex")),
            user=os.getenv("SECOND_BRAIN_PGUSER", os.getenv("PGUSER", "dev")),
            password=os.getenv("SECOND_BRAIN_PGPASSWORD", os.getenv("PGPASSWORD", "password")),
        )


@dataclass(frozen=True)
class SecondBrainSettings:
    postgres: PostgresSettings
    default_owner_id: str
    migrations_path: Path
    google_api_key: str | None
    google_embedding_model: str
    google_embedding_dimensions: int
    google_generation_model: str

    @classmethod
    def from_env(cls) -> "SecondBrainSettings":
        env_file = Path(__file__).resolve().parent / ".env.local"
        load_env_file(env_file)
        default_migrations = Path(__file__).resolve().parent / "migrations"
        return cls(
            postgres=PostgresSettings.from_env(),
            default_owner_id=os.getenv("SECOND_BRAIN_DEFAULT_OWNER_ID", "owner"),
            migrations_path=Path(os.getenv("SECOND_BRAIN_MIGRATIONS_PATH", str(default_migrations))),
            google_api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
            google_embedding_model=os.getenv("SECOND_BRAIN_EMBEDDING_MODEL", "gemini-embedding-2"),
            google_embedding_dimensions=int(os.getenv("SECOND_BRAIN_EMBEDDING_DIMENSIONS", "768")),
            google_generation_model=os.getenv("SECOND_BRAIN_GENERATION_MODEL", "gemini-3.5-flash"),
        )


def load_env_file(path: Path) -> None:
    """Load a local env file without logging values.

    Existing environment variables win so shells/CI can override local files.
    """

    if not path.exists():
        return
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
