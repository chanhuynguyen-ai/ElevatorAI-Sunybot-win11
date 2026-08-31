import numpy as np

from elevator_vision.posture import classify_posture


def _blank():
    return np.zeros((17, 3), dtype=float)


def _put(kpts, idx, x, y, conf=0.95):
    kpts[idx] = [x, y, conf]


def _add_common_head_arms(k, cx=50, y=20):
    _put(k, 0, cx, y)
    _put(k, 1, cx - 3, y - 2)
    _put(k, 2, cx + 3, y - 2)
    _put(k, 7, cx - 15, y + 35)
    _put(k, 8, cx + 15, y + 35)


def test_posture_returns_supported_label():
    kpts = _blank()
    label, meta = classify_posture(kpts, [0, 0, 100, 200], return_meta=True)
    assert label in {"unknown", "standing", "sitting", "lying", "bending"}
    assert isinstance(meta, dict)


def test_upright_full_body_is_standing():
    k = _blank()
    _add_common_head_arms(k)
    _put(k, 5, 42, 45); _put(k, 6, 58, 45)
    _put(k, 11, 45, 95); _put(k, 12, 55, 95)
    _put(k, 13, 45, 145); _put(k, 14, 55, 145)
    _put(k, 15, 45, 195); _put(k, 16, 55, 195)
    label, meta = classify_posture(k, [20, 5, 80, 205], return_meta=True)
    assert label == "standing", meta
    assert meta["torso_angle_deg"] < 10


def test_closeup_upright_missing_legs_is_not_lying():
    # This mirrors the elevator webcam failure mode: upper body fills the box,
    # knees/ankles are outside frame. The old span-ratio rules could say lying.
    k = _blank()
    _put(k, 0, 50, 18)
    _put(k, 5, 38, 50); _put(k, 6, 62, 50)
    _put(k, 7, 30, 80); _put(k, 8, 70, 80)
    _put(k, 11, 42, 125); _put(k, 12, 58, 125)
    label, meta = classify_posture(k, [15, 5, 85, 155], return_meta=True)
    assert label == "standing", meta
    assert meta["torso_angle_deg"] < 10
    assert meta["lower_body_visible"] is False


def test_horizontal_body_is_lying():
    k = _blank()
    _put(k, 0, 35, 82)
    _put(k, 5, 55, 82); _put(k, 6, 55, 98)
    _put(k, 7, 75, 75); _put(k, 8, 75, 105)
    _put(k, 11, 115, 86); _put(k, 12, 115, 102)
    _put(k, 13, 155, 88); _put(k, 14, 155, 104)
    _put(k, 15, 195, 90); _put(k, 16, 195, 106)
    label, meta = classify_posture(k, [20, 60, 210, 125], return_meta=True)
    assert label == "lying", meta
    assert meta["torso_angle_deg"] > 70


def test_seated_leg_geometry_is_sitting():
    k = _blank()
    _add_common_head_arms(k)
    _put(k, 5, 42, 45); _put(k, 6, 58, 45)
    _put(k, 11, 45, 95); _put(k, 12, 55, 95)
    _put(k, 13, 92, 105); _put(k, 14, 102, 105)
    _put(k, 15, 92, 165); _put(k, 16, 102, 165)
    label, meta = classify_posture(k, [20, 5, 115, 175], return_meta=True)
    assert label == "sitting", meta
    assert meta["knee_angle_deg"] is not None


def test_forward_torso_is_bending_not_lying():
    k = _blank()
    _put(k, 0, 105, 42)
    _put(k, 5, 87, 62); _put(k, 6, 103, 62)
    _put(k, 7, 80, 90); _put(k, 8, 112, 90)
    _put(k, 11, 48, 105); _put(k, 12, 58, 105)
    _put(k, 13, 48, 150); _put(k, 14, 58, 150)
    _put(k, 15, 48, 195); _put(k, 16, 58, 195)
    label, meta = classify_posture(k, [20, 20, 125, 205], return_meta=True)
    assert label == "bending", meta
    assert 28 <= meta["torso_angle_deg"] < 58
