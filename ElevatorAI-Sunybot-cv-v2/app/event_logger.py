import traceback

from app import db


class EventLogger:
    def __init__(self, enabled=True):
        self.enabled = enabled

    @classmethod
    def from_config(cls):
        return cls(enabled=True)

    def log_event(self, **kwargs):
        if not self.enabled:
            return
        try:
            db.insert_event(kwargs)
        except Exception:
            traceback.print_exc()

    def log_occupancy(self, **kwargs):
        if not self.enabled:
            return
        try:
            db.insert_occupancy(kwargs)
        except Exception:
            traceback.print_exc()
