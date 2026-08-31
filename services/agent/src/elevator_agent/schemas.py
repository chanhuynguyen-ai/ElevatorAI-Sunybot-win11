from typing import Any, Dict, List,  Optional
from typing_extensions import Literal
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    reason: Optional[str] = None


class ToolTrace(BaseModel):
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    status: Literal["ok", "error", "blocked", "skipped"] = "ok"
    duration_ms: int = 0
    summary: str = ""


class Citation(BaseModel):
    source: str
    content: str
    score: Optional[float] = None


class AgentPlan(BaseModel):
    intent: str
    plan: List[str] = Field(default_factory=list)
    tool_calls: List[ToolCall] = Field(default_factory=list)
    final_response_format: str = "text"
    confidence: float = 0.0


class ChatRequest(BaseModel):
    message: str = ""
    question: str = ""
    session_id: Optional[str] = None
    employee_id: str = ""
    employee_name: str = ""


class ChatResponse(BaseModel):
    answer: str
    source: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    session_id: Optional[str] = None
    tool_trace: List[ToolTrace] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    memory_summary: Optional[str] = None
    requires_human: bool = False
    status: str = "ok"
