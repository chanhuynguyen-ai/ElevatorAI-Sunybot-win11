import os


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


APP_ENV = os.getenv("APP_ENV", "production")
CV_BACKEND = os.getenv("CV_BACKEND", "trt")  # trt | ultralytics

CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "0")
CAMERA_ID = os.getenv("CAMERA_ID", "CAM_01")

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = _env_int("PG_PORT", 5432)
PG_DATABASE = os.getenv("PG_DATABASE", "elevator_cv")
PG_USER = os.getenv("PG_USER", "elevator_ai")
PG_PASSWORD = os.getenv("PG_PASSWORD", "elevator123")

# DB LLM tách riêng, CV code không dùng để ghi dữ liệu camera
LLM_DB_HOST = os.getenv("LLM_DB_HOST", "localhost")
LLM_DB_PORT = _env_int("LLM_DB_PORT", 5432)
LLM_DB_NAME = os.getenv("LLM_DB_NAME", "elevator_llm")
LLM_DB_USER = os.getenv("LLM_DB_USER", "elevator_ai")
LLM_DB_PASSWORD = os.getenv("LLM_DB_PASSWORD", "elevator123")

ENABLE_FACE = _env_bool("ENABLE_FACE", False)
ENABLE_POSE = _env_bool("ENABLE_POSE", True)

DET_ENGINE_PATH = os.getenv("DET_ENGINE_PATH", "./models/yolov8n_fp16.engine")
POSE_ENGINE_PATH = os.getenv("POSE_ENGINE_PATH", "./models/yolov8n_pose_fp16.engine")
DET_MODEL_DEV = os.getenv("DET_MODEL_DEV", "./models/yolov8n.pt")
POSE_MODEL_DEV = os.getenv("POSE_MODEL_DEV", "./models/yolov8n-pose.pt")

DET_IMGSZ = _env_int("DET_IMGSZ", 320)
POSE_IMGSZ = _env_int("POSE_IMGSZ", 384)
DET_CONF = _env_float("DET_CONF", 0.35)
DET_IOU = _env_float("DET_IOU", 0.45)
POSE_CONF = _env_float("POSE_CONF", 0.35)
POSE_IOU = _env_float("POSE_IOU", 0.45)

YOLO_EVERY_N = _env_int("YOLO_EVERY_N", 4)
POSE_EVERY_N = _env_int("POSE_EVERY_N", 6)
OCCUPANCY_SAMPLE_SEC = _env_int("OCCUPANCY_SAMPLE_SEC", 10)
EVENT_COOLDOWN_SEC = _env_int("EVENT_COOLDOWN_SEC", 8)
CROWD_THRESHOLD = _env_int("CROWD_THRESHOLD", 4)

FACE_SIM_THRESHOLD = _env_float("FACE_SIM_THRESHOLD", 0.45)
FACE_DET_WIDTH = _env_int("FACE_DET_WIDTH", 96)
FACE_DET_HEIGHT = _env_int("FACE_DET_HEIGHT", 96)
FACE_DET_SIZE = (FACE_DET_WIDTH, FACE_DET_HEIGHT)

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = _env_int("API_PORT", 8000)
