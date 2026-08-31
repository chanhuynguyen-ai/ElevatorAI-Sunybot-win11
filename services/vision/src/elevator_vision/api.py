from datetime import datetime, timedelta
import os
from typing import Any, Dict, Optional

import cv2
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from elevator_vision import config, db
from elevator_vision.camera_service import CameraService
from elevator_vision.face_recog import extract_embedding

app = FastAPI(title="ElevatorAI Vision", version="1.0.0")
camera_service = CameraService()

DASHBOARD_HTML = """
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Elevator CV Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; }
    .wrap { max-width: 1280px; margin: 0 auto; padding: 16px; }
    h1 { margin: 0 0 16px; font-size: 28px; }
    .grid { display:grid; grid-template-columns: 2fr 1fr; gap:16px; }
    .card { background:#111827; border:1px solid #1f2937; border-radius:16px; padding:16px; box-shadow: 0 4px 24px rgba(0,0,0,.18); }
    .stream { width:100%; min-height:420px; object-fit:contain; background:#000; border-radius:12px; }
    .stats { display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; margin-top:12px; }
    .stat { background:#0b1220; border:1px solid #243041; border-radius:12px; padding:12px; }
    .label { font-size:12px; color:#93c5fd; text-transform:uppercase; letter-spacing:.04em; }
    .value { font-size:22px; font-weight:700; margin-top:6px; }
    table { width:100%; border-collapse: collapse; font-size:14px; }
    th, td { padding:10px 8px; border-bottom:1px solid #243041; text-align:left; vertical-align:top; }
    .ok { color:#34d399; }
    .bad { color:#f87171; }
    .muted { color:#94a3b8; }
    code { color:#fde68a; }
    @media (max-width: 980px) { .grid { grid-template-columns: 1fr; } .stats { grid-template-columns: repeat(2, 1fr);} }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Elevator CV Dashboard</h1>
    <div class="grid">
      <div class="card">
        <div class="muted" style="margin-bottom:10px">Luồng camera realtime từ <code>/api/cv/stream</code></div>
        <img id="stream" class="stream" src="/api/cv/stream" alt="camera stream">
        <div class="stats">
          <div class="stat"><div class="label">Trạng thái</div><div id="online" class="value">-</div></div>
          <div class="stat"><div class="label">FPS</div><div id="fps" class="value">-</div></div>
          <div class="stat"><div class="label">Số người</div><div id="people" class="value">-</div></div>
          <div class="stat"><div class="label">Người ngồi</div><div id="sitting" class="value">-</div></div>
          <div class="stat"><div class="label">Người nằm</div><div id="lying" class="value">-</div></div>
          <div class="stat"><div class="label">Té ngã</div><div id="fall" class="value">-</div></div>
          <div class="stat"><div class="label">Camera</div><div id="cam" class="value">-</div></div>
        </div>
        <div id="error" class="bad" style="margin-top:10px"></div>
      </div>
      <div class="card">
        <h3 style="margin-top:0">Sự kiện gần nhất</h3>
        <table>
          <thead><tr><th>Thời gian</th><th>Loại</th><th>Camera</th></tr></thead>
          <tbody id="events"><tr><td colspan="3" class="muted">Chưa có dữ liệu</td></tr></tbody>
        </table>
      </div>
    </div>
    <div class="card" style="margin-top:16px">
      <h3 style="margin-top:0">Mật độ người / ngày</h3>
      <table>
        <thead><tr><th>Ngày</th><th>Trung bình</th><th>Cao nhất</th></tr></thead>
        <tbody id="density"><tr><td colspan="3" class="muted">Chưa có dữ liệu</td></tr></tbody>
      </table>
    </div>
  </div>
<script>
async function loadStatus(){
  const r = await fetch('/api/cv/status');
  const s = await r.json();
  document.getElementById('online').textContent = s.online ? 'Online' : 'Offline';
  document.getElementById('online').className = 'value ' + (s.online ? 'ok' : 'bad');
  document.getElementById('fps').textContent = (s.fps || 0).toFixed ? (s.fps || 0).toFixed(2) : s.fps;
  document.getElementById('people').textContent = s.people_count ?? '-';
  document.getElementById('sitting').textContent = s.sitting_count ?? '-';
  document.getElementById('lying').textContent = s.lying_count ?? '-';
  document.getElementById('fall').textContent = s.fall_count ?? '-';
  document.getElementById('cam').textContent = s.cam_id || '-';
  document.getElementById('error').textContent = s.error || '';
}
async function loadEvents(){
  const r = await fetch('/api/cv/events?limit=10');
  const rows = await r.json();
  const el = document.getElementById('events');
  if (!rows.length) { el.innerHTML = '<tr><td colspan="3" class="muted">Chưa có event</td></tr>'; return; }
  el.innerHTML = rows.map(x => `<tr><td>${x.event_ts || ''}</td><td>${x.event_type || ''}</td><td>${x.cam_id || ''}</td></tr>`).join('');
}
async function loadDensity(){
  const r = await fetch('/api/cv/density?days=7');
  const rows = await r.json();
  const el = document.getElementById('density');
  if (!rows.length) { el.innerHTML = '<tr><td colspan="3" class="muted">Chưa có dữ liệu density</td></tr>'; return; }
  el.innerHTML = rows.map(x => `<tr><td>${(x.day || '').slice(0,10)}</td><td>${Number(x.avg_people || 0).toFixed(2)}</td><td>${x.peak_people || 0}</td></tr>`).join('');
}
async function refreshAll(){
  try { await Promise.all([loadStatus(), loadEvents(), loadDensity()]); } catch(e) { console.error(e); }
}
refreshAll();
setInterval(refreshAll, 3000);
</script>
</body>
</html>
"""


def startup():
    # Explicit event handlers keep JetPack 4 / Python 3.6 compatibility.
    db.init_schema()
    camera_service.start()


def shutdown():
    camera_service.stop()


app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)


class RegisterFaceRequest(BaseModel):
    employee_id: Optional[str] = None
    employee_code: Optional[str] = None
    employee_name: str = Field(..., min_length=1)
    department: str = "Kỹ thuật"
    snapshot_path: str = ""
    event_id: int = 0
    cam_id: str = ""
    track_id: str = ""
    note: str = ""
    source_event: Optional[Dict[str, Any]] = None



@app.get("/health")
def health():
    status = camera_service.get_status()
    return {"status": "ok", "service": "vision", "camera_online": bool(status.get("online")), "backend": status.get("backend"), "db_backend": "postgresql" if db.postgres_enabled() else "memory"}


@app.get("/")
def root_service_info():
    if config.CV_DASHBOARD_ENABLED:
        return HTMLResponse(DASHBOARD_HTML)
    return JSONResponse(
        {
            "service": "elevator_cv",
            "status": "ok",
            "dashboard_enabled": False,
            "message": "CV service dang chay headless. Dung /api/cv/status, /api/cv/stream, /api/cv/events, /api/cv/density.",
            "stream_url": "/api/cv/stream",
            "status_url": "/api/cv/status",
            "events_url": "/api/cv/events",
            "density_url": "/api/cv/density",
        }
    )


@app.get("/api/cv/status")
def cv_status():
    return camera_service.get_status()


@app.get("/api/cv/stream")
def cv_stream():
    return StreamingResponse(
        camera_service.mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache"},
    )


@app.get("/api/cv/events")
def cv_events(limit: int = 100, cam_id: str = None, event_type: str = None):
    return db.fetch_events(limit=limit, cam_id=cam_id, event_type=event_type)


@app.get("/api/cv/density")
def cv_density(cam_id: str = Query(default=config.CAMERA_ID), days: int = Query(default=7, ge=1, le=30)):
    end_ts = datetime.now()
    start_ts = end_ts - timedelta(days=days)
    return db.fetch_density(cam_id=cam_id, start_ts=start_ts, end_ts=end_ts)


@app.post("/api/cv/register-face")
def cv_register_face(req: RegisterFaceRequest):
    if not config.ENABLE_FACE:
        raise HTTPException(status_code=400, detail="ENABLE_FACE=false. Hay bat ENABLE_FACE=true truoc khi dang ky khuon mat.")
    if camera_service.face_app is None:
        raise HTTPException(status_code=500, detail="Face app chua san sang. Hay cai insightface/onnxruntime va khoi dong lai CV service.")

    source_event = req.source_event or {}
    employee_id = (req.employee_id or req.employee_code or "").strip()
    employee_name = req.employee_name.strip()
    department = req.department.strip() or "Kỹ thuật"
    event_id = req.event_id or int(source_event.get("event_id") or source_event.get("id") or 0)
    track_id = (req.track_id or str(source_event.get("track_id") or "")).strip()
    snapshot_path = (req.snapshot_path or str(source_event.get("snapshot_path") or "")).strip()
    cam_id = (req.cam_id or str(source_event.get("cam_id") or config.CAMERA_ID)).strip() or config.CAMERA_ID

    if not employee_id:
        raise HTTPException(status_code=422, detail="Thieu employee_id/employee_code khi dang ky khuon mat.")

    frame = None

    if track_id:
        frame = camera_service.get_latest_face_crop(track_id=track_id, prefer_unknown=True)

    if frame is None and snapshot_path and os.path.isfile(snapshot_path):
        frame = cv2.imread(snapshot_path)

    if frame is None and event_id:
        event_row = db.fetch_event_by_id(event_id)
        event_path = (event_row or {}).get("snapshot_path") if isinstance(event_row, dict) else None
        if event_path and os.path.isfile(event_path):
            frame = cv2.imread(event_path)

    if frame is None:
        frame = camera_service.get_latest_face_crop(prefer_unknown=True)

    if frame is None:
        frame = camera_service.get_latest_frame_copy()

    if frame is None:
        raise HTTPException(status_code=503, detail="Chua co frame camera de dang ky khuon mat.")

    person = db.upsert_person(employee_id, employee_name, department)
    embedding = extract_embedding(face_app=camera_service.face_app, frame=frame)
    if embedding is None:
        raise HTTPException(status_code=422, detail="Khong trich xuat duoc embedding khuon mat. Hay dua mat vao camera ro hon va thu lai.")
    saved = db.replace_face_embedding(person["person_id"], embedding.tolist())

    return {
        "ok": True,
        "message": "Dang ky khuon mat thanh cong.",
        "person": person,
        "embedding": saved,
        "source": "cv_service_register_face",
        "cam_id": cam_id,
        "track_id": track_id,
        "event_id": event_id,
    }


@app.post("/api/cv/face/register")
def cv_register_face_alias(req: RegisterFaceRequest):
    return cv_register_face(req)
