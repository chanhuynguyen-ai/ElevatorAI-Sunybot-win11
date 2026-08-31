import threading
import time
from datetime import datetime

import cv2
import numpy as np

from elevator_vision import config
from elevator_vision.event_logger import EventLogger
from elevator_vision.face_recog import create_face_app, extract_embedding, match_face
from elevator_vision.posture import classify_posture
from elevator_vision.tracker import SimpleTracker, iou_xyxy

COCO_PERSON = 0
COCO_BOTTLE = 39


class SyntheticCapture:
    """Small OpenCV-compatible source for smoke tests without a physical camera."""
    def __init__(self, width=960, height=540):
        self.width = width
        self.height = height
        self.opened = True
        self.counter = 0

    def isOpened(self):
        return self.opened

    def read(self):
        self.counter += 1
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        cv2.putText(frame, "ElevatorAI Vision - mock camera", (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)
        cv2.putText(frame, "frame %d" % self.counter, (40, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180,180,180), 2)
        return True, frame

    def release(self):
        self.opened = False


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
        self.track_state = {}
        self.status = {
            "cam_id": config.CAMERA_ID,
            "online": False,
            "fps": 0.0,
            "people_count": 0,
            "unknown_count": 0,
            "sitting_count": 0,
            "lying_count": 0,
            "fall_count": 0,
            "overload": False,
            "last_frame_ts": None,
            "error": None,
            "backend": config.CV_BACKEND,
            "camera_source": config.CAMERA_SOURCE,
            "face_enabled": bool(config.ENABLE_FACE),
        }

    def _open_camera(self):
        src = config.CAMERA_SOURCE
        if str(src).strip().lower() == "mock":
            return SyntheticCapture()
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
            from elevator_vision.runtimes.tensorrt import DetectorTRT, PoseTRT
            self.detector = DetectorTRT()
            self.pose_model = PoseTRT() if config.ENABLE_POSE else None
        elif config.CV_BACKEND == "ultralytics":
            from elevator_vision.runtimes.ultralytics import DetectorUltra, PoseUltra
            self.detector = DetectorUltra()
            self.pose_model = PoseUltra() if config.ENABLE_POSE else None
        elif config.CV_BACKEND == "mock":
            from elevator_vision.runtimes.mock import MockDetector, MockPose
            self.detector = MockDetector()
            self.pose_model = MockPose() if config.ENABLE_POSE else None
        else:
            raise ValueError("Unsupported CV_BACKEND: %s" % config.CV_BACKEND)

    def _destroy_runtime(self):
        for obj in (self.pose_model, self.detector):
            if obj is not None and hasattr(obj, "destroy"):
                try:
                    obj.destroy()
                except Exception:
                    pass
        self.pose_model = None
        self.detector = None

    def _event_ready(self, key):
        now = time.time()
        prev = self.cooldowns.get(key, 0.0)
        if now - prev >= config.EVENT_COOLDOWN_SEC:
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
    ):
        self.logger.log_event(
            cam_id=config.CAMERA_ID,
            event_type=event_type,
            track_id=str(track_id) if track_id is not None else None,
            person_id=person_id,
            person_name=person_name,
            bbox=bbox,
            posture=posture,
            people_count=people_count,
            confidence=confidence,
            snapshot_path=None,
            extra=extra or {},
        )

    def _posture_confirm_frames(self, posture: str) -> int:
        if posture == "lying":
            return max(1, config.LYING_CONFIRM_FRAMES)
        if posture == "sitting":
            return max(1, config.SITTING_CONFIRM_FRAMES)
        if posture == "bending":
            return max(1, config.BENDING_CONFIRM_FRAMES)
        if posture == "unknown":
            return max(1, config.POSTURE_CONFIRM_UNKNOWN_FRAMES)
        return 1

    def _decay_counter(self, value: int, step: int) -> int:
        return max(0, int(value) - max(1, int(step)))

    def _ema(self, prev_value: float, next_value: float, alpha: float) -> float:
        alpha = min(1.0, max(0.05, float(alpha)))
        return (1.0 - alpha) * float(prev_value or 0.0) + alpha * float(next_value or 0.0)

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

    def _run_loop(self):
        last_fps_ts = time.time()
        fps_count = 0
        last_person_dets = []
        last_bottle_dets = []
        last_poses = []

        try:
            self.cap = self._open_camera()
            if self.cap is None:
                self.status["error"] = (
                    "Khong mo duoc camera. Dat CAMERA_SOURCE=0 cho webcam USB, "
                    "hoac CAMERA_SOURCE='gst:<pipeline>' cho pipeline GStreamer."
                )
                return

            self._build_runtime_inside_thread()
            if self.detector is None:
                self.status["error"] = "Khong tao duoc detector runtime"
                return

            self.status["error"] = None

            while self.running:
                ok, frame = self.cap.read()
                if not ok or frame is None:
                    self.status["online"] = False
                    self.status["error"] = "Doc frame that bai tu camera"
                    time.sleep(0.1)
                    continue

                self.status["online"] = True
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
                    if best_tid is not None and best_iou >= config.POSE_TRACK_MATCH_IOU:
                        pose_by_track[best_tid] = pose

                people_count = len(track_assignments)
                unknown_count = 0
                sitting_count = 0
                lying_count = 0
                fall_count = 0

                overload = people_count >= config.OVERLOAD_THRESHOLD
                self.status["overload"] = overload

                if people_count >= config.CROWD_THRESHOLD and self._event_ready(("CROWD", config.CAMERA_ID)):
                    self._log_event("CROWD", people_count=people_count, extra={"threshold": config.CROWD_THRESHOLD})

                if overload and self._event_ready(("OVERLOAD", config.CAMERA_ID)):
                    self._log_event("OVERLOAD", people_count=people_count, extra={"threshold": config.OVERLOAD_THRESHOLD})

                if len(bottle_assignments) > 0 and self._event_ready(("BOTTLE", config.CAMERA_ID)):
                    self._log_event("BOTTLE", people_count=people_count, extra={"count": len(bottle_assignments)})

                now_ts = time.time()

                for tid, bbox in track_assignments:
                    state = self.track_state.setdefault(
                        tid,
                        {
                            "posture": "unknown",
                            "posture_candidate": "unknown",
                            "candidate_streak": 0,
                            "last_upright_ts": now_ts,
                            "last_non_lying_posture": "unknown",
                            "lying_started_ts": 0.0,
                            "danger_until": 0.0,
                            "danger_reason": None,
                            "person_name": None,
                            "person_id": None,
                            "face_score": None,
                            "last_face_check_ts": 0.0,
                            "last_unknown_event_ts": 0.0,
                            "last_center": None,
                            "last_motion_ts": now_ts,
                            "posture_meta": {},
                            "fall_candidate_streak": 0,
                            "smoothed_drop_ratio": 0.0,
                            "smoothed_vertical_speed": 0.0,
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

                    state["posture"] = confirmed_posture
                    state["posture_meta"] = posture_meta
                    state["last_bbox"] = list(bbox)

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

                    state["smoothed_drop_ratio"] = self._ema(
                        state.get("smoothed_drop_ratio", 0.0),
                        center_drop_ratio,
                        config.FALL_SPEED_EMA_ALPHA,
                    )
                    state["smoothed_vertical_speed"] = self._ema(
                        state.get("smoothed_vertical_speed", 0.0),
                        vertical_speed,
                        config.FALL_SPEED_EMA_ALPHA,
                    )

                    state["last_center"] = center
                    state["last_motion_ts"] = now_ts

                    if confirmed_posture in {"standing", "sitting", "bending"}:
                        state["last_upright_ts"] = now_ts
                        state["last_non_lying_posture"] = confirmed_posture
                        state["lying_started_ts"] = 0.0
                    elif confirmed_posture == "lying" and state.get("lying_started_ts", 0.0) <= 0.0:
                        state["lying_started_ts"] = now_ts

                    is_danger = False
                    posture_conf = float(posture_meta.get("posture_confidence") or 0.0)
                    lying_duration = 0.0
                    if confirmed_posture == "lying" and state.get("lying_started_ts", 0.0) > 0.0:
                        lying_duration = max(0.0, now_ts - state["lying_started_ts"])

                    event_extra = {
                        "posture_metrics": posture_meta,
                        "center_drop_ratio": round(center_drop_ratio, 3),
                        "vertical_speed": round(vertical_speed, 2),
                        "smoothed_drop_ratio": round(state.get("smoothed_drop_ratio", 0.0), 3),
                        "smoothed_vertical_speed": round(state.get("smoothed_vertical_speed", 0.0), 2),
                        "lying_duration_sec": round(lying_duration, 3),
                        "fall_candidate_streak": int(state.get("fall_candidate_streak", 0)),
                        "face_score": state.get("face_score"),
                    }

                    if confirmed_posture == "unknown":
                        unknown_count += 1
                    elif confirmed_posture == "sitting":
                        sitting_count += 1
                    elif confirmed_posture == "lying":
                        lying_count += 1
                        is_danger = True
                        if lying_duration >= config.LYING_EVENT_MIN_SEC and self._event_ready(("LYING", tid)):
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
                        and posture_conf >= config.FALL_POSTURE_CONF_MIN
                        and lying_duration >= config.FALL_MIN_LYING_SEC
                        and state.get("last_non_lying_posture") in {"standing", "sitting", "bending"}
                        and now_ts - state.get("last_upright_ts", now_ts) <= config.FALL_MAX_TRANSITION_SEC
                        and (
                            state.get("smoothed_drop_ratio", 0.0) >= config.FALL_MIN_CENTER_DROP_RATIO
                            or state.get("smoothed_vertical_speed", 0.0) >= config.FALL_MIN_VERTICAL_SPEED
                        )
                    )

                    if fall_candidate:
                        state["fall_candidate_streak"] = int(state.get("fall_candidate_streak", 0)) + 1
                    else:
                        state["fall_candidate_streak"] = self._decay_counter(
                            state.get("fall_candidate_streak", 0),
                            config.FALL_STREAK_DECAY,
                        )

                    fall_detected = bool(
                        confirmed_posture == "lying"
                        and state.get("fall_candidate_streak", 0) >= max(1, config.FALL_CONFIRM_FRAMES)
                    )

                    if fall_detected:
                        fall_count += 1
                        is_danger = True
                        state["danger_until"] = now_ts + config.DANGER_HOLD_SEC
                        state["danger_reason"] = "FALL"
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

                    if now_ts < state.get("danger_until", 0.0):
                        is_danger = True

                    person_name = state.get("person_name") or ("track:%s" % tid)
                    posture_text = confirmed_posture
                    if posture_conf > 0:
                        posture_text = "%s %.2f" % (confirmed_posture, posture_conf)

                    if fall_detected or state.get("danger_reason") == "FALL":
                        color = (0, 0, 255)
                    elif confirmed_posture == "lying":
                        color = (0, 165, 255)
                    elif confirmed_posture == "bending":
                        color = (0, 255, 255)
                    else:
                        color = (0, 255, 0)

                    self._draw_box(frame, bbox, "%s | %s" % (person_name, posture_text), color)

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
                            "sitting_count": sitting_count,
                        },
                    )

                ok, jpeg = cv2.imencode(".jpg", frame)
                if ok:
                    with self.lock:
                        self.latest_jpeg = jpeg.tobytes()
                        self.latest_frame_bgr = frame.copy()

        except Exception as ex:
            self.status["online"] = False
            self.status["error"] = repr(ex)
            self.running = False
        finally:
            self.running = False
            self.status["online"] = False
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

    def get_latest_face_crop(self, track_id=None, prefer_unknown=False):
        with self.lock:
            if self.latest_frame_bgr is None:
                return None
            frame = self.latest_frame_bgr.copy()
        candidates = []
        for tid, state in self.track_state.items():
            if track_id is not None and str(tid) != str(track_id):
                continue
            bbox = state.get("last_bbox")
            if not bbox:
                continue
            score = 1 if (prefer_unknown and not state.get("person_id")) else 0
            candidates.append((score, tid, bbox))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return self._crop_face_region(frame, candidates[0][2])

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
        return self.status
