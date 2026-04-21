# csv_db.py
import csv
import os
import time

import numpy as np

import config
import pg_store

CSV_PATH = config.CSV_PATH
EMB_DIR = config.EMB_DIR
SNAP_DIR = config.SNAP_DIR
FIELDNAMES = config.FIELDNAMES


# ---------------- CSV low-level ----------------
def tao_db_csv():
    os.makedirs(EMB_DIR, exist_ok=True)
    os.makedirs(SNAP_DIR, exist_ok=True)

    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDNAMES)
            w.writeheader()


def _tai_tat_ca_csv_only():
    tao_db_csv()
    ds = []

    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            person_id_text = (row.get("person_id") or "").strip()
            if not person_id_text:
                continue

            emb_path = (row.get("emb_file") or "").strip()
            emb = None

            if emb_path and os.path.exists(emb_path):
                try:
                    emb = np.load(emb_path).astype(np.float32)
                except Exception:
                    emb = None

            ds.append({
                "person_id": int(person_id_text),
                "ho_ten": row.get("ho_ten", ""),
                "ma_nv": row.get("ma_nv", ""),
                "bo_phan": row.get("bo_phan", ""),
                "ngay_sinh": row.get("ngay_sinh", ""),
                "emb_file": emb_path,
                "embed": emb,
            })

    return ds


def ghi_lai_csv(ds):
    tao_db_csv()

    ds = sorted(ds, key=lambda p: int(p["person_id"]))

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()

        for p in ds:
            w.writerow({
                "person_id": int(p["person_id"]),
                "ho_ten": p.get("ho_ten", ""),
                "ma_nv": p.get("ma_nv", ""),
                "bo_phan": p.get("bo_phan", ""),
                "ngay_sinh": p.get("ngay_sinh", ""),
                "emb_file": p.get("emb_file", ""),
            })


def next_person_id(ds):
    if not ds:
        return 1
    return max(int(p["person_id"]) for p in ds) + 1


def person_id_exists(ds, person_id):
    return any(int(p["person_id"]) == int(person_id) for p in ds)


def _them_nhan_su_csv_only(person_id, ho_ten, ma_nv, bo_phan, ngay_sinh, embed):
    ds = _tai_tat_ca_csv_only()

    if person_id is None or str(person_id).strip() == "":
        new_id = next_person_id(ds)
    else:
        new_id = int(person_id)
        if person_id_exists(ds, new_id):
            print(f"[DK] person_id={new_id} da ton tai.")
            return None

    emb_path = os.path.join(EMB_DIR, f"person_{new_id}.npy")
    np.save(emb_path, np.asarray(embed, dtype=np.float32))

    ds.append({
        "person_id": new_id,
        "ho_ten": ho_ten,
        "ma_nv": ma_nv,
        "bo_phan": bo_phan,
        "ngay_sinh": ngay_sinh,
        "emb_file": emb_path,
        "embed": np.asarray(embed, dtype=np.float32),
    })

    ghi_lai_csv(ds)
    return int(new_id)


def _sua_thong_tin_csv_only(person_id: int):
    ds = _tai_tat_ca_csv_only()
    p = None

    for x in ds:
        if int(x["person_id"]) == int(person_id):
            p = x
            break

    if p is None:
        print(f"[SUA] Khong tim thay person_id={person_id}")
        return False

    print("\n=== SUA THONG TIN (bo trong = giu nguyen) ===")
    print(f"person_id: {p['person_id']}")
    print(f"ho_ten: {p['ho_ten']}")
    print(f"ma_nv: {p['ma_nv']}")
    print(f"bo_phan: {p['bo_phan']}")
    print(f"ngay_sinh: {p['ngay_sinh']}")

    person_id_moi = input("person_id moi: ").strip()
    ho_ten = input("Ho va ten moi: ").strip()
    ma_nv = input("Ma NV moi: ").strip()
    bo_phan = input("Bo phan moi: ").strip()
    ngay_sinh = input("Ngay sinh moi (YYYY-MM-DD): ").strip()

    if person_id_moi:
        person_id_moi = int(person_id_moi)
        for x in ds:
            if int(x["person_id"]) == person_id_moi and int(x["person_id"]) != int(person_id):
                print(f"[SUA] person_id={person_id_moi} da ton tai.")
                return False

        old_emb = (p.get("emb_file") or "").strip()
        if old_emb and os.path.exists(old_emb):
            new_emb = os.path.join(EMB_DIR, f"person_{person_id_moi}.npy")
            if os.path.exists(new_emb) and old_emb != new_emb:
                print(f"[SUA] File embedding dich da ton tai: {new_emb}")
                return False
            try:
                os.rename(old_emb, new_emb)
                p["emb_file"] = new_emb
            except Exception as ex:
                print("[SUA] Loi doi ten file embedding:", ex)
                return False
        p["person_id"] = person_id_moi

    if ho_ten:
        p["ho_ten"] = ho_ten
    if ma_nv:
        p["ma_nv"] = ma_nv
    if bo_phan:
        p["bo_phan"] = bo_phan
    if ngay_sinh:
        p["ngay_sinh"] = ngay_sinh

    ghi_lai_csv(ds)
    print("[SUA] Da cap nhat CSV.\n")
    return True


def reindex_person_ids(ds):
    ds = sorted(ds, key=lambda p: int(p["person_id"]))
    mapping = {int(p["person_id"]): i for i, p in enumerate(ds, start=1)}
    tmp_map = {}

    for p in ds:
        old_id = int(p["person_id"])
        old_path = (p.get("emb_file") or "").strip()

        if old_path and os.path.exists(old_path):
            tmp_path = os.path.join(EMB_DIR, f".tmp_{old_id}_{int(time.time() * 1000)}.npy")
            try:
                os.rename(old_path, tmp_path)
                tmp_map[old_id] = tmp_path
            except Exception as ex:
                print("[REINDEX] Loi rename tmp:", ex)

    for p in ds:
        old_id = int(p["person_id"])
        new_id = mapping[old_id]

        if old_id in tmp_map:
            final_path = os.path.join(EMB_DIR, f"person_{new_id}.npy")
            try:
                os.rename(tmp_map[old_id], final_path)
                p["emb_file"] = final_path
            except Exception as ex:
                print("[REINDEX] Loi rename final:", ex)

        p["person_id"] = new_id

    return ds


def _xoa_person_va_reindex_csv_only(person_id_can_xoa: int):
    ds = _tai_tat_ca_csv_only()
    target = None

    for p in ds:
        if int(p["person_id"]) == int(person_id_can_xoa):
            target = p
            break

    if target is None:
        print(f"[XOA] Khong tim thay person_id={person_id_can_xoa}")
        return False

    emb_path = (target.get("emb_file") or "").strip()
    if emb_path and os.path.exists(emb_path):
        try:
            os.remove(emb_path)
        except Exception as ex:
            print("[XOA] Khong xoa duoc emb:", ex)

    ds = [p for p in ds if int(p["person_id"]) != int(person_id_can_xoa)]
    ds = reindex_person_ids(ds)
    ghi_lai_csv(ds)

    print(f"[XOA] Da xoa person_id={person_id_can_xoa} va danh lai ID 1..{len(ds)}")
    return True


# ---------------- Unified backend ----------------
def storage_backend_name():
    if config.USE_POSTGRES_REGISTRY and pg_store.postgres_enabled() and pg_store.postgres_driver_ready():
        return "postgres"
    return "csv"


def bootstrap_storage():
    tao_db_csv()

    if not (config.USE_POSTGRES and pg_store.postgres_driver_ready()):
        if config.USE_POSTGRES and not pg_store.postgres_driver_ready():
            print("[PG] Chua cai psycopg2, se dung CSV.")
        return False

    if not pg_store.init_schema():
        return False

    if config.AUTO_MIGRATE_CSV_TO_PG:
        count = pg_store.count_people()
        if count == 0:
            csv_people = _tai_tat_ca_csv_only()
            if csv_people:
                pg_store.migrate_csv_people(csv_people)

    return True


def tai_tat_ca():
    if config.USE_POSTGRES_REGISTRY:
        ds_pg = pg_store.load_all_people()
        if ds_pg is not None:
            print(f"[REGISTRY] Dang dung PostgreSQL ({len(ds_pg)} nhan su)")
            return ds_pg

    if config.ENABLE_CSV_FALLBACK:
        ds_csv = _tai_tat_ca_csv_only()
        print(f"[REGISTRY] Fallback CSV ({len(ds_csv)} nhan su)")
        return ds_csv

    print("[REGISTRY] Khong tai duoc danh sach nhan su.")
    return []


def them_nhan_su(person_id, ho_ten, ma_nv, bo_phan, ngay_sinh, embed):
    if config.USE_POSTGRES_REGISTRY:
        new_id = pg_store.upsert_person(person_id, ho_ten, ma_nv, bo_phan, ngay_sinh, embed)
        if new_id is not None:
            return new_id

    if config.ENABLE_CSV_FALLBACK:
        return _them_nhan_su_csv_only(person_id, ho_ten, ma_nv, bo_phan, ngay_sinh, embed)

    return None


def sua_thong_tin(person_id: int):
    ds = tai_tat_ca()
    p = None
    for item in ds:
        if int(item["person_id"]) == int(person_id):
            p = item
            break

    if p is None:
        print(f"[SUA] Khong tim thay person_id={person_id}")
        return False

    print("\n=== SUA THONG TIN (bo trong = giu nguyen) ===")
    print(f"person_id: {p['person_id']}")
    print(f"ho_ten: {p['ho_ten']}")
    print(f"ma_nv: {p['ma_nv']}")
    print(f"bo_phan: {p['bo_phan']}")
    print(f"ngay_sinh: {p['ngay_sinh']}")

    person_id_moi = input("person_id moi: ").strip()
    ho_ten = input("Ho va ten moi: ").strip()
    ma_nv = input("Ma NV moi: ").strip()
    bo_phan = input("Bo phan moi: ").strip()
    ngay_sinh = input("Ngay sinh moi (YYYY-MM-DD): ").strip()

    if config.USE_POSTGRES_REGISTRY:
        ok = pg_store.update_person(
            existing_person_id=int(person_id),
            new_person_id=person_id_moi or None,
            ho_ten=ho_ten or None,
            ma_nv=ma_nv or None,
            bo_phan=bo_phan or None,
            ngay_sinh=ngay_sinh or None,
        )
        if ok:
            print("[SUA] Da cap nhat PostgreSQL.\n")
            return True

    if config.ENABLE_CSV_FALLBACK:
        return _sua_thong_tin_csv_only(person_id)

    return False


def xoa_person(person_id_can_xoa: int):
    if config.USE_POSTGRES_REGISTRY:
        ok = pg_store.delete_person(person_id_can_xoa)
        if ok:
            print(f"[XOA] Da xoa person_id={person_id_can_xoa} trong PostgreSQL")
            return True

    if config.ENABLE_CSV_FALLBACK:
        return _xoa_person_va_reindex_csv_only(person_id_can_xoa)

    return False


# ---------------- Backward-compatible names ----------------
def tai_tat_ca_csv():
    return tai_tat_ca()


def them_nhan_su_csv(person_id, ho_ten, ma_nv, bo_phan, ngay_sinh, embed):
    return them_nhan_su(person_id, ho_ten, ma_nv, bo_phan, ngay_sinh, embed)


def sua_thong_tin_csv(person_id: int):
    return sua_thong_tin(person_id)


def xoa_person_va_reindex(person_id_can_xoa: int):
    return xoa_person(person_id_can_xoa)
