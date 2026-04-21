import time
from datetime import datetime

import cv2
import numpy as np

import config
import events
import face_recog
import pose_fall
import utils_cv
from sort_tracker import Sort

DISPLAY_SCALE = config.DISPLAY_SCALE
MAX_POSE_PERSONS = config.MAX_POSE_PERSONS
POSE_DRAW_COLOR = (255, 255, 255)


def _find_nearest_bottle_for_person(px1, py1, px2, py2, bottles):
    if not bottles:
        return None
    pcx = (px1 + px2) / 2
    pcy = (py1 + py2) / 2
    pw = (px2 - px1) + 1e-6
    best = None
    best_dist = 1e18
    for bx1, by1, bx2, by2, score in bottles:
        bcx = (bx1 + bx2) / 2
        bcy = (by1 + by2) / 2
        dist = ((bcx - pcx) ** 2 + (bcy - pcy) ** 2) ** 0.5
        if dist < best_dist:
            best_dist = dist
            best = (bx1, by1, bx2, by2, score, dist)
    if best is None:
        return None
    if best[5] <= config.HOLD_DIST_RATIO * pw:
        return best
    return None


def _run_pose_on_roi(pose_model, frame, x1, y1, x2, y2):
    if pose_model is None:
        return None
    roi = utils_cv.cat_roi_an_toan(frame, x1, y1, x2, y2, pad=10)
    if roi is None or roi.size == 0:
        return None
    res = pose_model.predict(
        roi,
        imgsz=config.POSE_IMGSZ,
        conf=config.POSE_CONF,
        device=config.POSE_DEVICE,
        verbose=False,
    )[0]
    if res.keypoints is None or len(res.keypoints) == 0:
        return None
    kps = res.keypoints.data[0].cpu().numpy()
    kps[:, 0] += (x1 - 10)
    kps[:, 1] += (y1 - 10)
    return kps


def _safe_log_event(logger, **kwargs):
    if logger is None:
        return
    try:
        logger.log_event(**kwargs)
    except Exception as ex:
        print("[LOGGER] log_event loi:", repr(ex))


def _safe_log_occupancy(logger, **kwargs):
    if logger is None:
        return
    try:
        logger.log_occupancy_sample(**kwargs)
    except Exception as ex:
        print("[LOGGER] log_occupancy_sample loi:", repr(ex))


def _get_person_name(person):
    if person is None:
        return "Unknown"
    return person.get("ho_ten", "Unknown")


def _get_person_id(person):
    if person is None:
        return None
    try:
        return int(person["person_id"])
    except Exception:
        return None


def run_camera_session(det_model, pose_model, face_app, ds_nhan_su,
                       yolo_every_n, nguong_sim, nhan_dien_moi,
                       mirror, rotate_mode, logger=None):
    cap = cv2.VideoCapture(config.CAM_INDEX)
    if not cap.isOpened():
        print("Khong mo duoc webcam.")
        return ("EXIT", (yolo_every_n, nguong_sim, nhan_dien_moi, mirror, rotate_mode))

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

    tracker = Sort(max_age=30, min_hits=1, iou_threshold=0.35)
    fstate = pose_fall.FallState()

    last_recog = {}
    tid_to_person = {}
    tid_to_showid = {}
    free_showids = []
    next_showid = 0
    miss_count = {}
    tid_posture = {}
    tid_is_fall = {}

    frame_id = 0
    dets_cache = np.empty((0, 5), dtype=np.float32)
    bottles_cache = []
    last_frame = None

    paused = False
    show_help = False

    t0 = time.time()
    frames = 0
    fps = 0.0

    last_hold_ids_str = "-"
    last_alarm_time = {}
    alarm_gap = config.ALARM_GAP_SEC
    last_sample_ts = 0.0

    while True:
        if not paused:
            ok, frame = cap.read()
            if not ok:
                break

            if rotate_mode is not None:
                frame = cv2.rotate(frame, rotate_mode)
            if mirror:
                frame = cv2.flip(frame, 1)

            last_frame = frame.copy()
            H, W = frame.shape[:2]
            frame_id += 1
            now = time.time()

            if frame_id % max(1, int(yolo_every_n)) == 0:
                res = det_model.predict(
                    frame,
                    imgsz=config.IMGSZ,
                    conf=min(config.CONF_PERSON, config.CONF_BOTTLE),
                    device=config.YOLO_DEVICE,
                    verbose=False,
                )[0]
                dets_person = []
                dets_bottle = []
                for box in res.boxes:
                    cls_id = int(box.cls[0])
                    x1, y1, x2, y2 = map(float, box.xyxy[0])
                    score = float(box.conf[0])
                    if cls_id == config.PERSON_ID:
                        area = (x2 - x1) * (y2 - y1)
                        if area >= config.MIN_AREA and score >= config.CONF_PERSON:
                            dets_person.append([x1, y1, x2, y2, score])
                    elif cls_id == config.BOTTLE_ID and score >= config.CONF_BOTTLE:
                        dets_bottle.append([x1, y1, x2, y2, score])
                dets_cache = np.array(dets_person, dtype=np.float32) if dets_person else np.empty((0, 5), dtype=np.float32)
                bottles_cache = dets_bottle

            tracks = tracker.update(dets_cache)
            cur_tids = set(int(t[4]) for t in tracks) if len(tracks) else set()

            for tid in list(tid_to_showid.keys()):
                if tid not in cur_tids:
                    miss_count[tid] = miss_count.get(tid, 0) + 1
                    if miss_count[tid] >= config.MISS_MAX:
                        sid = tid_to_showid.pop(tid, None)
                        if sid is not None:
                            free_showids.append(sid)
                            free_showids.sort()
                        miss_count.pop(tid, None)
                        last_recog.pop(tid, None)
                        tid_to_person.pop(tid, None)
                        tid_posture.pop(tid, None)
                        tid_is_fall.pop(tid, None)
                        fstate.tid_last_pose.pop(tid, None)
                else:
                    miss_count[tid] = 0

            for tid in cur_tids:
                if tid not in tid_to_showid:
                    if free_showids:
                        tid_to_showid[tid] = free_showids.pop(0)
                    else:
                        tid_to_showid[tid] = next_showid
                        next_showid += 1

            tid_holding = events.detect_bottle_holding(tracks, bottles_cache)
            holding_ids = [tid_to_showid.get(tid, tid) for tid, h in tid_holding.items() if h]
            holding_ids.sort()
            last_hold_ids_str = ",".join(map(str, holding_ids)) if holding_ids else "-"
            num_holding = len(holding_ids)

            if config.ENABLE_FACE and face_app is not None:
                for x1, y1, x2, y2, tid in tracks:
                    x1, y1, x2, y2, tid = int(x1), int(y1), int(x2), int(y2), int(tid)
                    if (tid not in last_recog) or (now - last_recog[tid] > nhan_dien_moi):
                        roi = utils_cv.cat_roi_an_toan(frame, x1, y1, x2, y2, pad=10)
                        person = None
                        if roi is not None:
                            faces = face_app.get(roi)
                            f = utils_cv.pick_face_largest(faces)
                            if f is not None:
                                emb = f.normed_embedding.astype(np.float32)
                                person, _sim = face_recog.so_khop(emb, ds_nhan_su, nguong_sim)
                        tid_to_person[tid] = person
                        last_recog[tid] = now
            else:
                for _, _, _, _, tid in tracks:
                    tid_to_person.setdefault(int(tid), None)

            if config.ENABLE_POSE and pose_model is not None and frame_id % max(1, config.POSE_EVERY_N) == 0 and len(tracks):
                tracks_sorted = sorted(tracks, key=lambda t: (t[2] - t[0]) * (t[3] - t[1]), reverse=True)
                for idx, (x1, y1, x2, y2, tid) in enumerate(tracks_sorted):
                    x1, y1, x2, y2, tid = int(x1), int(y1), int(x2), int(y2), int(tid)
                    if idx < MAX_POSE_PERSONS:
                        kps = _run_pose_on_roi(pose_model, frame, x1, y1, x2, y2)
                        if kps is not None:
                            fstate.tid_last_pose[tid] = kps
                    else:
                        kps = fstate.tid_last_pose.get(tid, None)
                    tid_posture[tid] = pose_fall.classify_posture(kps, person_bbox=(x1, y1, x2, y2), frame_h=H)
                    tid_is_fall[tid] = pose_fall.update_fall_by_pose(fstate, tid, now, kps)
            else:
                for _, _, _, _, tid in tracks:
                    tid = int(tid)
                    tid_posture.setdefault(tid, "UNKNOWN")
                    tid_is_fall.setdefault(tid, False)

            frames += 1
            if time.time() - t0 >= 1.0:
                fps = frames / (time.time() - t0)
                t0 = time.time()
                frames = 0

            people_n = len(tracks)
            num_lying = sum(1 for v in tid_posture.values() if v == "NAM")
            now_dt = datetime.now()
            thu_str = now_dt.strftime("%A").upper()
            realtime_str = f"{now_dt.strftime('%d-%m-%Y %H:%M:%S')} | {thu_str}"

            unknown_n = 0
            fall_n = 0
            for _, _, _, _, tid in tracks:
                tid = int(tid)
                if tid_to_person.get(tid) is None:
                    unknown_n += 1
                if bool(tid_is_fall.get(tid, False)):
                    fall_n += 1

            if config.ENABLE_OCCUPANCY_SAMPLE and logger is not None and (now - last_sample_ts) >= config.OCCUPANCY_SAMPLE_SEC:
                _safe_log_occupancy(
                    logger,
                    cam_id=config.CAMERA_ID,
                    people_count=people_n,
                    unknown_count=unknown_n,
                    lying_count=num_lying,
                    fall_count=fall_n,
                    extra={"fps": round(float(fps), 2), "holding_count": num_holding, "realtime_str": realtime_str},
                )
                last_sample_ts = now

            utils_cv.overlay_rect_alpha(frame, 0, 0, W, 68, (0, 0, 0), alpha=0.45)
            hud_left = f"FPS:{fps:.1f}  |  Camera:{config.CAMERA_ID}  |  People:{people_n}"
            hud_right = f"So nguoi cam chai: {num_holding} (IDs:{last_hold_ids_str})"
            cv2.putText(frame, hud_left, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, hud_right, (max(10, W - 10 - 12 * len(hud_right)), 28), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(frame, f"Real time: {realtime_str}", (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.49, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, f"So nguoi te/nam: {fall_n}/{num_lying}", (max(10, W - 260), 58), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 0, 255), 2, cv2.LINE_AA)

            if people_n >= config.CROWD_WARN_N:
                utils_cv.draw_warning_logo(frame, x=10, y=78, size=70)
                utils_cv.put_text_bg(frame, f"CANH BAO: DONG NGUOI ({people_n})", (90, 122), font_scale=0.75, color=(255, 255, 255), bg=(0, 0, 255), alpha=0.55)
                last_t = last_alarm_time.get(("CROWD", "CROWD"), 0.0)
                if now - last_t >= alarm_gap:
                    _safe_log_event(
                        logger,
                        event_type="CROWD",
                        cam_id=config.CAMERA_ID,
                        person_id=None,
                        person_name="MULTI_PERSON",
                        extra={"people_count": people_n, "crowd_threshold": config.CROWD_WARN_N, "unknown_count": unknown_n, "realtime_str": realtime_str},
                    )
                    print(f"[EVENT] CROWD | camera={config.CAMERA_ID} | people={people_n} | time={realtime_str}")
                    last_alarm_time[("CROWD", "CROWD")] = now

            for x1, y1, x2, y2, tid in tracks:
                x1, y1, x2, y2, tid = int(x1), int(y1), int(x2), int(y2), int(tid)
                track_show_id = tid_to_showid.get(tid, tid)
                person = tid_to_person.get(tid)
                name = _get_person_name(person)
                person_id_val = _get_person_id(person)
                person_id_show = "--" if person_id_val is None else f"{person_id_val:02d}"
                line1 = f"ID:{person_id_show} | Track:{track_show_id} | {name}"
                posture = tid_posture.get(tid, "UNKNOWN")
                is_fall = bool(tid_is_fall.get(tid, False))
                is_lying = posture == "NAM"
                holding = bool(tid_holding.get(tid, False))
                posture_show = "TE NGA" if is_fall else posture
                is_alarm = is_fall or is_lying or holding
                alarm_type = None
                if is_fall:
                    alarm_type = "FALL"
                elif is_lying:
                    alarm_type = "LYING"
                elif holding:
                    alarm_type = "BOTTLE"
                if alarm_type is not None:
                    last_t = last_alarm_time.get((tid, alarm_type), 0.0)
                    if now - last_t >= alarm_gap:
                        _safe_log_event(
                            logger,
                            event_type=alarm_type,
                            cam_id=config.CAMERA_ID,
                            person_id=person_id_val,
                            person_name=name,
                            extra={
                                "people_count": people_n,
                                "posture": posture_show,
                                "holding": holding,
                                "track_id": int(track_show_id),
                                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                                "realtime_str": realtime_str,
                            },
                        )
                        print(f"[EVENT] {alarm_type} | camera={config.CAMERA_ID} | track={track_show_id} | time={realtime_str}")
                        last_alarm_time[(tid, alarm_type)] = now

                box_color = (0, 0, 255) if is_alarm else (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                utils_cv.put_text_bg(frame, line1, (x1, max(85, y1 - 8)), font_scale=0.55, color=(255, 255, 255), bg=(0, 0, 0), alpha=0.55)
                line2 = f"POSE:{posture_show}"
                if holding:
                    line2 += " | Bottle:YES"
                status_bg = (0, 0, 255) if is_alarm else (0, 90, 0)
                utils_cv.put_text_bg(frame, line2, (x1, y2 + 22), font_scale=0.60, color=(255, 255, 255), bg=status_bg, alpha=0.55)
                if holding:
                    bottle_box = _find_nearest_bottle_for_person(x1, y1, x2, y2, bottles_cache)
                    if bottle_box is not None:
                        bx1, by1, bx2, by2, bscore, _dist = bottle_box
                        bx1, by1, bx2, by2 = int(bx1), int(by1), int(bx2), int(by2)
                        cv2.rectangle(frame, (bx1, by1), (bx2, by2), (255, 0, 0), 2)
                        utils_cv.put_text_bg(frame, f"Chai nuoc {bscore:.2f}", (bx1, max(85, by1 - 8)), font_scale=0.55, color=(255, 255, 255), bg=(255, 0, 0), alpha=0.55)
                kps = fstate.tid_last_pose.get(tid)
                if kps is not None:
                    pose_fall.draw_pose(frame, kps, color=POSE_DRAW_COLOR)
                if is_alarm:
                    utils_cv.draw_warning_logo(frame, x=min(W - 80, x2 + 5), y=max(78, y1), size=55)

            if show_help:
                menu_text = "ESC Thoat | H Menu | R Dang ky | E Sua | X Xoa | L Reload | P Pause | +/- Sim | 1/2/3 YOLO | M Mirror | T Rotate | S Snapshot"
                utils_cv.overlay_rect_alpha(frame, 0, H - 36, W, H, (0, 0, 0), alpha=0.55)
                cv2.putText(frame, menu_text, (10, H - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 255), 2, cv2.LINE_AA)

            frame_show = cv2.resize(frame, None, fx=DISPLAY_SCALE, fy=DISPLAY_SCALE, interpolation=cv2.INTER_LINEAR)
            cv2.imshow(config.WINDOW_NAME, frame_show)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('p'), ord('P')):
            paused = not paused
        if key in (ord('h'), ord('H')):
            show_help = not show_help
        if key in (ord('r'), ord('R')):
            cap.release(); cv2.destroyAllWindows(); return ("REGISTER", (yolo_every_n, nguong_sim, nhan_dien_moi, mirror, rotate_mode))
        if key == ord('+') or key == ord('='):
            nguong_sim = min(0.95, nguong_sim + 0.02); print("[SIM] =", nguong_sim)
        if key == ord('-') or key == ord('_'):
            nguong_sim = max(0.10, nguong_sim - 0.02); print("[SIM] =", nguong_sim)
        if key == ord('1'):
            yolo_every_n = 1; print("[YOLO_EVERY_N] = 1")
        if key == ord('2'):
            yolo_every_n = 2; print("[YOLO_EVERY_N] = 2")
        if key == ord('3'):
            yolo_every_n = 3; print("[YOLO_EVERY_N] = 3")
        if key in (ord('m'), ord('M')):
            mirror = not mirror; print("[MIRROR] =", mirror)
        if key in (ord('t'), ord('T')):
            if rotate_mode is None:
                rotate_mode = cv2.ROTATE_90_CLOCKWISE
            elif rotate_mode == cv2.ROTATE_90_CLOCKWISE:
                rotate_mode = cv2.ROTATE_180
            elif rotate_mode == cv2.ROTATE_180:
                rotate_mode = cv2.ROTATE_90_COUNTERCLOCKWISE
            else:
                rotate_mode = None
            print("[ROTATE] =", rotate_mode)
        if key in (ord('s'), ord('S')):
            try:
                if last_frame is None:
                    raise RuntimeError("Chua co frame de snapshot")
                path = utils_cv.save_snapshot(last_frame, prefix="manual")
                print("[SNAP] Saved:", path)
            except Exception as ex:
                print("[SNAP] Error:", ex)
        if key in (ord('e'), ord('E')):
            cap.release(); cv2.destroyAllWindows(); return ("EDIT", (yolo_every_n, nguong_sim, nhan_dien_moi, mirror, rotate_mode))
        if key in (ord('x'), ord('X')):
            cap.release(); cv2.destroyAllWindows(); return ("DELETE", (yolo_every_n, nguong_sim, nhan_dien_moi, mirror, rotate_mode))
        if key in (ord('l'), ord('L')):
            cap.release(); cv2.destroyAllWindows(); return ("RELOAD", (yolo_every_n, nguong_sim, nhan_dien_moi, mirror, rotate_mode))
        if key == 27:
            cap.release(); cv2.destroyAllWindows(); return ("EXIT", (yolo_every_n, nguong_sim, nhan_dien_moi, mirror, rotate_mode))

    cap.release()
    cv2.destroyAllWindows()
    return ("RELOAD", (yolo_every_n, nguong_sim, nhan_dien_moi, mirror, rotate_mode))
