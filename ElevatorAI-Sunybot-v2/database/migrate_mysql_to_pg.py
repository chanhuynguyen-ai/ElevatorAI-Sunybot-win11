import json
import os
from typing import Any, Iterable, Optional

import pymysql
import psycopg
from psycopg.rows import dict_row

from database.remove_vietnamese_accent import remove_vietnamese_accent

MYSQL_CFG = {
    "host": os.getenv("MYSQL_HOST", os.getenv("DB_HOST", "localhost")),
    "user": os.getenv("MYSQL_USER", os.getenv("DB_USER", "elevator_ai")),
    "password": os.getenv("MYSQL_PASSWORD", os.getenv("DB_PASSWORD", "elevator123")),
    "database": os.getenv("MYSQL_DATABASE", os.getenv("DB_NAME", "elevator_ai")),
    "port": int(os.getenv("MYSQL_PORT", os.getenv("DB_PORT", "3306"))),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

PG_DSN = (
    "host={0} port={1} dbname={2} user={3} password={4}".format(
        os.getenv("PGHOST", "localhost"),
        os.getenv("PGPORT", "5432"),
        os.getenv("PGDATABASE", "elevator_ai_pg"),
        os.getenv("PGUSER", "elevator_ai"),
        os.getenv("PGPASSWORD", "elevator123"),
    )
)

TRUNCATE_FIRST = os.getenv("MIGRATE_TRUNCATE_FIRST", "1") == "1"


def to_pgvector(values: Optional[Iterable[Any]]) -> Optional[str]:
    if values is None:
        return None
    casted = []
    for item in values:
        try:
            casted.append(str(float(item)))
        except Exception:
            return None
    if not casted:
        return None
    return "[" + ",".join(casted) + "]"


def normalize_vi(text: Optional[str]) -> str:
    if not text:
        return ""
    return remove_vietnamese_accent(text).strip().lower()


def fetch_all(mysql_conn, sql: str):
    with mysql_conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall() or []


def parse_embedding(raw_emb: Any) -> Optional[str]:
    if not raw_emb:
        return None
    if isinstance(raw_emb, (list, tuple)):
        return to_pgvector(raw_emb)
    try:
        return to_pgvector(json.loads(raw_emb))
    except Exception:
        return None


def safe_json_text(raw_value: Any, default: str) -> str:
    if raw_value is None or raw_value == "":
        return default
    if isinstance(raw_value, str):
        try:
            json.loads(raw_value)
            return raw_value
        except Exception:
            return default
    try:
        return json.dumps(raw_value, ensure_ascii=False)
    except Exception:
        return default


def reset_sequences(cur):
    cur.execute("SELECT setval(pg_get_serial_sequence('intents', 'intent_id'), COALESCE(MAX(intent_id), 1), true) FROM intents")
    cur.execute("SELECT setval(pg_get_serial_sequence('prompts', 'prompt_id'), COALESCE(MAX(prompt_id), 1), true) FROM prompts")
    cur.execute("SELECT setval(pg_get_serial_sequence('answers', 'answer_id'), COALESCE(MAX(answer_id), 1), true) FROM answers")
    cur.execute("SELECT setval(pg_get_serial_sequence('employees', 'id'), COALESCE(MAX(id), 1), true) FROM employees")
    cur.execute("SELECT setval(pg_get_serial_sequence('chat_logs', 'log_id'), COALESCE(MAX(log_id), 1), true) FROM chat_logs")


def main():
    mysql_conn = pymysql.connect(**MYSQL_CFG)
    pg_conn = psycopg.connect(PG_DSN, autocommit=False, row_factory=dict_row)

    try:
        intents = fetch_all(mysql_conn, "SELECT * FROM intents ORDER BY intent_id")
        prompts = fetch_all(mysql_conn, "SELECT * FROM prompts ORDER BY prompt_id")
        answers = fetch_all(mysql_conn, "SELECT * FROM answers ORDER BY answer_id")
        employees = fetch_all(mysql_conn, "SELECT * FROM employees ORDER BY id")
        chat_logs = fetch_all(mysql_conn, "SELECT * FROM chat_logs ORDER BY log_id")

        intent_id_map = {}
        with pg_conn.transaction():
            with pg_conn.cursor() as cur:
                if TRUNCATE_FIRST:
                    cur.execute("TRUNCATE TABLE chat_logs RESTART IDENTITY CASCADE")
                    cur.execute("TRUNCATE TABLE answers RESTART IDENTITY CASCADE")
                    cur.execute("TRUNCATE TABLE prompts RESTART IDENTITY CASCADE")
                    cur.execute("TRUNCATE TABLE intents RESTART IDENTITY CASCADE")
                    cur.execute("TRUNCATE TABLE employees RESTART IDENTITY CASCADE")

                for row in intents:
                    cur.execute(
                        """
                        INSERT INTO intents (intent_name, domain, description, created_at, updated_at)
                        VALUES (%s, %s, %s, COALESCE(%s, NOW()), COALESCE(%s, NOW()))
                        ON CONFLICT (intent_name) DO UPDATE
                        SET domain = EXCLUDED.domain,
                            description = EXCLUDED.description,
                            updated_at = EXCLUDED.updated_at
                        RETURNING intent_id
                        """,
                        (
                            row.get("intent_name"),
                            row.get("domain"),
                            row.get("description"),
                            row.get("created_at"),
                            row.get("updated_at"),
                        ),
                    )
                    new_intent_id = cur.fetchone()["intent_id"]
                    intent_id_map[row["intent_id"]] = new_intent_id

                for row in prompts:
                    mapped_intent_id = intent_id_map.get(row.get("intent_id"))
                    if mapped_intent_id is None:
                        raise ValueError(
                            "Khong tim thay intent_id map cho prompts.intent_id={0} (prompt_id={1})".format(
                                row.get("intent_id"), row.get("prompt_id")
                            )
                        )

                    cur.execute(
                        """
                        INSERT INTO prompts (
                            prompt_id, intent_id, prompt_text, prompt_norm,
                            embedding, embedding_model, meta, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s::vector, %s, %s::jsonb, COALESCE(%s, NOW()), COALESCE(%s, NOW()))
                        ON CONFLICT (prompt_id) DO UPDATE
                        SET intent_id = EXCLUDED.intent_id,
                            prompt_text = EXCLUDED.prompt_text,
                            prompt_norm = EXCLUDED.prompt_norm,
                            embedding = EXCLUDED.embedding,
                            embedding_model = EXCLUDED.embedding_model,
                            meta = EXCLUDED.meta,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (
                            row.get("prompt_id"),
                            mapped_intent_id,
                            row.get("prompt_text"),
                            normalize_vi(row.get("prompt_text")),
                            parse_embedding(row.get("embedding")),
                            row.get("embedding_model") or "nomic-embed-text",
                            json.dumps({"migrated_from": "mysql"}, ensure_ascii=False),
                            row.get("created_at"),
                            row.get("updated_at"),
                        ),
                    )

                for row in answers:
                    mapped_intent_id = intent_id_map.get(row.get("intent_id"))
                    if mapped_intent_id is None:
                        raise ValueError(
                            "Khong tim thay intent_id map cho answers.intent_id={0} (answer_id={1})".format(
                                row.get("intent_id"), row.get("answer_id")
                            )
                        )

                    cur.execute(
                        """
                        INSERT INTO answers (answer_id, intent_id, answer_text, created_at, updated_at)
                        VALUES (%s, %s, %s, COALESCE(%s, NOW()), COALESCE(%s, NOW()))
                        ON CONFLICT (answer_id) DO UPDATE
                        SET intent_id = EXCLUDED.intent_id,
                            answer_text = EXCLUDED.answer_text,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (
                            row.get("answer_id"),
                            mapped_intent_id,
                            row.get("answer_text"),
                            row.get("created_at"),
                            row.get("updated_at"),
                        ),
                    )

                for row in employees:
                    cur.execute(
                        """
                        INSERT INTO employees (
                            employee_code, full_name, full_name_norm, birth_year, position,
                            department, hometown, phone, email, photo_path, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()), COALESCE(%s, NOW()))
                        ON CONFLICT (employee_code) DO UPDATE
                        SET full_name = EXCLUDED.full_name,
                            full_name_norm = EXCLUDED.full_name_norm,
                            birth_year = EXCLUDED.birth_year,
                            position = EXCLUDED.position,
                            department = EXCLUDED.department,
                            hometown = EXCLUDED.hometown,
                            phone = EXCLUDED.phone,
                            email = EXCLUDED.email,
                            photo_path = EXCLUDED.photo_path,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (
                            row.get("employee_code"),
                            row.get("full_name"),
                            normalize_vi(row.get("full_name")),
                            row.get("birth_year"),
                            row.get("position"),
                            row.get("department"),
                            row.get("hometown"),
                            row.get("phone"),
                            row.get("email"),
                            row.get("photo_path"),
                            row.get("created_at"),
                            row.get("updated_at"),
                        ),
                    )

                for row in chat_logs:
                    cur.execute(
                        """
                        INSERT INTO chat_logs (
                            log_id, session_id, question, intent_name, confidence, source,
                            answer_preview, tool_trace_json, tool_count, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, COALESCE(%s, NOW()))
                        ON CONFLICT (log_id) DO UPDATE
                        SET session_id = EXCLUDED.session_id,
                            question = EXCLUDED.question,
                            intent_name = EXCLUDED.intent_name,
                            confidence = EXCLUDED.confidence,
                            source = EXCLUDED.source,
                            answer_preview = EXCLUDED.answer_preview,
                            tool_trace_json = EXCLUDED.tool_trace_json,
                            tool_count = EXCLUDED.tool_count
                        """,
                        (
                            row.get("log_id"),
                            row.get("session_id"),
                            row.get("question"),
                            row.get("intent_name"),
                            float(row.get("confidence") or 0.0),
                            row.get("source") or "UNKNOWN",
                            row.get("answer_preview"),
                            safe_json_text(row.get("tool_trace_json"), "[]"),
                            int(row.get("tool_count") or 0),
                            row.get("created_at"),
                        ),
                    )

                reset_sequences(cur)

        print("[OK] Da migrate MySQL -> PostgreSQL thanh cong")
        print(
            "[SUMMARY] intents={0} prompts={1} answers={2} employees={3} chat_logs={4}".format(
                len(intents), len(prompts), len(answers), len(employees), len(chat_logs)
            )
        )
    except Exception:
        pg_conn.rollback()
        raise
    finally:
        mysql_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
