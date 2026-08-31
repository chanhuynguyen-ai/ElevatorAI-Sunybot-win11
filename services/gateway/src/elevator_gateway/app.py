from typing import Any, Dict

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from elevator_gateway import config
from elevator_gateway.clients import agent_url, request_json, service_available, vision_url
from elevator_gateway.database import (
    allowed_tables,
    connection,
    delete_row,
    fetch_table,
    list_existing_tables,
    normalize_database,
    save_row,
)
from elevator_gateway.schemas import (
    CallRequest,
    ChatRequest,
    DataDeleteRequest,
    DataSaveRequest,
    LoginRequest,
    RegisterRequest,
)
from elevator_gateway.security import hash_password, verify_password

app = FastAPI(title="ElevatorAI Gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "gateway",
        "agent": service_available(agent_url("/health")),
        "vision": service_available(vision_url("/health")),
    }


@app.get("/status")
def status() -> Dict[str, Any]:
    return health()


@app.post("/chat")
def chat(req: ChatRequest):
    return request_json("POST", agent_url("/chat"), json=req.model_dump())


@app.post("/api/chat/customer")
def chat_customer(req: ChatRequest):
    return request_json("POST", agent_url("/api/chat/customer"), json=req.model_dump())


@app.post("/api/chat/maintenance")
def chat_maintenance(req: ChatRequest):
    return request_json("POST", agent_url("/api/chat/maintenance"), json=req.model_dump())


@app.get("/api/elevator/status")
def elevator_status():
    base = request_json("GET", agent_url("/api/elevator/status"))
    try:
        cv = request_json("GET", vision_url("/api/cv/status"))
        if isinstance(base, dict):
            base.update(
                {
                    "people_count": cv.get("people_count", base.get("people_count")),
                    "overload": cv.get("overload", base.get("overload")),
                    "camera_online": cv.get("online"),
                    "cv_available": True,
                }
            )
    except HTTPException:
        if isinstance(base, dict):
            base["cv_available"] = False
    return base


@app.post("/command")
def command(req: CallRequest):
    return request_json("POST", agent_url("/api/elevator/call"), json=req.model_dump())


@app.post("/api/elevator/call")
def elevator_call(req: CallRequest):
    return command(req)


@app.post("/api/sos")
def sos(payload: Dict[str, Any]):
    message = "SOS emergency request for elevator {0} at floor {1}".format(
        payload.get("elevator", "A"), payload.get("floor", "unknown")
    )
    body = {
        "message": message,
        "scope": "customer",
        "persona": "customer_assistant",
        "include_trace": False,
    }
    response = request_json("POST", agent_url("/chat"), json=body)
    return {"ok": True, "status": "accepted", "agent": response}


@app.get("/api/integration/cv/config")
def cv_config():
    return {
        "service_url": config.VISION_SERVICE_URL,
        "stream_proxy": "/api/integration/cv/stream-proxy",
    }


@app.get("/api/integration/cv/status")
def cv_status():
    raw = request_json("GET", vision_url("/api/cv/status"))
    return {
        "available": True,
        "camera_online": bool(raw.get("online")),
        "cam_id": raw.get("cam_id"),
        "fps": raw.get("fps", 0),
        "people_count": raw.get("people_count", 0),
        "backend": raw.get("backend"),
        "source": "vision_service",
        "stream_url": "/api/integration/cv/stream-proxy",
        "error": raw.get("error"),
        "overload": raw.get("overload", False),
        "raw": raw,
    }


@app.get("/api/integration/cv/events")
def cv_events(limit: int = Query(20, ge=1, le=200)):
    rows = request_json("GET", vision_url("/api/cv/events"), params={"limit": limit})
    items = []
    for idx, row in enumerate(rows if isinstance(rows, list) else []):
        event_type = str(row.get("event_type") or "UNKNOWN").upper()
        severity = "critical" if event_type == "FALL" else ("high" if event_type == "LYING" else "medium")
        items.append(
            {
                "id": row.get("event_id") or idx,
                "timestamp": str(row.get("event_ts") or ""),
                "cam_id": row.get("cam_id"),
                "type": event_type,
                "title": event_type.replace("_", " ").title(),
                "severity": severity,
                "confidence": row.get("confidence"),
                "people_count": row.get("people_count"),
                "person_name": row.get("person_name"),
                "track_id": row.get("track_id"),
                "posture": row.get("posture"),
                "raw": row,
            }
        )
    return {"items": items, "count": len(items)}


@app.get("/api/integration/cv/density")
def cv_density(days: int = Query(7, ge=1, le=30)):
    return request_json("GET", vision_url("/api/cv/density"), params={"days": days})


@app.get("/api/integration/cv/stream-url")
def cv_stream_url():
    return {
        "stream_url": "/api/integration/cv/stream-proxy",
        "upstream_stream_url": vision_url("/api/cv/stream"),
    }


@app.get("/api/integration/cv/stream-proxy")
def cv_stream_proxy():
    try:
        upstream = requests.get(
            vision_url("/api/cv/stream"),
            stream=True,
            timeout=(3, config.STREAM_TIMEOUT),
        )
        upstream.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"vision stream unavailable: {exc}") from exc
    return StreamingResponse(
        upstream.iter_content(chunk_size=8192),
        media_type=upstream.headers.get("content-type", "multipart/x-mixed-replace; boundary=frame"),
    )


@app.get("/api/integration/cv/unknown-candidates")
def unknown_candidates(limit: int = Query(10, ge=1, le=100)):
    rows = request_json(
        "GET",
        vision_url("/api/cv/events"),
        params={"limit": max(limit * 5, 20), "event_type": "UNKNOWN_PERSON"},
    )
    return {"items": rows[:limit] if isinstance(rows, list) else []}


@app.post("/api/integration/cv/register-face")
def register_face(payload: Dict[str, Any]):
    return request_json("POST", vision_url("/api/cv/register-face"), json=payload)


@app.post("/api/integration/users/register")
@app.post("/api/maintenance/register")
def user_register(req: RegisterRequest):
    employee_code = req.employee_code.strip().upper()
    with connection("elevator_llm") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO employees(
                    employee_code, full_name, full_name_norm, department,
                    status, password_hash, role, auth_source
                )
                VALUES (%s, %s, %s, %s, 'active', %s, %s, 'gateway')
                ON CONFLICT(employee_code) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    full_name_norm = EXCLUDED.full_name_norm,
                    department = EXCLUDED.department,
                    password_hash = EXCLUDED.password_hash,
                    role = EXCLUDED.role,
                    status = 'active',
                    updated_at = NOW()
                RETURNING employee_code, full_name, department, role, status
                """,
                (
                    employee_code,
                    req.full_name.strip(),
                    req.full_name.strip().lower(),
                    req.department.strip(),
                    hash_password(req.password),
                    req.role.strip(),
                ),
            )
            row = dict(cur.fetchone())
            conn.commit()
    return {"ok": True, "user": row}


@app.post("/api/integration/users/login")
@app.post("/api/maintenance/login")
def user_login(req: LoginRequest):
    with connection("elevator_llm") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT employee_code, full_name, department, role, status, password_hash
                FROM employees WHERE employee_code = %s LIMIT 1
                """,
                (req.employee_code.strip().upper(),),
            )
            row = cur.fetchone()
    if not row or row.get("status") != "active" or not verify_password(req.password, row.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="invalid credentials")
    user = {key: value for key, value in dict(row).items() if key != "password_hash"}
    return {"ok": True, "user": user}


@app.get("/api/integration/data/catalog")
def data_catalog():
    return {
        "databases": [
            {"key": "elevator_cv", "label": "CV analytics", "read_only": True},
            {"key": "elevator_llm", "label": "LLM / application", "read_only": False},
        ]
    }


@app.get("/api/integration/data/tables")
def data_tables(database: str):
    key = normalize_database(database)
    with connection(key) as conn:
        tables = list_existing_tables(conn, key)
    # Keep `tables` for the current frontend and `items` for compatibility with the legacy API.
    return {"database": key, "tables": tables, "items": [{"name": name} for name in tables]}


@app.get("/api/integration/data/table")
def data_table(
    database: str,
    table: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return fetch_table(database, table, limit, offset)


@app.post("/api/integration/data/row/save")
def data_save(req: DataSaveRequest):
    return {
        "ok": True,
        "database": normalize_database(req.database),
        "table": req.table,
        "result": save_row(req.database, req.table, req.row),
    }


@app.post("/api/integration/data/row/delete")
def data_delete(req: DataDeleteRequest):
    return {
        "ok": True,
        "database": normalize_database(req.database),
        "table": req.table,
        "result": delete_row(req.database, req.table, req.keys),
    }
