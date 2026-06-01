import json
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from src.agent.agent import ReActAgent
from src.core.factory import create_llm_provider
from src.db import repository as repo
from src.tools import vehicle_lookup
from src.tools.registry import ToolExecutor
from src.tools import test_drive as test_drive_tool


def _extract_comparison_structured(agent_scratchpad: str | None, user_message: str) -> dict[str, Any] | None:
    if not re.search(r"VF\s*5|VF\s*6", user_message, re.I):
        return None
    if not re.search(r"so sánh|phan vân|phân vân|compare", user_message, re.I):
        return None
    try:
        data = vehicle_lookup.compare_vehicles("VF5", "VF6")
        return data.get("comparison")
    except Exception:
        return None


def _fallback_reply(
    db: Session, user_id: str, message: str
) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
    """Rule-based fallback when LLM is not configured."""
    msg = message.lower()
    pending = None
    structured = None

    if re.search(r"so sánh|phan vân|vf\s*5.*vf\s*6", msg):
        cmp = vehicle_lookup.compare_vehicles("VF5", "VF6")
        structured = cmp.get("comparison")
        reply = (
            "Dạ, em đã tra cứu dữ liệu VF5 và VF6. VF5 nhỏ gọn, giá từ ~529 triệu, phù hợp đi phố. "
            "VF6 rộng hơn cho gia đình 4 người, giá từ ~689 triệu. "
            "Anh/chị muốn em tính chênh lệch giá lăn bánh cụ thể không ạ?"
        )
        return reply, pending, structured

    if "vf" in msg:
        lookup = vehicle_lookup.lookup_vehicle(message, top_k=3)
        snippets = [r["snippet"][:200] for r in lookup.get("results", [])]
        reply = "Dạ, theo dữ liệu VinFast:\n- " + "\n- ".join(snippets[:2])
        return reply, pending, structured

    name_m = re.search(r"(?:tôi là|em là|tên(?:\s+là)?)\s+([A-Za-zÀ-ỹ\s]+)", message, re.I)
    phone_m = re.search(r"(0\d{9,10})", message)
    vf_m = re.search(r"VF\s*\d+", message, re.I)
    if name_m and phone_m and vf_m and re.search(r"lái thử|dat lich|đặt lịch", msg):
        payload = test_drive_tool.schedule_test_drive(
            db,
            user_id,
            name_m.group(1).strip(),
            phone_m.group(1),
            vf_m.group(0).upper().replace(" ", ""),
        )
        pending = {
            "type": "test_drive",
            "id": payload["appointment_id"],
            "summary": payload["message"],
        }
        reply = (
            f"{payload['message']} Anh/chị vui lòng bấm ĐỒNG Ý để em chốt lịch nhé!"
        )
        return reply, pending, structured

    return (
        "Hệ thống đang chạy chế độ fallback (chưa cấu hình LLM). "
        "Hãy đặt OPENAI_API_KEY trong .env hoặc hỏi: so sánh VF5 và VF6.",
        None,
        None,
    )


def handle_chat(
    db: Session,
    user_id: str,
    message: str,
    confirm_action_id: str | None = None,
) -> dict[str, Any]:
    trace_id = str(uuid.uuid4())
    repo.add_message(db, user_id, "user", message)

    if confirm_action_id and confirm_action_id != "string" and confirm_action_id.strip() != "":
        confirmed = test_drive_tool.confirm_appointment(db, user_id, confirm_action_id)
        reply = confirmed.get("message", confirmed.get("error", "Không xác nhận được."))
        repo.add_message(db, user_id, "assistant", reply)
        return {
            "reply": reply,
            "trace_id": trace_id,
            "pending_action": None,
            "structured": None,
            "mode": "confirm",
        }

    history = [
        {"role": m.role, "content": m.content}
        for m in repo.get_messages(db, user_id, limit=20)
    ]

    executor = ToolExecutor(db, user_id)
    llm = create_llm_provider()
    pending_action = None
    structured = None
    mode = "agent"

    if llm:
        try:
            agent = ReActAgent(llm, executor.execute, tool_context=executor)
            reply = agent.run(message, history=history[:-1])
            pending_action = agent.last_pending_action or executor.last_pending_action
            structured = _extract_comparison_structured(None, message)
        except Exception as e:
            from src.telemetry.logger import logger
            logger.log_event(
                "AGENT_ERROR_FALLBACK",
                {
                    "user_id": user_id,
                    "error": str(e),
                    "message": message
                }
            )
            reply, pending_action, structured = _fallback_reply(db, user_id, message)
            mode = "fallback"
    else:
        reply, pending_action, structured = _fallback_reply(db, user_id, message)
        mode = "fallback"

    repo.add_message(db, user_id, "assistant", reply)

    return {
        "reply": reply,
        "trace_id": trace_id,
        "pending_action": pending_action,
        "structured": structured,
        "mode": mode,
    }
