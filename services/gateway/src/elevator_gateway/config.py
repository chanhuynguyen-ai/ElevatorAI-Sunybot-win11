import os

VISION_SERVICE_URL = os.getenv("VISION_SERVICE_URL", "http://vision:8010").rstrip("/")
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://agent:8020").rstrip("/")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "8"))
STREAM_TIMEOUT = float(os.getenv("STREAM_TIMEOUT", "60"))
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "elevator_ai")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
CV_DB = os.getenv("ELEVATOR_CV_DB_NAME", "elevator_cv")
LLM_DB = os.getenv("ELEVATOR_LLM_DB_NAME", "elevator_llm")
