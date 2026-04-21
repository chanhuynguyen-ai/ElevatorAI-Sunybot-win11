# Elevator CV Service - Jetson Ready

## 1. Tao PostgreSQL rieng
```sql
CREATE USER elevator_ai WITH PASSWORD 'elevator123';
CREATE DATABASE elevator_cv OWNER elevator_ai;
CREATE DATABASE elevator_llm OWNER elevator_ai;
GRANT ALL PRIVILEGES ON DATABASE elevator_cv TO elevator_ai;
GRANT ALL PRIVILEGES ON DATABASE elevator_llm TO elevator_ai;
```

## 2. Chuan bi model
- Trên máy dev:
  - đặt `yolov8n.pt`, `yolov8n-pose.pt` vào `models/`
  - chạy `python scripts/export_models.py`
- Copy `models/*.onnx` sang Jetson Nano

## 3. Build TensorRT engine trên Nano
```bash
bash scripts/build_engines.sh
```

## 4. Cai Python deps tren Jetson Python 3.6
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv python3-psycopg2 build-essential python3-dev
python3 -m pip install --user -r requirements.txt
```

## 5. Nap env CV
```bash
source .env.cv.example
```

## 6. Chay service
```bash
python3 main.py
```

## 7. Test
- Status: `curl http://127.0.0.1:8000/api/cv/status`
- Stream: `http://<JETSON_IP>:8000/api/cv/stream`
- Events: `http://<JETSON_IP>:8000/api/cv/events`
- Density: `http://<JETSON_IP>:8000/api/cv/density?days=7`

## 8. Neu camera CSI khong mo duoc
Dat `CAMERA_SOURCE` thanh pipeline GStreamer, vi du:
```bash
export CAMERA_SOURCE='gst:nvarguscamerasrc ! video/x-raw(memory:NVMM), width=1280, height=720, framerate=30/1, format=NV12 ! nvvidconv flip-method=0 ! video/x-raw, format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink'
```
