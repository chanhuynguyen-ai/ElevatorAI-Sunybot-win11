import os
import numpy as np

from app import config, db

try:
    from insightface.app import FaceAnalysis
except Exception:
    FaceAnalysis = None


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _prefer_gpu() -> bool:
    raw = str(getattr(config, "CV_DEVICE", "auto") or "auto").strip().lower()
    if raw in {"cpu", "-1"}:
        return False
    if raw.startswith("cuda") or raw == "0":
        return True
    return _env_bool("FACE_USE_GPU", True)


def _build_providers():
    if _prefer_gpu():
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]


def _resolve_ctx_id(providers):
    return 0 if providers and providers[0] == "CUDAExecutionProvider" else -1


def create_face_app():
    if not getattr(config, "ENABLE_FACE", False):
        return None
    if FaceAnalysis is None:
        raise RuntimeError("ENABLE_FACE=true nhưng thiếu insightface/onnxruntime")

    providers = _build_providers()

    try:
        app = FaceAnalysis(name="buffalo_l", providers=providers)
    except TypeError:
        app = FaceAnalysis(name="buffalo_l")

    det_size = getattr(config, "FACE_DET_SIZE", (160, 160))
    if not isinstance(det_size, (tuple, list)) or len(det_size) != 2:
        det_size = (160, 160)

    ctx_id = _resolve_ctx_id(providers)
    try:
        app.prepare(ctx_id=ctx_id, det_size=tuple(det_size))
    except Exception:
        if ctx_id != -1:
            app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
            app.prepare(ctx_id=-1, det_size=tuple(det_size))
        else:
            raise
    return app


def cosine_sim(a, b):
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-6))


def _pick_best_face(faces):
    if not faces:
        return None

    def area(face):
        bbox = getattr(face, "bbox", None)
        if bbox is None or len(bbox) < 4:
            return 0.0
        x1, y1, x2, y2 = bbox[:4]
        return max(0.0, float(x2 - x1)) * max(0.0, float(y2 - y1))

    return max(faces, key=area)


def extract_embedding(*args, **kwargs):
    face_app = kwargs.get("face_app")
    frame = kwargs.get("frame")

    for a in args:
        if hasattr(a, "get"):
            face_app = a
        elif isinstance(a, np.ndarray):
            frame = a

    if face_app is None or frame is None:
        return None

    faces = face_app.get(frame)
    face = _pick_best_face(faces)
    if face is None:
        return None

    emb = getattr(face, "normed_embedding", None)
    if emb is None:
        emb = getattr(face, "embedding", None)
    if emb is None:
        return None

    return np.asarray(emb, dtype=np.float32)


def match_face(face_embedding):
    rows = db.load_face_embeddings()
    best_name, best_pid, best_score = None, None, -1.0

    for r in rows:
        score = cosine_sim(face_embedding, r["embedding"])
        if score > best_score:
            best_name = r["full_name"]
            best_pid = r["person_id"]
            best_score = score

    threshold = float(getattr(config, "FACE_SIM_THRESHOLD", 0.45))
    if best_score >= threshold:
        return {
            "person_id": best_pid,
            "person_name": best_name,
            "score": best_score,
        }
    return None


def register_person_embedding(*args, **kwargs):
    person_id = kwargs.get("person_id")
    embedding = kwargs.get("embedding")

    for a in args:
        if isinstance(a, (str, int)) and person_id is None:
            person_id = a
        elif isinstance(a, np.ndarray) and embedding is None:
            embedding = a

    for helper_name in [
        "replace_face_embedding",
        "save_face_embedding",
        "insert_face_embedding",
        "upsert_face_embedding",
    ]:
        helper = getattr(db, helper_name, None)
        if callable(helper):
            return helper(person_id, embedding)

    return False
