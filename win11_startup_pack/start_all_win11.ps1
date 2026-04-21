$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "[1/4] Start PostgreSQL" -ForegroundColor Cyan
& powershell -ExecutionPolicy Bypass -File (Join-Path $base '01_start_postgresql.ps1')

Write-Host "[2/4] Open CV backend window" -ForegroundColor Cyan
Start-Process powershell -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-File',(Join-Path $base '02_start_cv_backend.ps1')
Start-Sleep -Seconds 4

Write-Host "[3/4] Open main backend window" -ForegroundColor Cyan
Start-Process powershell -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-File',(Join-Path $base '03_start_main_backend.ps1')
Start-Sleep -Seconds 4

Write-Host "[4/4] Open frontend" -ForegroundColor Cyan
& powershell -ExecutionPolicy Bypass -File (Join-Path $base '04_open_frontend.ps1')

Write-Host 'Done. Frontend: http://127.0.0.1:8000/' -ForegroundColor Green
