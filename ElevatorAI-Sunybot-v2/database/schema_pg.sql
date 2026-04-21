-- PostgreSQL schema for Sunybot Mode A (Jetson Nano)
-- Lưu ý:
-- 1) File này dùng pgvector với dimension mặc định 768 cho nomic-embed-text.
-- 2) Nếu model embedding của bạn trả dimension khác, hãy sửa vector(768) thành vector(DIM_MOI)
--    và đồng bộ biến môi trường EMBED_DIM trong backend/build_embeddings.py.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS intents (
    intent_id SERIAL PRIMARY KEY,
    intent_name VARCHAR(100) NOT NULL UNIQUE,
    domain VARCHAR(50),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prompts (
    prompt_id SERIAL PRIMARY KEY,
    intent_id INT NOT NULL REFERENCES intents(intent_id) ON DELETE CASCADE ON UPDATE CASCADE,
    prompt_text TEXT NOT NULL,
    prompt_norm TEXT,
    embedding vector(768),
    embedding_model VARCHAR(100),
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', COALESCE(prompt_norm, ''))) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS answers (
    answer_id SERIAL PRIMARY KEY,
    intent_id INT NOT NULL REFERENCES intents(intent_id) ON DELETE CASCADE ON UPDATE CASCADE,
    answer_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_logs (
    log_id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64),
    question TEXT NOT NULL,
    intent_name VARCHAR(100),
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (confidence >= 0 AND confidence <= 1.2),
    source VARCHAR(50) NOT NULL DEFAULT 'UNKNOWN',
    answer_preview VARCHAR(250),
    tool_trace_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    tool_count INT NOT NULL DEFAULT 0 CHECK (tool_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    employee_code VARCHAR(20) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    full_name_norm TEXT,
    birth_year INT,
    position VARCHAR(50),
    department VARCHAR(50),
    hometown VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    photo_path VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_intents_domain ON intents(domain);
CREATE INDEX IF NOT EXISTS idx_prompts_intent_id ON prompts(intent_id);
CREATE INDEX IF NOT EXISTS idx_prompts_prompt_norm ON prompts(prompt_norm);
CREATE INDEX IF NOT EXISTS idx_prompts_tsv ON prompts USING GIN(tsv);
CREATE INDEX IF NOT EXISTS idx_prompts_meta ON prompts USING GIN(meta);
CREATE INDEX IF NOT EXISTS idx_chat_logs_session_id ON chat_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_logs_created_at ON chat_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_employees_employee_code ON employees(employee_code);
CREATE INDEX IF NOT EXISTS idx_employees_full_name_norm ON employees USING GIN(full_name_norm gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'public' AND indexname = 'idx_prompts_embedding_ivfflat'
    ) THEN
        CREATE INDEX idx_prompts_embedding_ivfflat
        ON prompts USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50);
    END IF;
END $$;

DROP TRIGGER IF EXISTS trg_intents_updated_at ON intents;
CREATE TRIGGER trg_intents_updated_at
BEFORE UPDATE ON intents
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_prompts_updated_at ON prompts;
CREATE TRIGGER trg_prompts_updated_at
BEFORE UPDATE ON prompts
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_answers_updated_at ON answers;
CREATE TRIGGER trg_answers_updated_at
BEFORE UPDATE ON answers
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_employees_updated_at ON employees;
CREATE TRIGGER trg_employees_updated_at
BEFORE UPDATE ON employees
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
