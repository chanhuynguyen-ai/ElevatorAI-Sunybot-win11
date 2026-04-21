#!/bin/bash
set -e

echo "=== Sunybot install for Jetson Nano ==="

sudo apt update
sudo apt install -y python3-venv python3-dev build-essential git curl

python3 -m venv elevator_env38
source elevator_env38/bin/activate

pip install --upgrade pip setuptools wheel
pip install -r requirements_jetson.txt

echo "=== Build native module (ARM64) ==="
python3 setup.py build_ext --inplace

echo "=== Done ==="
echo "Run:"
echo "source elevator_env38/bin/activate"
echo "uvicorn backend.api:app --host 0.0.0.0 --port 8000"

