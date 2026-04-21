#!/usr/bin/env bash
set -e

pkill -f "python -m uvicorn app.api:app" || true
pkill -f "uvicorn" || true
pkill -f "gst-launch-1.0" || true
pkill -f "nvgstcapture" || true
sleep 1

sudo systemctl restart nvargus-daemon
sleep 2

source ~/venvs/elevcv_36/bin/activate
cd ~/elevator_cv_jetson_bundle
source .env.cv.runtime

echo "[INFO] Starting CV service at http://0.0.0.0:8001"
python -m uvicorn app.api:app --host 0.0.0.0 --port 8001

