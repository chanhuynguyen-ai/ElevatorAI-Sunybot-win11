# ElevatorAI-Sunybot-win11

Monorepo Win11 cho du an ElevatorAI-Sunybot.

## Cau truc
- `Elev_Web-main/`: frontend React/Vite
- `ElevatorAI-Sunybot-v2/`: main backend + LLM + API integration
- `ElevatorAI-Sunybot-cv-v2/`: CV backend realtime
- `win11_startup_pack/`: bo script chay nhanh tren Win11
- `requirements-win.txt`: dependency Python cho Win11

## Runtime chuan Win11
- CV service chay cong `8001`
- Main backend + UI chay cong `8000`
- PostgreSQL local chay `127.0.0.1:5432`
- Ollama local/LAN chay `127.0.0.1:11434`

## Chay nhanh
1. Start PostgreSQL
2. Start CV backend
3. Start main backend
4. Mo frontend tai `http://127.0.0.1:8000/`

## File ho tro
- `win11_startup_pack/start_all_win11.ps1`
- `win11_startup_pack/start_all_win11.bat`
- `win11_startup_pack/stop_all_win11.ps1`

## Ghi chu
- Khong commit `.venv`, `node_modules`, `__pycache__`, file log, cache.
- Neu sua frontend, phai `npm run build` roi copy `dist` sang:
  `ElevatorAI-Sunybot-v2/gui/web/dist`
