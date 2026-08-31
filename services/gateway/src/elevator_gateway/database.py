import json
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List

from fastapi import HTTPException

from elevator_gateway import config

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - exercised only when driver is absent
    psycopg = None
    dict_row = None


CV_ALLOWED_TABLES = {
    "camera_events",
    "camera_occupancy_samples",
    "person_registry",
    "face_embeddings",
}
LLM_ALLOWED_TABLES = {
    "prompts",
    "answers",
    "intents",
    "employees",
    "chat_logs",
}

# These fields are intentionally never returned by the generic Data Manager.
SENSITIVE_COLUMNS = {"employees": {"password_hash"}}


def normalize_database(value: str) -> str:
    value = (value or "").strip().lower()
    if value in {"cv", "elevator_cv"}:
        return "elevator_cv"
    if value in {"llm", "elevator_llm", "elevator_user"}:
        return "elevator_llm"
    raise HTTPException(status_code=400, detail="unsupported database")


def allowed_tables(database: str) -> set[str]:
    key = normalize_database(database)
    return CV_ALLOWED_TABLES if key == "elevator_cv" else LLM_ALLOWED_TABLES


def ensure_allowed_table(database: str, table: str) -> str:
    key = normalize_database(database)
    if table not in allowed_tables(key):
        raise HTTPException(status_code=403, detail=f"table {table!r} is not allowed for {key}")
    return table


def _database_name(database: str) -> str:
    key = normalize_database(database)
    return config.CV_DB if key == "elevator_cv" else config.LLM_DB


def _require_driver() -> None:
    if psycopg is None:
        raise HTTPException(status_code=503, detail="PostgreSQL driver unavailable")


@contextmanager
def connection(database: str):
    _require_driver()
    conn = psycopg.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        dbname=_database_name(database),
        row_factory=dict_row,
        autocommit=False,
    )
    try:
        yield conn
    finally:
        conn.close()


def _ident(name: str) -> str:
    if not name or not name.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail=f"invalid identifier: {name!r}")
    return f'"{name}"'


def table_columns(conn, table: str) -> List[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default, is_generated
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        rows = [dict(row) for row in cur.fetchall()]
    sensitive = SENSITIVE_COLUMNS.get(table, set())
    return [row for row in rows if row["column_name"] not in sensitive]


def primary_keys(conn, table: str) -> List[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = 'public'
              AND tc.table_name = %s
              AND tc.constraint_type = 'PRIMARY KEY'
            ORDER BY kcu.ordinal_position
            """,
            (table,),
        )
        return [row["column_name"] for row in cur.fetchall()]


def list_existing_tables(conn, database: str) -> List[str]:
    allowed = allowed_tables(database)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
        return [row["table_name"] for row in cur.fetchall() if row["table_name"] in allowed]


def _safe_select_columns(columns: Iterable[Dict[str, Any]]) -> List[str]:
    return [row["column_name"] for row in columns]


def fetch_table(database: str, table: str, limit: int, offset: int) -> Dict[str, Any]:
    key = normalize_database(database)
    table = ensure_allowed_table(key, table)
    with connection(key) as conn:
        columns = table_columns(conn, table)
        if not columns:
            raise HTTPException(status_code=404, detail=f"table {table!r} not found")
        pk = primary_keys(conn, table)
        names = _safe_select_columns(columns)
        order_column = pk[0] if pk else names[0]
        select_list = ", ".join(_ident(name) for name in names)
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {select_list} FROM {_ident(table)} "
                f"ORDER BY {_ident(order_column)} DESC LIMIT %s OFFSET %s",
                (limit, offset),
            )
            rows = [dict(row) for row in cur.fetchall()]
            cur.execute(f"SELECT COUNT(*) AS total FROM {_ident(table)}")
            total = int(cur.fetchone()["total"])
    return {
        "database": key,
        "table": table,
        "columns": columns,
        "primary_keys": pk,
        "rows": rows,
        "limit": limit,
        "offset": offset,
        "total": total,
        "read_only": key == "elevator_cv",
    }


def _coerce_value(value: Any, metadata: Dict[str, Any]) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if value == "" and metadata.get("data_type") not in {
        "character varying",
        "character",
        "text",
    }:
        return None
    return value


def _clean_row(conn, table: str, row: Dict[str, Any], *, for_insert: bool) -> Dict[str, Any]:
    metadata = {item["column_name"]: item for item in table_columns(conn, table)}
    cleaned: Dict[str, Any] = {}
    for key, value in (row or {}).items():
        info = metadata.get(key)
        if info is None or str(info.get("is_generated", "NEVER")).upper() != "NEVER":
            continue
        coerced = _coerce_value(value, info)
        if for_insert and coerced is None and info.get("column_default") is not None:
            continue
        cleaned[key] = coerced
    return cleaned


def _row_exists(conn, table: str, keys: Dict[str, Any]) -> bool:
    where = " AND ".join(f"{_ident(key)} = %s" for key in keys)
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT 1 AS ok FROM {_ident(table)} WHERE {where} LIMIT 1",
            tuple(keys.values()),
        )
        return cur.fetchone() is not None


def save_row(database: str, table: str, row: Dict[str, Any]) -> Dict[str, Any]:
    key = normalize_database(database)
    table = ensure_allowed_table(key, table)
    if key == "elevator_cv":
        raise HTTPException(status_code=403, detail="CV database is read-only from the UI")

    with connection(key) as conn:
        pk = primary_keys(conn, table)
        initial = _clean_row(conn, table, row, for_insert=False)
        pk_values = {name: initial.get(name) for name in pk}
        has_full_pk = bool(pk) and all(value not in (None, "") for value in pk_values.values())

        if has_full_pk and _row_exists(conn, table, pk_values):
            update_values = {k: v for k, v in initial.items() if k not in pk}
            if update_values:
                set_clause = ", ".join(f"{_ident(name)} = %s" for name in update_values)
                where_clause = " AND ".join(f"{_ident(name)} = %s" for name in pk)
                params = tuple(update_values.values()) + tuple(pk_values[name] for name in pk)
                with conn.cursor() as cur:
                    cur.execute(
                        f"UPDATE {_ident(table)} SET {set_clause} WHERE {where_clause}",
                        params,
                    )
            conn.commit()
            return {"action": "update", "primary_key": pk_values}

        cleaned = _clean_row(conn, table, row, for_insert=True)
        # Empty auto-generated primary keys should not be inserted explicitly.
        for name in pk:
            if cleaned.get(name) in (None, ""):
                cleaned.pop(name, None)
        if not cleaned:
            raise HTTPException(status_code=400, detail="no writable fields supplied")

        names = list(cleaned)
        columns_sql = ", ".join(_ident(name) for name in names)
        placeholders = ", ".join(["%s"] * len(names))
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {_ident(table)} ({columns_sql}) VALUES ({placeholders})",
                tuple(cleaned[name] for name in names),
            )
        conn.commit()
        return {"action": "insert"}


def delete_row(database: str, table: str, keys: Dict[str, Any]) -> Dict[str, Any]:
    key = normalize_database(database)
    table = ensure_allowed_table(key, table)
    if key == "elevator_cv":
        raise HTTPException(status_code=403, detail="CV database is read-only from the UI")

    with connection(key) as conn:
        pk = primary_keys(conn, table)
        if not pk:
            raise HTTPException(status_code=400, detail=f"table {table!r} has no primary key")
        if not all(keys.get(name) not in (None, "") for name in pk):
            raise HTTPException(status_code=400, detail=f"required primary keys: {', '.join(pk)}")
        where_clause = " AND ".join(f"{_ident(name)} = %s" for name in pk)
        with conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {_ident(table)} WHERE {where_clause}",
                tuple(keys[name] for name in pk),
            )
            deleted = cur.rowcount
        conn.commit()
    return {"deleted": deleted, "primary_key": {name: keys[name] for name in pk}}
