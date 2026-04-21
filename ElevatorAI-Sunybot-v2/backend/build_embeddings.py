import os

from backend.embedding_service import EmbeddingService
from backend.text_utils import normalize_vi
from config.db_config import db, to_pgvector

EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
BATCH_LIMIT = int(os.getenv("EMBED_BATCH_LIMIT", "0"))
FORCE_REBUILD = os.getenv("EMBED_FORCE_REBUILD", "0") == "1"


def main():
    es = EmbeddingService()
    total = 0
    updated = 0
    skipped = 0

    with db.connection() as conn:
        with conn.cursor() as cur:
            sql = (
                "SELECT prompt_id, prompt_text, embedding_model, embedding "
                "FROM prompts ORDER BY prompt_id"
            )
            if BATCH_LIMIT > 0:
                sql += " LIMIT %s"
                cur.execute(sql, (BATCH_LIMIT,))
            else:
                cur.execute(sql)
            rows = cur.fetchall() or []

        total = len(rows)
        for row in rows:
            pid = row["prompt_id"]
            text = row.get("prompt_text") or ""
            norm = normalize_vi(text)
            existing_model = row.get("embedding_model")
            existing_embedding = row.get("embedding")

            if not FORCE_REBUILD and existing_embedding is not None and existing_model == EMBED_MODEL:
                skipped += 1
                print("[SKIP] prompt_id={0} đã có embedding model={1}".format(pid, EMBED_MODEL))
                continue

            emb = es.embed(text, task="document")
            if not emb:
                print("[WARN] prompt_id={0} không tạo được embedding".format(pid))
                continue

            if len(emb) != EMBED_DIM:
                raise ValueError(
                    "Embedding dimension không khớp: prompt_id={0}, got={1}, expected={2}. "
                    "Hãy chỉnh EMBED_DIM hoặc schema_pg.sql cho đúng model {3}.".format(
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
                    (norm, EMBED_MODEL, to_pgvector(emb), pid),
                )
            updated += 1
            print("[OK] Updated prompt_id={0} dim={1}".format(pid, len(emb)))

    print("[DONE] total={0} updated={1} skipped={2}".format(total, updated, skipped))


if __name__ == "__main__":
    main()
