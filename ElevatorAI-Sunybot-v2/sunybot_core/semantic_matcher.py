# sunybot_core/semantic_matcher.py
import json
import math
from typing import List, Dict, Optional
from sunybot_core.config.db_config import db
from sunybot_core.text_utils import normalize_vi

def cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))

class SemanticMatcher:
    def __init__(self):
        self.items: List[Dict] = []

    def load_from_db(self):
        conn = db.connect()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT i.intent_name, p.prompt_text, p.embedding, a.answer_text
                    FROM intents i
                    JOIN prompts p ON i.intent_id = p.intent_id
                    JOIN answers a ON i.intent_id = a.intent_id
                """)
                rows = cur.fetchall()

            items = []
            for r in rows:
                emb = None
                if r.get("embedding"):
                    try:
                        emb = json.loads(r["embedding"])
                    except Exception:
                        emb = None
                items.append({
                    "intent_name": r["intent_name"],
                    "prompt_text": r["prompt_text"],
                    "prompt_norm": normalize_vi(r["prompt_text"]),
                    "embedding": emb,
                    "answer_text": r["answer_text"],
                })
            self.items = items
        finally:
            conn.close()

    def keyword_fallback(self, user_norm: str) -> Optional[Dict]:
        for it in self.items:
            if it["prompt_norm"] == user_norm:
                return {**it, "confidence": 1.0}
        return None

    def match(self, user_embedding: List[float], user_text: str, threshold: float = 0.78) -> Optional[Dict]:
        user_norm = normalize_vi(user_text)

        hit = self.keyword_fallback(user_norm)
        if hit:
            return hit

        best = None
        best_score = -1.0
        for it in self.items:
            emb = it.get("embedding")
            if not emb:
                continue
            s = cosine(user_embedding, emb)
            if s > best_score:
                best_score = s
                best = it

        if best and best_score >= threshold:
            return {**best, "confidence": float(best_score)}

        return None

