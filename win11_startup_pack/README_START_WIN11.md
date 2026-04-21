# README - Start dự án Sunybot trên Win11

## Gói này gồm gì
- `WIN11_MIGRATION_AND_STARTUP_GUIDE.md`: tài liệu tổng hợp toàn bộ quá trình chuyển từ Jetson sang Win11 và cách chạy hiện tại
- `01_start_postgresql.ps1`: start PostgreSQL
- `02_start_cv_backend.ps1`: start CV backend với face recognition bật
- `02_start_cv_backend_light.ps1`: start CV backend mode nhẹ, tắt face
- `03_start_main_backend.ps1`: start main backend
- `04_open_frontend.ps1`: mở frontend
- `start_all_win11.ps1`: mở lần lượt PostgreSQL, CV backend, main backend, frontend
- `start_all_win11.bat`: file batch gọi PowerShell tổng
- `stop_all_win11.ps1`: dừng backend/CV đang chạy trên 8000/8001

## Cách chạy nhanh nhất
### Cách 1 - PowerShell
```powershell
powershell -ExecutionPolicy Bypass -File .\start_all_win11.ps1
```

### Cách 2 - Batch
Nhấp đúp:
- `start_all_win11.bat`

## Nếu muốn chạy tay từng bước
1. `01_start_postgresql.ps1`
2. `02_start_cv_backend.ps1`
3. `03_start_main_backend.ps1`
4. `04_open_frontend.ps1`

## Nếu máy yếu hoặc camera nặng
Dùng:
- `02_start_cv_backend_light.ps1`

## URL kiểm tra
- Main UI: `http://127.0.0.1:8000/`
- Health: `http://127.0.0.1:8000/health`
- CV status: `http://127.0.0.1:8001/api/cv/status`
- CV integration status: `http://127.0.0.1:8000/api/integration/cv/status`
