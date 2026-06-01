from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.schemas import SessionHistoryResponse, MessageOut, ToolLogOut
from src.db.database import get_db
from src.db import repository as repo

router = APIRouter(prefix="/api/v1", tags=["sessions"])


@router.get("/sessions/{user_id}/messages", response_model=SessionHistoryResponse)
def get_session_messages(
    user_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    messages = repo.get_messages(db, user_id, limit=limit)
    return SessionHistoryResponse(
        user_id=user_id,
        messages=[
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
    )


@router.get("/sessions/{user_id}/tool-logs", response_model=list[ToolLogOut])
def get_tool_logs(
    user_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    logs = repo.get_tool_logs(db, user_id, limit=limit)
    return [
        ToolLogOut(
            tool_name=log.tool_name,
            arguments=log.arguments,
            observation=log.observation[:500],
            latency_ms=log.latency_ms,
            created_at=log.created_at.isoformat(),
        )
        for log in logs
    ]


@router.delete("/sessions/{user_id}/messages")
def delete_session_messages(user_id: str, db: Session = Depends(get_db)):
    deleted_count = repo.delete_messages(db, user_id)
    return {
        "ok": True,
        "message": f"Đã xóa thành công {deleted_count} tin nhắn của session '{user_id}'.",
        "deleted_count": deleted_count
    }

