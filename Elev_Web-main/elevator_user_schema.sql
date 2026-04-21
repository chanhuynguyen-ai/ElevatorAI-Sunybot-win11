CREATE DATABASE IF NOT EXISTS elevator_user;

-- PostgreSQL logical schema proposal
CREATE TABLE IF NOT EXISTS technicians (
  technician_id VARCHAR(32) PRIMARY KEY,
  employee_code VARCHAR(32) UNIQUE NOT NULL,
  full_name VARCHAR(120) NOT NULL,
  department VARCHAR(120),
  role_name VARCHAR(64) DEFAULT 'technician',
  password_hash TEXT NOT NULL,
  phone VARCHAR(32),
  email VARCHAR(120),
  qr_token VARCHAR(128) UNIQUE,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS qr_access_tokens (
  token_id SERIAL PRIMARY KEY,
  technician_id VARCHAR(32) REFERENCES technicians(technician_id) ON DELETE CASCADE,
  qr_token VARCHAR(128) UNIQUE NOT NULL,
  description TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS floor_access_rules (
  rule_id SERIAL PRIMARY KEY,
  floor_no INTEGER NOT NULL,
  technician_id VARCHAR(32) REFERENCES technicians(technician_id) ON DELETE CASCADE,
  qr_token VARCHAR(128),
  pin_enabled BOOLEAN DEFAULT FALSE,
  qr_enabled BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auth_logs (
  log_id SERIAL PRIMARY KEY,
  technician_id VARCHAR(32),
  employee_code VARCHAR(32),
  method VARCHAR(16) NOT NULL,
  target_floor INTEGER,
  result_status VARCHAR(16) NOT NULL,
  raw_payload JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
