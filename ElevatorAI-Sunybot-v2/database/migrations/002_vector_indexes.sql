-- Chạy file này SAU KHI đã seed dữ liệu và build embeddings.
-- IVFFlat hợp với Jetson Nano hơn HNSW ở giai đoạn đầu vì build nhẹ hơn và dùng ít RAM hơn.

DROP INDEX IF EXISTS idx_prompts_embedding_ivfflat;
CREATE INDEX idx_prompts_embedding_ivfflat
ON prompts USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 10);
