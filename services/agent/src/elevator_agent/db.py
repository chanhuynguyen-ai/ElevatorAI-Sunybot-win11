import math
import os
from contextlib import contextmanager

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:
    psycopg = None
    dict_row = None

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:
    psycopg2 = None
    RealDictCursor = None


class DB(object):
    """Small PostgreSQL adapter that supports desktop psycopg3 and JetPack psycopg2."""

    def __init__(self):
        self.host = os.getenv("PGHOST", os.getenv("DB_HOST", "localhost"))
        self.user = os.getenv("PGUSER", os.getenv("DB_USER", "elevator_ai"))
        self.password = os.getenv("PGPASSWORD", os.getenv("DB_PASSWORD", ""))
        self.database = os.getenv("PGDATABASE", os.getenv("DB_NAME", "elevator_llm"))
        self.port = int(os.getenv("PGPORT", os.getenv("DB_PORT", "5432")))
        self.application_name = os.getenv("PGAPPNAME", "elevatorai-agent")
        self.sslmode = os.getenv("PGSSLMODE", "prefer")
        self.connect_timeout = int(os.getenv("PGCONNECT_TIMEOUT", "3"))
        self.statement_timeout_ms = int(os.getenv("PGSTATEMENT_TIMEOUT_MS", "30000"))

    @property
    def driver_ready(self):
        return psycopg is not None or psycopg2 is not None

    @property
    def driver_name(self):
        if psycopg is not None:
            return "psycopg3"
        if psycopg2 is not None:
            return "psycopg2"
        return "missing"

    def connect(self, autocommit=True):
        kwargs = {
            "host": self.host,
            "port": self.port,
            "dbname": self.database,
            "user": self.user,
            "password": self.password,
            "application_name": self.application_name,
            "sslmode": self.sslmode,
            "connect_timeout": self.connect_timeout,
            "options": "-c statement_timeout={0}".format(self.statement_timeout_ms),
        }
        if psycopg is not None:
            return psycopg.connect(autocommit=autocommit, row_factory=dict_row, **kwargs)
        if psycopg2 is not None:
            conn = psycopg2.connect(cursor_factory=RealDictCursor, **kwargs)
            conn.autocommit = autocommit
            return conn
        raise RuntimeError(
            "PostgreSQL driver is not installed. Install psycopg[binary] on desktop "
            "or psycopg2-binary on JetPack."
        )

    @contextmanager
    def connection(self, autocommit=True):
        conn = self.connect(autocommit=autocommit)
        try:
            yield conn
        finally:
            conn.close()

    def settings_snapshot(self):
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "application_name": self.application_name,
            "sslmode": self.sslmode,
            "connect_timeout": self.connect_timeout,
            "statement_timeout_ms": self.statement_timeout_ms,
            "driver": self.driver_name,
        }

    def test_connection(self):
        return bool(self.test_connection_details().get("ok"))

    def test_connection_details(self):
        if not self.driver_ready:
            return {"ok": False, "error": "PostgreSQL driver not installed", "settings": self.settings_snapshot()}
        try:
            with self.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT current_database() AS db, current_user AS usr, "
                        "version() AS version, NOW() AS server_time"
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
            return {"ok": False, "error": str(exc), "settings": self.settings_snapshot()}


def to_pgvector(values):
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
    return "[" + ",".join(casted) + "]" if casted else None


db = DB()
