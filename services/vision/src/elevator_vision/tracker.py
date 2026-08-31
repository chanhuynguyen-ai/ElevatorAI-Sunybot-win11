from dataclasses import dataclass


def iou_xyxy(a, b):
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = area_a + area_b - inter + 1e-6
    return inter / union


def smooth_bbox(old_box, new_box, alpha=0.65):
    return [
        alpha * old_box[0] + (1.0 - alpha) * new_box[0],
        alpha * old_box[1] + (1.0 - alpha) * new_box[1],
        alpha * old_box[2] + (1.0 - alpha) * new_box[2],
        alpha * old_box[3] + (1.0 - alpha) * new_box[3],
    ]


@dataclass
class Track:
    track_id: int
    bbox: list
    age: int = 0
    hits: int = 1
    misses: int = 0


class SimpleTracker:
    def __init__(self, iou_thresh=0.3, max_age=20, smooth_alpha=0.65, min_hits=1):
        self.iou_thresh = iou_thresh
        self.max_age = max_age
        self.smooth_alpha = smooth_alpha
        self.min_hits = min_hits
        self.next_id = 1
        self.tracks = {}

    def update(self, detections):
        detections = detections or []

        matched_tracks = set()
        matched_dets = set()
        candidates = []

        track_items = list(self.tracks.items())

        for tid, tr in track_items:
            for di, det in enumerate(detections):
                score = iou_xyxy(tr.bbox, det)
                if score >= self.iou_thresh:
                    candidates.append((score, tid, di))

        candidates.sort(reverse=True, key=lambda x: x[0])

        for score, tid, di in candidates:
            if tid in matched_tracks or di in matched_dets:
                continue
            tr = self.tracks[tid]
            tr.bbox = smooth_bbox(tr.bbox, detections[di], self.smooth_alpha)
            tr.age = 0
            tr.hits += 1
            tr.misses = 0
            matched_tracks.add(tid)
            matched_dets.add(di)

        for di, det in enumerate(detections):
            if di in matched_dets:
                continue
            tid = self.next_id
            self.next_id += 1
            self.tracks[tid] = Track(track_id=tid, bbox=list(det))
            matched_tracks.add(tid)

        dead = []
        for tid, tr in self.tracks.items():
            if tid not in matched_tracks:
                tr.age += 1
                tr.misses += 1
            if tr.age > self.max_age:
                dead.append(tid)

        for tid in dead:
            self.tracks.pop(tid, None)

        assigned = []
        for tid, tr in self.tracks.items():
            if tr.hits >= self.min_hits:
                assigned.append((tid, tr.bbox))
        return assigned


