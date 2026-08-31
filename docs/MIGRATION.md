# Repository consolidation

## Included legacy personal repositories

- `ElevatorAI-Sunybot-win11` -> latest integrated reference, Windows startup behavior, newest backend/CV code
- `ElevatorAI-Sunybot-v2` -> earlier integrated backend snapshot
- `ElevatorAI-Sunybot-cv-v2` -> earlier CV service snapshot
- `ELEVATOR_AI_AGENT` -> earlier agent/backend snapshot
- `Elev_Web-main` -> React/Vite source
- `ELEV-CV-YOLOV8N` -> earlier near-duplicate CV service
- `Computer-Vision-elevator-ai` -> older CV prototype / architecture history

`Elevator-DHT` is intentionally excluded because it is a separate group project.

## Rules used

1. Original repositories are never modified or deleted.
2. Newest working implementation wins when files are duplicated.
3. Generated artifacts, virtual environments, caches, `.save/.bak` files and device-specific TensorRT engines are excluded.
4. Hard-coded passwords are removed from source; only `.env.example` placeholders remain.
5. A hardware-free mock mode is the default so a clean clone can be smoke-tested without a camera, GPU, model or Jetson.
6. Real Laptop and Jetson deployments stay in the same Vision codebase through runtime adapters rather than duplicated applications.
