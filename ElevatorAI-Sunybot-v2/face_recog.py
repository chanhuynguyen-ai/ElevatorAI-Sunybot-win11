import numpy as np

from app import config, db

try:
    from insightface.app import FaceAnalysis
except Exception:
    FaceAnalysis = None



def create_face_app():
    if not config.ENABLE_FACE:
        return None
    if FaceAnalysis is None:
        raise RuntimeError("ENABLE_FACE=true nhưng thiếu insightface/onnxruntime")
    app = FaceAnalysis(name="buffalo_l")
    app.prepare(ctx_id=0, det_size=config.FACE_DET_SIZE)
    return app



def cosine_sim(a, b):
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-6))



def match_face(face_embedding):
    rows = db.load_face_embeddings()
    best_name, best_pid, best_score = None, None, -1.0
    for r in rows:
        score = cosine_sim(face_embedding, r["embedding"])
        if score > best_score:
            best_name = r["full_name"]
            best_pid = r["person_id"]
            best_score = score
    if best_score >= config.FACE_SIM_THRESHOLD:
        return {"person_id": best_pid, "person_name": best_name, "score": best_score}
    return None
