from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.schemas import ChatRequest, ChatResponse, ConfirmRequest
from src.db.database import get_db
from src.services.chat_service import handle_chat
from src.tools import test_drive as test_drive_tool

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def post_chat(body: ChatRequest, db: Session = Depends(get_db)):
    result = handle_chat(
        db,
        body.user_id,
        body.message,
        confirm_action_id=body.confirm_action_id,
    )
    return ChatResponse(**result)


@router.post("/actions/{action_id}/confirm", response_model=ChatResponse)
def confirm_action(action_id: str, body: ConfirmRequest, db: Session = Depends(get_db)):
    confirmed = test_drive_tool.confirm_appointment(db, body.user_id, action_id)
    reply = confirmed.get("message", confirmed.get("error", "Lỗi xác nhận."))
    return ChatResponse(
        reply=reply,
        trace_id=action_id,
        pending_action=None,
        mode="confirm",
    )
