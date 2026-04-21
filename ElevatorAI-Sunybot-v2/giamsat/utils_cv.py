# utils_cv.py
import cv2
import numpy as np
import os
import time
import config


# ===============================
# ROI SAFE CROP
# ===============================
def cat_roi_an_toan(frame, x1, y1, x2, y2, pad=10):

    h, w = frame.shape[:2]

    x1 = max(0, int(x1) - pad)
    y1 = max(0, int(y1) - pad)
    x2 = min(w - 1, int(x2) + pad)
    y2 = min(h - 1, int(y2) + pad)

    if x2 <= x1 or y2 <= y1:
        return None

    return frame[y1:y2, x1:x2].copy()


# ===============================
# PICK LARGEST FACE
# ===============================
def pick_face_largest(faces):

    if faces is None or len(faces) == 0:
        return None

    return max(
        faces,
        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
    )


# ===============================
# COSINE SIMILARITY
# ===============================
def cosine_sim(a, b):

    if a is None or b is None:
        return -1

    a = a.astype(np.float32)
    b = b.astype(np.float32)

    na = np.linalg.norm(a) + 1e-9
    nb = np.linalg.norm(b) + 1e-9

    return float(np.dot(a, b) / (na * nb))


# ===============================
# SAVE SNAPSHOT
# ===============================
def save_snapshot(frame, prefix="snap"):

    os.makedirs(config.SNAP_DIR, exist_ok=True)

    path = os.path.join(
        config.SNAP_DIR,
        f"{prefix}_{int(time.time())}.jpg"
    )

    cv2.imwrite(path, frame)

    return path


# ===============================
# WARNING LOGO
# ===============================
def draw_warning_logo(frame, x=10, y=10, size=60):

    pts = np.array([
        [x + size // 2, y],
        [x, y + size],
        [x + size, y + size]
    ])

    cv2.fillPoly(frame, [pts], (0, 0, 255))
    cv2.polylines(frame, [pts], True, (255, 255, 255), 2)

    cx = x + size // 2

    cv2.line(frame, (cx, y + 15), (cx, y + 40), (255, 255, 255), 4)
    cv2.circle(frame, (cx, y + 50), 4, (255, 255, 255), -1)


# ===============================
# ALPHA RECTANGLE
# ===============================
def overlay_rect_alpha(frame, x1, y1, x2, y2, color=(0, 0, 0), alpha=0.5):

    overlay = frame.copy()

    x1 = int(x1)
    y1 = int(y1)
    x2 = int(x2)
    y2 = int(y2)

    cv2.rectangle(
        overlay,
        (x1, y1),
        (x2, y2),
        color,
        -1
    )

    cv2.addWeighted(
        overlay,
        alpha,
        frame,
        1 - alpha,
        0,
        frame
    )


# ===============================
# TEXT WITH BACKGROUND
# ===============================
def put_text_bg(
    frame,
    text,
    org,
    font_scale=0.6,
    color=(255, 255, 255),
    bg=(0, 0, 0),
    thickness=2,
    alpha=0.5
):

    font = cv2.FONT_HERSHEY_SIMPLEX

    (w, h), _ = cv2.getTextSize(
        text,
        font,
        font_scale,
        thickness
    )

    x, y = org

    overlay_rect_alpha(
        frame,
        x - 5,
        y - h - 5,
        x + w + 5,
        y + 5,
        bg,
        alpha
    )

    cv2.putText(
        frame,
        text,
        (x, y),
        font,
        font_scale,
        color,
        thickness,
        cv2.LINE_AA
    )