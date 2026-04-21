$ErrorActionPreference = 'Stop'

Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -match '^python(\.exe)?$' -and
    $_.CommandLine -like "*ElevatorAI-Sunybot-v2*" -and
    $_.CommandLine -like "*uvicorn*"
  } |
  ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  }

$pid8000 = (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess)
if ($pid8000) { Stop-Process -Id $pid8000 -Force -ErrorAction SilentlyContinue }

cd C:\elevator_ai\ElevatorAI-Sunybot-v2

$env:PGHOST="127.0.0.1"
$env:PGPORT="5432"
$env:PGUSER="elevator_ai"
$env:PGPASSWORD="elevator123"
$env:PGDATABASE="elevator_llm"
$env:DB_NAME="elevator_llm"
$env:ELEVATOR_CV_DB_NAME="elevator_cv"
$env:ELEVATOR_LLM_DB_NAME="elevator_llm"
$env:CV_SERVICE_BASE_URL="http://127.0.0.1:8001"
$env:OLLAMA_HOST="http://127.0.0.1:11434"
$env:LLM_MODEL="qwen2.5:1.5b-instruct"
$env:EMBED_MODEL="nomic-embed-text"
$env:KB_ENABLE_VECTOR="0"
$env:WEB_ENABLE_LEGACY_FALLBACK="1"

Write-Host "[BE] Starting main backend on 8000..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
