import math
from typing import Any, Dict, Optional, Sequence

from elevator_vision import config


def _safe_visible(kpts, idx, conf: Optional[float] = None):
    conf = config.POSE_KEYPOINT_CONF if conf is None else conf

    if idx >= len(kpts):
        return None

    p = kpts[idx]

    if len(p) < 3 or float(p[2]) <= conf:
        return None

    return (
        float(p[0]),
        float(p[1]),
        float(p[2]),
    )


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


def _angle_from_vertical(a, b) -> Optional[float]:
    """
    Angle of vector AB relative to vertical.

    0 degrees  = perfectly vertical/upright
    90 degrees = perfectly horizontal
    """

    if a is None or b is None:
        return None

    dx = abs(float(b[0]) - float(a[0]))
    dy = abs(float(b[1]) - float(a[1]))

    if dx < 1e-6 and dy < 1e-6:
        return None

    return math.degrees(
        math.atan2(
            dx,
            max(dy, 1e-6),
        )
    )


def _joint_angle(a, b, c) -> Optional[float]:
    """
    Calculate angle ABC.

    Mainly used for:
        hip -> knee -> ankle
    """

    if a is None or b is None or c is None:
        return None

    bax = float(a[0]) - float(b[0])
    bay = float(a[1]) - float(b[1])

    bcx = float(c[0]) - float(b[0])
    bcy = float(c[1]) - float(b[1])

    na = math.hypot(bax, bay)
    nc = math.hypot(bcx, bcy)

    if na < 1e-6 or nc < 1e-6:
        return None

    cos_v = (
        bax * bcx + bay * bcy
    ) / (
        na * nc
    )

    cos_v = max(
        -1.0,
        min(1.0, cos_v),
    )

    return math.degrees(
        math.acos(cos_v)
    )


def _mean(
    values: Sequence[Optional[float]],
) -> Optional[float]:

    values = [
        float(v)
        for v in values
        if v is not None
    ]

    if not values:
        return None

    return sum(values) / len(values)


def _metrics_from_pose(
    kpts,
    bbox,
) -> Dict[str, Any]:

    x1, y1, x2, y2 = [
        float(v)
        for v in bbox
    ]

    width = max(
        1.0,
        x2 - x1,
    )

    height = max(
        1.0,
        y2 - y1,
    )

    visible = [
        (
            float(p[0]),
            float(p[1]),
            float(p[2]),
        )
        for p in kpts
        if len(p) >= 3
        and float(p[2]) > config.POSE_KEYPOINT_CONF
    ]

    if len(visible) < config.POSTURE_MIN_VISIBLE_KPTS:
        return {
            "ok": False,
            "reason": "too_few_keypoints",
            "visible_count": len(visible),
        }

    xs = [
        p[0]
        for p in visible
    ]

    ys = [
        p[1]
        for p in visible
    ]

    x_span = max(xs) - min(xs)
    y_span = max(ys) - min(ys)

    # COCO Pose indexes
    left_shoulder = _safe_visible(
        kpts,
        5,
    )

    right_shoulder = _safe_visible(
        kpts,
        6,
    )

    left_hip = _safe_visible(
        kpts,
        11,
    )

    right_hip = _safe_visible(
        kpts,
        12,
    )

    left_knee = _safe_visible(
        kpts,
        13,
    )

    right_knee = _safe_visible(
        kpts,
        14,
    )

    left_ankle = _safe_visible(
        kpts,
        15,
    )

    right_ankle = _safe_visible(
        kpts,
        16,
    )

    shoulder = _center(
        left_shoulder,
        right_shoulder,
    )

    hip = _center(
        left_hip,
        right_hip,
    )

    knee = _center(
        left_knee,
        right_knee,
    )

    ankle = _center(
        left_ankle,
        right_ankle,
    )

    # PRIMARY SIGNAL FOR BODY ORIENTATION
    torso_angle = _angle_from_vertical(
        shoulder,
        hip,
    )

    hip_knee_angle = _angle_from_vertical(
        hip,
        knee,
    )

    left_knee_angle = _joint_angle(
        left_hip,
        left_knee,
        left_ankle,
    )

    right_knee_angle = _joint_angle(
        right_hip,
        right_knee,
        right_ankle,
    )

    knee_angle = _mean(
        [
            left_knee_angle,
            right_knee_angle,
        ]
    )

    shoulder_width = None

    if (
        left_shoulder is not None
        and right_shoulder is not None
    ):
        shoulder_width = math.hypot(
            left_shoulder[0] - right_shoulder[0],
            left_shoulder[1] - right_shoulder[1],
        )

    torso_length = None

    if (
        shoulder is not None
        and hip is not None
    ):
        torso_length = math.hypot(
            shoulder[0] - hip[0],
            shoulder[1] - hip[1],
        )

    lower_body_visible = (
        sum(
            p is not None
            for p in [
                left_knee,
                right_knee,
                left_ankle,
                right_ankle,
            ]
        )
        >= 2
    )

    core_visible = (
        shoulder is not None
        and hip is not None
    )

    cloud_horizontal_ratio = _ratio(
        x_span,
        max(y_span, 1.0),
    )

    return {
        "ok": True,

        "visible_count":
            len(visible),

        "bbox_aspect_ratio":
            _ratio(
                width,
                height,
            ),

        "visible_x_span_ratio":
            _ratio(
                x_span,
                width,
            ),

        "visible_y_span_ratio":
            _ratio(
                y_span,
                height,
            ),

        "cloud_horizontal_ratio":
            cloud_horizontal_ratio,

        "torso_angle_deg":
            torso_angle,

        "hip_knee_angle_deg":
            hip_knee_angle,

        "knee_angle_deg":
            knee_angle,

        "shoulder_width_ratio":
            (
                _ratio(
                    shoulder_width,
                    width,
                )
                if shoulder_width is not None
                else None
            ),

        "torso_length_ratio":
            (
                _ratio(
                    torso_length,
                    height,
                )
                if torso_length is not None
                else None
            ),

        "core_visible":
            core_visible,

        "lower_body_visible":
            lower_body_visible,
    }


def _bounded_conf(
    base: float,
    score: float,
    scale: float = 0.08,
    high: float = 0.97,
) -> float:

    return max(
        0.0,
        min(
            high,
            base
            + scale
            * max(
                score,
                0.0,
            ),
        ),
    )


def classify_posture(
    kpts,
    bbox,
    return_meta: bool = False,
):
    """
    Posture classifier V2.

    Important design:

    lying:
        primarily determined using torso orientation.

    bounding-box:
        secondary signal only.

    This prevents an upright person near the camera
    from being detected as lying simply because
    legs are outside the image.
    """

    if (
        kpts is None
        or len(kpts) < 17
    ):

        meta = {
            "ok": False,
            "reason": "missing_pose",
            "posture_confidence": 0.0,
        }

        return (
            ("unknown", meta)
            if return_meta
            else "unknown"
        )

    meta = _metrics_from_pose(
        kpts,
        bbox,
    )

    if not meta.get("ok"):

        meta[
            "posture_confidence"
        ] = 0.0

        return (
            ("unknown", meta)
            if return_meta
            else "unknown"
        )

    bbox_ar = float(
        meta.get(
            "bbox_aspect_ratio"
        )
        or 0.0
    )

    cloud_horizontal = float(
        meta.get(
            "cloud_horizontal_ratio"
        )
        or 0.0
    )

    torso_angle = meta.get(
        "torso_angle_deg"
    )

    hip_knee_angle = meta.get(
        "hip_knee_angle_deg"
    )

    knee_angle = meta.get(
        "knee_angle_deg"
    )

    core_visible = bool(
        meta.get(
            "core_visible"
        )
    )

    lower_body_visible = bool(
        meta.get(
            "lower_body_visible"
        )
    )

    lying_torso_angle = float(
        getattr(
            config,
            "POSTURE_LYING_TORSO_ANGLE_DEG",
            58.0,
        )
    )

    bending_torso_angle = float(
        getattr(
            config,
            "POSTURE_BENDING_TORSO_ANGLE_DEG",
            28.0,
        )
    )

    upright_torso_angle = float(
        getattr(
            config,
            "POSTURE_UPRIGHT_TORSO_ANGLE_DEG",
            24.0,
        )
    )

    lying_ar = float(
        getattr(
            config,
            "POSTURE_LYING_BBOX_AR",
            1.12,
        )
    )

    lying_cloud = float(
        getattr(
            config,
            "POSTURE_LYING_CLOUD_RATIO",
            1.18,
        )
    )

    sitting_knee_max = float(
        getattr(
            config,
            "POSTURE_SITTING_KNEE_MAX_DEG",
            145.0,
        )
    )

    standing_knee_min = float(
        getattr(
            config,
            "POSTURE_STANDING_KNEE_MIN_DEG",
            150.0,
        )
    )

    # ==========================
    # LYING SCORE
    # ==========================

    lying_score = 0.0
    horizontal_votes = 0

    if (
        torso_angle is not None
        and torso_angle >= lying_torso_angle
    ):
        lying_score += 2.2
        horizontal_votes += 2

    elif (
        torso_angle is not None
        and torso_angle
        >= lying_torso_angle - 10.0
    ):
        lying_score += 0.8
        horizontal_votes += 1

    if bbox_ar >= lying_ar:
        lying_score += 0.75
        horizontal_votes += 1

    if (
        cloud_horizontal
        >= lying_cloud
    ):
        lying_score += 0.75
        horizontal_votes += 1

    # Important false-positive guard
    if (
        torso_angle is not None
        and torso_angle
        <= upright_torso_angle
    ):
        lying_score -= 2.0

    if bbox_ar < 0.85:
        lying_score -= 0.45

    # ==========================
    # SITTING SCORE
    # ==========================

    sitting_score = 0.0

    if (
        torso_angle is not None
        and torso_angle
        <= bending_torso_angle + 8.0
    ):
        sitting_score += 0.8

    if (
        knee_angle is not None
        and 55.0
        <= knee_angle
        <= sitting_knee_max
    ):
        sitting_score += 1.8

    if (
        hip_knee_angle is not None
        and hip_knee_angle >= 35.0
    ):
        sitting_score += 0.55

    if lower_body_visible:
        sitting_score += 0.25

    if bbox_ar >= lying_ar:
        sitting_score -= 0.8

    # ==========================
    # BENDING SCORE
    # ==========================

    bending_score = 0.0

    if (
        torso_angle is not None
        and bending_torso_angle
        <= torso_angle
        < lying_torso_angle
    ):

        bending_score += (
            1.2
            + (
                torso_angle
                - bending_torso_angle
            )
            / max(
                lying_torso_angle
                - bending_torso_angle,
                1.0,
            )
        )

    if (
        knee_angle is not None
        and knee_angle
        >= standing_knee_min
    ):
        bending_score += 0.35

    if bbox_ar >= lying_ar:
        bending_score -= 0.4

    # ==========================
    # STANDING SCORE
    # ==========================

    standing_score = 0.0

    if (
        torso_angle is not None
        and torso_angle
        <= upright_torso_angle
    ):
        standing_score += 2.0

    elif (
        torso_angle is not None
        and torso_angle
        <= bending_torso_angle
    ):
        standing_score += 1.25

    if (
        knee_angle is not None
        and knee_angle
        >= standing_knee_min
    ):
        standing_score += 1.2

    elif (
        not lower_body_visible
        and core_visible
    ):
        # Camera close-up:
        # conservative upright classification.
        standing_score += 0.75

    if bbox_ar < 0.9:
        standing_score += 0.35

    if (
        cloud_horizontal
        >= lying_cloud
    ):
        standing_score -= 0.35

    posture = "unknown"
    posture_conf = 0.0

    strong_horizontal_torso = (
        torso_angle is not None
        and torso_angle
        >= lying_torso_angle
    )

    # ==========================
    # FINAL CLASSIFICATION
    # ==========================

    if (
        lying_score >= 2.0
        and (
            horizontal_votes >= 2
            or strong_horizontal_torso
        )
    ):

        posture = "lying"

        posture_conf = _bounded_conf(
            0.60,
            lying_score,
            0.09,
        )

    elif (
        sitting_score >= 2.25
        and sitting_score
        >= standing_score + 0.35
    ):

        posture = "sitting"

        posture_conf = _bounded_conf(
            0.58,
            sitting_score,
            0.08,
            0.94,
        )

    elif (
        bending_score >= 1.45
        and bending_score
        >= standing_score + 0.15
    ):

        posture = "bending"

        posture_conf = _bounded_conf(
            0.56,
            bending_score,
            0.09,
            0.93,
        )

    elif standing_score >= 1.65:

        posture = "standing"

        posture_conf = _bounded_conf(
            0.58,
            standing_score,
            0.08,
            0.95,
        )

    meta.update(
        {
            "lying_score":
                round(
                    lying_score,
                    3,
                ),

            "sitting_score":
                round(
                    sitting_score,
                    3,
                ),

            "standing_score":
                round(
                    standing_score,
                    3,
                ),

            "bending_score":
                round(
                    bending_score,
                    3,
                ),

            "horizontal_votes":
                int(
                    horizontal_votes
                ),

            "posture_confidence":
                round(
                    posture_conf,
                    3,
                ),

            "posture":
                posture,

            "classifier_version":
                "v2-torso-angle",
        }
    )

    return (
        (posture, meta)
        if return_meta
        else posture
    )


def is_fall_transition(
    prev_posture,
    curr_posture,
):
    return (
        prev_posture
        in {
            "standing",
            "sitting",
            "bending",
        }
        and curr_posture
        == "lying"
    )