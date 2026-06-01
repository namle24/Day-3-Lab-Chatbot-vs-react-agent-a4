import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import chat, sessions, tools
from src.db.database import init_db
from src.rag.ingest import ingest as build_rag_index
from src.rag.store import VinFastRAGStore
from pathlib import Path

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


@app.get("/health")
def health():
    return {"status": "ok", "rag_index": str(INDEX_PATH), "index_exists": INDEX_PATH.exists()}
