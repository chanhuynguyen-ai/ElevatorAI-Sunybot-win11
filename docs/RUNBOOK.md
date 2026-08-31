# Runbook

## Fastest full-system start

```bash
cp .env.example .env
# change POSTGRES_PASSWORD in .env
docker compose up --build
```

Then open `http://localhost:8080`. Gateway API is available at `http://localhost:8000`.

The default Compose profile uses the mock CV runtime/camera, so it does not need a physical camera or model. Ollama is optional: without it, deterministic/rule and DB-backed paths continue to work while generative answers report a fallback.

## Laptop CV

Set in `.env`:

```text
CV_BACKEND=ultralytics
CAMERA_SOURCE=0
ENABLE_POSE=true
```

Install/download the model files as documented in `services/vision/models/README.md`.

## Jetson Nano CV

Use the same repository, but build TensorRT engines on the Nano and use the GStreamer camera source described in `services/vision/docs/JETSON_NANO.md`.
