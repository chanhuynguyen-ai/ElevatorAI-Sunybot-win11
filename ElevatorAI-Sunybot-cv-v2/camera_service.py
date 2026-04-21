import threading
import time
from datetime import datetime
from typing import Dict, Optional

import cv2

from app import config, db
from app.event_logger import EventLogger
from app.face_recog import create_face_app, extract_embedding, match_face
from app.posture import classify_posture, is_fall_transition
from app.tracker import SimpleTracker, iou_xyxy

COCO_PERSON = 0
COCO_BOTTLE = 39

EVENT_TITLE_MAP = {
    "BOTTLE": "Phát hiện chai nhựa",
    "FALL": "Phát hiện té ngã",
    "LYING": "Phát hiện nằm bất thường",
    "SITTING": "Phát hiện ngồi",
    "STANDING": "Phát hiện đứng",
    "CROWD": "Mật độ đông người",
    "OVERLOAD": "Quá tải cabin",
    "UNKNOWN_PERSON": "Người chưa gán nhãn",
}


class CameraService:
    def __init__(self):
        self.detector = None
        self.pose_model = None
        self.logger = EventLogger.from_config()
        self.face_app = create_face_app() if config.ENABLE_FACE else None

        self.cap = None
        self.tracker = SimpleTracker(
            iou_thresh=config.TRACK_IOU_THRESH,
            max_age=config.TRACK_MAX_AGE,
            smooth_alpha=config.TRACK_SMOOTH_ALPHA,
            min_hits=config.TRACK_MIN_HITS,
        )
        self.bottle_tracker = SimpleTracker(
            iou_thresh=config.BOTTLE_TRACK_IOU_THRESH,
            max_age=config.BOTTLE_TRACK_MAX_AGE,
            smooth_alpha=config.TRACK_SMOOTH_ALPHA,
            min_hits=config.BOTTLE_TRACK_MIN_HITS,
        )

        self.running = False
        self.thread = None
        self.latest_jpeg = None
        self.latest_frame_bgr = None
        self.lock = threading.Lock()

        self.frame_idx = 0
        self.last_occ_ts = 0.0
        self.cooldowns = {}
        self.track_state: Dict[int, Dict] = {}
        self.status = {
            "cam_id": config.CAMERA_ID,
            "online": False,
            "camera_online": False,
            "fps": 0.0,
            "people_count": 0,
            "unknown_count": 0,
            "sitting_count": 0,
            "lying_count": 0,
            "fall_count": 0,
            "overload": False,
            "last_frame_ts": None,
            "last_event_type": None,
            "last_event_title": None,
            "last_event_at": None,
            "error": None,
            "backend": config.CV_BACKEND,
            "camera_source": config.CAMERA_SOURCE,
            "face_enabled": bool(config.ENABLE_FACE),
        }

    def _open_camera(self):
        src = config.CAMERA_SOURCE
        if isinstance(src, str) and src.startswith("gst:"):
            pipeline = src[4:]
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            if cap.isOpened():
                return cap

        if str(src).isdigit():
            idx = int(src)
            for backend in (cv2.CAP_V4L2, cv2.CAP_ANY):
                cap = cv2.VideoCapture(idx, backend)
                if cap.isOpened():
                    return cap
        else:
            for backend in (cv2.CAP_GSTREAMER, cv2.CAP_ANY):
                cap = cv2.VideoCapture(src, backend)
                if cap.isOpened():
                    return cap
        return None

    def _build_runtime_inside_thread(self):
        if config.CV_BACKEND == "trt":
            from app.runtime_trt import DetectorTRT, PoseTRT

            self.detector = DetectorTRT()
            self.pose_model = PoseTRT() if config.ENABLE_POSE else None
        else:
            from app.runtime_ultra import DetectorUltra, PoseUltra

            self.detector = DetectorUltra()
            self.pose_model = PoseUltra() if config.ENABLE_POSE else None

    def _destroy_runtime(self):
        for obj in (self.pose_model, self.detector):
            if obj is not None and hasattr(obj, "destroy"):
                try:
                    obj.destroy()
                except Exception:
                    pass
        self.pose_model = None
        self.detector = None

    def _event_ready(self, key, cooldown_sec=None):
        now = time.time()
        prev = self.cooldowns.get(key, 0.0)
        cooldown_sec = config.EVENT_COOLDOWN_SEC if cooldown_sec is None else cooldown_sec
        if now - prev >= cooldown_sec:
            self.cooldowns[key] = now
            return True
        return False

    def _draw_box(self, frame, bbox, label, color):
        x1, y1, x2, y2 = map(int, bbox)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame,
            label,
            (x1, max(0, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
        )

    def _mark_last_event(self, event_type: str, event_ts: Optional[str] = None):
        event_ts = event_ts or datetime.now().isoformat()
        self.status["last_event_type"] = event_type
        self.status["last_event_title"] = EVENT_TITLE_MAP.get(event_type, event_type)
        self.status["last_event_at"] = event_ts

    def _log_event(
        self,
        event_type,
        track_id=None,
        person_id=None,
        bbox=None,
        posture=None,
        people_count=None,
        person_name=None,
        confidence=None,
        extra=None,
        snapshot_path=None,
    ):
        payload = {
            "cam_id": config.CAMERA_ID,
            "event_type": event_type,
            "track_id": str(track_id) if track_id is not None else None,
            "person_id": person_id,
            "person_name": person_name,
            "bbox": bbox,
            "posture": posture,
            "people_count": people_count,
            "confidence": confidence,
            "snapshot_path": snapshot_path,
            "extra": extra or {},
        }
        result = self.logger.log_event(**payload)
        event_ts = None
        if isinstance(result, dict):
            raw_ts = result.get("event_ts")
            event_ts = raw_ts.isoformat() if hasattr(raw_ts, "isoformat") else raw_ts
        self._mark_last_event(event_type, event_ts)
        return result

    def _posture_confirm_frames(self, posture: str) -> int:
        if posture == "lying":
            return max(1, config.LYING_CONFIRM_FRAMES)
        if posture == "sitting":
            return max(1, config.SITTING_CONFIRM_FRAMES)
        if posture == "unknown":
            return max(1, config.POSTURE_CONFIRM_UNKNOWN_FRAMES)
        return 1

    def _crop_face_region(self, frame, bbox):
        if frame is None or bbox is None:
            return None
        x1, y1, x2, y2 = [int(v) for v in bbox]
        h, w = frame.shape[:2]
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        margin_x = int(bw * config.FACE_MARGIN_RATIO)
        margin_y = int(bh * config.FACE_MARGIN_RATIO)
        face_h = int(bh * config.FACE_TOP_RATIO)
        xx1 = max(0, x1 - margin_x)
        yy1 = max(0, y1 - margin_y)
        xx2 = min(w, x2 + margin_x)
        yy2 = min(h, y1 + face_h + margin_y)
        if xx2 <= xx1 or yy2 <= yy1:
            return None
        return frame[yy1:yy2, xx1:xx2].copy()

    def _update_identity(self, frame, tid, bbox, state, people_count):
        if self.face_app is None:
            return

        now_ts = time.time()
        last_face_check_ts = state.get("last_face_check_ts", 0.0)
        if now_ts - last_face_check_ts < config.FACE_RECHECK_SEC:
            return
        state["last_face_check_ts"] = now_ts

        crop = self._crop_face_region(frame, bbox)
        if crop is None or crop.size == 0:
            return

        embedding = extract_embedding(face_app=self.face_app, frame=crop)
        if embedding is None:
            return

        match = match_face(embedding)
        if match:
            state["person_id"] = match.get("person_id")
            state["person_name"] = match.get("person_name")
            state["face_score"] = match.get("score")
            return

        last_unknown_ts = state.get("last_unknown_event_ts", 0.0)
        if now_ts - last_unknown_ts >= config.FACE_UNKNOWN_COOLDOWN_SEC and self._event_ready(("UNKNOWN_PERSON", tid)):
            state["last_unknown_event_ts"] = now_ts
            self._log_event(
                "UNKNOWN_PERSON",
                track_id=tid,
                person_id=None,
                person_name=None,
                bbox=bbox,
                posture=state.get("posture") or "unknown",
                people_count=people_count,
                confidence=0.0,
                extra={"reason": "face_not_registered"},
            )

    def _log_posture_change(self, tid, state, confirmed_posture, bbox, people_count):
        if confirmed_posture not in {"sitting", "standing"}:
            return
        event_type = confirmed_posture.upper()
        cooldown = config.POSTURE_EVENT_COOLDOWN_SEC
        if self._event_ready((event_type, tid), cooldown_sec=cooldown):
            self._log_event(
                event_type,
                track_id=tid,
                person_id=state.get("person_id"),
                person_name=state.get("person_name"),
                bbox=bbox,
                posture=confirmed_posture,
                people_count=people_count,
                confidence=(state.get("posture_meta") or {}).get("posture_confidence"),
                extra={"reason": "posture_transition"},
            )

    def _prime_status_from_db(self):
        try:
            latest_sample = db.fetch_latest_sample() or {}
            latest_event = db.fetch_latest_event() or {}
            if latest_sample:
                self.status["people_count"] = latest_sample.get("people_count") or 0
                self.status["unknown_count"] = latest_sample.get("unknown_count") or 0
                self.status["sitting_count"] = latest_sample.get("sitting_count") or 0
                self.status["lying_count"] = latest_sample.get("lying_count") or 0
                self.status["fall_count"] = latest_sample.get("fall_count") or 0
            if latest_event:
                raw_ts = latest_event.get("event_ts")
                self._mark_last_event(
                    latest_event.get("event_type") or "UNKNOWN",
                    raw_ts.isoformat() if hasattr(raw_ts, "isoformat") else raw_ts,
                )
        except Exception:
            pass

    def _run_loop(self):
        last_fps_ts = time.time()
        fps_count = 0
        last_person_dets = []
        last_bottle_dets = []
        last_poses = []

        try:
            self._prime_status_from_db()
            self.cap = self._open_camera()
            if self.cap is None:
                self.status["online"] = False
                self.status["camera_online"] = False
                self.status["error"] = (
                    "Khong mo duoc camera. Dat CAMERA_SOURCE=0 cho webcam USB, "
                    "hoac CAMERA_SOURCE='gst:<pipeline>' cho pipeline GStreamer."
                )
                return

            self._build_runtime_inside_thread()
            if self.detector is None:
                self.status["online"] = False
                self.status["camera_online"] = False
                self.status["error"] = "Khong tao duoc detector runtime"
                return

            self.status["error"] = None

            while self.running:
                ok, frame = self.cap.read()
                if not ok or frame is None:
                    self.status["online"] = False
                    self.status["camera_online"] = False
                    self.status["error"] = "Doc frame that bai tu camera"
                    time.sleep(0.1)
                    continue

                self.status["online"] = True
                self.status["camera_online"] = True
                self.status["last_frame_ts"] = datetime.now().isoformat()
                self.status["error"] = None
                self.frame_idx += 1
                fps_count += 1

                if time.time() - last_fps_ts >= 1.0:
                    self.status["fps"] = fps_count / max(time.time() - last_fps_ts, 1e-6)
                    fps_count = 0
                    last_fps_ts = time.time()

                if self.frame_idx % max(1, config.YOLO_EVERY_N) == 0:
                    dets = self.detector.predict(frame)
                    last_person_dets = [d for d in dets if d.get("cls") == COCO_PERSON]
                    last_bottle_dets = [d for d in dets if d.get("cls") == COCO_BOTTLE]

                if self.pose_model is not None and self.frame_idx % max(1, config.POSE_EVERY_N) == 0:
                    last_poses = self.pose_model.predict(frame)

                track_assignments = self.tracker.update([d["bbox"] for d in last_person_dets])
                bottle_assignments = self.bottle_tracker.update([d["bbox"] for d in last_bottle_dets])

                pose_by_track = {}
                for pose in last_poses:
                    best_tid, best_iou = None, 0.0
                    for tid, tb in track_assignments:
                        score = iou_xyxy(pose["bbox"], tb)
                        if score > best_iou:
                            best_tid, best_iou = tid, score
                    if best_tid is not None and best_iou >= 0.25:
                        pose_by_track[best_tid] = pose

                people_count = len(track_assignments)
                unknown_count = 0
                sitting_count = 0
                lying_count = 0
                fall_count = 0

                overload = people_count >= config.OVERLOAD_THRESHOLD
                self.status["overload"] = overload

                if people_count >= config.CROWD_THRESHOLD and self._event_ready(("CROWD", config.CAMERA_ID)):
                    self._log_event(
                        "CROWD",
                        people_count=people_count,
                        extra={"threshold": config.CROWD_THRESHOLD},
                    )

                if overload and self._event_ready(("OVERLOAD", config.CAMERA_ID)):
                    self._log_event(
                        "OVERLOAD",
                        people_count=people_count,
                        extra={"threshold": config.OVERLOAD_THRESHOLD},
                    )

                if len(bottle_assignments) > 0 and self._event_ready(("BOTTLE", config.CAMERA_ID)):
                    self._log_event(
                        "BOTTLE",
                        people_count=people_count,
                        extra={"count": len(bottle_assignments)},
                    )

                now_ts = time.time()

                for tid, bbox in track_assignments:
                    state = self.track_state.setdefault(
                        tid,
                        {
                            "posture": "unknown",
                            "posture_candidate": "unknown",
                            "candidate_streak": 0,
                            "last_upright_ts": now_ts,
                            "danger_until": 0.0,
                            "person_name": None,
                            "person_id": None,
                            "face_score": None,
                            "last_face_check_ts": 0.0,
                            "last_unknown_event_ts": 0.0,
                            "last_center": None,
                            "last_motion_ts": now_ts,
                            "posture_meta": {},
                            "fall_candidate_streak": 0,
                            "last_logged_posture": None,
                        },
                    )

                    candidate_posture = "unknown"
                    posture_meta = {"ok": False, "reason": "no_pose"}
                    if tid in pose_by_track:
                        candidate_posture, posture_meta = classify_posture(
                            pose_by_track[tid]["keypoints"], bbox, return_meta=True
                        )

                    if candidate_posture == state["posture_candidate"]:
                        state["candidate_streak"] += 1
                    else:
                        state["posture_candidate"] = candidate_posture
                        state["candidate_streak"] = 1

                    confirmed_posture = state["posture"]
                    if candidate_posture != "unknown" and state["candidate_streak"] >= self._posture_confirm_frames(candidate_posture):
                        confirmed_posture = candidate_posture
                    elif candidate_posture == "unknown" and state["candidate_streak"] >= self._posture_confirm_frames("unknown"):
                        confirmed_posture = state["posture"]

                    prev_posture = state["posture"]
                    state["posture"] = confirmed_posture
                    state["posture_meta"] = posture_meta

                    if confirmed_posture != prev_posture and confirmed_posture in {"sitting", "standing"}:
                        self._log_posture_change(tid, state, confirmed_posture, bbox, people_count)
                        state["last_logged_posture"] = confirmed_posture

                    self._update_identity(frame, tid, bbox, state, people_count)

                    x1, y1, x2, y2 = bbox
                    center = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
                    prev_center = state.get("last_center")
                    prev_motion_ts = state.get("last_motion_ts", now_ts)
                    dt = max(now_ts - prev_motion_ts, 1e-3)
                    center_drop_ratio = 0.0
                    vertical_speed = 0.0
                    if prev_center is not None:
                        center_drop = max(center[1] - prev_center[1], 0.0)
                        center_drop_ratio = center_drop / max(float(y2 - y1), 1.0)
                        vertical_speed = center_drop / dt

                    state["last_center"] = center
                    state["last_motion_ts"] = now_ts

                    if confirmed_posture in {"standing", "sitting"}:
                        state["last_upright_ts"] = now_ts

                    is_danger = False
                    posture_conf = float((posture_meta or {}).get("posture_confidence") or 0.0)
                    event_extra = {
                        "posture_metrics": posture_meta,
                        "center_drop_ratio": round(center_drop_ratio, 3),
                        "vertical_speed": round(vertical_speed, 2),
                        "face_score": state.get("face_score"),
                    }

                    if confirmed_posture == "unknown":
                        unknown_count += 1
                    elif confirmed_posture == "sitting":
                        sitting_count += 1
                    elif confirmed_posture == "lying":
                        lying_count += 1
                        is_danger = True
                        if self._event_ready(("LYING", tid)):
                            self._log_event(
                                "LYING",
                                track_id=tid,
                                person_id=state.get("person_id"),
                                bbox=bbox,
                                posture=confirmed_posture,
                                people_count=people_count,
                                person_name=state.get("person_name"),
                                confidence=posture_conf,
                                extra=event_extra,
                            )

                    fall_candidate = (
                        confirmed_posture == "lying"
                        and posture_conf >= 0.58
                        and is_fall_transition(prev_posture, confirmed_posture)
                        and (
                            center_drop_ratio >= config.FALL_MIN_CENTER_DROP_RATIO
                            or vertical_speed >= config.FALL_MIN_VERTICAL_SPEED
                            or now_ts - state["last_upright_ts"] <= config.FALL_MAX_TRANSITION_SEC
                        )
                    )
                    if fall_candidate:
                        state["fall_candidate_streak"] = state.get("fall_candidate_streak", 0) + 1
                    else:
                        state["fall_candidate_streak"] = 0

                    if state["fall_candidate_streak"] >= max(1, config.FALL_CONFIRM_FRAMES):
                        fall_count += 1
                        is_danger = True
                        state["danger_until"] = now_ts + config.DANGER_HOLD_SEC
                        if self._event_ready(("FALL", tid)):
                            self._log_event(
                                "FALL",
                                track_id=tid,
                                person_id=state.get("person_id"),
                                bbox=bbox,
                                posture=confirmed_posture,
                                people_count=people_count,
                                person_name=state.get("person_name"),
                                confidence=posture_conf,
                                extra=event_extra,
                            )
                            state["fall_candidate_streak"] = 0

                    if now_ts < state["danger_until"]:
                        is_danger = True

                    person_name = state.get("person_name") or ("track:%s" % tid)
                    posture_text = confirmed_posture
                    if posture_conf:
                        posture_text = "%s %.2f" % (confirmed_posture, posture_conf)
                    color = (0, 0, 255) if is_danger else (0, 255, 0)
                    self._draw_box(frame, bbox, "%s | %s" % (person_name, posture_text), color)

                # clean dead tracks
                active_ids = {tid for tid, _ in track_assignments}
                stale_ids = [tid for tid in self.track_state.keys() if tid not in active_ids]
                for tid in stale_ids:
                    self.track_state.pop(tid, None)

                for _, bottle_bbox in bottle_assignments:
                    self._draw_box(frame, bottle_bbox, "bottle", (0, 140, 255))

                if overload:
                    cv2.putText(
                        frame,
                        "OVERLOAD",
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (0, 0, 255),
                        3,
                    )

                self.status["people_count"] = people_count
                self.status["unknown_count"] = unknown_count
                self.status["sitting_count"] = sitting_count
                self.status["lying_count"] = lying_count
                self.status["fall_count"] = fall_count

                if time.time() - self.last_occ_ts >= config.OCCUPANCY_SAMPLE_SEC:
                    self.last_occ_ts = time.time()
                    self.logger.log_occupancy(
                        cam_id=config.CAMERA_ID,
                        people_count=people_count,
                        unknown_count=unknown_count,
                        sitting_count=sitting_count,
                        lying_count=lying_count,
                        fall_count=fall_count,
                        extra={
                            "fps": self.status["fps"],
                            "overload": overload,
                            "overload_threshold": config.OVERLOAD_THRESHOLD,
                            "backend": config.CV_BACKEND,
                        },
                    )

                ok, jpeg = cv2.imencode(".jpg", frame)
                if ok:
                    with self.lock:
                        self.latest_jpeg = jpeg.tobytes()
                        self.latest_frame_bgr = frame.copy()

        except Exception as ex:
            self.status["online"] = False
            self.status["camera_online"] = False
            self.status["error"] = repr(ex)
        finally:
            try:
                if self.cap is not None:
                    self.cap.release()
            except Exception:
                pass
            self._destroy_runtime()

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def mjpeg_generator(self):
        while True:
            with self.lock:
                frame = self.latest_jpeg
            if frame is not None:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            time.sleep(0.03)

    def get_latest_frame_copy(self):
        with self.lock:
            if self.latest_frame_bgr is None:
                return None
            return self.latest_frame_bgr.copy()

    def stop(self):
        self.running = False
        try:
            if self.thread is not None and self.thread.is_alive():
                self.thread.join(timeout=2.0)
        except Exception:
            pass
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass
        self._destroy_runtime()

    def get_status(self):
        return dict(self.status)
