-- Runs once in the official Postgres image.
CREATE DATABASE elevator_cv OWNER elevator_ai;
CREATE DATABASE elevator_llm OWNER elevator_ai;
\connect elevator_cv
CREATE TABLE IF NOT EXISTS person_registry (
   person_id SERIAL PRIMARY KEY,
   person_code TEXT UNIQUE,
   full_name TEXT NOT NULL,
   department TEXT,
   is_active BOOLEAN NOT NULL DEFAULT TRUE,
   created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS face_embeddings (
   embedding_id SERIAL PRIMARY KEY,
   person_id INT NOT NULL REFERENCES person_registry(person_id) ON DELETE CASCADE,
   embedding FLOAT8[] NOT NULL,
   created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS camera_events (
   event_id BIGSERIAL PRIMARY KEY,
   event_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
   cam_id TEXT NOT NULL,
   event_type TEXT NOT NULL,
   track_id TEXT,
   person_id INT,
   person_name TEXT,
   bbox JSONB,
   posture TEXT,
   people_count INT,
   confidence REAL,
   snapshot_path TEXT,
   extra JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS camera_occupancy_samples (
   sample_id BIGSERIAL PRIMARY KEY,
   sample_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
   cam_id TEXT NOT NULL,
   people_count INT NOT NULL DEFAULT 0,
   unknown_count INT NOT NULL DEFAULT 0,
   sitting_count INT NOT NULL DEFAULT 0,
   lying_count INT NOT NULL DEFAULT 0,
   fall_count INT NOT NULL DEFAULT 0,
   extra JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_camera_events_ts
ON camera_events(event_ts DESC);

CREATE INDEX IF NOT EXISTS idx_camera_events_cam_ts
ON camera_events(cam_id, event_ts DESC);

CREATE INDEX IF NOT EXISTS idx_camera_events_type_ts
ON camera_events(event_type, event_ts DESC);

CREATE INDEX IF NOT EXISTS idx_occ_ts
ON camera_occupancy_samples(sample_ts DESC);

CREATE INDEX IF NOT EXISTS idx_occ_cam_ts
ON camera_occupancy_samples(cam_id, sample_ts DESC);


\connect elevator_llm
-- Windows-friendly PostgreSQL schema for Sunybot Step 1
-- Muc tieu:
-- 1) Tao du du lieu cau truc cho intent / prompt / answer / employee
-- 2) Khong phu thuoc pgvector de chay duoc tren Windows nhanh
-- 3) Van giu full-text + pg_trgm cho prompts
-- 4) Bo sung truong auth cho employees de dang ky / dang nhap bang DB that

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
    domain VARCHAR(50) NOT NULL DEFAULT 'general',
    description TEXT,
    priority SMALLINT NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prompts (
    prompt_id SERIAL PRIMARY KEY,
    intent_id INT NOT NULL REFERENCES intents(intent_id) ON DELETE CASCADE ON UPDATE CASCADE,
    prompt_text TEXT NOT NULL,
    prompt_norm TEXT,
    embedding_model VARCHAR(100),
    lang VARCHAR(10) NOT NULL DEFAULT 'vi',
    weight REAL NOT NULL DEFAULT 1.0,
    source_tag VARCHAR(50) NOT NULL DEFAULT 'seed',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', COALESCE(prompt_norm, ''))) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_prompts_intent_text UNIQUE (intent_id, prompt_text)
);

CREATE TABLE IF NOT EXISTS answers (
    answer_id SERIAL PRIMARY KEY,
    intent_id INT NOT NULL REFERENCES intents(intent_id) ON DELETE CASCADE ON UPDATE CASCADE,
    answer_text TEXT NOT NULL,
    answer_type VARCHAR(30) NOT NULL DEFAULT 'default',
    source_note VARCHAR(150),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_logs (
    log_id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64),
    question TEXT NOT NULL,
    question_norm TEXT,
    intent_name VARCHAR(100),
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (confidence >= 0 AND confidence <= 1.2),
    source VARCHAR(50) NOT NULL DEFAULT 'UNKNOWN',
    answer_preview VARCHAR(250),
    tool_trace_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    tool_count INT NOT NULL DEFAULT 0 CHECK (tool_count >= 0),
    latency_ms INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    employee_code VARCHAR(20) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    full_name_norm TEXT,
    birth_year INT,
    position VARCHAR(80),
    department VARCHAR(80),
    hometown VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    photo_path VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    password_hash TEXT,
    role VARCHAR(50) NOT NULL DEFAULT 'technician',
    auth_source VARCHAR(50) NOT NULL DEFAULT 'local_db',
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE employees ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS role VARCHAR(50) NOT NULL DEFAULT 'technician';
ALTER TABLE employees ADD COLUMN IF NOT EXISTS auth_source VARCHAR(50) NOT NULL DEFAULT 'local_db';
ALTER TABLE employees ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS full_name_norm TEXT;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active';

CREATE INDEX IF NOT EXISTS idx_intents_domain ON intents(domain);
CREATE INDEX IF NOT EXISTS idx_intents_active_priority ON intents(is_active, priority);
CREATE INDEX IF NOT EXISTS idx_prompts_intent_id ON prompts(intent_id);
CREATE INDEX IF NOT EXISTS idx_prompts_prompt_norm ON prompts USING GIN(prompt_norm gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_prompts_tsv ON prompts USING GIN(tsv);
CREATE INDEX IF NOT EXISTS idx_prompts_meta ON prompts USING GIN(meta);
CREATE INDEX IF NOT EXISTS idx_prompts_active ON prompts(is_active);
CREATE INDEX IF NOT EXISTS idx_answers_intent_id ON answers(intent_id);
CREATE INDEX IF NOT EXISTS idx_answers_active ON answers(is_active);
CREATE INDEX IF NOT EXISTS idx_chat_logs_session_id ON chat_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_logs_created_at ON chat_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_logs_intent_name ON chat_logs(intent_name);
CREATE INDEX IF NOT EXISTS idx_employees_employee_code ON employees(employee_code);
CREATE INDEX IF NOT EXISTS idx_employees_full_name_norm ON employees USING GIN(full_name_norm gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department);
CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status);

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

INSERT INTO intents (intent_name, domain, description, priority, is_active) VALUES
('customer_greeting','customer','Basic greeting',10,TRUE),
('customer_safety','customer','Elevator safety guidance',20,TRUE),
('maintenance_cv_summary','maintenance_cv','Summarize CV events for technicians',10,TRUE)
ON CONFLICT (intent_name) DO NOTHING;

INSERT INTO prompts (intent_id,prompt_text,prompt_norm,lang,source_tag,is_active,meta)
SELECT i.intent_id, x.prompt_text, x.prompt_norm, 'vi', 'demo_seed', TRUE, x.meta::jsonb
FROM intents i JOIN (VALUES
('customer_greeting','xin chao','xin chao','{"scope":"customer"}'),
('customer_safety','neu bi ket trong thang may thi lam gi','neu bi ket trong thang may thi lam gi','{"scope":"customer"}'),
('maintenance_cv_summary','tom tat su kien camera hom nay','tom tat su kien camera hom nay','{"scope":"maintenance"}')
) AS x(intent_name,prompt_text,prompt_norm,meta) ON x.intent_name=i.intent_name
ON CONFLICT (intent_id,prompt_text) DO NOTHING;

INSERT INTO answers (intent_id,answer_text,answer_type,source_note,is_active)
SELECT i.intent_id,x.answer_text,'default','demo_seed',TRUE
FROM intents i JOIN (VALUES
('customer_greeting','Xin chào, tôi là Sunybot. Tôi có thể hỗ trợ hướng dẫn và thông tin an toàn thang máy.'),
('customer_safety','Hãy giữ bình tĩnh, dùng nút SOS hoặc intercom và không tự cạy cửa khi cabin chưa ở vị trí an toàn.'),
('maintenance_cv_summary','Tôi sẽ đọc dữ liệu CV đã ghi nhận thay vì tự suy đoán từ mô hình ngôn ngữ.')
) AS x(intent_name,answer_text) ON x.intent_name=i.intent_name
WHERE NOT EXISTS (SELECT 1 FROM answers a WHERE a.intent_id=i.intent_id AND a.answer_text=x.answer_text);

