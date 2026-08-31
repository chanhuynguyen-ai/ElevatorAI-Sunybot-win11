# Hybrid Laptop + Jetson Nano deployment

Recommended production-shaped layout for the original project:

- **Laptop/Windows:** Web, Gateway, Agent, PostgreSQL, Ollama
- **Jetson Nano:** camera + TensorRT Vision service

This keeps heavy LLM/web/database workloads off the Nano while letting the Nano own low-latency edge inference.

## Laptop side

Set `VISION_SERVICE_URL` to the Jetson's LAN address and start only the core services:

```powershell
Copy-Item .env.example .env
# edit POSTGRES_PASSWORD in .env
$env:VISION_SERVICE_URL = "http://192.168.1.50:8010"

docker compose -f docker-compose.yml -f deployments/hybrid-jetson-nano/compose.override.yml `
  up --build postgres agent gateway web
```

The override exposes PostgreSQL on port 5432 so the Jetson Vision service can write events to `elevator_cv`. Only do this on a trusted LAN and restrict the host firewall to the Jetson's IP.

## Jetson Nano side

Use the same Vision source under `services/vision` (or clone `ElevatorAI-Vision`). Install `requirements/jetson-nano.txt`, build TensorRT engines on the Nano, then configure:

```bash
export PYTHONPATH=src
export CV_BACKEND=trt
export CAMERA_SOURCE='gst:<your validated GStreamer pipeline>'
export ENABLE_POSE=true
export CV_DB_ENABLED=true
export PG_HOST='<laptop LAN IP>'
export PG_PORT=5432
export PG_DATABASE=elevator_cv
export PG_USER=elevator_ai
export PG_PASSWORD='<same value as POSTGRES_PASSWORD>'
python3 -m elevator_vision
```

See `services/vision/docs/JETSON_NANO.md` for JetPack/TensorRT details.
