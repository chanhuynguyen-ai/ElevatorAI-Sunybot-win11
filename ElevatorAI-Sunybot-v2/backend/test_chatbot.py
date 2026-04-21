from backend.chatbot_engine import ChatbotEngine


def test_greeting_db():
    engine = ChatbotEngine()
    result = engine.handle("Xin chào")
    assert "sunybot" in result["answer"].lower()
    assert result["source"] in ["AGENT", "KB", "LLM", "FALLBACK"]


def test_employee_code_lookup():
    engine = ChatbotEngine()
    result = engine.handle("NV020")
    assert "Nguyen Chan Huy" in result["answer"]
    assert result["source"] == "EMPLOYEE"


def test_status_tool_route():
    engine = ChatbotEngine()
    result = engine.handle("Trạng thái thang máy hiện tại")
    assert "tầng" in result["answer"].lower()
    assert result["intent"] in ["elevator_status", "emergency_support"]


def test_healthcheck_reports_postgres():
    engine = ChatbotEngine()
    status = engine.healthcheck()
    assert status["db_backend"] == "postgresql"
