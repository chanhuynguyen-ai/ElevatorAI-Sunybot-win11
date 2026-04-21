import os
import re
from typing import Any, Dict, List, Optional

import psycopg
from psycopg.rows import dict_row

DB_HOST = os.getenv("DB_HOST", os.getenv("PGHOST", "127.0.0.1"))
DB_PORT = int(os.getenv("DB_PORT", os.getenv("PGPORT", "5432")))
DB_USER = os.getenv("DB_USER", os.getenv("PGUSER", "elevator_ai"))
DB_PASSWORD = os.getenv("DB_PASSWORD", os.getenv("PGPASSWORD", "elevator123"))
CV_DB_NAME = os.getenv("ELEVATOR_CV_DB_NAME", os.getenv("DB_CV_NAME", "elevator_cv"))

EVENT_TYPE_MAP = {
    "fall": "FALL",
    "te nga": "FALL",
    "lying": "LYING",
    "nam": "LYING",
    "nằm": "LYING",
    "crowd": "CROWD",
    "dong nguoi": "CROWD",
    "đông người": "CROWD",
    "bottle": "BOTTLE",
    "chai nhua": "BOTTLE",
    "chai nhựa": "BOTTLE",
    "unknown": "UNKNOWN_PERSON",
    "nguoi la": "UNKNOWN_PERSON",
    "người lạ": "UNKNOWN_PERSON",
    "chua gan nhan": "UNKNOWN_PERSON",
    "chưa gán nhãn": "UNKNOWN_PERSON",
}

EVENT_VI = {
    "FALL": "té ngã",
    "LYING": "nằm bất thường",
    "CROWD": "đông người",
    "BOTTLE": "chai nhựa/vật thể lạ",
    "UNKNOWN_PERSON": "người chưa gán nhãn",
}


class CVQueryService(object):
    def _conn(self):
        return psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=CV_DB_NAME,
            row_factory=dict_row,
        )

    def infer_event_type(self, normalized_text: str) -> Optional[str]:
        for key, value in EVENT_TYPE_MAP.items():
            if key in normalized_text:
                return value
        return None

    def infer_hours(self, normalized_text: str) -> Optional[int]:
        m = re.search(r"(\d+)\s*(gio|giờ|hour|hours)", normalized_text)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
        return None

    def event_label(self, event_type: Optional[str]) -> str:
        if not event_type:
            return "sự kiện"
        return EVENT_VI.get(event_type, event_type)

    def get_latest_status(self) -> Dict[str, Any]:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT sample_ts, cam_id, people_count, unknown_count, lying_count, fall_count, extra
                    FROM camera_occupancy_samples
                    ORDER BY sample_ts DESC
                    LIMIT 1
                    """
                )
                return cur.fetchone() or {}

    def recent_events(self, limit: int = 5, event_type: Optional[str] = None, hours: Optional[int] = None) -> List[Dict[str, Any]]:
        sql = """
            SELECT event_ts, cam_id, event_type, track_id, person_id, person_name,
                   posture, people_count, confidence, snapshot_path, extra
            FROM camera_events
            WHERE 1=1
        """
        params = []
        if event_type:
            sql += " AND event_type = %s"
            params.append(event_type)
        if hours is not None:
            sql += " AND event_ts >= NOW() - (%s || ' hours')::interval"
            params.append(str(hours))
        sql += " ORDER BY event_ts DESC LIMIT %s"
        params.append(limit)
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall() or []

    def count_events(self, event_type: Optional[str] = None, hours: Optional[int] = None, today_only: bool = False) -> int:
        sql = "SELECT COUNT(*) AS cnt FROM camera_events WHERE 1=1"
        params = []
        if event_type:
            sql += " AND event_type = %s"
            params.append(event_type)
        if today_only:
            sql += " AND event_ts::date = CURRENT_DATE"
        elif hours is not None:
            sql += " AND event_ts >= NOW() - (%s || ' hours')::interval"
            params.append(str(hours))
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone() or {}
                return int(row.get("cnt") or 0)

    def peak_hour_today(self) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXTRACT(HOUR FROM sample_ts)::int AS hour_of_day,
                           MAX(people_count) AS peak_people,
                           AVG(people_count)::float AS avg_people
                    FROM camera_occupancy_samples
                    WHERE sample_ts::date = CURRENT_DATE
                    GROUP BY EXTRACT(HOUR FROM sample_ts)
                    ORDER BY peak_people DESC, avg_people DESC
                    LIMIT 1
                    """
                )
                return cur.fetchone()

    def summarize_today(self) -> Dict[str, Any]:
        latest = self.get_latest_status()
        counts = {}
        for et in ["FALL", "LYING", "CROWD", "BOTTLE", "UNKNOWN_PERSON"]:
            counts[et] = self.count_events(event_type=et, today_only=True)
        return {"latest_status": latest, "counts_today": counts}
