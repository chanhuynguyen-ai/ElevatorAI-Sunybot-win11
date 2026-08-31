# Laptop / Windows deployment

This layout keeps the camera-facing Vision service **native on Windows** and runs PostgreSQL, Agent, Gateway and Web in Docker. This avoids unreliable webcam passthrough through Docker Desktop.

## 1. Start the platform core

From the repository root:

```powershell
Copy-Item .env.example .env
# edit POSTGRES_PASSWORD in .env

docker compose -f docker-compose.yml -f deployments/laptop-windows/compose.override.yml `
  up --build postgres agent gateway web
```

## 2. Start Vision natively

In a second PowerShell terminal:

```powershell
cd services/vision
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements/laptop.txt
$env:PYTHONPATH = "src"
$env:CV_BACKEND = "ultralytics"
$env:CAMERA_SOURCE = "0"
$env:ENABLE_POSE = "true"
$env:CV_DB_ENABLED = "true"
$env:PG_HOST = "127.0.0.1"
$env:PG_PORT = "5432"
$env:PG_DATABASE = "elevator_cv"
$env:PG_USER = "elevator_ai"
$env:PG_PASSWORD = "<same value as POSTGRES_PASSWORD>"
python -m elevator_vision
```

Put the model files described in `services/vision/models/README.md` under `services/vision/models/` before selecting the Ultralytics backend.

Open `http://localhost:8080`.
