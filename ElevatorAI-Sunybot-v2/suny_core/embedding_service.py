# backend/embedding_service.py
import os
import time
import requests
from backend.text_utils import normalize_vi

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

class EmbeddingService:
    def embed(self, text: str, timeout_sec: int = 30, retries: int = 2):
        t = normalize_vi(text)
        if not t:
            return []

        url = f"{OLLAMA_HOST}/api/embeddings"
        payload = {"model": EMBED_MODEL, "prompt": t}

        last_err = None
        for attempt in range(retries + 1):
            try:
                r = requests.post(url, json=payload, timeout=timeout_sec)
                r.raise_for_status()
                data = r.json()
                emb = data.get("embedding", [])
                return emb if isinstance(emb, list) else []
            except Exception as e:
                last_err = e
                time.sleep(0.6)

        # Không crash build_embeddings, chỉ trả [] để hệ thống vẫn chạy được
        print(f"[WARN] Embedding timeout/fail: {last_err}")
        return []

