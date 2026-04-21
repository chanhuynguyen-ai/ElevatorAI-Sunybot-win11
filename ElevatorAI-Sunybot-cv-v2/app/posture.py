from typing import Any, Dict, Optional

from app import config


def _safe_visible(kpts, idx, conf: Optional[float] = None):
    conf = config.POSE_KEYPOINT_CONF if conf is None else conf
    if idx >= len(kpts):
        return None
    p = kpts[idx]
    if len(p) < 3 or p[2] <= conf:
        return None
    return p


def _center(*pts):
    pts = [p for p in pts if p is not None]
    if not pts:
        return None
    x = sum(p[0] for p in pts) / len(pts)
    y = sum(p[1] for p in pts) / len(pts)
    c = sum(p[2] for p in pts) / len(pts)
    return (x, y, c)


def _ratio(a: float, b: float) -> float:
    return float(a) / float(max(abs(b), 1e-6))


def _metrics_from_pose(kpts, bbox) -> Dict[str, Any]:
    x1, y1, x2, y2 = bbox
    w = max(1.0, float(x2 - x1))
    h = max(1.0, float(y2 - y1))

    visible = [p for p in kpts if len(p) >= 3 and p[2] > config.POSE_KEYPOINT_CONF]
    if len(visible) < config.POSTURE_MIN_VISIBLE_KPTS:
        return {"ok": False, "reason": "too_few_keypoints", "visible_count": len(visible)}

    ys = [p[1] for p in visible]
    xs = [p[0] for p in visible]
    torso_span_ratio = _ratio(max(ys) - min(ys), h)
    aspect_ratio = _ratio(w, h)
    visible_x_span_ratio = _ratio(max(xs) - min(xs), w)

    shoulder = _center(_safe_visible(kpts, 5), _safe_visible(kpts, 6))
    hip = _center(_safe_visible(kpts, 11), _safe_visible(kpts, 12))
    knee = _center(_safe_visible(kpts, 13), _safe_visible(kpts, 14))
    ankle = _center(_safe_visible(kpts, 15), _safe_visible(kpts, 16))

    torso_height_ratio = None
    torso_dx_ratio = None
    hip_to_knee_ratio = None
    leg_extension_ratio = None

    if shoulder and hip:
        torso_height_ratio = _ratio(abs(hip[1] - shoulder[1]), h)
        torso_dx_ratio = _ratio(abs(hip[0] - shoulder[0]), h)

    if hip and knee:
        hip_to_knee_ratio = _ratio(max(knee[1] - hip[1], 0.0), h)

    if knee and ankle:
        leg_extension_ratio = _ratio(max(ankle[1] - knee[1], 0.0), h)

    return {
        "ok": True,
        "visible_count": len(visible),
        "aspect_ratio": aspect_ratio,
        "visible_x_span_ratio": visible_x_span_ratio,
        "torso_span_ratio": torso_span_ratio,
        "torso_height_ratio": torso_height_ratio,
        "torso_dx_ratio": torso_dx_ratio,
        "hip_to_knee_ratio": hip_to_knee_ratio,
        "leg_extension_ratio": leg_extension_ratio,
    }


def classify_posture(kpts, bbox, return_meta: bool = False):
    if not kpts or len(kpts) < 17:
        meta = {"ok": False, "reason": "missing_pose"}
        return ("unknown", meta) if return_meta else "unknown"

    meta = _metrics_from_pose(kpts, bbox)
    if not meta.get("ok"):
        return ("unknown", meta) if return_meta else "unknown"

    aspect_ratio = float(meta.get("aspect_ratio") or 0.0)
    visible_x_span_ratio = float(meta.get("visible_x_span_ratio") or 0.0)
    torso_span_ratio = float(meta.get("torso_span_ratio") or 0.0)
    torso_height_ratio = float(meta.get("torso_height_ratio") or 0.0)
    torso_dx_ratio = float(meta.get("torso_dx_ratio") or 0.0)
    hip_to_knee_ratio = float(meta.get("hip_to_knee_ratio") or 0.0)
    leg_extension_ratio = float(meta.get("leg_extension_ratio") or 0.0)

    margin = float(getattr(config, "POSTURE_SCORE_MARGIN", 0.28))
    lying_min = float(getattr(config, "POSTURE_LYING_MIN_SCORE", 2.25))
    sitting_min = float(getattr(config, "POSTURE_SITTING_MIN_SCORE", 1.85))
    standing_min = float(getattr(config, "POSTURE_STANDING_MIN_SCORE", 1.85))
    bending_min = float(getattr(config, "POSTURE_BENDING_MIN_SCORE", 1.55))

    lying_score = 0.0
    if aspect_ratio >= config.POSTURE_HORIZONTAL_AR:
        lying_score += 1.0
    if visible_x_span_ratio >= 0.72:
        lying_score += 0.35
    if torso_span_ratio <= config.POSTURE_LYING_TORSO_SPAN_RATIO:
        lying_score += 1.0
    if torso_height_ratio and torso_height_ratio <= config.POSTURE_LYING_TORSO_HEIGHT_RATIO:
        lying_score += 0.9
    if torso_dx_ratio and torso_dx_ratio >= config.POSTURE_MAX_VERTICAL_DX_RATIO:
        lying_score += 0.75
    if leg_extension_ratio and leg_extension_ratio <= config.POSTURE_STANDING_LEG_EXTENSION_RATIO:
        lying_score += 0.25

    sitting_score = 0.0
    if aspect_ratio < config.POSTURE_HORIZONTAL_AR:
        sitting_score += 0.55
    if torso_height_ratio and torso_height_ratio >= config.POSTURE_LYING_TORSO_HEIGHT_RATIO:
        sitting_score += 0.6
    if hip_to_knee_ratio and hip_to_knee_ratio <= config.POSTURE_SITTING_KNEE_LIFT_RATIO:
        sitting_score += 1.0
    if leg_extension_ratio and leg_extension_ratio <= config.POSTURE_STANDING_LEG_EXTENSION_RATIO:
        sitting_score += 0.85
    if torso_dx_ratio and torso_dx_ratio < config.POSTURE_MAX_VERTICAL_DX_RATIO:
        sitting_score += 0.2

    bending_score = 0.0
    if torso_dx_ratio and torso_dx_ratio >= config.POSTURE_BENDING_MIN_DX_RATIO:
        bending_score += 1.0
    if torso_height_ratio and torso_height_ratio <= config.POSTURE_BENDING_MAX_HEIGHT_RATIO:
        bending_score += 0.85
    if leg_extension_ratio and leg_extension_ratio > config.POSTURE_STANDING_LEG_EXTENSION_RATIO:
        bending_score += 0.55
    if aspect_ratio >= 0.9:
        bending_score += 0.35

    standing_score = 0.0
    if aspect_ratio < config.POSTURE_HORIZONTAL_AR:
        standing_score += 0.6
    if torso_height_ratio and torso_height_ratio > config.POSTURE_LYING_TORSO_HEIGHT_RATIO:
        standing_score += 0.9
    if torso_dx_ratio and torso_dx_ratio < config.POSTURE_MAX_VERTICAL_DX_RATIO:
        standing_score += 0.65
    if leg_extension_ratio and leg_extension_ratio > config.POSTURE_STANDING_LEG_EXTENSION_RATIO:
        standing_score += 1.0

    # Penalize standing when the torso is clearly folded forward
    if torso_dx_ratio and torso_dx_ratio >= config.POSTURE_BENDING_MIN_DX_RATIO:
        standing_score -= 0.75
    if torso_height_ratio and torso_height_ratio <= config.POSTURE_BENDING_MAX_HEIGHT_RATIO:
        standing_score -= 0.35

    posture = "unknown"
    posture_conf = 0.45

    if lying_score >= lying_min and lying_score >= sitting_score + margin and lying_score >= standing_score + margin:
        posture = "lying"
        posture_conf = min(0.98, 0.54 + 0.11 * lying_score)
    elif bending_score >= bending_min and bending_score >= standing_score + 0.12 and lying_score < lying_min:
        posture = "bending"
        posture_conf = min(0.94, 0.50 + 0.11 * bending_score)
    elif sitting_score >= sitting_min and sitting_score >= standing_score + 0.12 and sitting_score >= lying_score - 0.08:
        posture = "sitting"
        posture_conf = min(0.95, 0.52 + 0.10 * sitting_score)
    elif standing_score >= standing_min:
        posture = "standing"
        posture_conf = min(0.96, 0.54 + 0.10 * standing_score)

    meta.update(
        {
            "lying_score": round(lying_score, 3),
            "sitting_score": round(sitting_score, 3),
            "standing_score": round(standing_score, 3),
            "bending_score": round(bending_score, 3),
            "posture_confidence": round(posture_conf, 3),
            "posture": posture,
        }
    )

    return (posture, meta) if return_meta else posture


def is_fall_transition(prev_posture, curr_posture):
    return prev_posture in {"standing", "sitting", "bending"} and curr_posture == "lying"
