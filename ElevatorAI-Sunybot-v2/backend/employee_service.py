import re
from typing import Optional

from config.db_config import db
from backend.text_utils import normalize_vi

EMP_CODE_RE = re.compile(r"^(nv\d{3,})$", re.IGNORECASE)


def is_employee_code(text: str) -> bool:
    return bool(EMP_CODE_RE.match((text or "").strip()))


def find_employee_by_code(code: str):
    code = (code or "").strip().upper()
    if not code:
        return None
    conn = db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT employee_code, full_name, full_name_norm, birth_year, position, department,
                       hometown, phone, email, photo_path
                FROM employees
                WHERE employee_code = %s
                LIMIT 1
                """,
                (code,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def find_employee_by_name(name: str):
    query = normalize_vi(name)
    if not query:
        return None
    conn = db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT employee_code, full_name, full_name_norm, birth_year, position, department,
                       hometown, phone, email, photo_path
                FROM employees
                WHERE full_name_norm ILIKE %s OR full_name ILIKE %s
                ORDER BY employee_code ASC
                LIMIT 1
                """,
                (f"%{query}%", f"%{name.strip()}%"),
            )
            row = cur.fetchone()
            if row:
                return row

            cur.execute(
                """
                SELECT employee_code, full_name, full_name_norm, birth_year, position, department,
                       hometown, phone, email, photo_path
                FROM employees
                ORDER BY employee_code ASC
                LIMIT 100
                """
            )
            rows = cur.fetchall() or []
        for row in rows:
            full_name_norm = row.get("full_name_norm") or ""
            if query in full_name_norm or full_name_norm in query:
                return row
        return None
    finally:
        conn.close()


def format_employee_answer(emp: Optional[dict]) -> str:
    if not emp:
        return "Không tìm thấy nhân viên phù hợp."
    return (
        f"Thông tin nhân viên:\n"
        f"- Mã nhân viên: {emp.get('employee_code')}\n"
        f"- Họ và tên: {emp.get('full_name')}\n"
        f"- Năm sinh: {emp.get('birth_year')}\n"
        f"- Vị trí: {emp.get('position')}\n"
        f"- Phòng ban: {emp.get('department')}\n"
        f"- Quê quán: {emp.get('hometown')}\n"
        f"- SĐT: {emp.get('phone')}\n"
        f"- Email: {emp.get('email')}"
    )
