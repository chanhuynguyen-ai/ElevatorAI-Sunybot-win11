#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Nap bien moi truong. Thu tu uu tien: .env.cv -> .env.cv.trt -> .env.cv.example -> .env
ENV_FILE=""
for f in ".env.cv" ".env.cv.trt" ".env.cv.example" ".env"; do
  if [ -f "$f" ]; then
    ENV_FILE="$f"
    break
  fi
done

if [ -z "$ENV_FILE" ]; then
  echo "[ERROR] Khong tim thay file env (.env.cv / .env.cv.trt / .env.cv.example / .env) trong $ROOT_DIR"
  exit 1
fi

echo "[INFO] Dang nap cau hinh tu: $ENV_FILE"
# shellcheck disable=SC1090
source "$ENV_FILE"

# Kich hoat venv neu co
if [ -f ".venv/bin/activate" ]; then
  echo "[INFO] Dang kich hoat .venv"
  # shellcheck disable=SC1091
  source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
  echo "[INFO] Dang kich hoat venv"
  # shellcheck disable=SC1091
  source venv/bin/activate
else
  echo "[WARN] Khong tim thay .venv/venv. Se dung python he thong hien tai."
fi

# Kiem tra model TRT khi dung backend trt
if [ "${CV_BACKEND:-trt}" = "trt" ]; then
  if [ ! -f "${DET_ENGINE_PATH:-./models/yolov8n_fp16.engine}" ]; then
    echo "[ERROR] Khong tim thay DET_ENGINE_PATH: ${DET_ENGINE_PATH:-./models/yolov8n_fp16.engine}"
    exit 1
  fi
  if [ ! -f "${POSE_ENGINE_PATH:-./models/yolov8n_pose_fp16.engine}" ]; then
    echo "[ERROR] Khong tim thay POSE_ENGINE_PATH: ${POSE_ENGINE_PATH:-./models/yolov8n_pose_fp16.engine}"
    exit 1
  fi
fi

echo "[INFO] CV_BACKEND=${CV_BACKEND:-trt}"
echo "[INFO] CAMERA_SOURCE=${CAMERA_SOURCE:-0}"
echo "[INFO] PG_DATABASE=${PG_DATABASE:-elevator_cv}"
echo "[INFO] API_HOST=${API_HOST:-0.0.0.0}"
echo "[INFO] API_PORT=${API_PORT:-8001}"

echo "[INFO] Dang chay backend CV..."
exec python3 -m uvicorn app.api:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8001}"
