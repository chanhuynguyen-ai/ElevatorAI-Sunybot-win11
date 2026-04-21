import math
import os
from contextlib import contextmanager
from typing import Dict, Iterable, Optional

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Thiếu psycopg. Hãy cài: pip install 'psycopg[binary]'") from exc


class DB:
    def __init__(self):
        self.host = os.getenv("PGHOST", os.getenv("DB_HOST", "localhost"))
        self.user = os.getenv("PGUSER", os.getenv("DB_USER", "elevator_ai"))
        self.password = os.getenv("PGPASSWORD", os.getenv("DB_PASSWORD", "elevator123"))
        self.database = os.getenv("PGDATABASE", os.getenv("DB_NAME", "elevator_ai_pg"))
        self.port = int(os.getenv("PGPORT", os.getenv("DB_PORT", "5432")))
        self.application_name = os.getenv("PGAPPNAME", "sunybot")
        self.sslmode = os.getenv("PGSSLMODE", "prefer")
        self.connect_timeout = int(os.getenv("PGCONNECT_TIMEOUT", "5"))
        self.statement_timeout_ms = int(os.getenv("PGSTATEMENT_TIMEOUT_MS", "30000"))

    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.database} "
            f"user={self.user} password={self.password} "
            f"application_name={self.application_name} sslmode={self.sslmode} "
            f"connect_timeout={self.connect_timeout} "
            f"options='-c statement_timeout={self.statement_timeout_ms}'"
        )

    def connect(self, autocommit: bool = True):
        return psycopg.connect(
            self.dsn(),
            autocommit=autocommit,
            row_factory=dict_row,
        )

    @contextmanager
    def connection(self, autocommit: bool = True):
        conn = self.connect(autocommit=autocommit)
        try:
            yield conn
        finally:
            conn.close()

    def settings_snapshot(self) -> Dict[str, object]:
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "application_name": self.application_name,
            "sslmode": self.sslmode,
            "connect_timeout": self.connect_timeout,
            "statement_timeout_ms": self.statement_timeout_ms,
        }

    def test_connection(self) -> bool:
        return self.test_connection_details().get("ok", False)

    def test_connection_details(self) -> Dict[str, object]:
        try:
            with self.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT current_database() AS db,
                               current_user AS usr,
                               version() AS version,
                               NOW() AS server_time
                        """
                    )
                    row = cur.fetchone() or {}
                    return {
                        "ok": True,
                        "database": row.get("db"),
                        "user": row.get("usr"),
                        "version": row.get("version"),
                        "server_time": str(row.get("server_time")) if row.get("server_time") else None,
                        "settings": self.settings_snapshot(),
                    }
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                "settings": self.settings_snapshot(),
            }


def to_pgvector(values: Optional[Iterable[float]]) -> Optional[str]:
    if values is None:
        return None

    casted = []
    for item in values:
        try:
            value = float(item)
        except Exception:
            return None
        if not math.isfinite(value):
            return None
        casted.append(str(value))

    if not casted:
        return None
    return "[" + ",".join(casted) + "]"


# Dùng chung toàn project
# Runtime chatbot đã chuyển sang PostgreSQL + pgvector.
db = DB()
