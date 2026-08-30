# Elev_Web-main update patch

## Phạm vi đã cập nhật
- Hiện cảnh báo overload cố định ở góc trái trên cùng màn hình.
- Maintenance login chuyển sang form đăng nhập + đăng ký tài khoản thật.
- Maintenance center dùng Data Manager thật để đọc bảng từ backend.
- Bổ sung export `.csv` và `.xlsx`.
- FPS format 2 chữ số thập phân.
- Timeline đã ghép thêm sự kiện thao tác bảo trì / QR / PIN.
- Mật độ người/ngày đổi sang line chart trực quan.
- Quản lý khóa tầng đổi `Face ID` sang `QR code`.
- Màn hình gọi tầng đổi `Face ID` sang `QR code`, đồng bộ với cấu hình khóa tầng qua localStorage dùng chung.

## File frontend đã sửa
- `package.json`
- `src/App.jsx`
- `src/App.css`
- `src/hooks/useElevatorStatus.js`
- `src/services/api.js`
- `src/pages/Maintenance.jsx`
- `src/pages/Maintenance.css`
- `src/pages/CallFloor.jsx`
- `src/pages/CallFloor.css`
- `src/utils/elevatorAccess.js`
- `src/utils/exporters.js`

## Cách áp dụng vào repo `Elev_Web-main`
1. Copy đè toàn bộ các file trong patch này vào repo `Elev_Web-main`.
2. Chạy:
   ```bash
   npm install
   npm run build
   ```
3. Lấy thư mục `dist/` mới và đưa vào `ELEVATOR_AI_AGENT/gui/web/dist` để backend chính serve ở `/`.

## Lưu ý backend bắt buộc
Bản frontend này đã sẵn UI cho `elevator_user`, login/register kỹ thuật viên và data manager thật.
Để chạy full chức năng, backend chính cần có thêm:
- database `elevator_user`
- endpoint login/register cho kỹ thuật viên
- mở catalog Data Manager để có thêm `elevator_user`
- nếu muốn ghi/sửa DB thật trên UI thì backend phải cho phép `save/delete` với `elevator_user` và `elevator_llm`

## Gợi ý route backend
- `POST /api/integration/users/login`
- `POST /api/integration/users/register`
- mở rộng `DB_CATALOG` thêm `elevator_user`
