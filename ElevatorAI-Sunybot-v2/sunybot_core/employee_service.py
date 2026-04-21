# backend/employee_service.py
import re
from config.db_config import db
from backend.text_utils import normalize_vi

EMP_CODE_RE = re.compile(r"^(nv\d{3,})$", re.IGNORECASE)

def is_employee_code(text: str) -> bool:
    return bool(EMP_CODE_RE.match(text.strip()))

def find_employee_by_code(code: str):
    code = code.strip().upper()
    conn = db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT employee_code, full_name, birth_year, position, department,
                       hometown, phone, email, photo_path
                FROM employees
                WHERE employee_code=%s
                LIMIT 1
            """, (code,))
            return cur.fetchone()
    finally:
        conn.close()

def find_employee_by_name(name: str):
    # normalized contains
    q = normalize_vi(name)
    if not q:
        return None
    conn = db.connect()
    try:
        with conn.cursor() as cur:
            # Tìm gần đúng theo full_name (cách đơn giản)
            cur.execute("""
                SELECT employee_code, full_name, birth_year, position, department,
                       hometown, phone, email, photo_path
                FROM employees
                WHERE LOWER(full_name) LIKE %s
                LIMIT 1
            """, (f"%{name.strip().lower()}%",))
            row = cur.fetchone()
            if row:
                return row

            # fallback: tìm theo normalized (nếu bạn lưu normalized_full_name thì tốt hơn)
            # tạm thời dùng LIKE thường
            return None
    finally:
        conn.close()

def format_employee_answer(emp: dict) -> str:
    return (
        f"Thông tin nhân viên:\n"
        f"- Mã nhân viên: {emp.get('employee_code')}\n"
        f"- Họ và tên: {emp.get('full_name')}\n"
        f"- Năm sinh: {emp.get('birth_year')}\n"
        f"- Vị trí: {emp.get('position')}\n"
        f"- Phòng ban: {emp.get('department')}\n"
        f"- Quê quán: {emp.get('hometown')}\n"
        f"- SĐt: {emp.get('phone')}\n"
        f"- Email: {emp.get('email')}"
    )

