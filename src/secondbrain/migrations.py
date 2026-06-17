from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol


class SqlRunner(Protocol):
    def execute(self, sql: str) -> None: ...

    def query(self, sql: str) -> list[str]: ...


def apply_migrations(runner: SqlRunner, migrations_path: Path) -> list[str]:
    runner.execute(
        """
        CREATE TABLE IF NOT EXISTS secondbrain_schema_migrations (
          version TEXT PRIMARY KEY,
          checksum TEXT NOT NULL,
          applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    applied_versions = set(
        runner.query(
            """
            SELECT version
            FROM secondbrain_schema_migrations
            ORDER BY version;
            """
        )
    )
    applied_now: list[str] = []

    for migration_file in sorted(migrations_path.glob("*.sql")):
        version = migration_file.stem
        sql = migration_file.read_text()
        checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        if version in applied_versions:
            _assert_checksum_unchanged(runner, version, checksum)
            continue
        runner.execute(sql)
        runner.execute(
            f"""
            INSERT INTO secondbrain_schema_migrations (version, checksum)
            VALUES ({_sql_literal(version)}, {_sql_literal(checksum)});
            """
        )
        applied_now.append(version)

    return applied_now


def _assert_checksum_unchanged(runner: SqlRunner, version: str, checksum: str) -> None:
    rows = runner.query(
        f"""
        SELECT checksum
        FROM secondbrain_schema_migrations
        WHERE version = {_sql_literal(version)};
        """
    )
    if rows and rows[0] != checksum:
        raise RuntimeError(f"migration checksum changed after apply: {version}")


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"

