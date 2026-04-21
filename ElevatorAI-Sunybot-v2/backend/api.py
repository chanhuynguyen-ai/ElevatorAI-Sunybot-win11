from contextlib import contextmanager
import hashlib
import json
import os
import socket
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.chatbot_engine import ChatbotEngine
from backend.text_utils import normalize_vi

try:
    import psycopg
    from psycopg.rows import dict_row as psycopg3_dict_row
except Exception:
    psycopg = None
    psycopg3_dict_row = None

try:
    import psycopg2
    import psycopg2.extras
except Exception:
    psycopg2 = None

app = FastAPI(title="Sunybot Elevator Chatbot", version="1.6.0")
engine = ChatbotEngine()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "gui", "web")
PAGES_DIR = os.path.join(WEB_DIR, "pages")
STATIC_DIR = os.path.join(WEB_DIR, "static")
DIST_DIR = os.path.join(WEB_DIR, "dist")
DIST_INDEX = os.path.join(DIST_DIR, "index.html")
DIST_ASSETS_DIR = os.path.join(DIST_DIR, "assets")
DIST_FAVICON = os.path.join(DIST_DIR, "favicon.ico")
DIST_MANIFEST = os.path.join(DIST_DIR, "manifest.webmanifest")
DIST_SW = os.path.join(DIST_DIR, "sw.js")
DIST_ICONS_DIR = os.path.join(DIST_DIR, "icons")
FAVICON_PATH = os.path.join(STATIC_DIR, "favicon.ico")
LEGACY_INDEX = os.path.join(WEB_DIR, "index.html")
WEB_ENABLE_LEGACY_FALLBACK = os.getenv("WEB_ENABLE_LEGACY_FALLBACK", "0").lower() in {"1", "true", "yes"}
MAINT_USERS_FILE = os.path.join(BASE_DIR, "runtime_data", "maintenance_users.json")
ENABLE_BACKEND_DEMO_LOGIN = os.getenv("ENABLE_BACKEND_DEMO_LOGIN", "1").lower() not in {"0", "false", "no"}
BACKEND_DEMO_ACCOUNT = {
    "employee_code": os.getenv("DEMO_EMPLOYEE_CODE", "DEMO001"),
    "password": os.getenv("DEMO_PASSWORD", "123456"),
    "full_name": os.getenv("DEMO_FULL_NAME", "Kỹ thuật viên Demo"),
    "department": os.getenv("DEMO_DEPARTMENT", "Trung tâm bảo trì"),
    "role": os.getenv("DEMO_ROLE", "maintenance_demo"),
}

CV_SERVICE_BASE_URL = os.getenv("CV_SERVICE_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
CV_REQUEST_TIMEOUT = float(os.getenv("CV_REQUEST_TIMEOUT", "3.0"))
CV_STREAM_TIMEOUT = float(os.getenv("CV_STREAM_TIMEOUT", "8.0"))
CV_STREAM_PROXY_ENABLED = os.getenv("CV_STREAM_PROXY_ENABLED", "1").lower() not in {"0", "false", "no"}

EVENT_TITLE_MAP = {
    "BOTTLE": "Phát hiện chai nhựa",
    "FALL": "Phát hiện té ngã",
    "LYING": "Phát hiện nằm bất thường",
    "CROWD": "Phát hiện đông người",
    "UNKNOWN_PERSON": "Phát hiện người chưa gán nhãn",
}
EVENT_SEVERITY_MAP = {
    "FALL": "critical",
    "LYING": "high",
    "CROWD": "medium",
    "BOTTLE": "medium",
    "UNKNOWN_PERSON": "medium",
}

DB_HOST = os.getenv("PGHOST", os.getenv("DB_HOST", "127.0.0.1"))
DB_PORT = int(os.getenv("PGPORT", os.getenv("DB_PORT", "5432")))
DB_USER = os.getenv("PGUSER", os.getenv("DB_USER", "elevator_ai"))
DB_PASSWORD = os.getenv("PGPASSWORD", os.getenv("DB_PASSWORD", "elevator123"))
ELEVATOR_CV_DB_NAME = os.getenv("ELEVATOR_CV_DB_NAME", "elevator_cv")
ELEVATOR_LLM_DB_NAME = os.getenv("ELEVATOR_LLM_DB_NAME", "elevator_llm")
CV_ALLOWED_TABLES = [t.strip() for t in os.getenv("ELEVATOR_CV_ALLOWED_TABLES", "camera_events,camera_occupancy_samples,person_registry,face_embeddings").split(",") if t.strip()]
LLM_ALLOWED_TABLES = [t.strip() for t in os.getenv("ELEVATOR_LLM_ALLOWED_TABLES", "prompts,answers,intents,employees,chat_logs,knowledge_documents,knowledge_chunks,faq_items").split(",") if t.strip()]
DB_CATALOG = {
    "elevator_cv": {"key": "elevator_cv", "label": "CV analytics", "dbname": ELEVATOR_CV_DB_NAME, "allowed_tables": CV_ALLOWED_TABLES},
    "elevator_llm": {"key": "elevator_llm", "label": "Chatbot / LLM", "dbname": ELEVATOR_LLM_DB_NAME, "allowed_tables": LLM_ALLOWED_TABLES},
}


def _file_exists(path: str) -> bool:
    try:
        return os.path.isfile(path)
    except Exception:
        return False


def _dir_exists(path: str) -> bool:
    try:
        return os.path.isdir(path)
    except Exception:
        return False


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _sha256_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _build_backend_demo_user() -> Dict[str, Any]:
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    return {
        "employee_code": BACKEND_DEMO_ACCOUNT["employee_code"],
        "password_hash": _sha256_text(BACKEND_DEMO_ACCOUNT["password"]),
        "full_name": BACKEND_DEMO_ACCOUNT["full_name"],
        "full_name_norm": normalize_vi(BACKEND_DEMO_ACCOUNT["full_name"]),
        "department": BACKEND_DEMO_ACCOUNT["department"],
        "role": BACKEND_DEMO_ACCOUNT["role"],
        "source": "backend_demo_local",
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }


def _sanitize_user_profile(user: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(user, dict):
        return None
    return {
        "employee_code": user.get("employee_code"),
        "employee_id": user.get("employee_code"),
        "full_name": user.get("full_name") or user.get("employee_name") or user.get("employee_code"),
        "employee_name": user.get("full_name") or user.get("employee_name") or user.get("employee_code"),
        "department": user.get("department") or "Kỹ thuật",
        "role": user.get("role") or "technician",
        "source": user.get("source") or user.get("auth_source") or "backend_local",
        "status": user.get("status") or "active",
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
        "last_login_at": user.get("last_login_at"),
    }


def _load_maintenance_users() -> List[Dict[str, Any]]:
    users: List[Dict[str, Any]] = []
    try:
        if _file_exists(MAINT_USERS_FILE):
            with open(MAINT_USERS_FILE, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            if isinstance(payload, list):
                users = [item for item in payload if isinstance(item, dict)]
    except Exception:
        users = []

    if ENABLE_BACKEND_DEMO_LOGIN:
        demo_user = _build_backend_demo_user()
        if not any((item.get("employee_code") or "").strip().upper() == demo_user["employee_code"].strip().upper() for item in users):
            users.insert(0, demo_user)
    return users


def _save_maintenance_users(users: List[Dict[str, Any]]) -> None:
    _ensure_parent_dir(MAINT_USERS_FILE)
    with open(MAINT_USERS_FILE, "w", encoding="utf-8") as fh:
        json.dump(users, fh, ensure_ascii=False, indent=2)


def _serve_main_ui_response():
    if _file_exists(DIST_INDEX):
        return FileResponse(DIST_INDEX)
    if WEB_ENABLE_LEGACY_FALLBACK and _file_exists(LEGACY_INDEX):
        return FileResponse(LEGACY_INDEX)
    detail = {
        "error": "Frontend dist not found",
        "message": "Khong tim thay gui/web/dist/index.html. Hay build frontend React roi copy dist sang backend. UI cu da bi tat mac dinh de tranh chay nham runtime.",
        "dist_index": DIST_INDEX,
        "legacy_available": _file_exists(LEGACY_INDEX),
        "legacy_enabled": WEB_ENABLE_LEGACY_FALLBACK,
        "legacy_url": "/legacy" if _file_exists(LEGACY_INDEX) else None,
    }
    return JSONResponse(status_code=503, content=detail)


def _serve_legacy_ui_response():
    if _file_exists(LEGACY_INDEX):
        return FileResponse(LEGACY_INDEX)
    return JSONResponse(status_code=404, content={"error": "Legacy UI not found"})


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _cv_url(path: str) -> str:
    return f"{CV_SERVICE_BASE_URL}{path}"


def _load_json_response(raw: bytes) -> Any:
    return json.loads(raw.decode("utf-8"))


def _http_get_json(url: str, timeout: float = CV_REQUEST_TIMEOUT) -> Any:
    req = urllib_request.Request(url, headers={"Accept": "application/json"})
    with urllib_request.urlopen(req, timeout=timeout) as resp:
        return _load_json_response(resp.read())


def _http_post_json(url: str, payload: Dict[str, Any], timeout: float = CV_REQUEST_TIMEOUT) -> Any:
    raw = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(url, data=raw, method="POST", headers={"Accept": "application/json", "Content-Type": "application/json"})
    with urllib_request.urlopen(req, timeout=timeout) as resp:
        return _load_json_response(resp.read())


def _extract_items(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "events", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _normalize_cv_status(payload: Dict[str, Any]) -> Dict[str, Any]:
    latest_event = payload.get("latest_event") or payload.get("last_event") or {}
    if not isinstance(latest_event, dict):
        latest_event = {}
    last_event_type = payload.get("last_event_type") or latest_event.get("event_type") or latest_event.get("type")
    people_count = payload.get("people_count")
    if people_count is None:
        people_count = payload.get("person_count")
    if people_count is None:
        people_count = payload.get("occupancy")
    if people_count is None:
        people_count = 0
    fps = payload.get("fps") or payload.get("avg_fps") or 0.0
    camera_online = payload.get("camera_online")
    if camera_online is None:
        camera_online = payload.get("online")
    if camera_online is None:
        camera_online = payload.get("running")
    if camera_online is None:
        camera_online = True
    return {
        "available": True,
        "camera_online": bool(camera_online),
        "cam_id": payload.get("cam_id") or payload.get("camera_id") or "cam_01",
        "fps": fps,
        "people_count": people_count,
        "backend": payload.get("backend") or payload.get("runtime") or "cv_service",
        "source": payload.get("source") or "cv_service",
        "last_event_type": last_event_type,
        "last_event_title": EVENT_TITLE_MAP.get(last_event_type, last_event_type),
        "last_event_at": payload.get("last_event_at") or latest_event.get("event_ts") or latest_event.get("timestamp"),
        "stream_url": "/api/integration/cv/stream-proxy" if CV_STREAM_PROXY_ENABLED else _cv_url("/api/cv/stream"),
        "cv_service_base_url": CV_SERVICE_BASE_URL,
        "raw": payload,
    }


def _normalize_cv_event(event: Dict[str, Any]) -> Dict[str, Any]:
    event_type = event.get("event_type") or event.get("type") or "UNKNOWN"
    return {
        "id": event.get("id") or event.get("event_id") or event.get("event_ts") or event.get("timestamp"),
        "timestamp": event.get("event_ts") or event.get("timestamp") or event.get("created_at"),
        "cam_id": event.get("cam_id") or event.get("camera_id") or "cam_01",
        "type": event_type,
        "title": EVENT_TITLE_MAP.get(event_type, event_type),
        "severity": EVENT_SEVERITY_MAP.get(event_type, "info"),
        "track_id": event.get("track_id"),
        "person_id": event.get("person_id"),
        "person_name": event.get("person_name"),
        "people_count": event.get("people_count"),
        "confidence": event.get("confidence"),
        "posture": event.get("posture"),
        "bbox": event.get("bbox"),
        "snapshot_path": event.get("snapshot_path"),
        "extra": event.get("extra"),
        "raw": event,
    }


def _cv_status_fallback(error_message: str) -> Dict[str, Any]:
    return {
        "available": False,
        "camera_online": False,
        "cam_id": "cam_01",
        "fps": 0.0,
        "people_count": 0,
        "backend": "cv_service_unavailable",
        "source": "integration_fallback",
        "last_event_type": None,
        "last_event_title": None,
        "last_event_at": None,
        "stream_url": "/api/integration/cv/stream-proxy" if CV_STREAM_PROXY_ENABLED else _cv_url("/api/cv/stream"),
        "cv_service_base_url": CV_SERVICE_BASE_URL,
        "error": error_message,
    }


def _fetch_cv_status() -> Dict[str, Any]:
    payload = _http_get_json(_cv_url("/api/cv/status"))
    if not isinstance(payload, dict):
        raise ValueError("CV status payload is not a JSON object")
    return _normalize_cv_status(payload)


def _normalize_db_key(value: str) -> str:
    value = (value or "").strip().lower()
    if value in {"cv", "elevator_cv"}:
        return "elevator_cv"
    if value in {"llm", "elevator_llm"}:
        return "elevator_llm"
    raise HTTPException(status_code=400, detail="Database khong hop le. Chi ho tro elevator_cv hoac elevator_llm.")


def _get_db_cfg(db_key: str) -> Dict[str, Any]:
    return DB_CATALOG[_normalize_db_key(db_key)]


def _ensure_db_driver():
    if psycopg is None and psycopg2 is None:
        raise HTTPException(status_code=500, detail="Chua co PostgreSQL driver. Cai psycopg hoac psycopg2 truoc khi dung Data Manager API.")


@contextmanager
def _db_connection(db_key: str):
    _ensure_db_driver()
    cfg = _get_db_cfg(db_key)
    conn = None
    try:
        if psycopg is not None:
            conn = psycopg.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, dbname=cfg["dbname"], autocommit=False)
        else:
            conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, dbname=cfg["dbname"])
        yield conn
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _fetch_all(conn, sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    if psycopg is not None and conn.__class__.__module__.startswith("psycopg"):
        with conn.cursor(row_factory=psycopg3_dict_row) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def _fetch_one(conn, sql: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
    rows = _fetch_all(conn, sql, params)
    return rows[0] if rows else None


def _execute(conn, sql: str, params: Tuple[Any, ...] = ()) -> int:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def _quote_ident(name: str) -> str:
    if not name or not name.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail=f"Identifier khong hop le: {name}")
    return f'"{name}"'


def _ensure_allowed_table(db_key: str, table: str) -> str:
    cfg = _get_db_cfg(db_key)
    if table not in set(cfg["allowed_tables"]):
        raise HTTPException(status_code=403, detail=f"Bang {table} khong nam trong danh sach cho phep cua {cfg['key']}.")
    return table


def _table_columns(conn, table: str) -> List[Dict[str, Any]]:
    sql = """
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = %s
    ORDER BY ordinal_position
    """
    return _fetch_all(conn, sql, (table,))


def _table_primary_keys(conn, table: str) -> List[str]:
    sql = """
    SELECT kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
    WHERE tc.table_schema = 'public'
      AND tc.table_name = %s
      AND tc.constraint_type = 'PRIMARY KEY'
    ORDER BY kcu.ordinal_position
    """
    rows = _fetch_all(conn, sql, (table,))
    return [row["column_name"] for row in rows]


def _serializable_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _sanitize_row_for_write(conn, table: str, row: Dict[str, Any]) -> Dict[str, Any]:
    columns = _table_columns(conn, table)
    allowed = {col["column_name"] for col in columns}
    cleaned = {}
    for key, value in (row or {}).items():
        if key in allowed:
            cleaned[key] = _serializable_value(value)
    return cleaned


def _list_tables_from_catalog(conn, db_key: str) -> List[Dict[str, Any]]:
    cfg = _get_db_cfg(db_key)
    allowed = set(cfg["allowed_tables"])
    sql = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name
    """
    rows = _fetch_all(conn, sql)
    return [{"name": row["table_name"]} for row in rows if row["table_name"] in allowed]


def _upsert_generic_row(conn, table: str, row: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = _sanitize_row_for_write(conn, table, row)
    if not cleaned:
        raise HTTPException(status_code=400, detail="Khong co du lieu hop le de luu.")
    pk_columns = _table_primary_keys(conn, table)
    has_full_pk = bool(pk_columns) and all(col in cleaned and cleaned[col] not in (None, "") for col in pk_columns)
    existing = None
    if has_full_pk:
        where_clause = " AND ".join(f"{_quote_ident(col)} = %s" for col in pk_columns)
        existing = _fetch_one(conn, f"SELECT 1 AS ok FROM {_quote_ident(table)} WHERE {where_clause} LIMIT 1", tuple(cleaned[col] for col in pk_columns))
    if existing:
        update_cols = [col for col in cleaned if col not in pk_columns]
        if update_cols:
            set_clause = ", ".join(f"{_quote_ident(col)} = %s" for col in update_cols)
            params = tuple(cleaned[col] for col in update_cols) + tuple(cleaned[col] for col in pk_columns)
            _execute(conn, f"UPDATE {_quote_ident(table)} SET {set_clause} WHERE {where_clause}", params)
        conn.commit()
        return {"action": "update", "pk": {col: cleaned[col] for col in pk_columns}}
    columns = list(cleaned.keys())
    cols_sql = ", ".join(_quote_ident(col) for col in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    _execute(conn, f"INSERT INTO {_quote_ident(table)} ({cols_sql}) VALUES ({placeholders})", tuple(cleaned[col] for col in columns))
    conn.commit()
    return {"action": "insert", "pk": {col: cleaned.get(col) for col in pk_columns}}


def _delete_generic_row(conn, table: str, keys: Dict[str, Any]) -> Dict[str, Any]:
    pk_columns = _table_primary_keys(conn, table)
    if not pk_columns:
        raise HTTPException(status_code=400, detail=f"Bang {table} khong co primary key, khong the xoa an toan.")
    if not all(col in keys and keys[col] not in (None, "") for col in pk_columns):
        raise HTTPException(status_code=400, detail=f"Can cung cap day du PK: {', '.join(pk_columns)}")
    where_clause = " AND ".join(f"{_quote_ident(col)} = %s" for col in pk_columns)
    params = tuple(keys[col] for col in pk_columns)
    affected = _execute(conn, f"DELETE FROM {_quote_ident(table)} WHERE {where_clause}", params)
    conn.commit()
    return {"deleted": affected, "pk": {col: keys[col] for col in pk_columns}}


def _best_effort_register_person(conn, payload: Dict[str, Any]) -> Dict[str, Any]:
    table = _ensure_allowed_table("elevator_cv", "person_registry")
    columns = {col["column_name"] for col in _table_columns(conn, table)}
    row: Dict[str, Any] = {}
    employee_id = payload.get("employee_id") or payload.get("person_id")
    employee_name = payload.get("employee_name") or payload.get("person_name")
    department = payload.get("department")
    note = payload.get("note")
    extra = {
        "source": "main_backend_register_face",
        "event_id": payload.get("event_id"),
        "cam_id": payload.get("cam_id"),
        "track_id": payload.get("track_id"),
        "snapshot_path": payload.get("snapshot_path"),
        "status": "pending_embedding_capture",
    }
    if "person_code" in columns:
        row["person_code"] = employee_id
    if "full_name" in columns:
        row["full_name"] = employee_name
    if department and "department" in columns:
        row["department"] = department
    if "is_active" in columns:
        row["is_active"] = True
    if "extra" in columns:
        row["extra"] = extra
    if note:
        for candidate in ("note", "notes", "remark", "remarks"):
            if candidate in columns:
                row[candidate] = note
                break
    return _upsert_generic_row(conn, table, row)


def _employees_auth_ready(conn) -> bool:
    try:
        cols = {col["column_name"] for col in _table_columns(conn, "employees")}
    except Exception:
        return False
    required = {"employee_code", "full_name", "password_hash", "role", "status"}
    return required.issubset(cols)


def _find_maintenance_user_db(employee_code: str) -> Optional[Dict[str, Any]]:
    code = (employee_code or "").strip().upper()
    if not code:
        return None
    try:
        with _db_connection("elevator_llm") as conn:
            if not _employees_auth_ready(conn):
                return None
            row = _fetch_one(
                conn,
                """
                SELECT id, employee_code, full_name, full_name_norm, department, position, role,
                       status, password_hash, auth_source, created_at, updated_at, last_login_at
                FROM employees
                WHERE UPPER(employee_code) = %s
                LIMIT 1
                """,
                (code,),
            )
            return row
    except Exception:
        return None


def _create_demo_user_in_db_if_needed() -> None:
    if not ENABLE_BACKEND_DEMO_LOGIN:
        return
    demo = _build_backend_demo_user()
    try:
        with _db_connection("elevator_llm") as conn:
            if not _employees_auth_ready(conn):
                return
            existing = _fetch_one(
                conn,
                "SELECT id FROM employees WHERE UPPER(employee_code) = %s LIMIT 1",
                (demo["employee_code"].upper(),),
            )
            if existing:
                return
            _execute(
                conn,
                """
                INSERT INTO employees(
                    employee_code, full_name, full_name_norm, department, position, role,
                    status, password_hash, auth_source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    demo["employee_code"],
                    demo["full_name"],
                    demo["full_name_norm"],
                    demo["department"],
                    "Kỹ thuật viên demo",
                    demo["role"],
                    demo["status"],
                    demo["password_hash"],
                    demo["source"],
                ),
            )
            conn.commit()
    except Exception:
        return


def _build_auth_session(user: Dict[str, Any]) -> Dict[str, Any]:
    profile = _sanitize_user_profile(user) or {}
    profile.update({
        "login_mode": "postgresql" if user.get("auth_source") or user.get("source") else "backend_local",
        "logged_in_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    return profile


def _register_maintenance_user_db(req) -> Dict[str, Any]:
    employee_code = req.employee_code.strip().upper()
    full_name = req.full_name.strip()
    department = (req.department or "Kỹ thuật").strip() or "Kỹ thuật"
    role = (req.role or "technician").strip() or "technician"
    password_hash = _sha256_text(req.password)
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    with _db_connection("elevator_llm") as conn:
        if not _employees_auth_ready(conn):
            raise HTTPException(status_code=500, detail="Bang employees chua san sang cho dang nhap DB. Hay chay schema_pg_step1_windows.sql truoc.")
        existing = _fetch_one(
            conn,
            "SELECT id FROM employees WHERE UPPER(employee_code) = %s LIMIT 1",
            (employee_code,),
        )
        if existing:
            raise HTTPException(status_code=409, detail="Mã nhân viên đã tồn tại.")
        _execute(
            conn,
            """
            INSERT INTO employees(
                employee_code, full_name, full_name_norm, department, position,
                role, status, password_hash, auth_source, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                employee_code,
                full_name,
                normalize_vi(full_name),
                department,
                "Kỹ thuật viên",
                role,
                "active",
                password_hash,
                "postgresql",
                now,
                now,
            ),
        )
        conn.commit()
        user = _fetch_one(
            conn,
            "SELECT id, employee_code, full_name, department, role, status, auth_source, created_at, updated_at FROM employees WHERE UPPER(employee_code) = %s LIMIT 1",
            (employee_code,),
        )
        return {"ok": True, "mode": "postgresql", "user": _sanitize_user_profile(user)}


def _login_maintenance_user_db(req) -> Optional[Dict[str, Any]]:
    employee_code = req.employee_code.strip().upper()
    with _db_connection("elevator_llm") as conn:
        if not _employees_auth_ready(conn):
            return None
        row = _fetch_one(
            conn,
            """
            SELECT id, employee_code, full_name, department, role, status,
                   password_hash, auth_source, created_at, updated_at, last_login_at
            FROM employees
            WHERE UPPER(employee_code) = %s
            LIMIT 1
            """,
            (employee_code,),
        )
        if not row:
            return None
        if (row.get("status") or "active").lower() != "active":
            raise HTTPException(status_code=403, detail="Tài khoản đã bị khóa hoặc ngưng hoạt động.")
        if row.get("password_hash") != _sha256_text(req.password):
            raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu.")
        _execute(
            conn,
            "UPDATE employees SET last_login_at = NOW() WHERE id = %s",
            (row.get("id"),),
        )
        conn.commit()
        row["last_login_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        return {
            "ok": True,
            "mode": "postgresql",
            "user": _sanitize_user_profile(row),
            "session": _build_auth_session({**row, "source": "postgresql"}),
        }


def _find_maintenance_user_file(employee_code: str) -> Optional[Dict[str, Any]]:
    code = (employee_code or "").strip().upper()
    if not code:
        return None
    for user in _load_maintenance_users():
        if (user.get("employee_code") or "").strip().upper() == code:
            return user
    return None


def _register_maintenance_user_file(req) -> Dict[str, Any]:
    employee_code = req.employee_code.strip().upper()
    if _find_maintenance_user_file(employee_code):
        raise HTTPException(status_code=409, detail="Mã nhân viên đã tồn tại.")

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    user = {
        "employee_code": employee_code,
        "password_hash": _sha256_text(req.password),
        "full_name": req.full_name.strip(),
        "full_name_norm": normalize_vi(req.full_name),
        "department": (req.department or "Kỹ thuật").strip() or "Kỹ thuật",
        "role": (req.role or "technician").strip() or "technician",
        "status": "active",
        "source": "backend_local_file",
        "created_at": now,
        "updated_at": now,
    }
    users = _load_maintenance_users()
    users.append(user)
    _save_maintenance_users(users)
    return {"ok": True, "mode": "backend_local_file", "user": _sanitize_user_profile(user)}


def _login_maintenance_user_file(req) -> Dict[str, Any]:
    user = _find_maintenance_user_file(req.employee_code)
    if not user or user.get("password_hash") != _sha256_text(req.password):
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu.")
    return {
        "ok": True,
        "mode": user.get("source") or "backend_local_file",
        "user": _sanitize_user_profile(user),
        "session": _build_auth_session(user),
    }


def print_ui_links(port: int = 8000):
    lan_ip = get_local_ip()
    print("\n================ SUNYBOT UI ================")
    print(f"Local UI  : http://127.0.0.1:{port}/")
    print(f"LAN UI    : http://{lan_ip}:{port}/")
    print(f"Health    : http://{lan_ip}:{port}/health")
    print(f"Assistant : http://{lan_ip}:{port}/pages/assistant.html")
    print(f"Legacy UI : http://{lan_ip}:{port}/legacy")
    print(f"CV base   : {CV_SERVICE_BASE_URL}")
    print(f"DB host   : {DB_HOST}:{DB_PORT}")
    print(f"DB user   : {DB_USER}")
    print(f"Legacy fallback enabled: {WEB_ENABLE_LEGACY_FALLBACK}")
    if _file_exists(DIST_INDEX):
        print("Frontend  : React dist dang duoc uu tien tai /")
    else:
        print("Frontend  : Chua thay dist/index.html. / se tra ve loi ro rang thay vi tu dong roi vao UI cu.")
    print("============================================\n")


@app.on_event("startup")
def startup_debug():
    print("========== SUNYBOT UI STARTUP ==========")
    print(f"cwd={os.getcwd()}")
    print(f"BASE_DIR={BASE_DIR}")
    print(f"WEB_DIR={WEB_DIR} | exists={_dir_exists(WEB_DIR)}")
    print(f"DIST_DIR={DIST_DIR} | exists={_dir_exists(DIST_DIR)}")
    print(f"DIST_INDEX={DIST_INDEX} | exists={_file_exists(DIST_INDEX)}")
    print(f"DIST_ASSETS_DIR={DIST_ASSETS_DIR} | exists={_dir_exists(DIST_ASSETS_DIR)}")
    print("========================================")
    _create_demo_user_in_db_if_needed()
    print_ui_links(8000)


if _dir_exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if _dir_exists(DIST_ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=DIST_ASSETS_DIR), name="assets")
if _dir_exists(DIST_ICONS_DIR):
    app.mount("/icons", StaticFiles(directory=DIST_ICONS_DIR), name="icons")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    if _file_exists(DIST_FAVICON):
        return FileResponse(DIST_FAVICON)
    if _file_exists(FAVICON_PATH):
        return FileResponse(FAVICON_PATH)
    return Response(status_code=204)


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    if _file_exists(DIST_MANIFEST):
        return FileResponse(DIST_MANIFEST, media_type="application/manifest+json")
    return JSONResponse(status_code=404, content={"error": "manifest not found"})


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    if _file_exists(DIST_SW):
        return FileResponse(DIST_SW, media_type="application/javascript")
    return JSONResponse(status_code=404, content={"error": "service worker not found"})


@app.get("/", include_in_schema=False)
def home():
    return _serve_main_ui_response()


@app.get("/legacy", include_in_schema=False)
def legacy_home():
    return _serve_legacy_ui_response()


@app.get("/pages/{page}", include_in_schema=False)
def serve_pages(page: str):
    safe_page = os.path.basename(page)
    file_path = os.path.join(PAGES_DIR, safe_page)
    if not _file_exists(file_path):
        return JSONResponse(status_code=404, content={"error": "Page not found"})
    return FileResponse(file_path)


@app.get("/health")
def health():
    engine_health = engine.healthcheck()
    try:
        cv_status = _fetch_cv_status()
    except Exception as exc:
        cv_status = _cv_status_fallback(str(exc))
    db_ok = True
    db_error = None
    try:
        with _db_connection("elevator_cv") as conn:
            _fetch_one(conn, "SELECT 1 AS ok")
        with _db_connection("elevator_llm") as conn:
            _fetch_one(conn, "SELECT 1 AS ok")
    except Exception as exc:
        db_ok = False
        db_error = str(exc)
    return {
        "status": "ok" if engine_health.get("db_ok") and db_ok else "degraded",
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cv_service": {
            "available": cv_status.get("available", False),
            "camera_online": cv_status.get("camera_online", False),
            "cam_id": cv_status.get("cam_id"),
            "fps": cv_status.get("fps"),
            "people_count": cv_status.get("people_count"),
            "base_url": CV_SERVICE_BASE_URL,
        },
        "data_manager": {
            "db_ok": db_ok,
            "error": db_error,
            "host": DB_HOST,
            "port": DB_PORT,
            "cv_db": ELEVATOR_CV_DB_NAME,
            "llm_db": ELEVATOR_LLM_DB_NAME,
        },
        **engine_health,
    }


@app.get("/api/elevator/status")
def elevator_status():
    engine_payload = None
    engine_error = None
    try:
        engine_payload = engine.get_elevator_status(elevator_id=1)
    except Exception as exc:
        engine_error = str(exc)

    cv_payload = None
    try:
        cv_payload = _fetch_cv_status()
    except Exception:
        cv_payload = None

    floor = None
    direction = None
    door = None
    overload = False
    source = "backend_realtime"

    if isinstance(engine_payload, dict) and engine_payload:
        status_data = engine_payload.get("status_data") or engine_payload
        floor = status_data.get("floor")
        direction = status_data.get("direction")
        door = status_data.get("door")
        overload = bool(status_data.get("overload", False))
        source = engine_payload.get("source") or "chatbot_engine"

    people_count = None
    if isinstance(engine_payload, dict):
        status_data = engine_payload.get("status_data") or engine_payload
        people_count = status_data.get("people_count")

    if people_count in (None, "", "--") and isinstance(cv_payload, dict):
        people_count = cv_payload.get("people_count")

    return {
        "elevator_id": 1,
        "floor": floor if floor not in (None, "") else "--",
        "direction": direction if direction not in (None, "") else "--",
        "door": door if door not in (None, "") else "--",
        "people_count": people_count if people_count not in (None, "") else "--",
        "overload": overload,
        "status": "OVERLOAD" if overload else "NORMAL",
        "time": time.strftime("%H:%M:%S"),
        "source": source,
        "camera_online": cv_payload.get("camera_online") if isinstance(cv_payload, dict) else None,
        "cv_available": cv_payload.get("available") if isinstance(cv_payload, dict) else False,
        "engine_error": engine_error,
    }


@app.get("/api/integration/cv/config")
def cv_config():
    return {
        "cv_service_base_url": CV_SERVICE_BASE_URL,
        "request_timeout": CV_REQUEST_TIMEOUT,
        "stream_timeout": CV_STREAM_TIMEOUT,
        "stream_proxy_enabled": CV_STREAM_PROXY_ENABLED,
        "stream_url": "/api/integration/cv/stream-proxy" if CV_STREAM_PROXY_ENABLED else _cv_url("/api/cv/stream"),
    }


@app.get("/api/integration/cv/status")
def cv_status():
    try:
        return _fetch_cv_status()
    except Exception as exc:
        return _cv_status_fallback(str(exc))


@app.get("/api/integration/cv/events")
def cv_events(limit: int = Query(20, ge=1, le=200)):
    query = urllib_parse.urlencode({"limit": limit})
    try:
        payload = _http_get_json(f"{_cv_url('/api/cv/events')}?{query}")
        items = [_normalize_cv_event(item) for item in _extract_items(payload)]
        return {"available": True, "items": items, "count": len(items), "source": "cv_service", "cv_service_base_url": CV_SERVICE_BASE_URL}
    except Exception as exc:
        return {"available": False, "items": [], "count": 0, "source": "integration_fallback", "cv_service_base_url": CV_SERVICE_BASE_URL, "error": str(exc)}


@app.get("/api/integration/cv/density")
def cv_density(days: int = Query(7, ge=1, le=30)):
    query = urllib_parse.urlencode({"days": days})
    try:
        payload = _http_get_json(f"{_cv_url('/api/cv/density')}?{query}")
        return {"available": True, "data": payload, "source": "cv_service", "cv_service_base_url": CV_SERVICE_BASE_URL}
    except Exception as exc:
        return {"available": False, "data": [], "source": "integration_fallback", "cv_service_base_url": CV_SERVICE_BASE_URL, "error": str(exc)}


@app.get("/api/integration/cv/stream-url")
def cv_stream_url():
    return {
        "stream_url": "/api/integration/cv/stream-proxy" if CV_STREAM_PROXY_ENABLED else _cv_url("/api/cv/stream"),
        "upstream_stream_url": _cv_url("/api/cv/stream"),
        "stream_proxy_enabled": CV_STREAM_PROXY_ENABLED,
        "cv_service_base_url": CV_SERVICE_BASE_URL,
    }


@app.get("/api/integration/cv/stream-proxy")
def cv_stream_proxy():
    upstream_url = _cv_url("/api/cv/stream")
    try:
        urllib_request.urlopen(upstream_url, timeout=CV_REQUEST_TIMEOUT).close()
    except Exception as exc:
        return JSONResponse(status_code=503, content={"error": "CV stream unavailable", "detail": str(exc), "upstream_stream_url": upstream_url})

    def generate():
        req = urllib_request.Request(upstream_url)
        try:
            with urllib_request.urlopen(req, timeout=CV_STREAM_TIMEOUT) as upstream:
                while True:
                    try:
                        chunk = upstream.read(4096)
                    except (socket.timeout, TimeoutError, ConnectionResetError, OSError):
                        break
                    if not chunk:
                        break
                    yield chunk
        except (urllib_error.URLError, socket.timeout, TimeoutError, ConnectionResetError, OSError):
            return

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame", headers={"Cache-Control": "no-store"})


@app.get("/api/integration/cv/unknown-candidates")
def cv_unknown_candidates(limit: int = Query(10, ge=1, le=50)):
    try:
        with _db_connection("elevator_cv") as conn:
            _ensure_allowed_table("elevator_cv", "camera_events")
            columns = {col["column_name"] for col in _table_columns(conn, "camera_events")}
            base_cols = [c for c in ["event_id", "event_ts", "cam_id", "event_type", "track_id", "person_id", "person_name", "snapshot_path", "confidence", "bbox", "extra"] if c in columns]
            if not base_cols:
                return {"items": [], "count": 0}
            order_col = "event_ts" if "event_ts" in columns else base_cols[0]
            where_parts = []
            params: List[Any] = []
            if "event_type" in columns:
                where_parts.append(f"{_quote_ident('event_type')} = %s")
                params.append("UNKNOWN_PERSON")
            if "person_id" in columns and "person_name" in columns:
                where_parts.append(f"({_quote_ident('person_id')} IS NULL AND {_quote_ident('person_name')} IS NULL)")
            if not where_parts:
                return {"items": [], "count": 0}
            sql = f"SELECT {', '.join(_quote_ident(c) for c in base_cols)} FROM {_quote_ident('camera_events')} WHERE ({' OR '.join(where_parts)}) ORDER BY {_quote_ident(order_col)} DESC LIMIT %s"
            params.append(limit)
            rows = _fetch_all(conn, sql, tuple(params))
            return {"items": rows, "count": len(rows)}
    except Exception as exc:
        return {"items": [], "count": 0, "error": str(exc)}


ALLOW_REGISTER_FACE_DB_FALLBACK = os.getenv("ALLOW_REGISTER_FACE_DB_FALLBACK", "0").strip().lower() in {"1", "true", "yes", "on"}


class RegisterFaceRequest(BaseModel):
    employee_id: Optional[str] = None
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    note: Optional[str] = None
    event_id: Optional[Any] = None
    cam_id: Optional[str] = None
    track_id: Optional[Any] = None
    snapshot_path: Optional[str] = None
    source_event: Optional[Dict[str, Any]] = None


def _normalize_register_face_payload(req: RegisterFaceRequest) -> Dict[str, Any]:
    source_event = req.source_event if isinstance(req.source_event, dict) else {}

    employee_code = (req.employee_code or req.employee_id or '').strip().upper()
    employee_name = (req.employee_name or req.full_name or '').strip()
    if not employee_code:
        raise HTTPException(status_code=422, detail='employee_code/employee_id la bat buoc')
    if not employee_name:
        raise HTTPException(status_code=422, detail='employee_name/full_name la bat buoc')

    event_id = req.event_id or source_event.get('event_id') or source_event.get('id')
    track_id = req.track_id or source_event.get('track_id')
    snapshot_path = (req.snapshot_path or source_event.get('snapshot_path') or '').strip()
    cam_id = (req.cam_id or source_event.get('cam_id') or source_event.get('camera_id') or '').strip()

    return {
        'employee_id': employee_code,
        'employee_code': employee_code,
        'employee_name': employee_name,
        'full_name': employee_name,
        'department': (req.department or '').strip() or 'Kỹ thuật',
        'note': (req.note or '').strip() or None,
        'event_id': event_id,
        'cam_id': cam_id or None,
        'track_id': track_id,
        'snapshot_path': snapshot_path,
        'source_event': source_event or None,
    }


@app.post("/api/integration/cv/register-face")
def register_face(req: RegisterFaceRequest):
    payload = _normalize_register_face_payload(req)
    upstream_candidates = [_cv_url("/api/cv/register-face"), _cv_url("/api/cv/face/register")]
    last_upstream_error = None
    for url in upstream_candidates:
        try:
            data = _http_post_json(url, payload, timeout=max(CV_REQUEST_TIMEOUT, 15.0))
            return {
                "ok": True,
                "mode": "cv_service_proxy",
                "upstream_url": url,
                "data": data,
                "message": "Da dang ky khuon mat va luu embedding qua CV service.",
            }
        except Exception as exc:
            last_upstream_error = str(exc)

    if not ALLOW_REGISTER_FACE_DB_FALLBACK:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "CV service dang ky khuon mat khong san sang. Khong thuc hien fallback DB de tranh bao thanh cong gia.",
                "upstream_error": last_upstream_error,
                "cv_service_base_url": CV_SERVICE_BASE_URL,
            },
        )

    try:
        with _db_connection("elevator_cv") as conn:
            result = _best_effort_register_person(conn, payload)
            return {
                "ok": True,
                "mode": "db_fallback_pending_embedding",
                "upstream_error": last_upstream_error,
                "data": result,
                "message": "Da luu person_registry. Embedding se can duoc capture o buoc sau.",
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": "Khong the dang ky khuon mat.", "upstream_error": last_upstream_error, "db_error": str(exc)})


class MaintenanceLoginRequest(BaseModel):
    employee_code: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class MaintenanceRegisterRequest(BaseModel):
    employee_code: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    full_name: str = Field(..., min_length=1)
    department: Optional[str] = None
    role: Optional[str] = "technician"


def _register_maintenance_user(req: MaintenanceRegisterRequest) -> Dict[str, Any]:
    try:
        return _register_maintenance_user_db(req)
    except HTTPException:
        raise
    except Exception:
        return _register_maintenance_user_file(req)


def _login_maintenance_user(req: MaintenanceLoginRequest) -> Dict[str, Any]:
    try:
        db_result = _login_maintenance_user_db(req)
        if db_result:
            return db_result
    except HTTPException:
        raise
    except Exception:
        pass
    return _login_maintenance_user_file(req)


@app.post("/api/integration/users/login")
@app.post("/api/maintenance/login")
def maintenance_login(req: MaintenanceLoginRequest):
    return _login_maintenance_user(req)


@app.post("/api/integration/users/register")
@app.post("/api/maintenance/register")
def maintenance_register(req: MaintenanceRegisterRequest):
    return _register_maintenance_user(req)


class DataRowSaveRequest(BaseModel):
    database: str
    table: str
    row: Dict[str, Any]


class DataRowDeleteRequest(BaseModel):
    database: str
    table: str
    keys: Dict[str, Any]


@app.get("/api/integration/data/catalog")
def data_catalog():
    items = []
    for key, cfg in DB_CATALOG.items():
        items.append({"key": key, "label": cfg["label"], "dbname": cfg["dbname"], "host": DB_HOST, "port": DB_PORT, "allowed_tables": cfg["allowed_tables"]})
    return {"driver": "psycopg3" if psycopg is not None else ("psycopg2" if psycopg2 is not None else "missing"), "items": items}


@app.get("/api/integration/data/tables")
def data_tables(database: str):
    with _db_connection(database) as conn:
        return {"database": _normalize_db_key(database), "items": _list_tables_from_catalog(conn, database)}


@app.get("/api/integration/data/table")
def data_table(database: str, table: str, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    normalized_db = _normalize_db_key(database)
    safe_table = _ensure_allowed_table(normalized_db, table)
    with _db_connection(normalized_db) as conn:
        columns = _table_columns(conn, safe_table)
        pk_columns = _table_primary_keys(conn, safe_table)
        if not columns:
            raise HTTPException(status_code=404, detail=f"Khong tim thay bang {safe_table}")
        order_by = _quote_ident(pk_columns[0]) if pk_columns else _quote_ident(columns[0]["column_name"])
        sql = f"SELECT * FROM {_quote_ident(safe_table)} ORDER BY {order_by} DESC LIMIT %s OFFSET %s"
        count_sql = f"SELECT COUNT(*) AS total FROM {_quote_ident(safe_table)}"
        rows = _fetch_all(conn, sql, (limit, offset))
        total_row = _fetch_one(conn, count_sql) or {"total": 0}
        return {"database": normalized_db, "table": safe_table, "columns": columns, "primary_keys": pk_columns, "rows": rows, "limit": limit, "offset": offset, "total": int(total_row.get("total", 0)), "read_only": normalized_db == "elevator_cv"}


@app.post("/api/integration/data/row/save")
def data_row_save(req: DataRowSaveRequest):
    normalized_db = _normalize_db_key(req.database)
    safe_table = _ensure_allowed_table(normalized_db, req.table)
    if normalized_db == "elevator_cv":
        raise HTTPException(status_code=403, detail="elevator_cv dang de read-only tren UI de tranh ghi de du lieu realtime.")
    with _db_connection(normalized_db) as conn:
        result = _upsert_generic_row(conn, safe_table, req.row)
        return {"ok": True, "database": normalized_db, "table": safe_table, "result": result}


@app.post("/api/integration/data/row/delete")
def data_row_delete(req: DataRowDeleteRequest):
    normalized_db = _normalize_db_key(req.database)
    safe_table = _ensure_allowed_table(normalized_db, req.table)
    if normalized_db == "elevator_cv":
        raise HTTPException(status_code=403, detail="elevator_cv dang de read-only tren UI de tranh ghi de du lieu realtime.")
    with _db_connection(normalized_db) as conn:
        result = _delete_generic_row(conn, safe_table, req.keys)
        return {"ok": True, "database": normalized_db, "table": safe_table, "result": result}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    scope: str = "customer"
    persona: Optional[str] = None
    include_trace: bool = False


class ChatResponse(BaseModel):
    answer: str
    source: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    session_id: Optional[str] = None
    scope: Optional[str] = None
    persona: Optional[str] = None
    query_type: Optional[str] = None
    tool_trace: Optional[List[Dict[str, Any]]] = None


def _run_chat(req: ChatRequest, forced_scope: Optional[str] = None, forced_persona: Optional[str] = None) -> Dict[str, Any]:
    scope = forced_scope or req.scope
    persona = forced_persona or req.persona
    result = engine.handle(req.message, session_id=req.session_id, scope=scope, persona=persona)
    if not req.include_trace:
        result = {**result, "tool_trace": None}
    return {
        "answer": result.get("answer", ""),
        "source": result.get("source", "UNKNOWN"),
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "session_id": result.get("session_id"),
        "scope": result.get("scope"),
        "persona": result.get("persona"),
        "query_type": result.get("query_type"),
        "tool_trace": result.get("tool_trace"),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    return _run_chat(req)


@app.post("/api/chat/customer", response_model=ChatResponse)
def chat_customer(req: ChatRequest):
    return _run_chat(req, forced_scope="customer", forced_persona="customer_assistant")


@app.post("/api/chat/maintenance", response_model=ChatResponse)
def chat_maintenance(req: ChatRequest):
    return _run_chat(req, forced_scope="maintenance", forced_persona="maintenance_console")


@app.post("/api/knowledge/reload")
def reload_knowledge():
    return engine.reload_knowledge()


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    if full_path.startswith(("api", "chat", "health", "static", "assets", "icons", "pages", "legacy", "manifest.webmanifest", "sw.js")):
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return _serve_main_ui_response()
