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

