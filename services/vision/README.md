# ElevatorAI-Vision

Computer Vision subsystem extracted from the ElevatorAI project. It keeps the latest CV service implementation from `ElevatorAI-Sunybot-win11` and supports **one codebase with three inference backends**:

- `mock`: hardware-free smoke test (default after clone)
- `ultralytics`: laptop/workstation inference
- `trt`: NVIDIA Jetson Nano TensorRT inference

## Quick start (no camera/model required)

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements/base.txt
export PYTHONPATH=src      # PowerShell: $env:PYTHONPATH="src"
python -m elevator_vision
```

Open `http://localhost:8010/health` and `http://localhost:8010/api/cv/status`.

## Real laptop mode

```bash
pip install -r requirements/laptop.txt
# put yolov8n.pt + yolov8n-pose.pt in models/
CV_BACKEND=ultralytics CAMERA_SOURCE=0 ENABLE_POSE=true PYTHONPATH=src python -m elevator_vision
```

## Jetson Nano mode

See `docs/JETSON_NANO.md`. The source remains compatible with the Python 3.6-era JetPack 4 stack used by many Jetson Nano installations. TensorRT engines must be built on the target Jetson and are not committed.

## Main features

- YOLO person/bottle detection
- multi-object tracking
- pose/posture classification and fall-event logic
- occupancy and overload events
- optional face embeddings/registration
- PostgreSQL event storage with in-memory fallback
- MJPEG stream + FastAPI status/events/density API

## Provenance

The current implementation is based primarily on the Apr-22 Win11-integrated CV snapshot. Earlier `ELEV-CV-YOLOV8N`, `ElevatorAI-Sunybot-cv-v2`, and `Computer-Vision-elevator-ai` repositories remain untouched as historical sources. See `docs/MIGRATION.md`.
