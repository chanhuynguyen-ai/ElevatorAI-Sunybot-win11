# ElevatorAI-Platform

A consolidated, reviewable and runnable version of the ElevatorAI smart-elevator project. This repository replaces seven overlapping personal repositories with clear service boundaries while **leaving every original repository untouched for rollback/history**.

## What is in this repository?

- `apps/web` — the real React/Vite interface from `Elev_Web-main`
- `services/vision` — the latest YOLO/tracking/posture/face CV service, supporting Laptop + Jetson Nano
- `services/agent` — the latest LLM/RAG/agent router, planner, memory and tool registry
- `services/gateway` — browser-facing integration API and CV proxy
- `infrastructure/postgres` — reproducible initialization for separate `elevator_cv` and `elevator_llm` databases

## Clone-and-run path

```bash
git clone <this-repo>
cd ElevatorAI-Platform
cp .env.example .env
# edit .env and change POSTGRES_PASSWORD
docker compose up --build
```

Open `http://localhost:8080`.

**Why mock CV by default?** A senior reviewer or CI runner should be able to start the project without a Jetson, camera or 40 MB of generated model binaries. The real Ultralytics and TensorRT implementations are included and selected through environment variables; hardware-specific assets are set up explicitly.

## Deployment targets

| Target | Vision runtime | Camera | Intended use |
|---|---|---|---|
| Clone/CI | mock | synthetic | smoke test/review |
| Laptop/Windows | Ultralytics/PyTorch | USB/webcam | all-in-one development/full demo |
| Hybrid Laptop + Jetson Nano | TensorRT on Nano | CSI/GStreamer | recommended edge deployment |

For a Windows webcam, run Vision natively and the remaining services in Docker; see `deployments/laptop-windows/`. For the Jetson version, keep Web/Agent/PostgreSQL/Ollama on the laptop and run only Vision on the Nano; see `deployments/hybrid-jetson-nano/`. This avoids maintaining two duplicated applications.

## Safety/cleanliness improvements made during consolidation

- removed committed virtualenv/cache/generated build output
- excluded portable-incompatible TensorRT `.engine` files
- removed hard-coded database passwords from application defaults
- removed duplicate CV/backend copies
- fixed the CV face-registration path by implementing the missing latest-face-crop accessor
- separated frontend serving from the LLM service
- preserved `elevator_cv` vs `elevator_llm` database boundaries
- added a hardware-free runtime for smoke testing

See `docs/ARCHITECTURE.md`, `docs/MIGRATION.md`, `docs/RUNBOOK.md` and `docs/SOURCE_MANIFEST.md`.

## Verification strategy

A clean clone has a hardware-free path so reviewers can exercise the service boundaries before configuring a camera or Jetson. The repository includes unit tests for Vision, Agent and Gateway plus `scripts/check_repo.py` for repository hygiene. Real Ultralytics/TensorRT deployment is selected explicitly and documented separately because those paths depend on target hardware, model files and JetPack/CUDA versions.
