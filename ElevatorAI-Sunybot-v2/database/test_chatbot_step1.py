from backend.chatbot_engine import ChatbotEngine


def test_greeting_db():
    engine = ChatbotEngine()
    result = engine.handle("Xin chao")
    assert "sunybot" in result["answer"].lower()
    assert result["source"] in ["AGENT", "KB", "LLM", "FALLBACK"]


def test_employee_code_lookup():
    engine = ChatbotEngine()
    result = engine.handle("NV020")
    assert "Nguyen Chan Huy" in result["answer"]
    assert result["source"] == "EMPLOYEE"


def test_status_tool_route():
    engine = ChatbotEngine()
    result = engine.handle("Trang thai thang may hien tai")
    assert "tang" in result["answer"].lower()
    assert result["intent"] in ["elevator_status", "emergency_support"]


def test_overload_kb_route():
    engine = ChatbotEngine()
    result = engine.handle("Thang may qua tai thi sao")
    assert any(token in result["answer"].lower() for token in ["qua tai", "tai trong", "giam bot"])


def test_healthcheck_reports_postgres():
    engine = ChatbotEngine()
    status = engine.healthcheck()
    assert status["db_backend"] == "postgresql"
