import os
import time
from typing import List

import requests

from backend.text_utils import normalize_vi

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")


class EmbeddingService:
    def _prepare_text(self, text: str, task: str) -> str:
        t = normalize_vi(text)
        if not t:
            return ""
        model_name = EMBED_MODEL.lower()
        if "nomic" in model_name:
            prefix = "search_query: " if task == "query" else "search_document: "
            return prefix + t
        return t

    def embed(self, text: str, task: str = "query", timeout_sec: int = 30, retries: int = 2) -> List[float]:
        prepared = self._prepare_text(text, task=task)
        if not prepared:
            return []

        url = f"{OLLAMA_HOST}/api/embeddings"
        payload = {"model": EMBED_MODEL, "prompt": prepared}

        last_err = None
        for _attempt in range(retries + 1):
            try:
                response = requests.post(url, json=payload, timeout=timeout_sec)
                response.raise_for_status()
                data = response.json()
                emb = data.get("embedding", [])
                return emb if isinstance(emb, list) else []
            except Exception as exc:
                last_err = exc
                time.sleep(0.6)

        print(f"[WARN] Embedding timeout/fail: {last_err}")
        return []
