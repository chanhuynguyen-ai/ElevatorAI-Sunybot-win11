#!/usr/bin/env bash
set -e

source ~/venvs/sunybot_jetson/bin/activate
cd ~/elevator_ai_project
source .env.llm.lan

echo "[INFO] Backend mode: LAN"
echo "[INFO] OLLAMA_HOST=$OLLAMA_HOST"
echo "[INFO] CV_SERVICE_BASE_URL=$CV_SERVICE_BASE_URL"

python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

