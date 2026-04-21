#!/usr/bin/env bash
set +e

BASE_DIR=~/elevator_ai_project
cd "$BASE_DIR"

clear
echo "========================================"
echo "ELEVATOR AI - STOP PROJECT"
echo "========================================"
echo
echo "[INFO] Dang tat toan bo backend / CV ..."
./stop_all.sh

sleep 2

BACKEND_ALIVE=0
CV_ALIVE=0

curl -s http://127.0.0.1:8000/health >/dev/null 2>&1
if [ $? -eq 0 ]; then
  BACKEND_ALIVE=1
fi

curl -s http://127.0.0.1:8001/api/cv/status >/dev/null 2>&1
if [ $? -eq 0 ]; then
  CV_ALIVE=1
fi

echo
echo "========================================"
if [ "$BACKEND_ALIVE" -eq 0 ] && [ "$CV_ALIVE" -eq 0 ]; then
  echo "[OK] Tat toan bo backend thanh cong."
else
  echo "[WARN] Da chay stop_all.sh nhung van con service phan hoi."
  echo "[WARN] Backend alive: $BACKEND_ALIVE"
  echo "[WARN] CV alive     : $CV_ALIVE"
fi
echo "========================================"
echo
echo "Nhan Enter de dong cua so..."
read
