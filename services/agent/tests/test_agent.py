from elevator_agent.chatbot_engine import ChatbotEngine

def test_greeting_works_without_ollama_or_db():
    engine = ChatbotEngine()
    result = engine.handle("xin chao", scope="customer")
    assert result["answer"]
    assert result["scope"] == "customer"

def test_customer_scope_does_not_expose_cv_history():
    engine = ChatbotEngine()
    result = engine.handle("cho toi lich su camera hom nay", scope="customer")
    assert result["answer"]
    assert result["scope"] == "customer"

from elevator_agent.text_utils import normalize_vi


def test_vietnamese_normalization_collapses_whitespace_and_accents():
    assert normalize_vi("  Thang   máy, TẦNG 5! ") == "thang may tang 5"
