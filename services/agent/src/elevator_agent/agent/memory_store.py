import re
from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional


class ConversationMemoryStore:
    EMPLOYEE_CODE_RE = re.compile(r"\b[A-Z]{1,4}\d{2,8}\b")
    ELEVATOR_RE = re.compile(r"(?:thang may|thang|elevator)\s*(\d+)", re.IGNORECASE)
    FLOOR_RE = re.compile(r"(?:tang|floor)\s*(\d+)", re.IGNORECASE)

    def __init__(self, max_turns: int = 12, summary_turns: int = 6, summary_item_chars: int = 140):
        self.max_turns = max_turns
        self.summary_turns = summary_turns
        self.summary_item_chars = summary_item_chars
        self._store: Dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=self.max_turns))

    def add_turn(self, session_id: str, role: str, content: str, metadata: Optional[dict] = None):
        if not session_id or not content:
            return
        text = " ".join(str(content).split())
        if not text:
            return
        self._store[session_id].append(
            {
                "role": role,
                "content": text,
                "metadata": metadata or {},
            }
        )

    def clear(self, session_id: Optional[str]):
        if session_id and session_id in self._store:
            del self._store[session_id]

    def get_history(self, session_id: Optional[str]) -> List[dict]:
        if not session_id:
            return []
        return list(self._store.get(session_id, []))

    def get_slot_context(self, session_id: Optional[str]) -> Dict[str, object]:
        history = self.get_history(session_id)
        slots: Dict[str, object] = {
            "last_employee_code": None,
            "last_elevator_id": None,
            "last_floor": None,
            "last_target_floor": None,
            "last_intent": None,
        }

        for item in reversed(history):
            meta = item.get("metadata") or {}
            if slots["last_intent"] is None and meta.get("intent"):
                slots["last_intent"] = meta.get("intent")
            if slots["last_elevator_id"] is None and meta.get("elevator_id") is not None:
                slots["last_elevator_id"] = meta.get("elevator_id")
            if slots["last_floor"] is None and meta.get("from_floor") is not None:
                slots["last_floor"] = meta.get("from_floor")
            if slots["last_target_floor"] is None and meta.get("target_floor") is not None:
                slots["last_target_floor"] = meta.get("target_floor")
            if slots["last_employee_code"] is None and meta.get("employee_code"):
                slots["last_employee_code"] = meta.get("employee_code")

            text = item.get("content", "")
            if slots["last_employee_code"] is None:
                match = self.EMPLOYEE_CODE_RE.search(text or "")
                if match:
                    slots["last_employee_code"] = match.group(0).upper()
            if slots["last_elevator_id"] is None:
                match = self.ELEVATOR_RE.search(text or "")
                if match:
                    slots["last_elevator_id"] = int(match.group(1))
            if slots["last_floor"] is None or slots["last_target_floor"] is None:
                floors = [int(x) for x in self.FLOOR_RE.findall(text or "")]
                if floors and slots["last_floor"] is None:
                    slots["last_floor"] = floors[0]
                if len(floors) > 1 and slots["last_target_floor"] is None:
                    slots["last_target_floor"] = floors[1]

            if all(value is not None for key, value in slots.items() if key != "last_target_floor"):
                break

        return slots

    def build_summary(self, session_id: Optional[str]) -> str:
        history = self.get_history(session_id)
        if not history:
            return ""

        items = []
        for item in history[-self.summary_turns:]:
            role = "U" if item.get("role") == "user" else "A"
            content = item.get("content", "")
            content = content[: self.summary_item_chars].rstrip()
            items.append("{0}: {1}".format(role, content))
        return " | ".join(items)
