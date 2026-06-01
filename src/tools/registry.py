import json
import time
from typing import Any, Callable

from sqlalchemy.orm import Session

from src.tools import calculator, reviews_search, test_drive, vehicle_lookup
from src.telemetry.logger import logger

ToolHandler = Callable[..., str]


def get_tool_specs() -> list[dict[str, Any]]:
    """Metadata for ReAct agent registration."""
    return [
        {
            "name": "lookup_vehicle",
            "description": (
                "Tra cứu thông tin chung, tính năng, và mô tả xe VinFast "
                "từ knowledge base. Tham số: query (string), optional top_k (int)."
            ),
            "parameters": {"query": "string", "top_k": "int optional"},
        },
        {
            "name": "get_vehicle_specs",
            "description": (
                "Tra cứu ĐẶC TÍNH, THÔNG SỐ KỸ THUẬT (kích thước, pin, quãng đường, giá, số chỗ) "
                "của một dòng xe cụ thể. Trả về cấu trúc JSON dễ đọc. Tham số: car_model (string)."
            ),
            "parameters": {"car_model": "string"},
        },
        {
            "name": "compare_vehicles",
            "description": (
                "So sánh hai dòng xe (ví dụ VF5 vs VF6). "
                "Tham số: model_a (string), model_b (string)."
            ),
            "parameters": {"model_a": "string", "model_b": "string"},
        },
        {
            "name": "calculate",
            "description": (
                "Tính toán an toàn: trả trước %, chênh lệch giá, biểu thức số học. "
                "Tham số JSON: mode=expression|down_payment|difference và các field tương ứng."
            ),
            "parameters": {
                "mode": "expression | down_payment | difference",
                "expression": "string optional",
                "price": "float optional",
                "percent": "float optional",
                "price_a": "float optional",
                "price_b": "float optional",
            },
        },
        {
            "name": "schedule_test_drive",
            "description": (
                "Ghi nhận lịch lái thử/xem xe — trạng thái pending, cần xác nhận. "
                "Tham số: customer_name, phone, car_model."
            ),
            "parameters": {
                "customer_name": "string",
                "phone": "string",
                "car_model": "string",
            },
        },
        {
            "name": "search_reviews",
            "description": (
                "Tìm đoạn đánh giá / ưu nhược điểm xe từ knowledge base. "
                "Tham số: query, optional car_model."
            ),
            "parameters": {"query": "string", "car_model": "string optional"},
        },
    ]


class ToolExecutor:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.last_pending_action: dict[str, Any] | None = None

    def execute(self, tool_name: str, args_raw: str) -> str:
        start = time.perf_counter()
        parsed_args: dict[str, Any] = {}
        try:
            parsed_args = _parse_args(args_raw)
            result = self._dispatch(tool_name, parsed_args)
            observation = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        except Exception as e:
            observation = json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)

        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.log_event(
            "TOOL_CALL",
            {
                "user_id": self.user_id,
                "tool": tool_name,
                "args": args_raw,
                "latency_ms": latency_ms,
                "observation_preview": observation[:300],
            },
        )
        from src.db import repository as repo

        repo.log_tool_call(
            self.db,
            self.user_id,
            tool_name,
            parsed_args,
            observation,
            latency_ms,
        )
        return observation

    def _dispatch(self, tool_name: str, args: dict[str, Any]) -> Any:
        if tool_name == "lookup_vehicle":
            return vehicle_lookup.lookup_vehicle(
                args.get("query", ""),
                int(args.get("top_k", 4)),
            )
        if tool_name == "get_vehicle_specs":
            return vehicle_lookup.get_vehicle_specs(
                args.get("car_model", "VF5")
            )
        if tool_name == "compare_vehicles":
            return vehicle_lookup.compare_vehicles(
                args.get("model_a", "VF5"),
                args.get("model_b", "VF6"),
            )
        if tool_name == "calculate":
            mode = args.get("mode", "expression")
            if mode == "down_payment":
                return calculator.down_payment(
                    float(args["price"]),
                    float(args["percent"]),
                )
            if mode == "difference":
                return calculator.price_difference(
                    float(args["price_a"]),
                    float(args["price_b"]),
                )
            return calculator.calculate(args.get("expression", ""))
        if tool_name == "schedule_test_drive":
            payload = test_drive.schedule_test_drive(
                self.db,
                self.user_id,
                args.get("customer_name", ""),
                args.get("phone", ""),
                args.get("car_model", ""),
            )
            if payload.get("requires_confirmation"):
                self.last_pending_action = {
                    "type": "test_drive",
                    "id": payload["appointment_id"],
                    "summary": payload["message"],
                }
            return payload
        if tool_name == "search_reviews":
            return reviews_search.search_reviews(
                args.get("query", ""),
                args.get("car_model"),
                int(args.get("top_k", 3)),
            )
        return {"ok": False, "error": f"Tool '{tool_name}' không tồn tại."}


def _parse_args(args_raw: str) -> dict[str, Any]:
    args_raw = (args_raw or "").strip()
    if not args_raw:
        return {}
    if args_raw.startswith("{"):
        return json.loads(args_raw)
    # key=value, comma separated
    out: dict[str, Any] = {}
    for part in args_raw.split(","):
        if "=" not in part:
            if not out and part:
                out["query"] = part.strip()
            continue
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip().strip("\"'")
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v
    return out
