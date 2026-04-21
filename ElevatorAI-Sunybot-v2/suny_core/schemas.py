# backend/schemas.py
from pydantic import BaseModel

class ChatRequest(BaseModel):
    employee_id: str = ""
    employee_name: str = ""
    question: str

class ChatResponse(BaseModel):
    answer: str

