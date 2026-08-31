# Architecture

## Service boundaries

```text
Browser
  |
  v
ElevatorAI-Web (React + Nginx)
  |
  v
Gateway :8000
  |-----------------------------|
  v                             v
Agent :8020                 Vision :8010
  |                             |
  +-- elevator_llm DB           +-- detection / tracking / posture / events
  +-- Ollama (optional)         +-- elevator_cv DB
                                +-- runtime adapter
                                      |- mock (review/CI)
                                      |- Ultralytics (Laptop)
                                      `- TensorRT (Jetson Nano)
```

- **Web** owns presentation only.
- **Gateway** owns browser-facing orchestration, CV proxying, maintenance authentication and allow-listed Data Manager operations.
- **Agent** owns LLM/RAG/planning/tool logic; it does not serve frontend files.
- **Vision** owns camera/inference/tracking/event generation; it does not contain the main web UI or agent.
- **PostgreSQL** keeps `elevator_cv` and `elevator_llm` as separate databases.

## Deployment shape A: Laptop / Windows

```text
Windows host
  |- Native Vision -> USB webcam -> Ultralytics
  `- Docker Desktop
       |- PostgreSQL
       |- Agent -> host Ollama
       |- Gateway -> host.docker.internal:8010
       `- Web
```

Vision is native because Windows webcam passthrough through Docker Desktop is not a reliable deployment boundary.

## Deployment shape B: Laptop + Jetson Nano

```text
Jetson Nano                         Laptop / Windows
-------------                      ----------------
CSI camera                         Web
   |                               Gateway
GStreamer                          Agent + Ollama
   |                               PostgreSQL
TensorRT Vision :8010  <------->   elevator_cv + elevator_llm
```

The Jetson runs only the edge CV workload. The laptop keeps LLM, database and web workloads. Both deployment shapes use the **same Vision source tree**, so there is no Laptop-vs-Jetson code fork.

This separation removes the circular duplication present in the legacy repositories while keeping every original repository intact for rollback.
