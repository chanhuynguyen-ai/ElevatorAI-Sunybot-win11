#!/usr/bin/env bash
set -e

BASE_DIR=~/elevator_ai_project
LOG_DIR=$BASE_DIR/logs
TS=$(date +%F_%H-%M-%S)

mkdir -p "$LOG_DIR"

echo "[1/3] Starting PostgreSQL..."
cd "$BASE_DIR"
./run_postgres.sh > "$LOG_DIR/postgres_$TS.log" 2>&1 || true

echo "[2/3] Starting CV service..."
nohup "$BASE_DIR/run_cv.sh" > "$LOG_DIR/cv_$TS.log" 2>&1 &
CV_PID=$!

echo "[INFO] Waiting for CV service on 8001..."
for i in {1..30}; do
  if curl -s http://127.0.0.1:8001/api/cv/status >/dev/null 2>&1; then
    echo "[OK] CV service is up"
    break
  fi
  sleep 2
done

echo "[3/3] Starting backend..."
nohup "$BASE_DIR/run_backend_auto.sh" > "$LOG_DIR/backend_$TS.log" 2>&1 &
BE_PID=$!

echo "[INFO] Waiting for backend on 8000..."
for i in {1..30}; do
  if curl -s http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "[OK] Backend is up"
    break
  fi
  sleep 2
done

echo
echo "=============================="
echo "SYSTEM STARTED"
echo "CV PID      : $CV_PID"
echo "Backend PID : $BE_PID"
echo "Logs        : $LOG_DIR"
echo "CV test     : curl http://127.0.0.1:8001/api/cv/status"
echo "BE test     : curl http://127.0.0.1:8000/health"
echo "=============================="


