# backend/chatbot_engine.py
from typing import Dict, Any, Optional
from backend.employee_service import (
    is_employee_code, find_employee_by_code,
    find_employee_by_name, format_employee_answer
)
from backend.semantic_matcher import SemanticMatcher
from backend.embedding_service import EmbeddingService
from backend.ollama_service import OllamaService, FALLBACK_TEXT
from config.db_config import db

class ChatbotEngine:
    def __init__(self):
        self.matcher = SemanticMatcher()
        self.matcher.load_from_db()
        self.embedder = EmbeddingService()
        self.ollama = OllamaService()

    def reload_knowledge(self):
        self.matcher.load_from_db()

    def log_chat(self, question: str, intent_name: str, confidence: float, source: str, answer: str):
        conn = db.connect()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO chat_logs(question, intent_name, confidence, source, answer_preview)
                    VALUES (%s, %s, %s, %s, %s)
                """, (question, intent_name, confidence, source, (answer or "")[:250]))
        finally:
            conn.close()

    def handle(self, user_text: str) -> Dict[str, Any]:
        q = (user_text or "").strip()
        if not q:
            return {"answer": "Bạn vui lòng nhập câu hỏi.", "source": "SYSTEM"}

        # 1) Employee by code
        if is_employee_code(q):
            emp = find_employee_by_code(q)
            if emp:
                ans = format_employee_answer(emp)
                self.log_chat(q, "employee_lookup", 1.0, "EMPLOYEE", ans)
                return {"answer": ans, "source": "EMPLOYEE", "confidence": 1.0}
            else:
                ans = "Không tìm thấy nhân viên với mã này."
                self.log_chat(q, "employee_lookup", 1.0, "EMPLOYEE", ans)
                return {"answer": ans, "source": "EMPLOYEE", "confidence": 1.0}

        # 2) Employee by name (heuristic: nếu có >=2 từ thì thử)
        if len(q.split()) >= 2:
            emp = find_employee_by_name(q)
            if emp:
                ans = format_employee_answer(emp)
                self.log_chat(q, "employee_lookup", 1.0, "EMPLOYEE", ans)
                return {"answer": ans, "source": "EMPLOYEE", "confidence": 1.0}

        # 3) DB semantic match
        user_emb = self.embedder.embed(q)
        hit = self.matcher.match(user_emb, q, threshold=0.78)
        if hit:
            ans = hit["answer_text"]
            intent_name = hit["intent_name"]
            conf = float(hit.get("confidence", 0.0))
            self.log_chat(q, intent_name, conf, "DB_PROMPT", ans)
            return {"answer": ans, "source": "DB_PROMPT", "intent": intent_name, "confidence": conf}

        # 4) LLM fallback
        llm_ans = self.ollama.chat(q, timeout_sec=60) #dat thoi gian cho chatbot
        if llm_ans == FALLBACK_TEXT:
            self.log_chat(q, "fallback", 0.0, "FALLBACK", llm_ans)
            return {"answer": llm_ans, "source": "FALLBACK", "confidence": 0.0}

        self.log_chat(q, "llm", 0.0, "LLM", llm_ans)
        return {"answer": llm_ans, "source": "LLM", "confidence": 0.0}

