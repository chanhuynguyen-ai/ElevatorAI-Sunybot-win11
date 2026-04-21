import os
import time

from backend.embedding_service import EmbeddingService
from backend.text_utils import normalize_vi
from config.db_config import db, to_pgvector

EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
BATCH_LIMIT = int(os.getenv("EMBED_BATCH_LIMIT", "0"))
FORCE_REBUILD = os.getenv("EMBED_FORCE_REBUILD", "0") == "1"
EMBED_TEXT_MODE = os.getenv("EMBED_TEXT_MODE", "prompt")  # prompt|norm
SLEEP_MS = int(os.getenv("EMBED_SLEEP_MS", "0"))
ANALYZE_AFTER = os.getenv("EMBED_ANALYZE_AFTER", "1") == "1"


def pick_embed_text(prompt_text: str, prompt_norm: str) -> str:
    if EMBED_TEXT_MODE == "norm":
        return prompt_norm or normalize_vi(prompt_text or "")
    return prompt_text or ""


def main():
    es = EmbeddingService()
    total = 0
    updated = 0
    skipped = 0
    failed = 0
    started = time.time()

    with db.connection() as conn:
        with conn.cursor() as cur:
            sql = (
                "SELECT prompt_id, prompt_text, prompt_norm, embedding_model, embedding "
                "FROM prompts WHERE is_active = TRUE ORDER BY prompt_id"
            )
            if BATCH_LIMIT > 0:
                sql += " LIMIT %s"
                cur.execute(sql, (BATCH_LIMIT,))
            else:
                cur.execute(sql)
            rows = cur.fetchall() or []

        total = len(rows)
        print("[INFO] total prompts={0} embed_model={1} mode={2}".format(total, EMBED_MODEL, EMBED_TEXT_MODE))

        for idx, row in enumerate(rows, 1):
            pid = row["prompt_id"]
            prompt_text = row.get("prompt_text") or ""
            prompt_norm = row.get("prompt_norm") or normalize_vi(prompt_text)
            existing_model = row.get("embedding_model")
            existing_embedding = row.get("embedding")

            if not FORCE_REBUILD and existing_embedding is not None and existing_model == EMBED_MODEL and prompt_norm:
                skipped += 1
                print("[SKIP] {0}/{1} prompt_id={2}".format(idx, total, pid))
                continue

            embed_text = pick_embed_text(prompt_text, prompt_norm)
            emb = es.embed(embed_text, task="document")
            if not emb:
                failed += 1
                print("[WARN] {0}/{1} prompt_id={2} khong tao duoc embedding".format(idx, total, pid))
                continue

            if len(emb) != EMBED_DIM:
                raise ValueError(
                    "Embedding dimension khong khop: prompt_id={0}, got={1}, expected={2}. "
                    "Hay dong bo schema_pg_step1.sql va EMBED_DIM cho model {3}.".format(
                        pid, len(emb), EMBED_DIM, EMBED_MODEL
                    )
                )

            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE prompts
                    SET prompt_norm = %s,
                        embedding_model = %s,
                        embedding = %s::vector,
                        updated_at = NOW()
                    WHERE prompt_id = %s
                    """,
                    (prompt_norm, EMBED_MODEL, to_pgvector(emb), pid),
                )
            updated += 1
            print("[OK] {0}/{1} prompt_id={2} dim={3}".format(idx, total, pid, len(emb)))

            if SLEEP_MS > 0:
                time.sleep(SLEEP_MS / 1000.0)

        if ANALYZE_AFTER:
            with conn.cursor() as cur:
                cur.execute("ANALYZE prompts")
            print("[INFO] ANALYZE prompts done")

    elapsed = round(time.time() - started, 2)
    print("[DONE] total={0} updated={1} skipped={2} failed={3} elapsed_s={4}".format(
        total, updated, skipped, failed, elapsed
    ))


if __name__ == "__main__":
    main()
