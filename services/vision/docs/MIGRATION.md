# CV migration decisions

Primary source: latest CV code embedded in `ElevatorAI-Sunybot-win11` (Apr 22 snapshot).

- `ElevatorAI-Sunybot-cv-v2`: almost identical earlier service; retained only as provenance.
- `ELEV-CV-YOLOV8N`: earlier near-duplicate; not copied as a second implementation.
- `Computer-Vision-elevator-ai`: older prototype. Its useful architectural ideas (PostgreSQL fallback, face registration history) were reviewed, while duplicate/obsolete desktop scripts were not migrated.
- Generated `__pycache__`, TensorRT engines, local runtime env files and old frontend demo are intentionally excluded.
