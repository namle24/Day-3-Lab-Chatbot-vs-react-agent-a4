import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.api.routes import chat, sessions, tools
from src.db.database import init_db, get_db
from src.db import repository as repo
from src.services.chat_service import handle_chat
from src.api.schemas import ChatRequest
from src.rag.ingest import ingest as build_rag_index
from src.rag.store import VinFastRAGStore

load_dotenv()

INDEX_PATH = Path(os.getenv("RAG_INDEX_PATH", Path(__file__).resolve().parents[2] / "data" / "rag_index.pkl"))
DATA_PATH = Path(__file__).resolve().parents[2] / "vinfast_rag_data.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    store = VinFastRAGStore()
    if not store.load(INDEX_PATH):
        build_rag_index(DATA_PATH, INDEX_PATH)
    yield


app = FastAPI(
    title="VinFast Smart Sales API",
    description="Backend tools & chat API for VinFast ReAct agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(tools.router)

# Mount static files
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def read_index():
    return FileResponse(static_dir / "index.html")


MOCK_USERS = [
    {
        "id": "user_1",
        "name": "Nguyễn Văn A",
        "avatar": "💬",
        "status": "online",
        "profile": "Khách hàng quan tâm dòng xe VF 5 và VF 6",
        "last_message": "Chào em, anh muốn so sánh VF 5 và VF 6"
    },
    {
        "id": "user_2",
        "name": "Trần Thị B",
        "avatar": "🚗",
        "status": "online",
        "profile": "Khách hàng cần tính lãi suất mua trả góp VF 8",
        "last_message": "Tính giúp chị trả trước 30% VF 8"
    },
    {
        "id": "user_3",
        "name": "Lê Văn C",
        "avatar": "📅",
        "status": "offline",
        "profile": "Đã đăng ký lái thử VF 9",
        "last_message": "Cảm ơn em, anh đã chốt lịch"
    }
]


@app.get("/api/users")
def get_users():
    return MOCK_USERS


@app.get("/api/chat/{user_id}/history")
def get_chat_history(user_id: str, db: Session = Depends(get_db)):
    messages = repo.get_messages(db, user_id)
    if not messages:
        # Prepopulate with a mock message so the chat isn't blank
        initial_messages = []
        if user_id == "user_1":
            initial_messages = [("user", "Chào em, anh muốn so sánh VF 5 và VF 6")]
        elif user_id == "user_2":
            initial_messages = [("user", "Tính giúp chị trả trước 30% VF 8")]
        elif user_id == "user_3":
            initial_messages = [
                ("user", "Anh muốn đăng ký lái thử VF 9"),
                ("assistant", "Dạ vâng, em đã ghi nhận thông tin đăng ký lái thử của anh Lê Văn C rồi ạ. Hệ thống đang tạo lịch hẹn mang xe qua xưởng. Anh vui lòng phản hồi ĐỒNG Ý để em chốt lịch cho anh nhé!")
            ]
        for role, content in initial_messages:
            repo.add_message(db, user_id, role, content)
        messages = repo.get_messages(db, user_id)

    return [
        {
            "sender": "user" if m.role == "user" else "agent",
            "text": m.content
        }
        for m in messages
    ]


@app.post("/api/chat")
def post_chat_api(body: ChatRequest, db: Session = Depends(get_db)):
    start_time = time.time()
    
    # We call the real handle_chat service
    result = handle_chat(
        db,
        body.user_id,
        body.message,
        confirm_action_id=body.confirm_action_id,
    )
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Determine the active model and provider
    provider = os.getenv("DEFAULT_PROVIDER", "openai")
    model = os.getenv("DEFAULT_MODEL", "gpt-4o")
    
    if provider == "local":
        model = "Phi-3-mini"
    elif provider == "google":
        model = "gemini-1.5-flash"
    
    return {
        "reply": result["reply"],
        "trace_id": result["trace_id"],
        "pending_action": result["pending_action"],
        "structured": result["structured"],
        "mode": result["mode"],
        "model": model,
        "provider": provider.capitalize(),
        "latency_ms": latency_ms
    }


@app.get("/health")
def health():
    return {"status": "ok", "rag_index": str(INDEX_PATH), "index_exists": INDEX_PATH.exists()}
