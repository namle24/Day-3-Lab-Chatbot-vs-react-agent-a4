import json
import re
import time
from typing import Any, Callable, List, Dict, Optional

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.tools.registry import get_tool_specs

ACTION_RE = re.compile(
    r"Action:\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)\)\s*$",
    re.MULTILINE | re.DOTALL,
)
FINAL_RE = re.compile(r"Final Answer:\s*(.+)", re.DOTALL | re.IGNORECASE)


class ReActAgent:
    """ReAct agent: Thought -> Action -> Observation loop."""

    def __init__(
        self,
        llm: LLMProvider,
        tool_executor: Callable[[str, str], str],
        tool_context: Any = None,
        max_steps: int = 5,
    ):
        self.llm = llm
        self.tool_executor = tool_executor
        self.tool_context = tool_context
        self.max_steps = max_steps
        self.tool_specs = get_tool_specs()
        self.last_pending_action: dict[str, Any] | None = None

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join(
            [f"- {t['name']}: {t['description']}" for t in self.tool_specs]
        )
        return f"""Bạn là VinFast Smart Sales Agent — tư vấn xe điện VinFast bằng tiếng Việt.

Công cụ:
{tool_descriptions}

Quy tắc:
1. Luôn dùng lookup_vehicle hoặc compare_vehicles trước khi nêu giá/thông số.
2. Dùng calculate cho phép tính (trả trước %, chênh lệch giá).
3. schedule_test_drive chỉ khi khách đã cho tên + SĐT; nhắc khách xác nhận ĐỒNG Ý.
4. Không bịa số liệu ngoài Observation.

Định dạng bắt buộc mỗi bước:
Thought: ...
Action: tool_name({{"key": "value"}})
(hệ thống trả Observation)

Khi đủ thông tin:
Final Answer: câu trả lời cho khách (tiếng Việt, rõ ràng, có số liệu từ tool).
"""

    def run(self, user_input: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        logger.log_event(
            "AGENT_START",
            {"input": user_input, "model": self.llm.model_name},
        )

        history_text = ""
        if history:
            lines = [f"{m['role']}: {m['content']}" for m in history[-10:]]
            history_text = "Lịch sử hội thoại:\n" + "\n".join(lines) + "\n\n"

        scratchpad = ""
        steps = 0
        final_answer = ""

        while steps < self.max_steps:
            prompt = (
                f"{history_text}"
                f"Câu hỏi khách: {user_input}\n\n"
                f"{scratchpad}\n"
                "Tiếp tục (Thought + Action HOẶC Final Answer):"
            )

            start = time.perf_counter()
            result = self.llm.generate(prompt, system_prompt=self.get_system_prompt())
            latency_ms = int((time.perf_counter() - start) * 1000)
            content = result.get("content", "")

            logger.log_event(
                "LLM_METRIC",
                {
                    "step": steps,
                    "latency_ms": latency_ms,
                    "usage": result.get("usage"),
                    "provider": result.get("provider"),
                },
            )

            final_match = FINAL_RE.search(content)
            if final_match:
                final_answer = final_match.group(1).strip()
                break

            action_match = ACTION_RE.search(content)
            if not action_match:
                scratchpad += f"Assistant:\n{content}\nObservation: Không parse được Action. Hãy dùng đúng format.\n"
                steps += 1
                continue

            tool_name = action_match.group(1).strip()
            args_raw = action_match.group(2).strip()
            thought = content.split("Action:")[0].replace("Thought:", "").strip()

            observation = self.tool_executor(tool_name, args_raw)
            if self.tool_context is not None and hasattr(self.tool_context, "last_pending_action"):
                self.last_pending_action = self.tool_context.last_pending_action

            scratchpad += (
                f"Thought: {thought}\n"
                f"Action: {tool_name}({args_raw})\n"
                f"Observation: {observation}\n"
            )
            steps += 1

        if not final_answer:
            final_answer = (
                "Em cần thêm thông tin hoặc đã đạt giới hạn bước suy luận. "
                "Anh/chị vui lòng thử hỏi cụ thể hơn (ví dụ: so sánh VF5 và VF6)."
            )

        logger.log_event("AGENT_END", {"steps": steps})
        return final_answer
