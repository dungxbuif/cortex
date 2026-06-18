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
            host=_env("PGHOST", "localhost"),
            port=int(_env("PGPORT", "5432")),
            database=_env("PGDATABASE", "cortex"),
            user=_env("PGUSER", "dev"),
            password=_env("PGPASSWORD", "password"),
        )


@dataclass(frozen=True)
class AIServiceSettings:
    postgres: PostgresSettings
    default_owner_id: str
    migrations_path: Path
    google_api_key: str | None
    google_embedding_model: str
    google_embedding_dimensions: int
    google_generation_model: str

    @classmethod
    def from_env(cls) -> "AIServiceSettings":
        env_file = Path(__file__).resolve().parents[1] / ".env.local"
        load_env_file(env_file)
        default_migrations = Path(__file__).resolve().parents[1] / "migrations"
        return cls(
            postgres=PostgresSettings.from_env(),
            default_owner_id=_env("DEFAULT_OWNER_ID", "owner"),
            migrations_path=Path(_env("MIGRATIONS_PATH", str(default_migrations))),
            google_api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
            google_embedding_model=_env("EMBEDDING_MODEL", "gemini-embedding-2"),
            google_embedding_dimensions=int(_env("EMBEDDING_DIMENSIONS", "768")),
            google_generation_model=_env("GENERATION_MODEL", "gemini-3.5-flash"),
        )


SecondBrainSettings = AIServiceSettings


def _env(name: str, default: str) -> str:
    return os.getenv(f"AI_SERVICE_{name}", os.getenv(f"SECOND_BRAIN_{name}", os.getenv(name, default)))


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
