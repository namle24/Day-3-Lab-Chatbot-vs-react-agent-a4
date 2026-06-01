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
    # Check if message is asking for comparison
    if not re.search(r"so sánh|phan vân|phân vân|compare", user_message, re.I):
        return None
    
    # Extract all VF models from user message
    models = re.findall(r"VF\s*(\d+)", user_message, re.I)
    if not models:
        return None
    
    # Remove duplicates while preserving order
    unique_models = []
    for m in models:
        if m not in unique_models:
            unique_models.append(m)
    
    # Need exactly 2 different models to compare
    if len(unique_models) < 2:
        return None
    
    # Take first two unique models
    model_a = f"VF{unique_models[0]}"
    model_b = f"VF{unique_models[1]}"
    
    try:
        data = vehicle_lookup.compare_vehicles(model_a, model_b)
        return data.get("comparison")
    except Exception:
        return None


def _build_comparison_reply_from_struct(structured: dict[str, Any], user_message: str) -> str:
    """Create a concise comparison reply from a structured compare_vehicles result."""
    if not structured:
        return ""
    models = list((structured.get("models") or {}).keys())
    if len(models) < 2:
        # Try to extract from user message
        m = re.findall(r"VF\s*(\d+)", user_message, re.I)
        if len(m) >= 2:
            models = [f"VF{m[0]}", f"VF{m[1]}"]
    if len(models) < 2:
        return ""

    model_a, model_b = models[0], models[1]
    a = (structured.get("models") or {}).get(model_a, {})
    b = (structured.get("models") or {}).get(model_b, {})

    def _ph(item):
        return (item.get("highlights") or {}).get("price_hint")

    def _rolling(item):
        for c in item.get("chunks", []):
            snip = c.get("snippet", "")
            m = re.search(r"Giá lăn bánh\s*([\d,]+)\s*VNĐ", snip, re.I)
            if m:
                return int(m.group(1).replace(",", ""))
        return None

    price_a = _ph(a)
    price_b = _ph(b)
    roll_a = _rolling(a)
    roll_b = _rolling(b)

    lines = [f"So sánh {model_a} và {model_b}:"]
    if price_a:
        lines.append(f"- {model_a}: Giá niêm yết {price_a}")
    if roll_a:
        lines.append(f"  Giá lăn bánh (ghi trong dữ liệu): {roll_a:,} VNĐ")
    if price_b:
        lines.append(f"- {model_b}: Giá niêm yết {price_b}")
    if roll_b:
        lines.append(f"  Giá lăn bánh (ghi trong dữ liệu): {roll_b:,} VNĐ")
    if roll_a is not None and roll_b is not None:
        lines.append(f"Chênh lệch (ước tính, lăn bánh): {abs(roll_a - roll_b):,} VNĐ")

    return "\n".join(lines)


def _fallback_reply(
    db: Session, user_id: str, message: str
) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
    """Rule-based fallback when LLM is not configured."""
    msg = message.lower()
    pending = None
    structured = None

    # Try dynamic comparison extraction first
    if re.search(r"so sánh|phan vân|phân vân|compare", msg):
        models = re.findall(r"VF\s*(\d+)", message, re.I)
        if models:
            unique_models = []
            for m in models:
                if m not in unique_models:
                    unique_models.append(m)
            if len(unique_models) >= 2:
                model_a = f"VF{unique_models[0]}"
                model_b = f"VF{unique_models[1]}"
                try:
                    cmp = vehicle_lookup.compare_vehicles(model_a, model_b)
                    structured = cmp.get("comparison") if cmp else None
                    if not structured:
                        # No comparison data returned; bail to friendly prompt
                        reply = "Xin lỗi, hiện không tìm thấy dữ liệu so sánh chi tiết. Bạn vui lòng thử lại hoặc nêu rõ hai mẫu cần so sánh."
                        return reply, pending, None
                    # Build a concise, non-canned comparison reply from the tool data
                    a = structured.get("models", {}).get(model_a, {})
                    b = structured.get("models", {}).get(model_b, {})

                    def _extract_price_hint(item):
                        return (item.get("highlights") or {}).get("price_hint")

                    def _extract_rolling_from_chunks(item):
                        chunks = item.get("chunks", [])
                        for c in chunks:
                            snip = c.get("snippet", "")
                            m = re.search(r"Giá lăn bánh\s*([\d,]+)\s*VNĐ", snip, re.I)
                            if m:
                                return m.group(1).replace(",", "")
                        return None

                    price_a = _extract_price_hint(a)
                    price_b = _extract_price_hint(b)
                    rolling_a = _extract_rolling_from_chunks(a)
                    rolling_b = _extract_rolling_from_chunks(b)

                    def _num(s):
                        if not s:
                            return None
                        m = re.search(r"([0-9,]+)", s)
                        if not m:
                            return None
                        return int(m.group(1).replace(",", ""))

                    n_roll_a = _num(rolling_a) or _num(price_a)
                    n_roll_b = _num(rolling_b) or _num(price_b)
                    diff = None
                    if n_roll_a is not None and n_roll_b is not None:
                        diff = abs(n_roll_a - n_roll_b)

                    lines = [f"So sánh {model_a} và {model_b}:"]
                    if price_a:
                        lines.append(f"- {model_a}: Giá niêm yết {price_a}")
                    if rolling_a:
                        lines.append(f"  Giá lăn bánh (ghi trong dữ liệu): {int(rolling_a):,} VNĐ".replace(',', ','))
                    if price_b:
                        lines.append(f"- {model_b}: Giá niêm yết {price_b}")
                    if rolling_b:
                        lines.append(f"  Giá lăn bánh (ghi trong dữ liệu): {int(rolling_b):,} VNĐ".replace(',', ','))

                    if diff is not None:
                        lines.append(f"Chênh lệch (ước tính, lăn bánh): {diff:,} VNĐ")

                    # If nothing useful, fall back to a short prompt asking to clarify
                    if len(lines) == 1:
                        reply = f"Mình tìm thấy {model_a} và {model_b} nhưng không có thông tin giá chi tiết. Bạn muốn mình tra thêm không?"
                    else:
                        reply = "\n".join(lines)

                    return reply, pending, structured
                except Exception:
                    pass
        
        # Could not extract two models to compare
        reply = (
            "Mình chưa nhận diện được đủ hai mẫu để so sánh. Vui lòng nêu rõ hai mẫu (ví dụ: 'So sánh VF3 và VF5')."
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
        "Hệ thống đang chạy chế độ fallback (LLM chưa hoạt động). Vui lòng cấu hình API key hoặc hỏi lại với hai mẫu rõ ràng.",
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
            # Log a structured event for telemetry
            try:
                logger.log_event(
                    "AGENT_ERROR_FALLBACK",
                    {
                        "user_id": user_id,
                        "error": str(e),
                        "message": message,
                    },
                )
            except Exception:
                # Fallback to simple info logging if structured logging fails
                logger.info(f"Error running agent (structured log failed): {e}")
            # Also emit a human-readable info log
            logger.info(f"Error running agent, falling back to simulated logic: {e}")
            reply, pending_action, structured = _fallback_reply(db, user_id, message)
            mode = "fallback"
    else:
        reply, pending_action, structured = _fallback_reply(db, user_id, message)
        mode = "fallback"

    # If the user explicitly mentioned two VF models, call compare_vehicles directly
    models = re.findall(r"VF\s*(\d+)", message, re.I)
    if len(models) >= 2:
        model_a = f"VF{models[0]}"
        model_b = f"VF{models[1]}"
        try:
            from src.telemetry.logger import logger
            logger.info(f"Fallback direct-compare: extracted models {model_a}, {model_b}")
            cmp = vehicle_lookup.compare_vehicles(model_a, model_b)
            logger.info(f"Fallback compare result keys: {list((cmp.get('comparison') or {}).get('models', {}).keys()) if cmp else 'no cmp'}")
            structured = cmp.get("comparison") if cmp else structured
            dynamic = _build_comparison_reply_from_struct(structured, message)
            if dynamic:
                reply = dynamic
        except Exception:
            pass

    repo.add_message(db, user_id, "assistant", reply)

    return {
        "reply": reply,
        "trace_id": trace_id,
        "pending_action": pending_action,
        "structured": structured,
        "mode": mode,
    }
