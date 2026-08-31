from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    question: Optional[str] = None
    session_id: Optional[str] = None
    scope: str = "customer"
    persona: Optional[str] = None
    include_trace: bool = False


class CallRequest(BaseModel):
    elevator_id: int = 1
    from_floor: Optional[int] = None
    target_floor: Optional[int] = None
    floor: Optional[int] = None
    direction: str = "up"


class LoginRequest(BaseModel):
    employee_code: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    employee_code: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)
    department: str = "Maintenance"
    role: str = "technician"


class DataSaveRequest(BaseModel):
    database: str
    table: str
    row: Dict[str, Any]


class DataDeleteRequest(BaseModel):
    database: str
    table: str
    keys: Dict[str, Any]
