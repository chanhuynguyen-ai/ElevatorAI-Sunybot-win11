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


@dataclass
class Track:
    track_id: int
    bbox: list
    age: int = 0
    hits: int = 1


class SimpleTracker:
    def __init__(self, iou_thresh=0.3, max_age=20):
        self.iou_thresh = iou_thresh
        self.max_age = max_age
        self.next_id = 1
        self.tracks = {}

    def update(self, detections):
        matched = set()
        assigned = []

        for det in detections:
            best_id, best_iou = None, 0.0
            for tid, tr in self.tracks.items():
                score = iou_xyxy(det, tr.bbox)
                if score > best_iou:
                    best_iou = score
                    best_id = tid
            if best_id is not None and best_iou >= self.iou_thresh:
                self.tracks[best_id].bbox = det
                self.tracks[best_id].age = 0
                self.tracks[best_id].hits += 1
                matched.add(best_id)
                assigned.append((best_id, det))
            else:
                tid = self.next_id
                self.next_id += 1
                self.tracks[tid] = Track(track_id=tid, bbox=det)
                matched.add(tid)
                assigned.append((tid, det))

        dead = []
        for tid, tr in self.tracks.items():
            if tid not in matched:
                tr.age += 1
            if tr.age > self.max_age:
                dead.append(tid)
        for tid in dead:
            self.tracks.pop(tid, None)

        return assigned
