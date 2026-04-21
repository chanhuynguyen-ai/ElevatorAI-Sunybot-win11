** Phần mềm hệ thống thang máy AI agent**

SETUP POSTGRES:

lệnh khởi động sever postgre:

```bash
sudo -u postgres /usr/local/pgsql16/bin/pg_ctl \
  -D /usr/local/pgsql16/data \
  -l /usr/local/pgsql16/data/logfile start
```

lệnh khởi động test sever postgre:

```bash
sudo -u postgres /usr/local/pgsql16/bin/pg_ctl \
  -D /usr/local/pgsql16/data status
```


```bash
export CV_SERVICE_BASE_URL=http://127.0.0.1:8001
export DB_HOST=127.0.0.1
export DB_PORT=5432
export DB_USER=elevator_ai
export DB_PASSWORD=elevator123
export ELEVATOR_CV_DB_NAME=elevator_cv
export ELEVATOR_LLM_DB_NAME=elevator_llm

```
lệnh test postgresqsl:

```bash
psql -h 127.0.0.1 -p 5432 -U elevator_ai -d elevator_cv
```
```bash
SELECT COUNT(*) FROM camera_events;
SELECT COUNT(*) FROM camera_occupancy_samples;
SELECT COUNT(*) FROM person_registry;
SELECT COUNT(*) FROM face_embeddings;
```

SETUP BACKEND LLM:
```bash
source ~/venvs/sunybot_jetson/bin/activate
```
```bash
cd ~/elevator_ai_project
```

chạy backend llm:
```bash
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

test backend :

```bash
curl http://127.0.0.1:8001/api/cv/status
curl http://127.0.0.1:8001/api/cv/events
curl "http://127.0.0.1:8001/api/cv/density?days=7"

curl http://127.0.0.1:8000/api/integration/data/catalog
curl "http://127.0.0.1:8000/api/integration/data/tables?database=elevator_cv"
curl "http://127.0.0.1:8000/api/integration/data/table?database=elevator_cv&table=camera_events&limit=10"
curl "http://127.0.0.1:8000/api/integration/data/table?database=elevator_cv&table=camera_occupancy_samples&limit=10"
```

SETUP CV:

test hiệu năng:
```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

Bật chế độ hiệu năng tối đa
```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```
1) Dọn sạch mọi process đang giữ camera
```bash
pkill -f "python3 main.py"
pkill -f "uvicorn"
pkill -f "gst-launch-1.0"
pkill -f "nvgstcapture"
sleep 1
sudo systemctl restart nvargus-daemon
sleep 2
```

2) Test camera CSI độc lập trước
```bash
gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! \
'video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1,format=NV12' ! \
nvvidconv ! xvimagesink -e
```
lệnh test camera(IMX219):

kiểm tra jetson có nhận camera chưa:

```bash
gst-inspect-1.0 nvarguscamerasrc
```

lệnh chạy test camera:

```bash
gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! nvvidconv ! xvimagesink
```
lệnh chạy test camera bằng tool invdia:

```bash
nvgstcapture-1.0
```

Nếu cửa sổ preview hiện hình, camera ổn. Thoát bằng Ctrl+C.

3) Chạy app ở chế độ nhẹ để test UI trước

Tạm tắt pose để stream mượt hơn trên Nano:
```bash
cd ~/elevator_cv_jetson_bundle
```
```bash
source .env.cv.example
```
```bash
export CAMERA_SOURCE='gst:nvarguscamerasrc sensor-id=0 ! video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1,format=NV12 ! nvvidconv flip-method=0 ! video/x-raw,format=BGRx ! videoconvert ! video/x-raw,format=BGR ! appsink drop=1 max-buffers=1 sync=false'
export ENABLE_POSE=true
export ENABLE_FACE=true
export YOLO_EVERY_N=6
```

chạy backend cv:
```bash
python3 -m uvicorn app.api:app --host 0.0.0.0 --port 8001
```

lệnh khởi động riêng project cv:
```bash
python3 main.py
```
