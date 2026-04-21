from fastapi import FastAPI
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import os
import time
import socket

from backend.chatbot_engine import ChatbotEngine

# =========================
# App & Engine
# =========================
app = FastAPI(title="Sunybot Elevator Chatbot", version="1.1.0")
engine = ChatbotEngine()

# =========================
# Path config
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WEB_DIR = os.path.join(BASE_DIR, "gui", "web")
PAGES_DIR = os.path.join(WEB_DIR, "pages")
STATIC_DIR = os.path.join(WEB_DIR, "static")

# New Vite/React build output
DIST_DIR = os.path.join(WEB_DIR, "dist")
DIST_INDEX = os.path.join(DIST_DIR, "index.html")
DIST_ASSETS_DIR = os.path.join(DIST_DIR, "assets")
DIST_FAVICON = os.path.join(DIST_DIR, "favicon.ico")

# Old UI favicon
FAVICON_PATH = os.path.join(STATIC_DIR, "favicon.ico")


def _file_exists(path: str) -> bool:
    try:
        return os.path.isfile(path)
    except Exception:
        return False


def _dir_exists(path: str) -> bool:
    try:
        return os.path.isdir(path)
    except Exception:
        return False


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def print_ui_links(port: int = 8000):
    lan_ip = get_local_ip()

    print("\n================ SUNYBOT UI ================")
    print(f"Local UI  : http://127.0.0.1:{port}/")
    print(f"LAN UI    : http://{lan_ip}:{port}/")
    print(f"Health    : http://{lan_ip}:{port}/health")
    print(f"Customer  : http://{lan_ip}:{port}/pages/assistant.html")
    print(f"Maint     : http://{lan_ip}:{port}/pages/maintenance.html")
    if _file_exists(DIST_INDEX):
        print("Frontend  : React dist đang được ưu tiên tại /")
    else:
        print("Frontend  : Chưa thấy dist/index.html, có thể đang fallback UI cũ")
    print("============================================\n")


@app.on_event("startup")
def startup_debug():
    print("========== SUNYBOT UI STARTUP ==========")
    print(f"cwd={os.getcwd()}")
    print(f"BASE_DIR={BASE_DIR}")
    print(f"WEB_DIR={WEB_DIR} | exists={_dir_exists(WEB_DIR)}")
    print(f"DIST_DIR={DIST_DIR} | exists={_dir_exists(DIST_DIR)}")
    print(f"DIST_INDEX={DIST_INDEX} | exists={_file_exists(DIST_INDEX)}")
    print(f"DIST_ASSETS_DIR={DIST_ASSETS_DIR} | exists={_dir_exists(DIST_ASSETS_DIR)}")
    print("========================================")
    print_ui_links(8000)


# =========================
# Static mounts
# =========================
if _dir_exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if _dir_exists(DIST_ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=DIST_ASSETS_DIR), name="assets")


# =========================
# Favicon
# =========================
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    if _file_exists(DIST_FAVICON):
        return FileResponse(DIST_FAVICON)

    if _file_exists(FAVICON_PATH):
        return FileResponse(FAVICON_PATH)

    return Response(status_code=204)


# =========================
# UI Routes
# =========================
@app.get("/", include_in_schema=False)
def home():
    if _file_exists(DIST_INDEX):
        return FileResponse(DIST_INDEX)

    old_index = os.path.join(WEB_DIR, "index.html")
    if _file_exists(old_index):
        return FileResponse(old_index)

    return JSONResponse(status_code=404, content={"error": "UI not found"})


@app.get("/pages/{page}", include_in_schema=False)
def serve_pages(page: str):
    safe_page = os.path.basename(page)
    file_path = os.path.join(PAGES_DIR, safe_page)

    if not _file_exists(file_path):
        return JSONResponse(status_code=404, content={"error": "Page not found"})

    return FileResponse(file_path)


# =========================
# Healthcheck
# =========================
@app.get("/health")
def health():
    engine_health = engine.healthcheck()
    return {
        "status": "ok" if engine_health.get("db_ok") else "degraded",
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        **engine_health,
    }


# =========================
# Elevator Status
# =========================
@app.get("/api/elevator/status")
def elevator_status():
    try:
        status = engine.get_elevator_status(elevator_id=1)
        if status:
            return status
    except Exception:
        pass

    return {
        "elevator_id": 1,
        "floor": 5,
        "direction": "UP",
        "door": "CLOSED",
        "people_count": 4,
        "overload": False,
        "status": "NORMAL",
        "time": time.strftime("%H:%M:%S"),
        "source": "mock_fallback",
    }


# =========================
# Chatbot API
# =========================
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    scope: str = "customer"
    persona: Optional[str] = None
    include_trace: bool = False


class ChatResponse(BaseModel):
    answer: str
    source: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    session_id: Optional[str] = None
    scope: Optional[str] = None
    persona: Optional[str] = None
    query_type: Optional[str] = None
    tool_trace: Optional[List[Dict[str, Any]]] = None


def _run_chat(req: ChatRequest, forced_scope: Optional[str] = None, forced_persona: Optional[str] = None) -> Dict[str, Any]:
    scope = forced_scope or req.scope
    persona = forced_persona or req.persona
    result = engine.handle(
        req.message,
        session_id=req.session_id,
        scope=scope,
        persona=persona,
    )
    if not req.include_trace:
        result = {**result, "tool_trace": None}
    return {
        "answer": result.get("answer", ""),
        "source": result.get("source", "UNKNOWN"),
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "session_id": result.get("session_id"),
        "scope": result.get("scope"),
        "persona": result.get("persona"),
        "query_type": result.get("query_type"),
        "tool_trace": result.get("tool_trace"),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    return _run_chat(req)


@app.post("/api/chat/customer", response_model=ChatResponse)
def chat_customer(req: ChatRequest):
    return _run_chat(req, forced_scope="customer", forced_persona="customer_assistant")


@app.post("/api/chat/maintenance", response_model=ChatResponse)
def chat_maintenance(req: ChatRequest):
    return _run_chat(req, forced_scope="maintenance", forced_persona="maintenance_console")


@app.post("/api/knowledge/reload")
def reload_knowledge():
    return engine.reload_knowledge()


# =========================
# SPA fallback for React Router
# =========================
@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    if full_path.startswith(("api", "chat", "health", "static", "assets", "pages")):
        return JSONResponse(status_code=404, content={"error": "Not found"})

    if _file_exists(DIST_INDEX):
        return FileResponse(DIST_INDEX)

    old_index = os.path.join(WEB_DIR, "index.html")
    if _file_exists(old_index):
        return FileResponse(old_index)

    return JSONResponse(status_code=404, content={"error": "UI not found"})
