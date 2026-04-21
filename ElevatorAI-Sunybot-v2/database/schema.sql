CREATE DATABASE IF NOT EXISTS elevator_ai
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE elevator_ai;

CREATE TABLE IF NOT EXISTS intents (
    intent_id INT AUTO_INCREMENT PRIMARY KEY,
    intent_name VARCHAR(100) NOT NULL,
    domain VARCHAR(50),
    description TEXT,
    UNIQUE KEY uq_intent_name (intent_name)
);

CREATE TABLE IF NOT EXISTS prompts (
    prompt_id INT AUTO_INCREMENT PRIMARY KEY,
    intent_id INT NOT NULL,
    prompt_text TEXT NOT NULL,
    embedding LONGTEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (intent_id) REFERENCES intents(intent_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS answers (
    answer_id INT AUTO_INCREMENT PRIMARY KEY,
    intent_id INT NOT NULL,
    answer_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (intent_id) REFERENCES intents(intent_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS chat_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(64) NULL,
    question TEXT NOT NULL,
    intent_name VARCHAR(100) NULL,
    confidence FLOAT DEFAULT 0,
    source VARCHAR(50) DEFAULT 'UNKNOWN',
    answer_preview VARCHAR(250) NULL,
    tool_trace_json LONGTEXT NULL,
    tool_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_chat_logs_session_id (session_id),
    INDEX idx_chat_logs_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_code VARCHAR(20) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    birth_year INT,
    position VARCHAR(50),
    department VARCHAR(50),
    hometown VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    photo_path VARCHAR(255),
    UNIQUE KEY uq_employee_code (employee_code)
);
