# ElevatorAI-Agent

LLM/RAG/agent subsystem extracted from the latest ElevatorAI backend. This repository contains the real router, planner, tool registry, conversation memory, PostgreSQL retrieval and Ollama integration without the old bundled frontend/CV copies.

## Quick start

```bash
python -m venv .venv
pip install -r requirements.txt
# activate the venv, then:
export PYTHONPATH=src
python -m elevator_agent
```

`GET http://localhost:8020/health` works even when PostgreSQL/Ollama are unavailable; dependency health is reported explicitly instead of crashing the service. Greeting/rule routes also continue to work. Full RAG/CV analytics require PostgreSQL, and generative responses require Ollama. Desktop deployments use psycopg3; the Jetson Nano requirements use psycopg2 and the database adapter supports both.

## API

- `POST /chat`
- `POST /api/chat/customer`
- `POST /api/chat/maintenance`
- `GET /api/elevator/status`
- `POST /api/elevator/call`
- `POST /api/knowledge/reload`
- `GET /health`

## Data boundaries

- `elevator_llm`: prompts, answers, employees, chat logs
- `elevator_cv`: queried read-only by agent tools for realtime CV facts

The LLM is not allowed to invent camera facts; maintenance CV questions are routed to database tools.

See `docs/MIGRATION.md` for the legacy sources used.
