from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from .vector import VECTOR_DIMENSIONS


class PsqlRepositoryBase:
    host: str
    port: int
    database: str
    user: str
    password: str

    def execute(self, sql: str) -> None:
        self._execute(sql)

    def query(self, sql: str) -> list[str]:
        return self._query(sql)

    def _execute(self, sql: str) -> None:
        self._run_psql(sql)

    def _query(self, sql: str) -> list[str]:
        output = self._run_psql(sql)
        return output.splitlines() if output else []

    def _query_json_lines(self, sql: str) -> list[dict[str, Any]]:
        return [json.loads(line) for line in self._query(sql) if line.strip()]

    def _run_psql(self, sql: str) -> str:
        env = {**os.environ, "PGPASSWORD": self.password}
        command = [
            "psql",
            "-h",
            self.host,
            "-p",
            str(self.port),
            "-U",
            self.user,
            "-d",
            self.database,
            "-v",
            "ON_ERROR_STOP=1",
            "-q",
            "-At",
        ]
        result = subprocess.run(command, input=sql, text=True, capture_output=True, env=env, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result.stdout.strip()


def sql_literal(value: Any) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def sql_nullable(value: str | None) -> str:
    return "NULL" if value is None else sql_literal(value)


def sql_bool(value: bool) -> str:
    return "true" if value else "false"


def jsonb_literal(value: Any) -> str:
    return sql_literal(json.dumps(value, ensure_ascii=False, sort_keys=True)) + "::jsonb"


def vector_literal(value: tuple[float, ...]) -> str:
    return sql_literal("[" + ",".join(f"{item:.10f}" for item in value) + "]") + f"::vector({VECTOR_DIMENSIONS})"
