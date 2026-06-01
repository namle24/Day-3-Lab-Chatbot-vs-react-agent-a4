import os
from dotenv import load_dotenv
from typing import Generator, Dict, Any, Optional

# Load env variables
load_dotenv()

from src.core.llm_provider import LLMProvider
from src.core.openai_provider import OpenAIProvider
from src.core.gemini_provider import GeminiProvider
from src.core.local_provider import LocalProvider
from src.telemetry.logger import logger

class MockProvider(LLMProvider):
    """
    Fallback LLM Provider that simulates response generation
    when no API keys are configured.
    """
    def __init__(self):
        super().__init__("mock-simulator", "mock-key")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        import time
        start_time = time.time()
        time.sleep(1.0)  # Simulate network latency
        
        # A simple response selection based on prompt content
        prompt_lower = prompt.lower()
        if "chi phí" in prompt_lower or "giá" in prompt_lower:
            response_text = "Chào anh/chị! Chi phí triển khai chatbot e-commerce dao động từ 10 - 30 triệu VNĐ tùy vào độ phức tạp của việc tích hợp kho hàng và CRM. Bên em có hỗ trợ trả góp theo giai đoạn triển khai ạ."
        elif "python" in prompt_lower or "sdk" in prompt_lower:
            response_text = "Dạ, đây là link tài liệu hướng dẫn tích hợp SDK Python của bên em: https://docs.example.com/python-sdk. Anh/chị chỉ cần chạy `pip install chatbot-sdk` và làm theo hướng dẫn 3 dòng code cấu hình."
        elif "xong chưa" in prompt_lower or "chậm" in prompt_lower:
            response_text = "Dạ hệ thống đã tối ưu xong database index cho chatbot bot-992 của anh/chị rồi ạ. Tốc độ phản hồi hiện tại đã giảm xuống dưới 1.2s. Anh/chị kiểm tra lại giúp em xem đã mượt chưa nhé."
        else:
            response_text = f"Chào anh/chị! (Chế độ mô phỏng) Tôi đã nhận được tin nhắn: '{prompt}'. Để kết nối trực tiếp với Gemini hoặc OpenAI, vui lòng cập nhật GEMINI_API_KEY hoặc OPENAI_API_KEY trong file .env."

        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "content": response_text,
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(response_text.split()),
                "total_tokens": len(prompt.split()) + len(response_text.split())
            },
            "latency_ms": latency_ms,
            "provider": "mock"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        res = self.generate(prompt, system_prompt)
        words = res["content"].split(" ")
        for word in words:
            import time
            time.sleep(0.05)
            yield word + " "

def get_llm_provider() -> LLMProvider:
    """
    Loads default LLM provider configured in environment variables.
    Falls back to Gemini/OpenAI if key is present, otherwise falls back to MockProvider.
    """
    provider_name = os.getenv("DEFAULT_PROVIDER", "openai").lower()
    
    # Map 'google' or 'gemini' to GeminiProvider
    if provider_name in ["google", "gemini"]:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or "your_gemini_api_key" in api_key:
            logger.info("GEMINI_API_KEY not set or invalid. Falling back to MockProvider.")
            return MockProvider()
        model_name = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
        logger.info(f"Using Gemini Provider with model {model_name}")
        return GeminiProvider(model_name=model_name, api_key=api_key)
        
    elif provider_name == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or "your_openai_api_key" in api_key:
            logger.info("OPENAI_API_KEY not set or invalid. Checking GEMINI_API_KEY as secondary fallback...")
            # Let's check if Gemini key is available
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key and "your_gemini_api_key" not in gemini_key:
                logger.info("GEMINI_API_KEY found! Using Gemini Provider.")
                model_name = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
                return GeminiProvider(model_name=model_name, api_key=gemini_key)
            logger.info("No valid LLM key found. Falling back to MockProvider.")
            return MockProvider()
        model_name = os.getenv("DEFAULT_MODEL", "gpt-4o")
        logger.info(f"Using OpenAI Provider with model {model_name}")
        return OpenAIProvider(model_name=model_name, api_key=api_key)
        
    elif provider_name == "local":
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        if not os.path.exists(model_path):
            logger.info(f"Local model not found at {model_path}. Falling back to MockProvider.")
            return MockProvider()
        logger.info(f"Using Local Provider with model path {model_path}")
        return LocalProvider(model_path=model_path)
        
    else:
        logger.info(f"Unknown provider: {provider_name}. Falling back to MockProvider.")
        return MockProvider()
