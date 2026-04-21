import json
import os
from datetime import datetime

import config
import pg_store

JSON_LOG_PATH = "events_log.json"


class EventLogger:
    def __init__(self, json_path=JSON_LOG_PATH, json_enabled=None, pg_enabled=None):
        self.json_path = json_path
        self.json_enabled = config.ENABLE_JSON_LOG if json_enabled is None else bool(json_enabled)
        self.pg_enabled = config.ENABLE_EVENT_DB if pg_enabled is None else bool(pg_enabled)
        self.pg_conn = None

        if self.json_enabled:
            self._init_json()
        self._init_postgres()

    @classmethod
    def from_config(cls):
        return cls(
            json_path=JSON_LOG_PATH,
            json_enabled=config.ENABLE_JSON_LOG,
            pg_enabled=config.ENABLE_EVENT_DB,
        )

    def _init_json(self):
        if not os.path.exists(self.json_path):
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def _init_postgres(self):
        if not self.pg_enabled:
            print("[LOGGER] PostgreSQL logging dang tat.")
            return

        self.pg_conn = pg_store.get_connection()
        if self.pg_conn is None:
            print("[LOGGER] Khong mo duoc ket noi PostgreSQL, se fallback JSON.")
            return

        try:
            with self.pg_conn.cursor() as cur:
                cur.execute("SELECT 1;")
            print("[LOGGER] PostgreSQL connected.")
        except Exception as ex:
            print("[LOGGER] PostgreSQL ping loi:", repr(ex))
            self._close_pg()

    def _close_pg(self):
        try:
            if self.pg_conn is not None:
                self.pg_conn.close()
        except Exception:
            pass
        self.pg_conn = None

    def _ensure_pg(self):
        if self.pg_conn is not None and getattr(self.pg_conn, "closed", 1) == 0:
            return True
        self._init_postgres()
        return self.pg_conn is not None and getattr(self.pg_conn, "closed", 1) == 0

    def _build_event(self, event_type, cam_id, person_id=None, person_name="Unknown", extra=None):
        now = datetime.now()
        extra = extra or {}
        return {
            "event_type": event_type,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "weekday": now.strftime("%A").upper(),
            "cam_id": str(cam_id),
            "person_id": person_id,
            "person_name": person_name,
            "extra": extra,
        }

    def log_event(self, event_type, cam_id, person_id=None, person_name="Unknown", extra=None):
        event = self._build_event(
            event_type=event_type,
            cam_id=cam_id,
            person_id=person_id,
            person_name=person_name,
            extra=extra,
        )

        if self.json_enabled:
            self._write_json(event)
        if self.pg_enabled:
            self._write_postgres_event(event)

        print(
            f"[LOG] {event['timestamp']} | {event_type} | "
            f"cam_id={cam_id} | person_id={person_id} | name={person_name}"
        )

    def log_occupancy_sample(self, cam_id, people_count, unknown_count=0, lying_count=0, fall_count=0, extra=None):
        now = datetime.now()
        record = {
            "sample_ts": now,
            "cam_id": str(cam_id),
            "people_count": int(people_count),
            "unknown_count": int(unknown_count),
            "lying_count": int(lying_count),
            "fall_count": int(fall_count),
            "extra": extra or {},
        }

        if self.json_enabled:
            self._write_json({
                "event_type": "OCCUPANCY_SAMPLE",
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "weekday": now.strftime("%A").upper(),
                "cam_id": str(cam_id),
                "person_id": None,
                "person_name": "SYSTEM",
                "extra": {
                    "people_count": int(people_count),
                    "unknown_count": int(unknown_count),
                    "lying_count": int(lying_count),
                    "fall_count": int(fall_count),
                    **(extra or {}),
                },
            })
        if self.pg_enabled:
            self._write_postgres_sample(record)

    def _write_json(self, event):
        try:
            data = []
            if os.path.exists(self.json_path):
                with open(self.json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

            data.append(event)

            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as ex:
            print("[LOGGER] Loi ghi JSON:", ex)

    def _write_postgres_event(self, event):
        if not self._ensure_pg():
            return
        try:
            extra = event.get("extra") or {}
            with self.pg_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO camera_events (
                        event_type, event_ts, event_date, event_time, weekday,
                        cam_id, person_id, person_name, people_count, posture,
                        holding, track_id, confidence, extra
                    )
                    VALUES (
                        %s, %s::timestamp, %s::date, %s::time, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s::jsonb
                    );
                    """,
                    (
                        event["event_type"],
                        event["timestamp"],
                        event["date"],
                        event["time"],
                        event["weekday"],
                        event["cam_id"],
                        event.get("person_id"),
                        event.get("person_name"),
                        extra.get("people_count"),
                        extra.get("posture"),
                        extra.get("holding"),
                        extra.get("track_id"),
                        extra.get("confidence"),
                        json.dumps(extra, ensure_ascii=False),
                    ),
                )
        except Exception as ex:
            print("[LOGGER] Loi ghi PostgreSQL camera_events:", repr(ex))
            self._close_pg()

    def _write_postgres_sample(self, record):
        if not self._ensure_pg():
            return
        try:
            with self.pg_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO camera_occupancy_samples (
                        sample_ts, cam_id, people_count, unknown_count,
                        lying_count, fall_count, extra
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb);
                    """,
                    (
                        record["sample_ts"],
                        record["cam_id"],
                        record["people_count"],
                        record["unknown_count"],
                        record["lying_count"],
                        record["fall_count"],
                        json.dumps(record.get("extra") or {}, ensure_ascii=False),
                    ),
                )
        except Exception as ex:
            print("[LOGGER] Loi ghi PostgreSQL camera_occupancy_samples:", repr(ex))
            self._close_pg()
