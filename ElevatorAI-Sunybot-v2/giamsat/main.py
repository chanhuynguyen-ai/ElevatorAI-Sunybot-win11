import os
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

from ultralytics import YOLO

import camera_session_step1 as camera_session
import config
import csv_db
import event_logger
import face_recog


def _load_face_app():
    if not config.ENABLE_FACE:
        print("[FACE] Dang tat theo config.ENABLE_FACE=False")
        return None
    print("[LOAD] Face recognition...")
    face_app = face_recog.create_face_app(
        ctx_id=config.FACE_CTX_ID,
        det_size=config.FACE_DET_SIZE,
    )
    print("[OK] Face model ready")
    return face_app


def _load_pose_model():
    if not config.ENABLE_POSE:
        print("[POSE] Dang tat theo config.ENABLE_POSE=False")
        return None
    print("[LOAD] YOLO pose:", config.MODEL_POSE_PATH)
    pose_model = YOLO(config.MODEL_POSE_PATH)
    print("[OK] YOLO pose ready")
    return pose_model


def main():
    yolo_every_n = config.YOLO_EVERY_N
    nguong_sim = config.NGUONG_SIM
    nhan_dien_moi = config.NHAN_DIEN_MOI
    mirror = config.MIRROR
    rotate_mode = config.ROTATE_MODE

    print("\n========== AI GIAM SAT - STEP 1 ==========")
    csv_db.bootstrap_storage()
    ds_nhan_su = csv_db.tai_tat_ca()
    print(f"[REGISTRY] So nhan su dang tai: {len(ds_nhan_su)}")

    logger = event_logger.EventLogger.from_config()
    face_app = _load_face_app()

    print("[LOAD] YOLO detect:", config.MODEL_DET_PATH)
    det_model = YOLO(config.MODEL_DET_PATH)
    print("[OK] YOLO detect ready")

    pose_model = _load_pose_model()

    print("\n===== PHIM =====")
    print(" ESC : Thoat")
    print(" R   : Dang ky")
    print(" H   : Hien/An menu")
    print(" E   : Sua theo person_id")
    print(" X   : Xoa theo person_id")
    print(" L   : Reload registry")
    print(" P   : Pause/Resume")
    print(" +/- : Tang/Giam similarity")
    print(" 1/2/3 : Doi toc do YOLO")
    print(" M   : Bat/tat Mirror")
    print(" T   : Xoay 90 do")
    print(" S   : Snapshot")
    print("====================\n")

    while True:
        action, state = camera_session.run_camera_session(
            det_model,
            pose_model,
            face_app,
            ds_nhan_su,
            yolo_every_n,
            nguong_sim,
            nhan_dien_moi,
            mirror,
            rotate_mode,
            logger,
        )

        yolo_every_n, nguong_sim, nhan_dien_moi, mirror, rotate_mode = state

        if action == "EXIT":
            print("[EXIT]")
            break

        if action == "RELOAD":
            ds_nhan_su = csv_db.tai_tat_ca()
            print(f"[REGISTRY] Reload: {len(ds_nhan_su)} nhan su")
            continue

        if action == "REGISTER":
            if face_app is None:
                print("[DK] Face recognition dang tat, khong the dang ky.")
                continue
            try:
                emb = face_recog.capture_face_embedding_for_register(
                    face_app,
                    mirror=mirror,
                    rotate_mode=rotate_mode,
                )
                if emb is None:
                    print("[DK] Huy hoac khong thu duoc embedding.")
                    continue

                print("\n=== DANG KY NHAN SU MOI ===")
                person_id = input("person_id (bo trong = tu tang): ").strip()
                ho_ten = input("Ho va ten: ").strip()
                ma_nv = input("Ma nhan vien: ").strip()
                bo_phan = input("Bo phan / Tang: ").strip()
                ngay_sinh = input("Ngay sinh (YYYY-MM-DD): ").strip()

                new_id = csv_db.them_nhan_su(
                    person_id,
                    ho_ten,
                    ma_nv,
                    bo_phan,
                    ngay_sinh,
                    emb,
                )
                if new_id is None:
                    print("[DK] Dang ky that bai.")
                    continue

                ds_nhan_su = csv_db.tai_tat_ca()
                print(f"[REGISTRY] Reload: {len(ds_nhan_su)} nhan su")
            except Exception as ex:
                print("[REGISTER] Loi:", ex)
            continue

        if action == "EDIT":
            try:
                pid = int(input("\nNhap person_id can sua: ").strip())
                ok = csv_db.sua_thong_tin(pid)
                if ok:
                    ds_nhan_su = csv_db.tai_tat_ca()
                    print(f"[REGISTRY] Reload: {len(ds_nhan_su)} nhan su")
            except Exception as ex:
                print("[EDIT] Loi:", ex)
            continue

        if action == "DELETE":
            try:
                pid = int(input("\nNhap person_id can xoa: ").strip())
                ok = csv_db.xoa_person(pid)
                if ok:
                    ds_nhan_su = csv_db.tai_tat_ca()
                    print(f"[REGISTRY] Reload: {len(ds_nhan_su)} nhan su")
            except Exception as ex:
                print("[DELETE] Loi:", ex)
            continue


if __name__ == "__main__":
    main()
