import os
from typing import Dict, List, Optional, Tuple

from elevator_agent.text_utils import normalize_vi
from elevator_agent.db import db, to_pgvector


DOMAIN_KEYWORDS = {
    "maintenance_cv": (
        "camera", "cam", "cv", "te nga", "fall", "person_id", "person_name", "nhan dien", "giam sat",
    ),
    "elevator_status": (
        "thang may", "trang thai", "overload", "door", "floor", "tang", "cua",
    ),
    "guide": (
        "huong dan", "cach dung", "faq", "gioi thieu", "su dung",
    ),
}


class SemanticMatcher:
    def __init__(self):
        self.items: List[Dict] = []
        self.item_count: int = 0
        self.min_confidence = float(os.getenv("KB_MIN_CONFIDENCE", "0.72"))
        self.default_top_k = int(os.getenv("KB_TOP_K", "4"))
        self.vector_enabled = os.getenv("KB_ENABLE_VECTOR", "0").strip().lower() not in {"0", "false", "no"}

    def load_from_db(self):
        try:
            with db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) AS cnt FROM prompts")
                    row = cur.fetchone() or {}
                    self.item_count = int(row.get("cnt") or 0)
            self.items = [{"loaded": True, "count": self.item_count}] if self.item_count > 0 else []
        except Exception as exc:
            print(f"[WARN] SemanticMatcher degraded mode (load_from_db): {exc}")
            self.item_count = 0
            self.items = []

    def keyword_fallback(self, user_norm: str) -> Optional[Dict]:
        if not user_norm:
            return None
        try:
            with db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT i.intent_name,
                               p.prompt_id,
                               p.prompt_text,
                               p.prompt_norm,
                               a.answer_text,
                               p.meta,
                               1.0::float AS confidence,
                               'EXACT'::text AS retrieval_mode
                        FROM prompts p
                        JOIN intents i ON i.intent_id = p.intent_id
                        JOIN answers a ON a.intent_id = p.intent_id
                        WHERE p.prompt_norm = %s
                        ORDER BY a.answer_id ASC
                        LIMIT 1
                        """,
                        (user_norm,),
                    )
                    return cur.fetchone()
        except Exception as exc:
            print(f"[WARN] SemanticMatcher keyword_fallback skipped: {exc}")
            return None

    def _fts_search(self, conn, user_norm: str, top_k: int) -> List[Dict]:
        if not user_norm:
            return []
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT i.intent_name,
                       p.prompt_id,
                       p.prompt_text,
                       p.prompt_norm,
                       a.answer_text,
                       p.meta,
                       LEAST(1.0, ts_rank_cd(p.tsv, plainto_tsquery('simple', %s))::float) AS confidence,
                       'FTS'::text AS retrieval_mode
                FROM prompts p
                JOIN intents i ON i.intent_id = p.intent_id
                JOIN answers a ON a.intent_id = p.intent_id
                WHERE p.tsv @@ plainto_tsquery('simple', %s)
                ORDER BY ts_rank_cd(p.tsv, plainto_tsquery('simple', %s)) DESC,
                         p.prompt_id ASC
                LIMIT %s
                """,
                (user_norm, user_norm, user_norm, top_k),
            )
            return cur.fetchall() or []

    def _vector_search(self, conn, user_embedding: Optional[List[float]], top_k: int) -> List[Dict]:
        if not self.vector_enabled:
            return []
        if not user_embedding:
            return []
        vector_literal = to_pgvector(user_embedding)
        if not vector_literal:
            return []
        with conn.cursor() as cur:
            cur.execute("SET LOCAL ivfflat.probes = %s", (max(1, min(10, top_k * 2)),))
            cur.execute(
                """
                SELECT i.intent_name,
                       p.prompt_id,
                       p.prompt_text,
                       p.prompt_norm,
                       a.answer_text,
                       p.meta,
                       GREATEST(0.0, 1 - (p.embedding <=> %s::vector))::float AS confidence,
                       'VECTOR'::text AS retrieval_mode
                FROM prompts p
                JOIN intents i ON i.intent_id = p.intent_id
                JOIN answers a ON a.intent_id = p.intent_id
                WHERE p.embedding IS NOT NULL
                ORDER BY p.embedding <=> %s::vector
                LIMIT %s
                """,
                (vector_literal, vector_literal, top_k),
            )
            return cur.fetchall() or []

    def _infer_query_domain(self, user_norm: str) -> Optional[str]:
        for domain, keywords in DOMAIN_KEYWORDS.items():
            if any(keyword in user_norm for keyword in keywords):
                return domain
        return None

    def _meta_domain_scope(self, item: Dict) -> Tuple[Optional[str], Optional[str]]:
        meta = item.get("meta") or {}
        if not isinstance(meta, dict):
            return None, None
        domain = meta.get("domain") or meta.get("query_domain") or meta.get("group")
        scope = meta.get("scope") or meta.get("audience") or meta.get("role")
        return (str(domain).lower() if domain else None, str(scope).lower() if scope else None)

    def _rerank_results(self, items: List[Dict], user_norm: str, scope: Optional[str]) -> List[Dict]:
        requested_domain = self._infer_query_domain(user_norm)
        normalized_scope = (scope or "").strip().lower() or None
        reranked = []

        for item in items:
            score = float(item.get("confidence") or 0.0)
            domain, item_scope = self._meta_domain_scope(item)

            if requested_domain and domain == requested_domain:
                score = min(1.0, score + 0.08)
            if normalized_scope and item_scope == normalized_scope:
                score = min(1.0, score + 0.05)
            if requested_domain == "maintenance_cv" and item_scope == "customer":
                score = max(0.0, score - 0.08)

            reranked.append({**item, "confidence": score})

        return sorted(
            reranked,
            key=lambda item: (float(item.get("confidence") or 0.0), int(item.get("prompt_id") or 0)),
            reverse=True,
        )

    def search(
        self,
        user_text: str,
        user_embedding: Optional[List[float]] = None,
        top_k: Optional[int] = None,
        scope: Optional[str] = None,
    ) -> List[Dict]:
        user_norm = normalize_vi(user_text)
        top_k = max(1, int(top_k or self.default_top_k))
        if not user_norm and not user_embedding:
            return []

        exact_hit = self.keyword_fallback(user_norm)

        try:
            with db.connection() as conn:
                fts_hits = self._fts_search(conn, user_norm, top_k=top_k)
                vector_hits = self._vector_search(conn, user_embedding, top_k=top_k)
        except Exception as exc:
            print(f"[WARN] SemanticMatcher degraded mode (search): {exc}")
            return [exact_hit] if exact_hit else []

        merged: Dict[str, Dict] = {}

        def merge_item(item: Optional[Dict], rank: int, weight: float):
            if not item:
                return
            key = "{0}::{1}::{2}".format(item.get("intent_name"), item.get("prompt_id"), item.get("answer_text"))
            base_conf = float(item.get("confidence") or 0.0)
            fused_score = min(1.0, base_conf * weight + (0.12 / max(1, rank)))
            if key not in merged:
                merged[key] = {
                    **item,
                    "confidence": fused_score,
                    "retrieval_mode": item.get("retrieval_mode", ""),
                }
                return

            prev = merged[key]
            prev_modes = [m for m in str(prev.get("retrieval_mode") or "").split("+") if m]
            new_mode = item.get("retrieval_mode", "")
            if new_mode and new_mode not in prev_modes:
                prev_modes.append(new_mode)

            prev_conf = float(prev.get("confidence") or 0.0)
            merged[key] = {
                **prev,
                **item,
                "confidence": min(1.0, max(prev_conf, fused_score) + (0.05 if len(prev_modes) > 1 else 0.0)),
                "retrieval_mode": "+".join(sorted(prev_modes)),
            }

        merge_item(exact_hit, rank=1, weight=1.0)
        for idx, row in enumerate(fts_hits, start=1):
            merge_item(row, rank=idx, weight=0.95)
        for idx, row in enumerate(vector_hits, start=1):
            merge_item(row, rank=idx, weight=0.90)

        results = self._rerank_results(list(merged.values()), user_norm=user_norm, scope=scope)
        return results[:top_k]

    def match(
        self,
        user_embedding: List[float],
        user_text: str,
        threshold: Optional[float] = None,
        scope: Optional[str] = None,
    ) -> Optional[Dict]:
        target = float(threshold if threshold is not None else self.min_confidence)
        results = self.search(user_text=user_text, user_embedding=user_embedding, top_k=1, scope=scope)
        if results and float(results[0].get("confidence") or 0.0) >= target:
            return results[0]
        return None
