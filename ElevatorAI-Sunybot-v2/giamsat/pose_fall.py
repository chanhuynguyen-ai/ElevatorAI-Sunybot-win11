# pose_fall.py
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import numpy as np
import cv2
import config

KP_TH = 0.20  # keypoint confidence threshold

SKELETON = [
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
]


@dataclass
class FallState:
    tid_suspect_start: Dict[int, float] = field(default_factory=dict)
    tid_last_fire: Dict[int, float] = field(default_factory=dict)
    tid_last_pose: Dict[int, np.ndarray] = field(default_factory=dict)


def draw_pose(frame, kps: np.ndarray, color=(255, 255, 255)):
    if kps is None:
        return
    for a, b in SKELETON:
        if kps[a, 2] > KP_TH and kps[b, 2] > KP_TH:
            ax, ay = int(kps[a, 0]), int(kps[a, 1])
            bx, by = int(kps[b, 0]), int(kps[b, 1])
            cv2.line(frame, (ax, ay), (bx, by), color, 2)
    for i in range(kps.shape[0]):
        if kps[i, 2] > KP_TH:
            x, y = int(kps[i, 0]), int(kps[i, 1])
            cv2.circle(frame, (x, y), 3, color, -1)


def _keypoint_bbox(kps: np.ndarray):
    pts = kps[kps[:, 2] > KP_TH]
    if len(pts) < 4:  # NÂNG CẤP: ít điểm vẫn chấp nhận
        return None
    xs, ys = pts[:, 0], pts[:, 1]
    return float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())


def classify_posture(
    kps: Optional[np.ndarray],
    person_bbox: Optional[Tuple[int, int, int, int]] = None,
    frame_h: int = 480
) -> str:
    """
    Return: DUNG / NGOI / NAM / UNKNOWN

    Fix lớn:
    - Khi pose thiếu chân (knee/ankle) do bàn che / camera gần:
      dùng person_bbox + vị trí vai để đoán NGOI/DUNG.
    """
    def bbox_fallback() -> str:
        if person_bbox is None:
            return "UNKNOWN"
        x1, y1, x2, y2 = person_bbox
        w = (x2 - x1) + 1e-6
        h = (y2 - y1) + 1e-6
        ar = w / h

        # người nằm: bbox rất ngang
        if ar > 1.35:
            return "NAM"

        # nếu bbox thấp (chỉ thấy phần thân trên), thường là NGỒI (bị bàn che chân)
        if h < 0.55 * frame_h:
            return "NGOI"

        return "DUNG"

    if kps is None:
        return bbox_fallback()

    bb = _keypoint_bbox(kps)
    if bb is None:
        return bbox_fallback()

    x1, y1, x2, y2 = bb
    w = (x2 - x1) + 1e-6
    h = (y2 - y1) + 1e-6
    ar = w / h

    def ok(i: int) -> bool:
        return kps[i, 2] > KP_TH

    # NAM: keypoint bbox ngang
    if ar > 1.35:
        return "NAM"

    # thiếu chân → fallback theo vai + bbox người
    leg_visible = ok(13) or ok(14) or ok(15) or ok(16)
    if not leg_visible:
        if person_bbox is None:
            return "UNKNOWN"

        px1, py1, px2, py2 = person_bbox
        ph = (py2 - py1) + 1e-6

        # vai nằm thấp trong bbox => ngồi
        if ok(5) and ok(6):
            sy = float((kps[5, 1] + kps[6, 1]) / 2.0)
            rel = (sy - py1) / ph  # 0..1
            # rel cao nghĩa là vai tụt xuống (ngồi)
            if rel > 0.25:
                return "NGOI"

        # bbox thấp => ngồi
        if ph < 0.55 * frame_h:
            return "NGOI"

        return "DUNG"

    # đủ chân thì dùng rule chuẩn hip-knee-ankle
    full_leg = ok(11) and ok(12) and ok(13) and ok(14) and ok(15) and ok(16)
    if full_leg:
        hip = float((kps[11, 1] + kps[12, 1]) / 2.0)
        knee = float((kps[13, 1] + kps[14, 1]) / 2.0)
        ankle = float((kps[15, 1] + kps[16, 1]) / 2.0)

        hip_knee = abs(knee - hip)
        knee_ankle = abs(ankle - knee)

        if hip_knee < 0.18 * h:
            return "NGOI"
        if knee_ankle > 0.25 * h:
            return "DUNG"

    return "UNKNOWN"


def _pose_is_fall(kps: np.ndarray) -> bool:
    """
    Fall: bbox ngang hoặc thân nghiêng nhiều.
    """
    bb = _keypoint_bbox(kps)
    if bb is None:
        return False

    x1, y1, x2, y2 = bb
    w = (x2 - x1) + 1e-6
    h = (y2 - y1) + 1e-6
    ar = w / h

    def ok(i: int) -> bool:
        return kps[i, 2] > KP_TH

    # bbox ngang => nghi ngờ ngã
    if ar > 1.35:
        # hip phải thấp để tránh false
        if ok(11) and ok(12):
            hip_y = float((kps[11, 1] + kps[12, 1]) / 2.0)
            if hip_y < y1 + 0.55 * h:
                return False
        return True

    # góc thân (shoulder->hip)
    if ok(5) and ok(6) and ok(11) and ok(12):
        sx = float((kps[5, 0] + kps[6, 0]) / 2.0)
        sy = float((kps[5, 1] + kps[6, 1]) / 2.0)
        hx = float((kps[11, 0] + kps[12, 0]) / 2.0)
        hy = float((kps[11, 1] + kps[12, 1]) / 2.0)

        slope = abs(hy - sy) / (abs(hx - sx) + 1e-6)
        if slope < 0.35:
            if ok(11) and ok(12):
                hip_y = float((kps[11, 1] + kps[12, 1]) / 2.0)
                if hip_y < y1 + 0.55 * h:
                    return False
            return True

    return False


def update_fall_by_pose(fstate: FallState, tid: int, now: float, kps: Optional[np.ndarray]) -> bool:
    if kps is None:
        fstate.tid_suspect_start.pop(tid, None)
        return False

    suspect = _pose_is_fall(kps)
    if suspect:
        if tid not in fstate.tid_suspect_start:
            fstate.tid_suspect_start[tid] = now
        return (now - fstate.tid_suspect_start[tid]) >= config.FALL_CONFIRM_SEC

    fstate.tid_suspect_start.pop(tid, None)
    return False


def can_fire_fall(fstate: FallState, tid: int, now: float) -> bool:
    last = fstate.tid_last_fire.get(tid, 0.0)
    return (now - last) >= config.FALL_COOLDOWN_SEC


def mark_fire_fall(fstate: FallState, tid: int, now: float):
    fstate.tid_last_fire[tid] = now