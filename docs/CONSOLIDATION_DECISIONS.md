# Consolidation decisions

## Canonical sources

- **Full integration:** newest `ElevatorAI-Sunybot-win11` snapshot
- **Vision:** newest CV copy embedded in the Win11 snapshot, reconciled with `ElevatorAI-Sunybot-cv-v2`, `ELEV-CV-YOLOV8N`, and the older `Computer-Vision-elevator-ai` prototype
- **Agent:** newest backend/agent copy embedded in the Win11 snapshot, reconciled with `ElevatorAI-Sunybot-v2` and `ELEVATOR_AI_AGENT`
- **Web:** `Elev_Web-main`

## Duplicate handling

`ElevatorAI-Sunybot-cv-v2` and `ELEV-CV-YOLOV8N` were near-duplicates. The newer integrated Win11 CV implementation was selected rather than keeping version folders.

`ElevatorAI-Sunybot-v2` and `ELEVATOR_AI_AGENT` were also near-duplicates. The newer integrated Win11 backend was used as the base, then separated into Agent and Gateway responsibilities.

## Deliberate refactors/fixes

- removed committed Python virtual environments/caches/generated frontend output
- removed hard-coded DB password defaults
- excluded TensorRT engines and model binaries from Git
- fixed NumPy truth-value handling in posture classification
- fixed the missing `CameraService.get_latest_face_crop()` path used by face registration
- made Vision restartable after camera/runtime startup failure
- added hardware-free mock camera/inference for clone/CI review
- added psycopg3 + psycopg2 database compatibility in Agent for desktop vs JetPack
- separated browser orchestration/auth/Data Manager into Gateway instead of leaving it inside the Agent service
- restored allow-listed, primary-key-safe Data Manager writes while keeping `elevator_cv` read-only
- hid `employees.password_hash` from generic Data Manager responses
- established Laptop-native Vision and Laptop+Jetson hybrid deployment layouts

## Excluded project

`Elevator-DHT` is intentionally not included. It is a separate group project, not part of this personal-project consolidation.
