# database/remove_vietnamese_accent.py
from unidecode import unidecode

def remove_accent(text):
    if text is None:
        return None
    return unidecode(text)

# ✅ Alias để code khác import đúng tên bạn đang dùng
def remove_vietnamese_accent(text: str) -> str:
    return remove_accent(text)

# ------------------------------
# Chỉ chạy convert DB khi chạy file trực tiếp:
# python3 database/remove_vietnamese_accent.py
# ------------------------------
if __name__ == "__main__":
    import pymysql

    DB_CONFIG = {
        "host": "localhost",
        "user": "elevator_ai",
        "password": "elevator123",
        "database": "elevator_ai",
        "charset": "utf8mb4"
    }

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    tables = {
        "employees": {
            "pk": "id",
            "cols": [
                "employee_code", "full_name",
                "position", "department",
                "hometown", "email"
            ]
        },
        "intents": {
            "pk": "intent_id",
            "cols": ["intent_name", "domain", "description"]
        },
        "prompts": {
            "pk": "prompt_id",
            "cols": ["prompt_text"]
        },
        "answers": {
            "pk": "answer_id",
            "cols": ["answer_text"]
        }
    }

    for table, meta in tables.items():
        pk = meta["pk"]
        cols = meta["cols"]

        sql_select = f"SELECT {pk}, {', '.join(cols)} FROM {table}"
        cursor.execute(sql_select)
        rows = cursor.fetchall()

        for row in rows:
            updates = []
            values = []

            for col in cols:
                updates.append(f"{col}=%s")
                values.append(remove_accent(row.get(col)))

            values.append(row[pk])

            sql_update = f"UPDATE {table} SET {', '.join(updates)} WHERE {pk}=%s"
            cursor.execute(sql_update, values)

        print(f"[OK] Converted table: {table}")

    conn.commit()
    cursor.close()
    conn.close()
    print("DONE — ALL VIETNAMESE ACCENTS REMOVED SUCCESSFULLY")

