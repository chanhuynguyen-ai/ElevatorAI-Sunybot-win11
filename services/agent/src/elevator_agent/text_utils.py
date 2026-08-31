import re
from unidecode import unidecode

def remove_vietnamese_accent(text):
    if text is None:
        return None
    return unidecode(text)

def normalize_vi(text):
    if not text:
        return ""
    t = remove_vietnamese_accent(str(text).strip().lower())
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()
