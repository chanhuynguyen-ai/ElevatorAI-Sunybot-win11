#!/usr/bin/env bash
set -e

source ~/venvs/sunybot_jetson/bin/activate
cd ~/elevator_ai_project

LAN_ENV=".env.llm.lan"
LOCAL_ENV=".env.llm.local"

if [ ! -f "$LAN_ENV" ]; then
 echo "[ERROR] Missing $LAN_ENV"
 exit 1
fi

if [ ! -f "$LOCAL_ENV" ]; then
 echo "[ERROR] Missing $LOCAL_ENV"
 exit 1
fi

CURRENT_HOST_LINE=$(grep '^export OLLAMA_HOST=' "$LAN_ENV" || true)

if [ -z "$CURRENT_HOST_LINE" ]; then
 echo "[ERROR] Cannot find export OLLAMA_HOST=... in $LAN_ENV"
 exit 1
fi

CURRENT_HOST=$(echo "$CURRENT_HOST_LINE" | sed 's/^export OLLAMA_HOST=//')

echo "[INFO] Probing LAN Ollama at: $CURRENT_HOST"

if curl -s --max-time 5 "$CURRENT_HOST/api/tags" >/dev/null 2>&1; then
 echo "[OK] LAN Ollama reachable -> use LAN mode"
 source "$LAN_ENV"
 MODE_USED="LAN"
else
 echo "[WARN] LAN Ollama unreachable -> fallback to LOCAL mode"
 source "$LOCAL_ENV"
 MODE_USED="LOCAL"
fi

echo
echo "========================================"
echo "BACKEND START MODE"
echo "Mode đang dùng       : $MODE_USED"
echo "OLLAMA_HOST hiệu lực : $OLLAMA_HOST"
echo "LLM_MODEL            : $LLM_MODEL"
echo "EMBED_MODEL          : $EMBED_MODEL"
echo "CV_SERVICE_BASE_URL  : $CV_SERVICE_BASE_URL"
echo "========================================"
echo

python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

