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
from src.rag.store import _first_match


NO_INFO_REPLY = "Không có thông tin cho câu hỏi của bạn trong cơ sở dữ liệu."
MIN_RELEVANCE_SCORE = 0.15


def _has_relevant_hits(hits: list[dict[str, Any]], min_score: float = MIN_RELEVANCE_SCORE) -> bool:
    return any(float(hit.get("score", 0)) >= min_score for hit in hits)


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

    def _extract_price_and_quarter(item):
        """Return (price_int_or_None, quarter_str_or_None) by scanning chunks."""
        quarter = None
        for c in item.get("chunks", []):
            snip = c.get("snippet", "")
            # Try to find rolling price
            m = re.search(r"Giá lăn bánh\s*([\d,]+)\s*VNĐ", snip, re.I)
            if m:
                price = int(m.group(1).replace(",", ""))
            else:
                price = None

            # Try to find explicit "Áp dụng" quarter text added by chunking
            q = re.search(r"Áp dụng:\s*([^\.\n]+)", snip, re.I)
            if q:
                quarter = q.group(1).strip()

            # If we found a price, return it (and any quarter we saw)
            if price is not None:
                return price, quarter

        return None, quarter

    price_a = _ph(a)
    price_b = _ph(b)
    roll_a, quarter_a = _extract_price_and_quarter(a)
    roll_b, quarter_b = _extract_price_and_quarter(b)

    lines = [f"Dạ, em đã tra cứu dữ liệu {model_a} và {model_b}.", f"So sánh {model_a} và {model_b}:"]
    if price_a:
        lines.append(f"- {model_a}: Giá niêm yết {price_a}")
    if roll_a:
        qtext = f" (Áp dụng: {quarter_a})" if quarter_a else ""
        lines.append(f"  Giá lăn bánh (ghi trong dữ liệu){qtext}: {roll_a:,} VNĐ")
    if price_b:
        lines.append(f"- {model_b}: Giá niêm yết {price_b}")
    if roll_b:
        qtext = f" (Áp dụng: {quarter_b})" if quarter_b else ""
        lines.append(f"  Giá lăn bánh (ghi trong dữ liệu){qtext}: {roll_b:,} VNĐ")
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
                        return NO_INFO_REPLY, pending, None

                    model_hits = [
                        (structured.get("models") or {}).get(model_a, {}).get("chunks", []),
                        (structured.get("models") or {}).get(model_b, {}).get("chunks", []),
                    ]
                    if not any(_has_relevant_hits(hits) for hits in model_hits):
                        return NO_INFO_REPLY, pending, None

                    # Build a concise, non-canned comparison reply from the tool data
                    a = structured.get("models", {}).get(model_a, {})
                    b = structured.get("models", {}).get(model_b, {})

                    def _extract_price_hint(item):
                        return (item.get("highlights") or {}).get("price_hint")

                    def _extract_rolling_from_chunks(item):
                        # Return tuple (price_str_or_None, quarter_or_None)
                        chunks = item.get("chunks", [])
                        quarter = None
                        for c in chunks:
                            snip = c.get("snippet", "")
                            m = re.search(r"Giá lăn bánh\s*([\d,]+)\s*VNĐ", snip, re.I)
                            if m:
                                # try to extract quarter text if present
                                q = re.search(r"Áp dụng:\s*([^\.\n]+)", snip, re.I)
                                if q:
                                    quarter = q.group(1).strip()
                                return m.group(1).replace(",", ""), quarter
                        return None, None

                    price_a = _extract_price_hint(a)
                    price_b = _extract_price_hint(b)
                    rolling_a, quarter_a = _extract_rolling_from_chunks(a)
                    rolling_b, quarter_b = _extract_rolling_from_chunks(b)

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

                    lines = [f"Dạ, em đã tra cứu dữ liệu {model_a} và {model_b}.", f"So sánh {model_a} và {model_b}:"]
                    if price_a:
                        lines.append(f"- {model_a}: Giá niêm yết {price_a}")
                    if rolling_a:
                        qtext = f" (Áp dụng: {quarter_a})" if quarter_a else ""
                        lines.append(f"  Giá lăn bánh (ghi trong dữ liệu){qtext}: {int(rolling_a):,} VNĐ")
                    if price_b:
                        lines.append(f"- {model_b}: Giá niêm yết {price_b}")
                    if rolling_b:
                        qtext = f" (Áp dụng: {quarter_b})" if quarter_b else ""
                        lines.append(f"  Giá lăn bánh (ghi trong dữ liệu){qtext}: {int(rolling_b):,} VNĐ")

                    if diff is not None:
                        lines.append(f"Chênh lệch (ước tính, lăn bánh): {diff:,} VNĐ")

                    # If nothing useful, fall back to a short prompt asking to clarify
                    if len(lines) == 1:
                        reply = NO_INFO_REPLY
                    else:
                        reply = "\n".join(lines)

                    return reply, pending, structured
                except Exception:
                    pass
        
        # Could not extract two models to compare
        return NO_INFO_REPLY, pending, structured

    if "vf" in msg:
        lookup = vehicle_lookup.lookup_vehicle(message, top_k=3)
        hits = lookup.get("results", [])
        if not _has_relevant_hits(hits):
            return NO_INFO_REPLY, pending, structured
        snippets = [r["snippet"][:200] for r in hits]
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
        NO_INFO_REPLY,
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
    sources: list[str] = []
    mode = "agent"

    if llm:
        try:
            agent = ReActAgent(llm, executor.execute, tool_context=executor)
            reply = agent.run(message, history=history[:-1])
            pending_action = agent.last_pending_action or executor.last_pending_action
            structured = _extract_comparison_structured(None, message)

            try:
                lookup = vehicle_lookup.lookup_vehicle(message, top_k=5)
                hits = lookup.get("results", [])

                def _has_price(text: str) -> bool:
                    if not text:
                        return False
                    return bool(_first_match(text, [r"(\d[\d.,]*\s*(?:triệu|tỷ|vnđ|đồng|VND))"]))

                prices_in_reply = _has_price(reply)
                prices_in_lookup = any(_has_price(h.get("snippet", "")) or _has_price(h.get("text", "")) for h in hits)
                sources = [h.get("url") for h in hits if h.get("url")]

                if prices_in_reply and not prices_in_lookup:
                    prefix = (
                        "[CHÚ Ý] Không tìm thấy nguồn xác nhận trong cơ sở dữ liệu RAG cho các con số trong câu trả lời. "
                        "Thông tin dưới đây có thể chưa được kiểm chứng:\n\n"
                    )
                    reply = prefix + reply
                elif sources:
                    reply = reply + "\n\nNguồn tham khảo:\n" + "\n".join(f"- {u}" for u in sources)
            except Exception:
                sources = []
        except Exception as e:
            from src.telemetry.logger import logger
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
                logger.info(f"Error running agent (structured log failed): {e}")
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

    res = {
        "reply": reply,
        "trace_id": trace_id,
        "pending_action": pending_action,
        "structured": structured,
        "mode": mode,
    }
    # include sources if available
    if llm:
        try:
            res["sources"] = sources
        except Exception:
            res["sources"] = []
    return res
