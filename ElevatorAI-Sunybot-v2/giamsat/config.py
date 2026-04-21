# config.py
import os
import cv2


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default


def _env_float(name, default):
    try:
        return float(os.getenv(name, default))
    except Exception:
        return default


# ===== MODELS =====
MODEL_DET_PATH = os.getenv("MODEL_DET_PATH", "yolov8n.pt")
MODEL_POSE_PATH = os.getenv("MODEL_POSE_PATH", "yolov8n-pose.pt")

CAM_INDEX = _env_int("CAM_INDEX", 0)
CAMERA_ID = os.getenv("CAMERA_ID", "CAM_01")
CAMERA_WIDTH = _env_int("CAMERA_WIDTH", 640)
CAMERA_HEIGHT = _env_int("CAMERA_HEIGHT", 480)
WINDOW_NAME = os.getenv("WINDOW_NAME", "NHAN DIEN")

# ===== FEATURE FLAGS =====
USE_POSTGRES = _env_bool("USE_POSTGRES", True)
USE_POSTGRES_REGISTRY = _env_bool("USE_POSTGRES_REGISTRY", True)
AUTO_MIGRATE_CSV_TO_PG = _env_bool("AUTO_MIGRATE_CSV_TO_PG", True)
ENABLE_CSV_FALLBACK = _env_bool("ENABLE_CSV_FALLBACK", True)
ENABLE_JSON_LOG = _env_bool("ENABLE_JSON_LOG", True)
ENABLE_EVENT_DB = _env_bool("ENABLE_EVENT_DB", True)
ENABLE_OCCUPANCY_SAMPLE = _env_bool("ENABLE_OCCUPANCY_SAMPLE", True)
ENABLE_FACE = _env_bool("ENABLE_FACE", True)
ENABLE_POSE = _env_bool("ENABLE_POSE", True)

# ===== YOLO DETECT (person + bottle) =====
IMGSZ = _env_int("IMGSZ", 384)
PERSON_ID = 0
BOTTLE_ID = 39

CONF_PERSON = _env_float("CONF_PERSON", 0.50)
CONF_BOTTLE = _env_float("CONF_BOTTLE", 0.35)

YOLO_EVERY_N = _env_int("YOLO_EVERY_N", 4)
MIN_AREA = _env_int("MIN_AREA", 12000)
YOLO_DEVICE = os.getenv("YOLO_DEVICE", "0")  # GPU id (0). CPU: "cpu"

# ===== YOLO POSE =====
POSE_EVERY_N = _env_int("POSE_EVERY_N", 6)
POSE_DEVICE = os.getenv("POSE_DEVICE", "0")
POSE_CONF = _env_float("POSE_CONF", 0.15)
POSE_IMGSZ = _env_int("POSE_IMGSZ", 512)

# ===== Fall =====
FALL_CONFIRM_SEC = _env_float("FALL_CONFIRM_SEC", 0.8)
FALL_COOLDOWN_SEC = _env_float("FALL_COOLDOWN_SEC", 8.0)

# ===== FACE =====
NGUONG_SIM = _env_float("NGUONG_SIM", 0.45)
NHAN_DIEN_MOI = _env_float("NHAN_DIEN_MOI", 3.0)
FACE_CTX_ID = _env_int("FACE_CTX_ID", 0)
FACE_DET_SIZE = (_env_int("FACE_DET_WIDTH", 128), _env_int("FACE_DET_HEIGHT", 128))

# ===== Tracking =====
MISS_MAX = _env_int("MISS_MAX", 25)

# ===== CAMERA =====
MIRROR = _env_bool("MIRROR", True)
ROTATE_MODE = None  # None / cv2.ROTATE_90_CLOCKWISE / cv2.ROTATE_180 / cv2.ROTATE_90_COUNTERCLOCKWISE
DISPLAY_SCALE = _env_float("DISPLAY_SCALE", 1.25)
MAX_POSE_PERSONS = _env_int("MAX_POSE_PERSONS", 4)

# ===== CSV + embedding =====
CSV_PATH = os.getenv("CSV_PATH", "nhan_su.csv")
EMB_DIR = os.getenv("EMB_DIR", "embeddings")
SNAP_DIR = os.getenv("SNAP_DIR", "snapshots")
FIELDNAMES = ["person_id", "ho_ten", "ma_nv", "bo_phan", "ngay_sinh", "emb_file"]

# ===== Bottle holding =====
HOLD_DIST_RATIO = _env_float("HOLD_DIST_RATIO", 0.40)
HOLD_COOLDOWN_SEC = _env_float("HOLD_COOLDOWN_SEC", 2.0)

# ===== Crowd / sampling =====
CROWD_WARN_N = _env_int("CROWD_WARN_N", 4)
ALARM_GAP_SEC = _env_float("ALARM_GAP_SEC", 600.0)
OCCUPANCY_SAMPLE_SEC = _env_float("OCCUPANCY_SAMPLE_SEC", 2.0)

# ===== PostgreSQL =====
DATABASE_URL = os.getenv("DATABASE_URL", "")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = _env_int("PG_PORT", 5432)
PG_DATABASE = os.getenv("PG_DATABASE", "elevator_ai")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "postgres")
PG_CONNECT_TIMEOUT = _env_int("PG_CONNECT_TIMEOUT", 5)
