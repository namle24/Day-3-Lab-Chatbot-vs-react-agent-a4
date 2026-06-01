import json
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import ChatMessage, TestDriveAppointment, ToolCallLog


def add_message(db: Session, user_id: str, role: str, content: str) -> ChatMessage:
    msg = ChatMessage(user_id=user_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_messages(db: Session, user_id: str, limit: int = 50) -> list[ChatMessage]:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def log_tool_call(
    db: Session,
    user_id: str,
    tool_name: str,
    arguments: dict,
    observation: str,
    latency_ms: int,
    message_id: int | None = None,
) -> ToolCallLog:
    entry = ToolCallLog(
        user_id=user_id,
        message_id=message_id,
        tool_name=tool_name,
        arguments=json.dumps(arguments, ensure_ascii=False),
        observation=observation[:8000],
        latency_ms=latency_ms,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_tool_logs(db: Session, user_id: str, limit: int = 100) -> list[ToolCallLog]:
    stmt = (
        select(ToolCallLog)
        .where(ToolCallLog.user_id == user_id)
        .order_by(ToolCallLog.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def create_test_drive(
    db: Session,
    user_id: str,
    customer_name: str,
    phone: str,
    car_model: str,
) -> TestDriveAppointment:
    appt = TestDriveAppointment(
        id=str(uuid.uuid4()),
        user_id=user_id,
        customer_name=customer_name,
        phone=phone,
        car_model=car_model,
        status="pending_confirmation",
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


def confirm_test_drive(db: Session, appointment_id: str, user_id: str) -> TestDriveAppointment | None:
    appt = db.get(TestDriveAppointment, appointment_id)
    if not appt or appt.user_id != user_id:
        return None
    appt.status = "confirmed"
    appt.confirmed_at = datetime.utcnow()
    db.commit()
    db.refresh(appt)
    return appt


def get_appointment(db: Session, appointment_id: str) -> TestDriveAppointment | None:
    return db.get(TestDriveAppointment, appointment_id)


def delete_messages(db: Session, user_id: str) -> int:
    from sqlalchemy import delete
    stmt = delete(ChatMessage).where(ChatMessage.user_id == user_id)
    result = db.execute(stmt)
    db.commit()
    return result.rowcount

