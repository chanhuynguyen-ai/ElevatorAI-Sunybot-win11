import re
from typing import Dict
from backend.text_utils import normalize_vi


class SafetyGuardrails:
    EMERGENCY_PATTERNS = [
        r"\bsos\b",
        r"\bkhan cap\b",
        r"\bcuu ho\b",
        r"\btoi dang mac ket\b",
        r"\bdang mac ket\b",
        r"\bket trong thang\b",
        r"\bco khoi\b",
        r"\bchay no\b",
        r"\bbi ngat\b",
    ]
    GUIDANCE_MARKERS = {
        "neu", "nếu", "phai lam gi", "phải làm gì", "nen lam gi", "nên làm gì",
        "la gi", "là gì", "huong dan", "hướng dẫn", "cach xu ly", "cách xử lý",
    }
    INJECTION_KEYWORDS = {
        "ignore previous", "system prompt", "developer prompt", "reveal prompt", "bypass", "sudo", "rm -rf"
    }
    ALLOWED_TOOLS = {
        "employee_lookup",
        "kb_search",
        "get_elevator_status",
        "call_elevator",
        "get_cv_status",
        "get_recent_cv_events",
        "get_today_fall_count",
        "get_peak_hour",
        "get_daily_density",
        "get_latest_person_seen",
        "answer_cv_query",
        "general_llm",
    }

    def normalize(self, text: str) -> str:
        return normalize_vi(text)

    def _looks_like_guidance_question(self, norm: str) -> bool:
        return any(token in norm for token in self.GUIDANCE_MARKERS)

    def _looks_like_direct_emergency(self, norm: str) -> bool:
        return any(re.search(pattern, norm) for pattern in self.EMERGENCY_PATTERNS)

    def precheck(self, text: str) -> Dict[str, str]:
        norm = self.normalize(text)
        if any(token in norm for token in self.INJECTION_KEYWORDS):
            return {
                "status": "blocked",
                "answer": "Yêu cầu này không hợp lệ. Sunybot chỉ hỗ trợ các tác vụ liên quan đến thang máy, bảo trì và thông tin nội bộ an toàn.",
                "intent": "blocked_request",
            }
        if self._looks_like_direct_emergency(norm) and not self._looks_like_guidance_question(norm):
            return {
                "status": "emergency",
                "answer": "Tôi đã chuyển sang chế độ hỗ trợ khẩn cấp. Hãy giữ bình tĩnh, nhấn nút SOS, không tự cạy cửa và chờ bộ phận kỹ thuật phản hồi.",
                "intent": "emergency_support",
            }
        return {"status": "ok", "intent": "unknown"}

    def allow_tool(self, tool_name: str) -> bool:
        return tool_name in self.ALLOWED_TOOLS
