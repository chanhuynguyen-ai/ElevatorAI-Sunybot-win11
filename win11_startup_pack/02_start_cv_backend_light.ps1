$ErrorActionPreference = 'Stop'

Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -match '^python(\.exe)?$' -and
    $_.CommandLine -like "*ElevatorAI-Sunybot-cv-v2*" -and
    ($_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*main.py*")
  } |
  ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  }

$pid8001 = (Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess)
if ($pid8001) { Stop-Process -Id $pid8001 -Force -ErrorAction SilentlyContinue }

cd C:\elevator_ai\ElevatorAI-Sunybot-cv-v2

$env:CV_BACKEND="ultralytics"
$env:CV_DEVICE="cpu"
$env:YOLO_USE_HALF="false"
$env:ENABLE_FACE="false"
$env:ENABLE_POSE="true"
$env:API_HOST="0.0.0.0"
$env:API_PORT="8001"
$env:CAMERA_SOURCE="0"
$env:CAMERA_ID="CAM_01"
$env:PG_HOST="127.0.0.1"
$env:PG_PORT="5432"
$env:PG_DATABASE="elevator_cv"
$env:PG_USER="elevator_ai"
$env:PG_PASSWORD="elevator123"
$env:CV_DASHBOARD_ENABLED="true"
$env:DET_MODEL_DEV="./models/yolov8n.pt"
$env:POSE_MODEL_DEV="./models/yolov8n-pose.pt"

Write-Host "[CV-LIGHT] Starting CV backend on 8001..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m uvicorn app.api:app --host 0.0.0.0 --port 8001
