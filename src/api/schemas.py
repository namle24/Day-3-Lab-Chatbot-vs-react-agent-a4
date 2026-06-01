from typing import Any, Optional, List

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(..., examples=["user1"])
    message: str
    confirm_action_id: Optional[str] = Field(default=None, examples=[None])


class PendingAction(BaseModel):
    type: str
    id: str
    summary: str


class ChatResponse(BaseModel):
    reply: str
    trace_id: str
    pending_action: Optional[dict[str, Any]] = None
    structured: Optional[dict[str, Any]] = None
    trace: Optional[List[dict[str, Any]]] = None
    mode: str = "agent"


class ConfirmRequest(BaseModel):
    user_id: str


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class SessionHistoryResponse(BaseModel):
    user_id: str
    messages: list[MessageOut]


class ToolLogOut(BaseModel):
    tool_name: str
    arguments: str
    observation: str
    latency_ms: int
    created_at: str
