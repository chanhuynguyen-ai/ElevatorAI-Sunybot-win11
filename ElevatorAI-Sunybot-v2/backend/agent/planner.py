import re
from typing import Dict, List, Optional

from backend.employee_service import is_employee_code
from backend.schemas import AgentPlan, ToolCall
from backend.text_utils import normalize_vi


class Planner:
    STATUS_KEYWORDS = [
        "trang thai hien tai", "thang dang o tang", "dang o tang may", "o tang may",
        "cua dang mo", "cua dang dong", "cua dang mo hay dong",
        "hien tai co bao nhieu nguoi", "qua tai khong", "tinh trang qua tai",
    ]
    CALL_KEYWORDS = [
        "goi thang", "call elevator", "goi cabin", "len tang", "xuong tang", "di tang", "dua toi tang",
    ]
    EMPLOYEE_HINTS = [
        "nhan vien", "ma nhan vien", "email", "so dien thoai", "phong ban", "thong tin nhan vien", "ho so",
    ]
    KNOWLEDGE_HINTS = [
        "thang may", "elevator", "sos", "bao tri", "ky thuat", "cabin", "cam bien", "qua tai",
        "van hanh", "an toan", "su co", "mat dien", "cuu ho", "cau tao", "nguyen ly",
        "la gi", "cach su dung", "huong dan", "phai lam gi", "nen lam gi",
    ]
    SMALLTALK_HINTS = [
        "xin chao", "chao", "hello", "hi", "cam on", "tam biet", "ban la ai", "ban lam duoc gi",
    ]
    DOMAIN_HINTS = [
        "thang may", "elevator", "tang", "cabin", "bao tri", "an toan", "sos", "qua tai", "cuu ho",
        "cam bien", "cua", "ket trong thang", "mac ket",
    ]
    ELEVATOR_RE = re.compile(r"(?:thang may|thang|elevator)\s*(\d+)", re.IGNORECASE)
    EMPLOYEE_CODE_RE = re.compile(r"\b[A-Z]{1,4}\d{2,8}\b")
    FLOOR_RE = re.compile(r"(?:tang|floor)\s*(\d+)", re.IGNORECASE)

    def create_plan(self, user_text: str, history: Optional[List[dict]] = None) -> AgentPlan:
        history = history or []
        norm = normalize_vi(user_text or "")
        history_text = self._build_history_text(history)
        ctx = self._context_from_history(history)

        if is_employee_code(user_text):
            return AgentPlan(
                intent="employee_lookup",
                plan=["Tra cứu nhân viên theo mã định danh."],
                tool_calls=[ToolCall(tool_name="employee_lookup", args={"query": user_text.strip()}, reason="Mã nhân viên hợp lệ")],
                confidence=0.99,
            )

        if self._looks_like_employee_query(norm, user_text, ctx):
            query = self._expand_employee_query(user_text, ctx)
            return AgentPlan(
                intent="employee_lookup",
                plan=["Tra cứu nhân viên theo mã, tên hoặc mô tả."],
                tool_calls=[ToolCall(tool_name="employee_lookup", args={"query": query}, reason="Câu hỏi có dấu hiệu tra cứu nhân viên")],
                confidence=0.93 if self._has_any(norm, self.EMPLOYEE_HINTS) else 0.88,
            )

        if self._is_call_request(norm):
            args = self._parse_call_args(user_text, ctx)
            return AgentPlan(
                intent="call_elevator",
                plan=["Phân tích yêu cầu gọi thang.", "Thực thi tool gọi thang ở chế độ mô phỏng an toàn."],
                tool_calls=[ToolCall(tool_name="call_elevator", args=args, reason="Người dùng muốn gọi thang hoặc di chuyển cabin")],
                confidence=0.92,
            )

        if self._is_status_request(norm, history_text):
            args = self._parse_status_args(user_text, ctx)
            return AgentPlan(
                intent="elevator_status",
                plan=["Lấy trạng thái thang máy gần nhất."],
                tool_calls=[ToolCall(tool_name="get_elevator_status", args=args, reason="Câu hỏi về trạng thái thang máy")],
                confidence=0.93,
            )

        if self._has_any(norm, self.KNOWLEDGE_HINTS):
            return AgentPlan(
                intent="knowledge_lookup",
                plan=["Tìm kiếm tri thức liên quan trong knowledge base.", "Nếu có ngữ cảnh phù hợp thì dùng LLM diễn giải bám sát nguồn."],
                tool_calls=[ToolCall(tool_name="kb_search", args={"query": user_text, "top_k": 4}, reason="Câu hỏi nằm trong domain thang máy hoặc vận hành")],
                confidence=0.84,
            )

        if self._has_any(norm, self.SMALLTALK_HINTS):
            return AgentPlan(
                intent="general_llm",
                plan=["Trả lời giao tiếp ngắn gọn, không mở rộng ngoài domain trợ lý."],
                tool_calls=[ToolCall(tool_name="general_llm", args={"query": user_text, "intent_hint": "smalltalk"}, reason="Câu hỏi giao tiếp cơ bản")],
                confidence=0.72,
            )

        if not self._has_any(norm, self.DOMAIN_HINTS):
            return AgentPlan(
                intent="out_of_domain",
                plan=["Từ chối lịch sự vì câu hỏi nằm ngoài phạm vi hệ thống thang máy."],
                tool_calls=[ToolCall(tool_name="general_llm", args={"query": user_text, "intent_hint": "out_of_domain"}, reason="Câu hỏi ngoài domain")],
                confidence=0.95,
            )

        return AgentPlan(
            intent="general_llm",
            plan=["Dùng LLM trả lời thận trọng và từ chối nếu ngoài phạm vi."],
            tool_calls=[ToolCall(tool_name="general_llm", args={"query": user_text, "intent_hint": "general"}, reason="Không khớp tool chuyên biệt")],
            confidence=0.58,
        )

    def _build_history_text(self, history: List[dict]) -> str:
        return " ".join(item.get("content", "") for item in history[-4:])

    def _context_from_history(self, history: List[dict]) -> Dict[str, object]:
        ctx: Dict[str, object] = {"employee_code": None, "elevator_id": None, "from_floor": None, "target_floor": None}
        for item in reversed(history):
            text = item.get("content", "")
            meta = item.get("metadata") or {}
            if ctx["employee_code"] is None:
                if meta.get("employee_code"):
                    ctx["employee_code"] = meta.get("employee_code")
                else:
                    m = self.EMPLOYEE_CODE_RE.search(text)
                    if m:
                        ctx["employee_code"] = m.group(0).upper()
            if ctx["elevator_id"] is None:
                if meta.get("elevator_id") is not None:
                    ctx["elevator_id"] = meta.get("elevator_id")
                else:
                    m = self.ELEVATOR_RE.search(text)
                    if m:
                        ctx["elevator_id"] = int(m.group(1))
            if ctx["from_floor"] is None or ctx["target_floor"] is None:
                floors = [int(x) for x in self.FLOOR_RE.findall(text)]
                if floors and ctx["from_floor"] is None:
                    ctx["from_floor"] = floors[0]
                if len(floors) > 1 and ctx["target_floor"] is None:
                    ctx["target_floor"] = floors[1]
        return ctx

    def _has_any(self, text: str, keywords: List[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _looks_like_employee_query(self, norm: str, original: str, ctx: Dict[str, object]) -> bool:
        if self._has_any(norm, self.EMPLOYEE_HINTS):
            return True
        if ctx.get("employee_code") and any(token in norm for token in ["nguoi nay", "ban nay", "nhan su nay"]):
            return True
        if len((original or "").split()) >= 2 and any(token in norm for token in ["truong phong", "ky su", "nhan su"]):
            return True
        return False

    def _expand_employee_query(self, user_text: str, ctx: Dict[str, object]) -> str:
        stripped = (user_text or "").strip()
        if stripped:
            return stripped
        if ctx.get("employee_code"):
            return str(ctx["employee_code"])
        return stripped

    def _is_status_request(self, norm: str, history_text: str) -> bool:
        if self._has_any(norm, self.STATUS_KEYWORDS):
            return True
        if "thang may" in norm and any(token in norm for token in ["dang o dau", "dang o tang", "tang may", "cua dang mo", "cua dang dong", "bao nhieu nguoi"]):
            return True
        history_norm = normalize_vi(history_text)
        if history_norm and any(token in norm for token in ["con sao", "the con", "bay gio"]):
            return "thang may" in history_norm or "elevator" in history_norm
        return False

    def _is_call_request(self, norm: str) -> bool:
        if self._has_any(norm, self.CALL_KEYWORDS):
            return True
        return "goi" in norm and "thang" in norm

    def _parse_status_args(self, user_text: str, ctx: Dict[str, object]) -> Dict[str, int]:
        m = self.ELEVATOR_RE.search(user_text or "")
        elevator_id = int(m.group(1)) if m else int(ctx.get("elevator_id") or 1)
        return {"elevator_id": elevator_id}

    def _parse_call_args(self, user_text: str, ctx: Dict[str, object]) -> Dict[str, object]:
        text = user_text or ""
        norm = normalize_vi(text)
        m = self.ELEVATOR_RE.search(text)
        elevator_id = int(m.group(1)) if m else int(ctx.get("elevator_id") or 1)

        floors = [int(x) for x in self.FLOOR_RE.findall(text)]
        from_floor = None
        target_floor = None

        from_match = re.search(r"(?:tu|tai)\s*(?:tang|floor)\s*(\d+)", norm)
        to_match = re.search(r"(?:toi|den|len|xuong)\s*(?:tang|floor)\s*(\d+)", norm)
        if from_match:
            from_floor = int(from_match.group(1))
        if to_match:
            target_floor = int(to_match.group(1))

        if len(floors) >= 2:
            from_floor = from_floor if from_floor is not None else floors[0]
            target_floor = target_floor if target_floor is not None else floors[1]
        elif len(floors) == 1 and target_floor is None and ("len tang" in norm or "xuong tang" in norm or "toi tang" in norm or "den tang" in norm):
            target_floor = floors[0]
        elif len(floors) == 1 and from_floor is None:
            from_floor = floors[0]

        if from_floor is None:
            from_floor = ctx.get("from_floor")
        if target_floor is None:
            target_floor = ctx.get("target_floor")

        direction = "up"
        if "xuong" in norm:
            direction = "down"
        elif "len" in norm:
            direction = "up"
        elif from_floor is not None and target_floor is not None:
            direction = "up" if int(target_floor) >= int(from_floor) else "down"

        return {
            "elevator_id": elevator_id,
            "from_floor": int(from_floor) if from_floor is not None else None,
            "target_floor": int(target_floor) if target_floor is not None else None,
            "direction": direction,
        }
