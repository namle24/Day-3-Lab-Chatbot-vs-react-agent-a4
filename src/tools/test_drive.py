import json
from typing import Any

from sqlalchemy.orm import Session

from src.db import repository as repo


def schedule_test_drive(
    db: Session,
    user_id: str,
    customer_name: str,
    phone: str,
    car_model: str,
) -> dict[str, Any]:
    appt = repo.create_test_drive(db, user_id, customer_name, phone, car_model)
    return {
        "ok": True,
        "status": "pending_confirmation",
        "appointment_id": appt.id,
        "message": (
            f"Đã ghi nhận lịch lái thử {car_model} cho {customer_name} ({phone}). "
            "Cần xác nhận ĐỒNG Ý từ khách hàng trước khi chốt."
        ),
        "requires_confirmation": True,
    }


def confirm_appointment(db: Session, user_id: str, appointment_id: str) -> dict[str, Any]:
    appt = repo.confirm_test_drive(db, appointment_id, user_id)
    if not appt:
        return {"ok": False, "error": "Không tìm thấy lịch hẹn hoặc không thuộc user này."}
    return {
        "ok": True,
        "status": "confirmed",
        "appointment_id": appt.id,
        "customer_name": appt.customer_name,
        "phone": appt.phone,
        "car_model": appt.car_model,
        "message": f"Đã chốt lịch lái thử {appt.car_model} cho {appt.customer_name}.",
    }


def format_schedule_for_agent(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)
