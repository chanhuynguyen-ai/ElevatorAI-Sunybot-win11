Write-Host "Stopping CV backend and main backend..." -ForegroundColor Yellow

Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -match '^python(\.exe)?$' -and (
      $_.CommandLine -like "*ElevatorAI-Sunybot-cv-v2*" -or
      $_.CommandLine -like "*ElevatorAI-Sunybot-v2*"
    ) -and $_.CommandLine -like "*uvicorn*"
  } |
  ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  }

foreach ($p in 8000,8001) {
  $pid = (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess)
  if ($pid) { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue }
}

Write-Host "Stopped." -ForegroundColor Green
