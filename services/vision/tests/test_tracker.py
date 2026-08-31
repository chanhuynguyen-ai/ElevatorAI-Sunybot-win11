from elevator_vision.tracker import SimpleTracker, iou_xyxy

def test_iou_identity_box():
    assert round(iou_xyxy([0,0,10,10], [0,0,10,10]), 6) == 1.0

def test_tracker_keeps_id_for_overlapping_box():
    tracker = SimpleTracker(iou_thresh=0.2, max_age=3, smooth_alpha=1.0, min_hits=1)
    first = tracker.update([[10,10,50,50]])
    second = tracker.update([[12,12,52,52]])
    assert first and second and first[0][0] == second[0][0]
