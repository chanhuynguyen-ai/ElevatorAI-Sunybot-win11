from psycopg2.extras import Json, RealDictCursor
import psycopg2

from app import config



def get_connection():
    return psycopg2.connect(
        host=config.PG_HOST,
        port=config.PG_PORT,
        dbname=config.PG_DATABASE,
        user=config.PG_USER,
        password=config.PG_PASSWORD,
    )



def init_schema():
    with get_connection() as conn, conn.cursor() as cur:
        with open("schema_cv.sql", "r", encoding="utf-8") as f:
            cur.execute(f.read())
        conn.commit()



def insert_event(payload: dict):
    sql = """
    INSERT INTO camera_events
    (event_ts, cam_id, event_type, track_id, person_id, person_name, bbox, posture,
     people_count, confidence, snapshot_path, extra)
    VALUES (NOW(), %(cam_id)s, %(event_type)s, %(track_id)s, %(person_id)s, %(person_name)s,
            %(bbox)s, %(posture)s, %(people_count)s, %(confidence)s, %(snapshot_path)s, %(extra)s)
    """
    row = {
        "cam_id": payload.get("cam_id"),
        "event_type": payload.get("event_type"),
        "track_id": payload.get("track_id"),
        "person_id": payload.get("person_id"),
        "person_name": payload.get("person_name"),
        "bbox": Json(payload.get("bbox")),
        "posture": payload.get("posture"),
        "people_count": payload.get("people_count"),
        "confidence": payload.get("confidence"),
        "snapshot_path": payload.get("snapshot_path"),
        "extra": Json(payload.get("extra", {})),
    }
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, row)
        conn.commit()



def insert_occupancy(payload: dict):
    sql = """
    INSERT INTO camera_occupancy_samples
    (sample_ts, cam_id, people_count, unknown_count, lying_count, fall_count, extra)
    VALUES (NOW(), %(cam_id)s, %(people_count)s, %(unknown_count)s, %(lying_count)s, %(fall_count)s, %(extra)s)
    """
    row = {
        "cam_id": payload.get("cam_id"),
        "people_count": payload.get("people_count", 0),
        "unknown_count": payload.get("unknown_count", 0),
        "lying_count": payload.get("lying_count", 0),
        "fall_count": payload.get("fall_count", 0),
        "extra": Json(payload.get("extra", {})),
    }
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, row)
        conn.commit()



def fetch_events(limit=100, cam_id=None, event_type=None):
    q = "SELECT * FROM camera_events WHERE 1=1"
    p = []
    if cam_id:
        q += " AND cam_id=%s"
        p.append(cam_id)
    if event_type:
        q += " AND event_type=%s"
        p.append(event_type)
    q += " ORDER BY event_ts DESC LIMIT %s"
    p.append(limit)
    with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q, p)
        return cur.fetchall()



def fetch_density(cam_id, start_ts, end_ts):
    q = """
    SELECT date_trunc('day', sample_ts) AS day,
           AVG(people_count)::float AS avg_people,
           MAX(people_count) AS peak_people
    FROM camera_occupancy_samples
    WHERE cam_id=%s AND sample_ts >= %s AND sample_ts < %s
    GROUP BY 1
    ORDER BY 1
    """
    with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q, [cam_id, start_ts, end_ts])
        return cur.fetchall()



def load_face_embeddings():
    q = """
    SELECT p.person_id, p.full_name, f.embedding
    FROM face_embeddings f
    JOIN person_registry p ON p.person_id = f.person_id
    WHERE p.is_active = TRUE
    """
    with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(q)
        return cur.fetchall()
