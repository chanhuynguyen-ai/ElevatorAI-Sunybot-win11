import json
import re
from typing import Any, Dict, Optional

from backend.agent import AgentRuntime
from backend.agent.tool_registry import ToolRegistry
from backend.embedding_service import EmbeddingService
from backend.ollama_service import FALLBACK_TEXT, OllamaService
from backend.semantic_matcher import SemanticMatcher
from backend.text_utils import normalize_vi
from config.db_config import db


CUSTOMER_CV_SENSITIVE_KEYWORDS = (
    "camera", " cam ", "cv", "person_id", "person_name", "cam_id",
    "nhan dien", "giam sat", "mat do", "density", "peak hour", "peak",
    "camera event", "su kien camera", "lich su camera", "history camera",
)
MAINTENANCE_CV_KEYWORDS = (
    "camera", "cv", "te nga", "fall", "lying", "bottle", "crowd",
    "mat do", "density", "peak hour", "peak", "nhan dien", "cam_id",
    "su kien", "event", "canh bao", "alert", "warning", "uu tien",
    "noi bat", "hom nay", "bao nhieu lan", "gan nhat", "overload", "qua tai",
    "loi", "xu ly", "priority",
)
SAFETY_FAQ_KEYWORDS = (
    "te nga nen lam gi", "khi te nga", "mac ket", "ket trong thang",
    "sos dung de lam gi", "de an toan", "qua tai thi lam gi", "nen lam gi",
)
STATUS_KEYWORDS = (
    "trang thai hien tai", "dang o tang", "o tang may", "cua dang mo",
    "cua dang dong", "hien tai co bao nhieu nguoi", "tinh trang qua tai",
    "qua tai hien tai", "thang may 1 dang o dau", "thang may dang o dau",
)
GREETING_PATTERNS = (
    r"^\s*(hi|hello|xin chao|chao|helo|hey)\b",
    r"^\s*(cam on|thanks|thank you)\b",
)


class ChatbotEngine:
    def __init__(
        self,
        matcher: Optional[SemanticMatcher] = None,
        embedder: Optional[EmbeddingService] = None,
        ollama: Optional[OllamaService] = None,
        tool_registry: Optional[ToolRegistry] = None,
        agent: Optional[AgentRuntime] = None,
    ):
        self.matcher = matcher or SemanticMatcher()
        self.matcher.load_from_db()
        self.embedder = embedder or EmbeddingService()
        self.ollama = ollama or OllamaService()
        self.tool_registry = tool_registry or ToolRegistry(
            matcher=self.matcher,
            embedder=self.embedder,
            ollama=self.ollama,
        )
        self.agent = agent or AgentRuntime(tool_registry=self.tool_registry)

    def reload_knowledge(self) -> Dict[str, Any]:
        self.matcher.load_from_db()
        return {"ok": True, "matcher_items": self.matcher.item_count}

    def _normalize_scope(self, scope: Optional[str], persona: Optional[str]) -> str:
        raw = (scope or persona or "customer").strip().lower()
        if raw in {"maintenance", "maint", "console", "operator", "admin", "maintenance_console"}:
            return "maintenance"
        return "customer"

    def _default_persona(self, scope: str, persona: Optional[str]) -> str:
        if persona:
            return str(persona).strip().lower()
        return "maintenance_console" if scope == "maintenance" else "customer_assistant"

    def _normalize_text(self, text: str) -> str:
        return normalize_vi(text or "")

    def _is_greeting(self, normalized_text: str) -> bool:
        return any(re.search(pattern, normalized_text) for pattern in GREETING_PATTERNS)

    def _looks_like_customer_cv_sensitive(self, normalized_text: str) -> bool:
        return any(keyword in normalized_text for keyword in CUSTOMER_CV_SENSITIVE_KEYWORDS)

    def _looks_like_maintenance_cv_query(self, normalized_text: str) -> bool:
        return any(keyword in normalized_text for keyword in MAINTENANCE_CV_KEYWORDS)

    def _looks_like_safety_faq(self, normalized_text: str) -> bool:
        return any(keyword in normalized_text for keyword in SAFETY_FAQ_KEYWORDS)

    def _looks_like_status_query(self, normalized_text: str) -> bool:
        if any(keyword in normalized_text for keyword in STATUS_KEYWORDS):
            return True
        followups = ("the con", "bay gio", "hien gio", "luc nay")
        if any(token in normalized_text for token in followups):
            return "thang may" in normalized_text or "thang" in normalized_text or "elevator" in normalized_text
        return False

    def _make_result(
        self,
        answer: str,
        source: str,
        *,
        intent: str,
        confidence: float,
        session_id: Optional[str],
        scope: str,
        persona: str,
        query_type: str,
        tool_trace: Optional[list] = None,
        citations: Optional[list] = None,
        memory_summary: Optional[str] = None,
        status: str = "ok",
        requires_human: bool = False,
    ) -> Dict[str, Any]:
        return {
            "answer": answer,
            "source": source,
            "intent": intent,
            "confidence": confidence,
            "session_id": session_id,
            "scope": scope,
            "persona": persona,
            "query_type": query_type,
            "tool_trace": tool_trace or [],
            "citations": citations or [],
            "memory_summary": memory_summary,
            "status": status,
            "requires_human": requires_human,
        }

    def _handle_empty_message(self, session_id: Optional[str], scope: str, persona: str) -> Dict[str, Any]:
        return self._make_result(
            "Bạn hãy nhập câu hỏi rõ hơn. Ví dụ: trạng thái thang máy hiện tại hoặc hôm nay có bao nhiêu lần té ngã.",
            "RULE",
            intent="empty_input",
            confidence=1.0,
            session_id=session_id,
            scope=scope,
            persona=persona,
            query_type="guardrail",
        )

    def _handle_greeting(self, session_id: Optional[str], scope: str, persona: str) -> Dict[str, Any]:
        prefix = "Sunybot bảo trì" if scope == "maintenance" else "Sunybot"
        return self._make_result(
            f"Xin chào, tôi là {prefix}. Bạn cứ hỏi tự nhiên nhé, tôi có thể hỗ trợ về trạng thái thang máy, dữ liệu camera và hướng xử lý kỹ thuật.",
            "RULE",
            intent="greeting",
            confidence=0.99,
            session_id=session_id,
            scope=scope,
            persona=persona,
            query_type="small_talk",
        )

    def _handle_scope_guard(self, session_id: Optional[str], scope: str, persona: str) -> Dict[str, Any]:
        return self._make_result(
            "Kênh chat khách hàng không được truy cập dữ liệu camera hoặc dữ liệu nhận diện người. Bạn hãy dùng LLM Console bảo trì nếu cần hỏi sự kiện CV và cảnh báo an toàn.",
            "POLICY",
            intent="cv_access_denied",
            confidence=1.0,
            session_id=session_id,
            scope=scope,
            persona=persona,
            query_type="policy_guard",
        )

    def _build_maintenance_context_blocks(self, tool_result: Dict[str, Any]) -> list:
        blocks = [
            "Nguồn chính: database elevator_cv và các tool truy xuất bảo trì.",
            "Yêu cầu trả lời cho kỹ thuật viên: tự nhiên, mượt, ngắn gọn, có ưu tiên xử lý, không bịa số liệu.",
        ]
        message = (tool_result.get("message") or "").strip()
        if message:
            blocks.append("Kết quả tool CV: {0}".format(message))

        for key in ("data", "events", "status_data"):
            value = tool_result.get(key)
            if value:
                try:
                    blocks.append(
                        "Dữ liệu cấu trúc {0}: {1}".format(
                            key, json.dumps(value, ensure_ascii=False, default=str)[:1800]
                        )
                    )
                except Exception:
                    blocks.append("Dữ liệu cấu trúc {0}: {1}".format(key, str(value)[:1800]))

        citations = tool_result.get("citations") or []
        if citations:
            preview = []
            for item in citations[:5]:
                src = item.get("source") or "unknown"
                content = item.get("content") or ""
                preview.append("[{0}] {1}".format(src, content[:240]))
            blocks.append("Trích dẫn tham chiếu:\n" + "\n".join(preview))
        return blocks

    def _build_answer_rewrite_blocks(self, answer: str, result: Dict[str, Any]) -> list:
        blocks = [
            "Câu trả lời kỹ thuật gốc cần diễn đạt lại tự nhiên hơn nhưng vẫn giữ nguyên ý và số liệu.",
            "Không được thêm dữ liệu mới nếu dữ liệu gốc không có.",
            "Nếu có cảnh báo, nêu mức ưu tiên xử lý trước rồi mới nói chi tiết.",
            "Câu trả lời gốc: {0}".format((answer or "").strip()),
        ]
        for key in ("tool_trace", "citations"):
            value = result.get(key)
            if value:
                try:
                    blocks.append("{0}: {1}".format(key, json.dumps(value, ensure_ascii=False, default=str)[:1400]))
                except Exception:
                    blocks.append("{0}: {1}".format(key, str(value)[:1400]))
        return blocks

    def _rewrite_answer_with_llm(self, user_text: str, answer: str, result: Dict[str, Any], persona: str, intent_hint: str) -> str:
        prompt = (
            "Hãy diễn đạt lại câu trả lời kỹ thuật sau thành giọng hội thoại tự nhiên, mượt và dễ hiểu hơn. "
            "Giữ nguyên số liệu, mức cảnh báo và ý chính. "
            "Nếu câu trả lời đã ổn thì chỉ làm nó mềm mại hơn một chút, không thay đổi nội dung thực tế.\n"
            f"Câu hỏi gốc: {user_text}"
        )
        rewritten = self.ollama.generate(
            user_text=prompt,
            context_blocks=self._build_answer_rewrite_blocks(answer, result),
            memory_summary="chưa có",
            intent_hint=intent_hint,
            persona=persona,
        )
        if rewritten == FALLBACK_TEXT or not rewritten.strip():
            return (answer or "").strip()
        return rewritten.strip()

    def _handle_status_shortcut(self, user_text: str, session_id: Optional[str], scope: str, persona: str) -> Optional[Dict[str, Any]]:
        try:
            payload = self.get_elevator_status(elevator_id=1) or {}
            status = payload.get("status_data") if isinstance(payload, dict) else {}
        except Exception:
            return None

        if not isinstance(status, dict) or not status:
            return None

        raw_answer = (
            "Trạng thái hiện tại của thang máy: tầng {floor}, hướng {direction}, cửa {door}, "
            "số người {people_count}, quá tải {overload}, trạng thái hệ thống {status}."
        ).format(
            floor=status.get("floor", "?"),
            direction=status.get("direction", "UNKNOWN"),
            door=status.get("door", "UNKNOWN"),
            people_count=status.get("people_count", "?"),
            overload="có" if status.get("overload") else "không",
            status=status.get("status", "UNKNOWN"),
        )

        result = self._make_result(
            raw_answer,
            "TOOL:ELEVATOR_STATUS",
            intent="elevator_status",
            confidence=0.92,
            session_id=session_id,
            scope=scope,
            persona=persona,
            query_type="status",
            tool_trace=[{"tool": "get_elevator_status", "ok": True, "elevator_id": 1, "mode": status.get("mode")}],
            citations=payload.get("citations", []),
        )

        if scope == "maintenance":
            result["answer"] = self._rewrite_answer_with_llm(
                user_text=user_text,
                answer=raw_answer,
                result=result,
                persona=persona,
                intent_hint="maintenance_status",
            )
            result["source"] = "TOOL:ELEVATOR_STATUS+LLM"
        return result

    def _llm_rewrite_maintenance_answer(self, user_text: str, tool_result: Dict[str, Any], persona: str) -> str:
        context_blocks = self._build_maintenance_context_blocks(tool_result)
        prompt = (
            "Hãy diễn đạt lại kết quả dữ liệu CV cho kỹ thuật viên theo kiểu nói chuyện tự nhiên, dễ hiểu và có cảm giác hỗ trợ thật. "
            "Nếu có cảnh báo nghiêm trọng thì nêu mức ưu tiên xử lý trước. "
            "Nếu thiếu dữ liệu thì nói rõ thiếu dữ liệu nào. "
            "Kết thúc bằng một gợi ý ngắn về bước kiểm tra tiếp theo khi phù hợp.\n"
            f"Câu hỏi gốc: {user_text}"
        )
        answer = self.ollama.generate(
            user_text=prompt,
            context_blocks=context_blocks,
            memory_summary="chưa có",
            intent_hint="maintenance_cv",
            persona=persona,
        )
        if answer == FALLBACK_TEXT or not answer.strip():
            return (tool_result.get("message") or "Không có dữ liệu CV phù hợp.").strip()
        return answer.strip()

    def _handle_maintenance_cv_query(
        self,
        user_text: str,
        session_id: Optional[str],
        scope: str,
        persona: str,
    ) -> Dict[str, Any]:
        tool_result = self.tool_registry.tool_answer_cv_query(user_text)
        rewritten = self._llm_rewrite_maintenance_answer(user_text, tool_result, persona)
        return self._make_result(
            rewritten,
            "TOOL:CV_DB+LLM" if tool_result.get("ok") else f"TOOL:{tool_result.get('source', 'CV_DB')}",
            intent="cv_query",
            confidence=0.95 if tool_result.get("ok") else 0.45,
            session_id=session_id,
            scope=scope,
            persona=persona,
            query_type="maintenance_cv",
            tool_trace=[
                {
                    "tool": "answer_cv_query",
                    "ok": bool(tool_result.get("ok")),
                    "source": tool_result.get("source"),
                    "preview": (tool_result.get("message") or "")[:180],
                },
                {
                    "tool": "maintenance_cv_rewrite",
                    "ok": True,
                    "source": "OLLAMA",
                    "preview": rewritten[:180],
                },
            ],
            citations=tool_result.get("citations", []),
        )

    def log_chat(self, result: Dict[str, Any], question: str) -> bool:
        trace_json = json.dumps(result.get("tool_trace", []), ensure_ascii=False)
        payload = (
            result.get("session_id"),
            question,
            result.get("intent"),
            float(result.get("confidence") or 0.0),
            result.get("source"),
            (result.get("answer") or "")[:250],
            trace_json,
            int(len(result.get("tool_trace", []))),
        )
        try:
            with db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chat_logs(
                            session_id, question, intent_name, confidence, source,
                            answer_preview, tool_trace_json, tool_count
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                        """,
                        payload,
                    )
            return True
        except Exception:
            return False

    def handle(
        self,
        user_text: str,
        session_id: Optional[str] = None,
        scope: Optional[str] = None,
        persona: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_text = self._normalize_text(user_text)
        normalized_scope = self._normalize_scope(scope, persona)
        normalized_persona = self._default_persona(normalized_scope, persona)

        if not normalized_text:
            result = self._handle_empty_message(session_id, normalized_scope, normalized_persona)
            self.log_chat(result, user_text)
            return result

        if self._is_greeting(normalized_text):
            result = self._handle_greeting(session_id, normalized_scope, normalized_persona)
            self.log_chat(result, user_text)
            return result

        if normalized_scope == "customer" and self._looks_like_customer_cv_sensitive(normalized_text) and not self._looks_like_safety_faq(normalized_text):
            result = self._handle_scope_guard(session_id, normalized_scope, normalized_persona)
            self.log_chat(result, user_text)
            return result

        if self._looks_like_status_query(normalized_text):
            status_result = self._handle_status_shortcut(user_text, session_id, normalized_scope, normalized_persona)
            if status_result:
                self.log_chat(status_result, user_text)
                return status_result

        if normalized_scope == "maintenance" and self._looks_like_maintenance_cv_query(normalized_text):
            result = self._handle_maintenance_cv_query(user_text, session_id, normalized_scope, normalized_persona)
            self.log_chat(result, user_text)
            return result

        result = self.agent.run(
            user_text,
            session_id=session_id,
            scope=normalized_scope,
            persona=normalized_persona,
        )
        result["session_id"] = result.get("session_id") or session_id
        result["scope"] = normalized_scope
        result["persona"] = normalized_persona
        result["query_type"] = result.get("query_type") or "general"
        result.setdefault("tool_trace", [])
        result.setdefault("citations", [])

        if normalized_scope == "maintenance" and result.get("answer") and result.get("source") not in {"RULE", "POLICY"}:
            result["answer"] = self._rewrite_answer_with_llm(
                user_text=user_text,
                answer=result.get("answer", ""),
                result=result,
                persona=normalized_persona,
                intent_hint="maintenance_general",
            )
            if "+LLM" not in str(result.get("source")):
                result["source"] = "{0}+LLM".format(result.get("source") or "AGENT")

        self.log_chat(result, user_text)
        return result

    def handle_request(self, req) -> Dict[str, Any]:
        if isinstance(req, dict):
            message = req.get("message") or req.get("question") or ""
            session_id = req.get("session_id")
            scope = req.get("scope") or req.get("role")
            persona = req.get("persona")
        else:
            message = getattr(req, "message", "") or getattr(req, "question", "")
            session_id = getattr(req, "session_id", None)
            scope = getattr(req, "scope", None) or getattr(req, "role", None)
            persona = getattr(req, "persona", None)
        return self.handle(message, session_id=session_id, scope=scope, persona=persona)

    def get_elevator_status(self, elevator_id: int = 1) -> Dict[str, Any]:
        return self.tool_registry.tool_get_elevator_status(elevator_id=elevator_id)

    def call_elevator(
        self,
        elevator_id: int = 1,
        from_floor: Optional[int] = None,
        target_floor: Optional[int] = None,
        direction: str = "up",
    ) -> Dict[str, Any]:
        return self.tool_registry.tool_call_elevator(
            elevator_id=elevator_id,
            from_floor=from_floor,
            target_floor=target_floor,
            direction=direction,
        )

    def healthcheck(self) -> Dict[str, Any]:
        db_info = db.test_connection_details()
        ollama_info = self.ollama.healthcheck_details()
        return {
            "db_ok": db_info.get("ok", False),
            "db_backend": "postgresql",
            "db_info": db_info,
            "matcher_items": self.matcher.item_count,
            "ollama_ok": ollama_info.get("ok", False),
            "ollama_info": ollama_info,
            "tools": self.tool_registry.available_tools(),
            "engine_mode": "router_plus_agent",
            "scopes": ["customer", "maintenance"],
            "cv_db_available": self.tool_registry.cv_db_available,
        }