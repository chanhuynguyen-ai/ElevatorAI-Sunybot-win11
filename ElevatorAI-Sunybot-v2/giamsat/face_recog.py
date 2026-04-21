# face_recog.py
import time
import numpy as np
import cv2
from insightface.app import FaceAnalysis

import config
import utils_cv


def create_face_app(ctx_id: int, det_size=(224, 224)) -> FaceAnalysis:
    face_app = FaceAnalysis(name="buffalo_l")
    face_app.prepare(ctx_id=ctx_id, det_size=det_size)
    return face_app


def so_khop(embed: np.ndarray, ds_nhan_su, nguong_sim=0.45):
    if embed is None or len(ds_nhan_su) == 0:
        return None, 0.0

    best_person = None
    best_sim = -1.0

    for p in ds_nhan_su:
        sim = utils_cv.cosine_sim(embed, p.get("embed"))
        if sim > best_sim:
            best_sim = sim
            best_person = p

    if best_person is not None and best_sim >= nguong_sim:
        return best_person, float(best_sim)

    return None, float(best_sim)


def _yaw_from_landmark(face):
    """
    Ước lượng quay trái/phải từ landmark 2D.
    yaw < 0: quay trái
    yaw > 0: quay phải
    """
    if not hasattr(face, "kps") or face.kps is None:
        return 0.0

    kps = np.asarray(face.kps, dtype=np.float32)
    if kps.shape[0] < 5:
        return 0.0

    left_eye = kps[0]
    right_eye = kps[1]
    nose = kps[2]

    eye_mid = (left_eye + right_eye) / 2.0
    face_w = np.linalg.norm(right_eye - left_eye) + 1e-6
    yaw = float((nose[0] - eye_mid[0]) / face_w)
    return yaw


def _get_face_direction_lr_center(face):
    """
    Chỉ phân loại 3 hướng:
      GIUA / TRAI / PHAI
    """
    yaw = _yaw_from_landmark(face)

    if yaw <= -0.16:
        return "TRAI"
    if yaw >= 0.16:
        return "PHAI"
    return "GIUA"


def _detect_largest_face_in_roi(face_app, frame, x1, y1, x2, y2):
    h, w = frame.shape[:2]
    x1 = max(0, int(x1))
    y1 = max(0, int(y1))
    x2 = min(w, int(x2))
    y2 = min(h, int(y2))

    if x2 <= x1 or y2 <= y1:
        return None

    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return None

    faces = face_app.get(roi)
    f = utils_cv.pick_face_largest(faces)
    if f is None:
        return None

    f.bbox[0] += x1
    f.bbox[1] += y1
    f.bbox[2] += x1
    f.bbox[3] += y1

    if hasattr(f, "kps") and f.kps is not None:
        f.kps[:, 0] += x1
        f.kps[:, 1] += y1

    return f


def capture_face_embedding_for_register(face_app, mirror=True, rotate_mode=None):
    """
    Đăng ký tự động 3 hướng:
      1. GIUA
      2. TRAI
      3. PHAI

    Không cần bấm SPACE.
    """
    cap = cv2.VideoCapture(config.CAM_INDEX)
    if not cap.isOpened():
        print("[DK] Khong mo duoc webcam.")
        return None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    steps = [
        ("GIUA", "Nhin thang vao camera"),
        ("TRAI", "Quay mat sang trai"),
        ("PHAI", "Quay mat sang phai"),
    ]

    embeddings = []
    step_idx = 0

    stable_need = 5
    stable_count = 0
    save_gap = 0.8
    last_saved_time = 0.0

    frame_id = 0
    detect_every_n = 2
    last_face = None

    flash_text = ""
    flash_until = 0.0

    print("[DK] Dang ky khuon mat tu dong 3 huong")
    print("[DK] ESC = huy")

    window_name = "REGISTER - LEFT RIGHT CENTER"

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if rotate_mode is not None:
            frame = cv2.rotate(frame, rotate_mode)
        if mirror:
            frame = cv2.flip(frame, 1)

        frame_id += 1
        now = time.time()
        show = frame.copy()

        h, w = show.shape[:2]
        center = (w // 2, h // 2 + 10)
        axes = (118, 150)

        roi_x1 = max(0, center[0] - axes[0])
        roi_y1 = max(0, center[1] - axes[1])
        roi_x2 = min(w, center[0] + axes[0])
        roi_y2 = min(h, center[1] + axes[1])

        if frame_id % detect_every_n == 0 or last_face is None:
            last_face = _detect_largest_face_in_roi(face_app, frame, roi_x1, roi_y1, roi_x2, roi_y2)

        f = last_face

        if step_idx >= len(steps):
            break

        target_key, target_guide = steps[step_idx]

        cv2.putText(show, f"BUOC {step_idx + 1}/{len(steps)}: {target_key}", (10, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 255), 2)
        cv2.putText(show, target_guide, (10, 64),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 255, 255), 2)
        cv2.putText(show, "ESC = HUY | Tu dong luu khi dung huong", (10, 96),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.64, (0, 255, 0), 2)

        bar_x1, bar_y1 = 10, 112
        bar_w, bar_h = 320, 18
        cv2.rectangle(show, (bar_x1, bar_y1), (bar_x1 + bar_w, bar_y1 + bar_h), (255, 255, 255), 2)
        fill = int(bar_w * (step_idx / len(steps)))
        cv2.rectangle(show, (bar_x1, bar_y1), (bar_x1 + fill, bar_y1 + bar_h), (0, 255, 0), -1)

        cv2.ellipse(show, center, axes, 0, 0, 360, (255, 255, 255), 2)

        if f is not None:
            x1, y1, x2, y2 = [int(v) for v in f.bbox]
            cv2.rectangle(show, (x1, y1), (x2, y2), (0, 255, 0), 2)

            face_center = ((x1 + x2) // 2, (y1 + y2) // 2)
            dx = abs(face_center[0] - center[0])
            dy = abs(face_center[1] - center[1])

            in_center = dx < axes[0] * 0.78 and dy < axes[1] * 0.78
            direction = _get_face_direction_lr_center(f)

            cv2.putText(show, f"Huong hien tai: {direction}", (10, 160),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2)

            if in_center and direction == target_key:
                stable_count += 1
                msg = f"DUNG HUONG... {stable_count}/{stable_need}"
                msg_color = (0, 255, 0)
            else:
                stable_count = 0
                msg = "CAN CHINH DUNG KHUNG / DUNG HUONG"
                msg_color = (0, 0, 255)

            cv2.putText(show, msg, (10, 195),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.78, msg_color, 2)

            if stable_count >= stable_need and (now - last_saved_time) >= save_gap:
                emb = f.normed_embedding.astype(np.float32)
                embeddings.append(emb)

                saved_name = target_key
                step_idx += 1
                stable_count = 0
                last_saved_time = now

                if step_idx < len(steps):
                    next_name = steps[step_idx][0]
                    flash_text = f"DA LUU: {saved_name}  ->  TIEP THEO: {next_name}"
                else:
                    flash_text = f"DA LUU: {saved_name}  ->  HOAN TAT"

                flash_until = now + 1.2
                print(f"[DK] Da luu buoc: {saved_name}")
        else:
            stable_count = 0
            cv2.putText(show, "KHONG THAY MAT RO", (10, 160),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 0, 255), 2)

        if now < flash_until and flash_text:
            cv2.rectangle(show, (10, h - 70), (w - 10, h - 20), (0, 120, 0), -1)
            cv2.putText(show, flash_text, (20, h - 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

        cv2.imshow(window_name, show)
        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            cap.release()
            cv2.destroyWindow(window_name)
            print("[DK] Huy dang ky.")
            return None

    cap.release()
    cv2.destroyWindow(window_name)

    if len(embeddings) == 0:
        print("[DK] Khong thu duoc embedding nao.")
        return None

    mean_emb = np.mean(np.stack(embeddings, axis=0), axis=0).astype(np.float32)
    mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-9)

    print(f"[DK] Hoan tat quet {len(embeddings)} huong mat.")
    return mean_emb