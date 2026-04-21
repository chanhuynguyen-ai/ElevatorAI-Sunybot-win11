def classify_posture(kpts, bbox):
    if not kpts or len(kpts) < 17:
        return "unknown"

    x1, y1, x2, y2 = bbox
    w = max(1.0, x2 - x1)
    h = max(1.0, y2 - y1)

    visible = [p for p in kpts if len(p) >= 3 and p[2] > 0.25]
    if len(visible) < 5:
        return "unknown"

    ys = [p[1] for p in visible]
    torso_span = max(ys) - min(ys)

    if w / h > 1.25 or torso_span < 0.35 * h:
        return "lying"

    return "standing"



def is_fall_transition(prev_posture, curr_posture):
    return prev_posture == "standing" and curr_posture == "lying"
