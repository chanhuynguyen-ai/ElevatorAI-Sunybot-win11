# suny_core/semantic_matcher.py
import json
import math
from typing import List, Dict, Optional

from config.db_config import db
from backend.text_utils import normalize_vi

# ====== Native (.so) ưu tiên nếu có ======
try:
    import sunycore_native as _native
    _HAS_NATIVE = True
except Exception:
    _native = None
    _HAS_NATIVE = False


def cosine(a: List[float], b: List[float]) -> float:
    """Fallback python cosine (khi không có .so)."""
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


def match_with_native(
    user_norm: str,
    user_emb: list,
    items: list,
    threshold: float = 0.78
) -> Optional[Dict]:
    """
    Nếu có sunycore_native.so thì dùng C++ để match nhanh & khó xem code.
    items: list dict có:
      - prompt_norm: str
      - embedding: list[float] hoặc None
    Return: dict best item + confidence hoặc None
    """
    if not _HAS_NATIVE:
        return None

    items_norm = [it.get("prompt_norm") or "" for it in items]
    items_emb = []
    for it in items:
        emb = it.get("embedding") or []
        items_emb.append([float(x) for x in emb] if emb else [])

    best_i, best_s = _native.match_index(
        user_norm=user_norm,
        user_emb=[float(x) for x in (user_emb or [])],
        items_prompt_norm=items_norm,
        items_emb=items_emb,
        threshold=float(threshold),
    )

    if int(best_i) >= 0:
        best = items[int(best_i)]
        # trả về bản copy để tránh sửa self.items trực tiếp
        return {**best, "confidence": float(best_s)}

    return None


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
        # match exact normalized text trước (python fallback)
        for it in self.items:
            if it["prompt_norm"] == user_norm:
                return {**it, "confidence": 1.0}
        return None

    def match(self, user_embedding: List[float], user_text: str, threshold: float = 0.78) -> Optional[Dict]:
        user_norm = normalize_vi(user_text)

        # 1) Nếu có native .so -> ưu tiên native (bao gồm cả exact match + cosine)
        hit = match_with_native(user_norm, user_embedding, self.items, threshold)
        if hit:
            return hit

        # 2) Không có native -> fallback python như cũ
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

