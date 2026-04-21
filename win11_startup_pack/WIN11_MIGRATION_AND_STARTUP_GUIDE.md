# Sunybot Smart Elevator - Hướng dẫn chuyển runtime từ Jetson Nano sang Win11

## 1. Mục tiêu tài liệu
Tài liệu này tổng hợp toàn bộ cách dựng và chạy lại dự án trên **Windows 11** sau khi bỏ hướng chạy chính trên **Jetson Nano**.

Mục tiêu hiện tại của hệ thống trên Win11 là:
- chạy được **PostgreSQL**
- chạy được **CV backend** ở cổng **8001**
- chạy được **main backend + UI** ở cổng **8000**
- frontend React truy cập qua `http://127.0.0.1:8000/`
- main backend lấy dữ liệu từ CV backend qua `CV_SERVICE_BASE_URL=http://127.0.0.1:8001`
- chatbot kỹ thuật viên và người dùng dùng backend chính
- phần CV có thể mở rộng dần từ mode nhẹ đến mode có nhận diện khuôn mặt nhân viên

---

## 2. Kiến trúc runtime hiện tại trên Win11

### 2.1. Luồng tổng thể
1. **PostgreSQL** chạy local trên Win11
2. **CV backend** chạy riêng ở cổng `8001`
3. **Main backend** chạy riêng ở cổng `8000`
4. **Frontend React dist** được main backend phục vụ tại `/`
5. Main backend gọi CV backend qua API để lấy:
   - trạng thái camera
   - event timeline
   - density
   - stream proxy
6. Chatbot maintenance và customer đều đi qua main backend

### 2.2. Tách database
- `elevator_cv`: dữ liệu realtime CV
  - `camera_events`
  - `camera_occupancy_samples`
  - `person_registry`
  - `face_embeddings`
- `elevator_llm`: dữ liệu chatbot / knowledge / employee
  - `employees`
  - `intents`
  - `prompts`
  - `answers`
  - `chat_logs`
- `elevator_user`: nhánh user/runtime mở rộng nếu backend hỗ trợ thêm

---

## 3. Repo đang dùng trên Win11

### 3.1. Frontend source
- `C:\elevator_ai\Elev_Web-main`

### 3.2. Main backend + React dist host
- `C:\elevator_ai\ElevatorAI-Sunybot-v2`

### 3.3. CV backend
- `C:\elevator_ai\ElevatorAI-Sunybot-cv-v2`

### 3.4. PostgreSQL binaries
- `C:\Users\ADMIN\Downloads\postgresql-16.13-3-windows-x64-binaries\pgsql\bin`

### 3.5. PostgreSQL data dir
- `C:\pgsql-data`

---

## 4. Những điểm đã chốt khi chuyển từ Jetson sang Win11

### 4.1. Jetson không còn là runtime chính
Hiện tại runtime chính là **Win11**.
Jetson được xem là nhánh triển khai sau, không phải nhánh demo chính lúc này.

### 4.2. Backend và CV không được gộp chung process
- CV backend phải chạy riêng ở `8001`
- main backend + UI phải chạy riêng ở `8000`

### 4.3. Nguồn sự thật của dữ liệu realtime
- dữ liệu camera / event / density / unknown / face phải lấy từ **CV backend** hoặc `elevator_cv`
- chatbot không được tự đoán dữ liệu camera

### 4.4. LLM runtime trên Win11
- dùng `OLLAMA_HOST=http://127.0.0.1:11434` hoặc máy Win11 local
- `LLM_MODEL` mặc định đang dùng: `qwen2.5:1.5b-instruct`
- `EMBED_MODEL` mặc định đang dùng: `nomic-embed-text`

### 4.5. CV hiện chạy an toàn nhất ở CPU mode
Vì máy hiện tại từng báo `torch.cuda.is_available(): False`, nên mode ổn định để debug là:
- `CV_DEVICE=cpu`
- `YOLO_USE_HALF=false`
- bật dần từng tính năng

---

## 5. Điều kiện cần trước khi start hệ thống

### 5.1. PostgreSQL đã được khởi tạo
Đã có các DB:
- `elevator_cv`
- `elevator_llm`

### 5.2. Main backend đã có bảng LLM cơ bản
Ít nhất cần có:
- `employees`
- `prompts`
- `intents`
- `answers`

### 5.3. Frontend đã build dist mới
Sau khi sửa frontend source, cần build lại:
```powershell
cd C:\elevator_ai\Elev_Web-main
npm install
npm run build
xcopy /E /I /Y C:\elevator_ai\Elev_Web-main\dist C:\elevator_ai\ElevatorAI-Sunybot-v2\gui\web\dist
```

---

## 6. Thứ tự chạy chuẩn trên Win11
Luôn chạy theo thứ tự:

1. **PostgreSQL**
2. **CV backend**
3. **Main backend**
4. **Refresh frontend**

Không nên đảo thứ tự.
Nếu CV backend chạy trước khi PostgreSQL chưa sống thì CV sẽ lỗi `connection refused 127.0.0.1:5432`.

---

## 7. Mode chạy khuyến nghị

### 7.1. Mode demo ổn định
Dùng khi cần demo mượt trước:
- `ENABLE_FACE=false`
- `ENABLE_POSE=true`
- `CV_DEVICE=cpu`

### 7.2. Mode đăng ký và nhận diện khuôn mặt nhân viên
Dùng khi test face registration / face recognition:
- `ENABLE_FACE=true`
- `ENABLE_POSE=true`
- `CV_DEVICE=cpu`

Lưu ý: nếu `ENABLE_FACE=false` thì UI có thể mở form đăng ký, nhưng **không thể nhận diện khuôn mặt realtime đúng nghĩa**.

---

## 8. Lệnh đang dùng để start dự án trên Win11

### 8.1. PostgreSQL
```powershell
$pgbin = "C:\Users\ADMIN\Downloads\postgresql-16.13-3-windows-x64-binaries\pgsql\bin"
$pgctl = Join-Path $pgbin "pg_ctl.exe"
$pgisready = Join-Path $pgbin "pg_isready.exe"

& $pgisready -h 127.0.0.1 -p 5432 -U postgres
if ($LASTEXITCODE -ne 0) {
  & $pgctl -D C:\pgsql-data -l C:\pgsql-data\postgres.log start
  Start-Sleep -Seconds 3
  & $pgisready -h 127.0.0.1 -p 5432 -U postgres
}
```

### 8.2. CV backend
```powershell
cd C:\elevator_ai\ElevatorAI-Sunybot-cv-v2

$env:CV_BACKEND="ultralytics"
$env:CV_DEVICE="cpu"
$env:YOLO_USE_HALF="false"
$env:ENABLE_FACE="true"
$env:ENABLE_POSE="true"

$env:API_HOST="0.0.0.0"
$env:API_PORT="8001"
$env:CAMERA_SOURCE="0"
$env:CAMERA_ID="CAM_01"

$env:PG_HOST="127.0.0.1"
$env:PG_PORT="5432"
$env:PG_DATABASE="elevator_cv"
$env:PG_USER="elevator_ai"
$env:PG_PASSWORD="elevator123"

$env:CV_DASHBOARD_ENABLED="true"
$env:DET_MODEL_DEV="./models/yolov8n.pt"
$env:POSE_MODEL_DEV="./models/yolov8n-pose.pt"

.\.venv\Scripts\python.exe -m uvicorn app.api:app --host 0.0.0.0 --port 8001
```

### 8.3. Main backend
```powershell
cd C:\elevator_ai\ElevatorAI-Sunybot-v2

$env:PGHOST="127.0.0.1"
$env:PGPORT="5432"
$env:PGUSER="elevator_ai"
$env:PGPASSWORD="elevator123"
$env:PGDATABASE="elevator_llm"
$env:DB_NAME="elevator_llm"

$env:ELEVATOR_CV_DB_NAME="elevator_cv"
$env:ELEVATOR_LLM_DB_NAME="elevator_llm"

$env:CV_SERVICE_BASE_URL="http://127.0.0.1:8001"

$env:OLLAMA_HOST="http://127.0.0.1:11434"
$env:LLM_MODEL="qwen2.5:1.5b-instruct"
$env:EMBED_MODEL="nomic-embed-text"

$env:KB_ENABLE_VECTOR="0"
$env:WEB_ENABLE_LEGACY_FALLBACK="1"

.\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

### 8.4. Frontend
Mở:
```text
http://127.0.0.1:8000/
```
Sau đó nhấn:
- `Ctrl + F5`

---

## 9. File script đã tạo kèm tài liệu này
Trong gói Win11 startup pack có các file:
- `README_START_WIN11.md`
- `WIN11_MIGRATION_AND_STARTUP_GUIDE.md`
- `01_start_postgresql.ps1`
- `02_start_cv_backend.ps1`
- `02_start_cv_backend_light.ps1`
- `03_start_main_backend.ps1`
- `04_open_frontend.ps1`
- `start_all_win11.ps1`
- `start_all_win11.bat`
- `stop_all_win11.ps1`

---

## 10. Cách dùng nhanh nhất

### 10.1. Dùng PowerShell tổng
```powershell
powershell -ExecutionPolicy Bypass -File .\start_all_win11.ps1
```

### 10.2. Dùng file batch
```bat
start_all_win11.bat
```

### 10.3. Chạy từng phần
- chạy `01_start_postgresql.ps1`
- chạy `02_start_cv_backend.ps1`
- chạy `03_start_main_backend.ps1`
- chạy `04_open_frontend.ps1`

---

## 11. Cách kiểm tra hệ thống đã lên chưa

### PostgreSQL
```powershell
& "C:\Users\ADMIN\Downloads\postgresql-16.13-3-windows-x64-binaries\pgsql\bin\pg_isready.exe" -h 127.0.0.1 -p 5432 -U postgres
```

### CV backend
```text
http://127.0.0.1:8001/api/cv/status
http://127.0.0.1:8001/api/cv/events
```

### Main backend
```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/api/integration/cv/status
http://127.0.0.1:8000/
```

---

## 12. Lỗi thường gặp và cách xử lý nhanh

### 12.1. CV lỗi PostgreSQL connection refused
Nguyên nhân: PostgreSQL chưa chạy.
Cách xử lý: chạy lại `01_start_postgresql.ps1` trước.

### 12.2. CV lỗi device=0 / CUDA unavailable
Nguyên nhân: máy đang dùng torch CPU-only.
Cách xử lý: để:
- `CV_DEVICE=cpu`
- `YOLO_USE_HALF=false`

### 12.3. Frontend vẫn là bản cũ
Nguyên nhân: chưa copy dist mới sang backend.
Cách xử lý:
```powershell
cd C:\elevator_ai\Elev_Web-main
npm run build
xcopy /E /I /Y C:\elevator_ai\Elev_Web-main\dist C:\elevator_ai\ElevatorAI-Sunybot-v2\gui\web\dist
```

### 12.4. Có status nhưng không có stream camera
Nguyên nhân: CV stream proxy lỗi hoặc camera source lỗi.
Cách xử lý:
- kiểm tra `http://127.0.0.1:8001/api/cv/stream`
- nếu webcam không ổn, đổi `CAMERA_SOURCE` sang video file để test

### 12.5. Đăng ký khuôn mặt có form nhưng không nhận diện nhân viên
Nguyên nhân thường gặp:
- `ENABLE_FACE=false`
- face runtime chưa sẵn sàng
- phần nhận diện realtime trong `camera_service.py` chưa hoàn thiện hoàn toàn

---

## 13. Khuyến nghị chạy thực tế
Để demo ổn định trên Win11:
- chạy PostgreSQL trước
- chạy CV ở mode CPU ổn định
- chỉ bật face khi thực sự cần test
- build lại frontend mỗi khi đã sửa `Maintenance.jsx` / `Maintenance.css`
- dùng `start_all_win11.ps1` để mở nhanh toàn bộ hệ thống

---

## 14. Kết luận
Bản Win11 hiện là nhánh chạy chính để:
- demo luận văn / đồ án
- kiểm thử tích hợp backend + CV + UI
- tối ưu dần chatbot bảo trì và nhận diện nhân viên

Jetson Nano hiện không còn là điểm chạy chính ở thời điểm này. Win11 là môi trường chạy nhanh, dễ dựng lại, dễ debug và phù hợp để hoàn thiện hệ thống từ đầu đến bây giờ.
