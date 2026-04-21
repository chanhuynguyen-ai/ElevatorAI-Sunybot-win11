#!/usr/bin/env bash
set +e

pkill -f "python -m uvicorn app.api:app" || true
pkill -f "python -m uvicorn backend.api:app" || true
pkill -f "uvicorn app.api:app" || true
pkill -f "uvicorn backend.api:app" || true
pkill -f "uvicorn" || true
pkill -f "gst-launch-1.0" || true
pkill -f "nvgstcapture" || true

sleep 2

echo "[INFO] stop_all.sh da chay xong"
exit 0
