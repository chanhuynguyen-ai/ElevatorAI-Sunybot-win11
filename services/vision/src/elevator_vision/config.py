import os


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


APP_ENV = os.getenv("APP_ENV", "production")
CV_BACKEND = os.getenv("CV_BACKEND", "mock")  # mock | ultralytics | trt
CV_DEVICE = os.getenv("CV_DEVICE", "auto")  # auto | cpu | cuda:0 | 0
YOLO_USE_HALF = _env_bool("YOLO_USE_HALF", True)

CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "mock")
CAMERA_ID = os.getenv("CAMERA_ID", "CAM_01")

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = _env_int("PG_PORT", 5432)
PG_DATABASE = os.getenv("PG_DATABASE", "elevator_cv")
PG_USER = os.getenv("PG_USER", "elevator_ai")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")

LLM_DB_HOST = os.getenv("LLM_DB_HOST", "localhost")
LLM_DB_PORT = _env_int("LLM_DB_PORT", 5432)
LLM_DB_NAME = os.getenv("LLM_DB_NAME", "elevator_llm")
LLM_DB_USER = os.getenv("LLM_DB_USER", "elevator_ai")
LLM_DB_PASSWORD = os.getenv("LLM_DB_PASSWORD", "")

ENABLE_FACE = _env_bool("ENABLE_FACE", False)
ENABLE_POSE = _env_bool("ENABLE_POSE", False)

CV_DASHBOARD_ENABLED = _env_bool("CV_DASHBOARD_ENABLED", False)

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

YOLO_EVERY_N = _env_int("YOLO_EVERY_N", 2)
POSE_EVERY_N = _env_int("POSE_EVERY_N", 2)

OCCUPANCY_SAMPLE_SEC = _env_int("OCCUPANCY_SAMPLE_SEC", 10)
EVENT_COOLDOWN_SEC = _env_int("EVENT_COOLDOWN_SEC", 8)
CROWD_THRESHOLD = _env_int("CROWD_THRESHOLD", 4)
OVERLOAD_THRESHOLD = _env_int("OVERLOAD_THRESHOLD", 4)

LYING_CONFIRM_FRAMES = _env_int("LYING_CONFIRM_FRAMES", 4)
LYING_EVENT_MIN_SEC = _env_float("LYING_EVENT_MIN_SEC", 0.70)
FALL_CONFIRM_FRAMES = _env_int("FALL_CONFIRM_FRAMES", 2)
FALL_MIN_LYING_SEC = _env_float("FALL_MIN_LYING_SEC", 0.25)
FALL_MAX_TRANSITION_SEC = _env_float("FALL_MAX_TRANSITION_SEC", 1.4)
FALL_POSTURE_CONF_MIN = _env_float("FALL_POSTURE_CONF_MIN", 0.68)
FALL_SPEED_EMA_ALPHA = _env_float("FALL_SPEED_EMA_ALPHA", 0.45)
FALL_STREAK_DECAY = _env_int("FALL_STREAK_DECAY", 1)
DANGER_HOLD_SEC = _env_float("DANGER_HOLD_SEC", 2.5)
POSE_TRACK_MATCH_IOU = _env_float("POSE_TRACK_MATCH_IOU", 0.25)

POSE_KEYPOINT_CONF = _env_float("POSE_KEYPOINT_CONF", 0.25)
POSTURE_MIN_VISIBLE_KPTS = _env_int("POSTURE_MIN_VISIBLE_KPTS", 5)
POSTURE_HORIZONTAL_AR = _env_float("POSTURE_HORIZONTAL_AR", 1.18)
POSTURE_LYING_TORSO_SPAN_RATIO = _env_float("POSTURE_LYING_TORSO_SPAN_RATIO", 0.42)
POSTURE_LYING_TORSO_HEIGHT_RATIO = _env_float("POSTURE_LYING_TORSO_HEIGHT_RATIO", 0.24)
POSTURE_MAX_VERTICAL_DX_RATIO = _env_float("POSTURE_MAX_VERTICAL_DX_RATIO", 0.42)
POSTURE_SITTING_KNEE_LIFT_RATIO = _env_float("POSTURE_SITTING_KNEE_LIFT_RATIO", 0.18)
POSTURE_STANDING_LEG_EXTENSION_RATIO = _env_float("POSTURE_STANDING_LEG_EXTENSION_RATIO", 0.24)
POSTURE_CONFIRM_UNKNOWN_FRAMES = _env_int("POSTURE_CONFIRM_UNKNOWN_FRAMES", 2)
POSTURE_RESET_UNKNOWN_FRAMES = _env_int("POSTURE_RESET_UNKNOWN_FRAMES", 8)
STANDING_CONFIRM_FRAMES = _env_int("STANDING_CONFIRM_FRAMES", 2)
SITTING_CONFIRM_FRAMES = _env_int("SITTING_CONFIRM_FRAMES", 3)
BENDING_CONFIRM_FRAMES = _env_int("BENDING_CONFIRM_FRAMES", 3)

POSTURE_SCORE_MARGIN = _env_float("POSTURE_SCORE_MARGIN", 0.28)
POSTURE_LYING_MIN_SCORE = _env_float("POSTURE_LYING_MIN_SCORE", 2.25)
POSTURE_SITTING_MIN_SCORE = _env_float("POSTURE_SITTING_MIN_SCORE", 1.85)
POSTURE_STANDING_MIN_SCORE = _env_float("POSTURE_STANDING_MIN_SCORE", 1.85)
POSTURE_BENDING_MIN_SCORE = _env_float("POSTURE_BENDING_MIN_SCORE", 1.55)
POSTURE_BENDING_MIN_DX_RATIO = _env_float("POSTURE_BENDING_MIN_DX_RATIO", 0.30)
POSTURE_BENDING_MAX_HEIGHT_RATIO = _env_float("POSTURE_BENDING_MAX_HEIGHT_RATIO", 0.33)

# Posture classifier V2: body-axis and joint-angle thresholds.
# Torso angle is measured from vertical: 0 = upright, 90 = horizontal.
POSTURE_UPRIGHT_TORSO_ANGLE_DEG = _env_float("POSTURE_UPRIGHT_TORSO_ANGLE_DEG", 24.0)
POSTURE_BENDING_TORSO_ANGLE_DEG = _env_float("POSTURE_BENDING_TORSO_ANGLE_DEG", 28.0)
POSTURE_LYING_TORSO_ANGLE_DEG = _env_float("POSTURE_LYING_TORSO_ANGLE_DEG", 58.0)
POSTURE_LYING_BBOX_AR = _env_float("POSTURE_LYING_BBOX_AR", 1.12)
POSTURE_LYING_CLOUD_RATIO = _env_float("POSTURE_LYING_CLOUD_RATIO", 1.18)
POSTURE_SITTING_KNEE_MAX_DEG = _env_float("POSTURE_SITTING_KNEE_MAX_DEG", 145.0)
POSTURE_STANDING_KNEE_MIN_DEG = _env_float("POSTURE_STANDING_KNEE_MIN_DEG", 150.0)

FALL_MIN_CENTER_DROP_RATIO = _env_float("FALL_MIN_CENTER_DROP_RATIO", 0.24)
FALL_MIN_VERTICAL_SPEED = _env_float("FALL_MIN_VERTICAL_SPEED", 155.0)

TRACK_IOU_THRESH = _env_float("TRACK_IOU_THRESH", 0.30)
TRACK_MAX_AGE = _env_int("TRACK_MAX_AGE", 8)
TRACK_SMOOTH_ALPHA = _env_float("TRACK_SMOOTH_ALPHA", 0.65)
TRACK_MIN_HITS = _env_int("TRACK_MIN_HITS", 1)

BOTTLE_TRACK_IOU_THRESH = _env_float("BOTTLE_TRACK_IOU_THRESH", 0.25)
BOTTLE_TRACK_MAX_AGE = _env_int("BOTTLE_TRACK_MAX_AGE", 6)
BOTTLE_TRACK_MIN_HITS = _env_int("BOTTLE_TRACK_MIN_HITS", 1)

FACE_SIM_THRESHOLD = _env_float("FACE_SIM_THRESHOLD", 0.45)
FACE_DET_WIDTH = _env_int("FACE_DET_WIDTH", 96)
FACE_DET_HEIGHT = _env_int("FACE_DET_HEIGHT", 96)
FACE_DET_SIZE = (FACE_DET_WIDTH, FACE_DET_HEIGHT)
FACE_RECHECK_SEC = _env_float("FACE_RECHECK_SEC", 2.0)
FACE_UNKNOWN_COOLDOWN_SEC = _env_float("FACE_UNKNOWN_COOLDOWN_SEC", 15.0)
FACE_TOP_RATIO = _env_float("FACE_TOP_RATIO", 0.55)
FACE_MARGIN_RATIO = _env_float("FACE_MARGIN_RATIO", 0.08)

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = _env_int("API_PORT", 8010)

CV_DB_ENABLED = _env_bool("CV_DB_ENABLED", False)
