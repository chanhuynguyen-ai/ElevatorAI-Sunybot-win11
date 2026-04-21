$ErrorActionPreference = 'Stop'

$pgbin = "C:\Users\ADMIN\Downloads\postgresql-16.13-3-windows-x64-binaries\pgsql\bin"
$pgctl = Join-Path $pgbin "pg_ctl.exe"
$pgisready = Join-Path $pgbin "pg_isready.exe"

Write-Host "[PG] Checking PostgreSQL..." -ForegroundColor Cyan
& $pgisready -h 127.0.0.1 -p 5432 -U postgres
if ($LASTEXITCODE -ne 0) {
  Write-Host "[PG] Starting PostgreSQL..." -ForegroundColor Yellow
  & $pgctl -D C:\pgsql-data -l C:\pgsql-data\postgres.log start
  Start-Sleep -Seconds 3
  & $pgisready -h 127.0.0.1 -p 5432 -U postgres
}
Write-Host "[PG] Done." -ForegroundColor Green
