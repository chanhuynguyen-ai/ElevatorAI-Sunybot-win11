from __future__ import print_function
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from elevator_vision import config

try:
    import psycopg2
    from psycopg2.extras import Json, RealDictCursor
except Exception:  # optional in hardware-free/demo mode
    psycopg2 = None
    Json = None
    RealDictCursor = None

_LOCK = RLock()
_EVENTS = []
_OCCUPANCY = []
_PEOPLE = {}
_EMBEDDINGS = {}


def postgres_enabled():
    return bool(config.CV_DB_ENABLED and psycopg2 is not None)


def get_connection():
    if not postgres_enabled():
        return None
    return psycopg2.connect(
        host=config.PG_HOST,
        port=config.PG_PORT,
        dbname=config.PG_DATABASE,
        user=config.PG_USER,
        password=config.PG_PASSWORD,
        connect_timeout=5,
    )


def init_schema():
    if not postgres_enabled():
        return True
    schema_path = Path(__file__).resolve().parents[2] / "database" / "schema.sql"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(schema_path.read_text(encoding="utf-8"))
        conn.commit()
    return True


def insert_event(payload):
    if not postgres_enabled():
        with _LOCK:
            row = dict(payload)
            row.setdefault("event_id", len(_EVENTS) + 1)
            row.setdefault("event_ts", datetime.now(timezone.utc).isoformat())
            _EVENTS.append(row)
        return row
    sql = """
    INSERT INTO camera_events
    (event_ts, cam_id, event_type, track_id, person_id, person_name, bbox, posture,
     people_count, confidence, snapshot_path, extra)
    VALUES (NOW(), %(cam_id)s, %(event_type)s, %(track_id)s, %(person_id)s, %(person_name)s,
            %(bbox)s, %(posture)s, %(people_count)s, %(confidence)s, %(snapshot_path)s, %(extra)s)
    """
    row = dict(payload)
    row["bbox"] = Json(payload.get("bbox"))
    row["extra"] = Json(payload.get("extra", {}))
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, row)
        conn.commit()


def insert_occupancy(payload):
    if not postgres_enabled():
        with _LOCK:
            row = dict(payload)
            row.setdefault("sample_id", len(_OCCUPANCY) + 1)
            row.setdefault("sample_ts", datetime.now(timezone.utc).isoformat())
            _OCCUPANCY.append(row)
        return row
    sql = """
    INSERT INTO camera_occupancy_samples
    (sample_ts, cam_id, people_count, unknown_count, sitting_count, lying_count, fall_count, extra)
    VALUES (NOW(), %(cam_id)s, %(people_count)s, %(unknown_count)s, %(sitting_count)s, %(lying_count)s, %(fall_count)s, %(extra)s)
    """
    row = dict(payload)
    row["extra"] = Json(payload.get("extra", {}))
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, row)
        conn.commit()


def fetch_events(limit=100, cam_id=None, event_type=None):
    if not postgres_enabled():
        with _LOCK:
            rows = list(reversed(_EVENTS))
        if cam_id:
            rows = [r for r in rows if r.get("cam_id") == cam_id]
        if event_type:
            rows = [r for r in rows if r.get("event_type") == event_type]
        return rows[:limit]
    q = "SELECT * FROM camera_events WHERE 1=1"
    p = []
    if cam_id:
        q += " AND cam_id=%s"; p.append(cam_id)
    if event_type:
        q += " AND event_type=%s"; p.append(event_type)
    q += " ORDER BY event_ts DESC LIMIT %s"; p.append(limit)
    with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q, p)
        return cur.fetchall()


def fetch_event_by_id(event_id):
    if not postgres_enabled():
        with _LOCK:
            for row in _EVENTS:
                if int(row.get("event_id") or 0) == int(event_id):
                    return dict(row)
        return None
    with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM camera_events WHERE event_id = %s LIMIT 1", [event_id])
        return cur.fetchone()


def fetch_density(cam_id, start_ts, end_ts):
    if not postgres_enabled():
        # Demo fallback intentionally simple: expose the latest samples, grouped by UTC date.
        buckets = {}
        with _LOCK:
            rows = list(_OCCUPANCY)
        for row in rows:
            if row.get("cam_id") != cam_id:
                continue
            ts = str(row.get("sample_ts") or "")[:10]
            if not ts:
                continue
            buckets.setdefault(ts, []).append(int(row.get("people_count") or 0))
        return [
            {"day": day, "avg_people": float(sum(vals)) / max(len(vals), 1), "peak_people": max(vals)}
            for day, vals in sorted(buckets.items())
        ]
    q = """
    SELECT date_trunc('day', sample_ts) AS day,
           AVG(people_count)::float AS avg_people,
           MAX(people_count) AS peak_people
    FROM camera_occupancy_samples
    WHERE cam_id=%s AND sample_ts >= %s AND sample_ts < %s
    GROUP BY 1 ORDER BY 1
    """
    with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q, [cam_id, start_ts, end_ts])
        return cur.fetchall()


def load_face_embeddings():
    if not postgres_enabled():
        with _LOCK:
            out = []
            for pid, emb in _EMBEDDINGS.items():
                person = _PEOPLE.get(pid, {})
                out.append({"person_id": pid, "full_name": person.get("full_name", ""), "embedding": emb})
            return out
    q = """
    SELECT p.person_id, p.full_name, f.embedding
    FROM face_embeddings f JOIN person_registry p ON p.person_id = f.person_id
    WHERE p.is_active = TRUE ORDER BY f.created_at DESC
    """
    with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q)
        return cur.fetchall()


def upsert_person(person_code, full_name, department=None):
    if not postgres_enabled():
        with _LOCK:
            existing = next((pid for pid, row in _PEOPLE.items() if row.get("person_code") == person_code), None)
            pid = existing or (max(_PEOPLE.keys() or [0]) + 1)
            _PEOPLE[pid] = {"person_id": pid, "person_code": person_code, "full_name": full_name,
                            "department": department, "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()}
            return dict(_PEOPLE[pid])
    sql = """
    INSERT INTO person_registry(person_code, full_name, department, is_active)
    VALUES (%s, %s, %s, TRUE)
    ON CONFLICT(person_code) DO UPDATE SET full_name=EXCLUDED.full_name, department=EXCLUDED.department, is_active=TRUE
    RETURNING person_id, person_code, full_name, department, is_active, created_at
    """
    with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, [person_code, full_name, department]); row = cur.fetchone(); conn.commit(); return row


def get_person_by_code(person_code):
    if not postgres_enabled():
        with _LOCK:
            for row in _PEOPLE.values():
                if row.get("person_code") == person_code:
                    return dict(row)
        return None
    with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT person_id, person_code, full_name, department, is_active, created_at FROM person_registry WHERE person_code=%s LIMIT 1", [person_code])
        return cur.fetchone()


def replace_face_embedding(person_id, embedding):
    emb_list = [float(x) for x in embedding]
    if not postgres_enabled():
        with _LOCK:
            _EMBEDDINGS[int(person_id)] = emb_list
            return {"embedding_id": int(person_id), "person_id": int(person_id), "created_at": datetime.now(timezone.utc).isoformat()}
    with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("DELETE FROM face_embeddings WHERE person_id=%s", [person_id])
        cur.execute("INSERT INTO face_embeddings(person_id, embedding) VALUES (%s,%s) RETURNING embedding_id,person_id,created_at", [person_id, emb_list])
        row=cur.fetchone(); conn.commit(); return row
