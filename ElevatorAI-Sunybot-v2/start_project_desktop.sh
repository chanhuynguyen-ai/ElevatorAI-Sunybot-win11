#!/usr/bin/env bash
set -e

BASE_DIR=~/elevator_ai_project
LAN_ENV="$BASE_DIR/.env.llm.lan"

cd "$BASE_DIR"

if [ ! -f "$LAN_ENV" ]; then
 echo "[ERROR] Missing $LAN_ENV"
 echo
 echo "Nhấn Enter để đóng..."
 read
 exit 1
fi

CURRENT_HOST_LINE=$(grep '^export OLLAMA_HOST=' "$LAN_ENV" || true)

if [ -z "$CURRENT_HOST_LINE" ]; then
 echo "[ERROR] Không tìm thấy export OLLAMA_HOST trong $LAN_ENV"
 echo
 echo "Nhấn Enter để đóng..."
 read
 exit 1
fi

CURRENT_HOST=$(echo "$CURRENT_HOST_LINE" | sed 's/^export OLLAMA_HOST=//')
CURRENT_IP=$(echo "$CURRENT_HOST" | sed -E 's#http://([^:/]+):([0-9]+)#\1#')
CURRENT_PORT=$(echo "$CURRENT_HOST" | sed -E 's#http://([^:/]+):([0-9]+)#\2#')

if [ -z "$CURRENT_PORT" ]; then
 CURRENT_PORT="11434"
fi

clear
echo "========================================"
echo "ELEVATOR AI - START PROJECT"
echo "========================================"
echo "IP LAN hiện đang set:"
echo "  $CURRENT_IP"
echo "Port:"
echo "  $CURRENT_PORT"
echo
echo "Nếu đúng IP Win11 hiện tại -> nhấn Enter"
echo "Nếu sai -> nhập IP mới rồi nhấn Enter"
echo
echo -n "IP Win11 [$CURRENT_IP]: "
read USER_IP

if [ -z "$USER_IP" ]; then
 FINAL_IP="$CURRENT_IP"
else
 FINAL_IP="$USER_IP"
fi

FINAL_HOST="http://$FINAL_IP:$CURRENT_PORT"

if [ "$FINAL_IP" != "$CURRENT_IP" ]; then
 sed -i "s|^export OLLAMA_HOST=.*|export OLLAMA_HOST=$FINAL_HOST|" "$LAN_ENV"
 echo
 echo "[INFO] Đã cập nhật .env.llm.lan:"
 echo "       $FINAL_HOST"
else
 echo
 echo "[INFO] Giữ nguyên IP LAN:"
 echo "       $FINAL_HOST"
fi

echo
echo "[INFO] Kiểm tra kết nối LAN tới Win11..."
if curl -s --max-time 5 "$FINAL_HOST/api/tags" >/dev/null 2>&1; then
 echo "[OK] Kết nối LAN thành công."
else
 echo "[WARN] Kết nối LAN thất bại."
 echo "[WARN] Backend sẽ fallback sang LOCAL nếu cần."
fi

echo
echo "[INFO] Bắt đầu khởi động toàn bộ project..."
./start_all.sh

echo
echo "========================================"
echo "[OK] Setup backend thành công."
echo "Project đã được khởi động."
echo "Health : http://127.0.0.1:8000/health"
echo "CV API : http://127.0.0.1:8001/api/cv/status"
echo "========================================"
echo
echo "Nhấn Enter để đóng cửa sổ..."
read

