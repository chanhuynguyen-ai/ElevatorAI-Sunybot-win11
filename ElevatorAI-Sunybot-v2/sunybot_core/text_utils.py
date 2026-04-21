# backend/text_utils.py
import re
from database.remove_vietnamese_accent import remove_vietnamese_accent

def normalize_vi(text: str) -> str:
    if not text:
        return ""
    t = text.strip().lower()
    t = remove_vietnamese_accent(t)
    # gọn khoảng trắng
    t = re.sub(r"\s+", " ", t)
    # bỏ ký tự lạ, giữ chữ/số/khoảng trắng
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

