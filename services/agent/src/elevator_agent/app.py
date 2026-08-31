from typing import Any, Dict, List, Optional
from fastapi import FastAPI
from pydantic import BaseModel, Field

from elevator_agent.chatbot_engine import ChatbotEngine

app = FastAPI(title="ElevatorAI Agent", version="1.0.0")
engine = ChatbotEngine()

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    question: Optional[str] = None
    session_id: Optional[str] = None
    scope: str = "customer"
    persona: Optional[str] = None
    include_trace: bool = False

class ElevatorCallRequest(BaseModel):
    elevator_id: int = 1
    from_floor: Optional[int] = None
    target_floor: Optional[int] = None
    floor: Optional[int] = None
    direction: str = "up"


def _run_chat(req, forced_scope=None, forced_persona=None):
    scope = forced_scope or req.scope
    persona = forced_persona or req.persona
    result = engine.handle(req.message or req.question or "", session_id=req.session_id, scope=scope, persona=persona)
    if not req.include_trace:
        result["tool_trace"] = None
    return result

@app.get("/health")
def health():
    details = engine.healthcheck()
    return {"status": "ok", "service": "agent", "dependencies": details}

@app.get("/status")
def status():
    return engine.healthcheck()

@app.post("/chat")
def chat(req: ChatRequest):
    return _run_chat(req)

@app.post("/api/chat/customer")
def chat_customer(req: ChatRequest):
    return _run_chat(req, "customer", "customer_assistant")

@app.post("/api/chat/maintenance")
def chat_maintenance(req: ChatRequest):
    return _run_chat(req, "maintenance", "maintenance_console")

@app.post("/api/knowledge/reload")
def reload_knowledge():
    return engine.reload_knowledge()

@app.get("/api/elevator/status")
def elevator_status(elevator_id: int = 1):
    return engine.get_elevator_status(elevator_id=elevator_id)

@app.post("/api/elevator/call")
def elevator_call(req: ElevatorCallRequest):
    target = req.target_floor if req.target_floor is not None else req.floor
    return engine.call_elevator(elevator_id=req.elevator_id, from_floor=req.from_floor, target_floor=target, direction=req.direction)
