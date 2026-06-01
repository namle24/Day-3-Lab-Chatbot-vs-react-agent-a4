import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from src.api.main import app
from src.core.gemini_provider import GeminiProvider
from src.core.openai_provider import OpenAIProvider
from unittest.mock import patch

client = TestClient(app, raise_server_exceptions=False)

def test_flow():
    user_id = "test_user_robustness"
    
    print("\n--- 1. Resetting Chat Session (DELETE) ---")
    del_res = client.delete(f"/api/v1/sessions/{user_id}/messages")
    print("Delete Response:", del_res.json())
    assert del_res.status_code == 200
    assert del_res.json()["ok"] is True

    print("\n--- 2. Checking Empty Chat History (GET) ---")
    get_res = client.get(f"/api/v1/sessions/{user_id}/messages")
    print("Get History Response:", get_res.json())
    assert get_res.status_code == 200
    assert len(get_res.json()["messages"]) == 0

    print("\n--- 3. Normal Chat Query (POST) ---")
    # Let's post a query that triggers fallback or normal mode
    # Since API key might not be fully configured, it could default to fallback or agent
    chat_res = client.post("/api/v1/chat", json={"user_id": user_id, "message": "tìm giá xe vf3"})
    print("Chat Response Status:", chat_res.status_code)
    print("Chat Response Body:", chat_res.json())
    assert chat_res.status_code == 200
    assert "reply" in chat_res.json()
    assert chat_res.json()["mode"] in ("agent", "fallback")

    print("\n--- 4. Simulating LLM Failure (Graceful Fallback Test) ---")
    # We patch both providers to raise a runtime exception
    def mock_fail(*args, **kwargs):
        raise RuntimeError("API quota completely exhausted or connection timed out!")

    with patch.object(GeminiProvider, "generate", side_effect=mock_fail), \
         patch.object(OpenAIProvider, "generate", side_effect=mock_fail):
        
        # We override DEFAULT_PROVIDER to google or openai so it initializes a provider
        with patch.dict(os.environ, {"DEFAULT_PROVIDER": "google", "GEMINI_API_KEY": "dummy_key_to_force_init"}):
            fallback_chat_res = client.post("/api/v1/chat", json={"user_id": user_id, "message": "so sánh VF5 và VF6"})
            print("Fallback Chat Status:", fallback_chat_res.status_code)
            print("Fallback Chat Response Body:", fallback_chat_res.json())
            assert fallback_chat_res.status_code == 200
            assert fallback_chat_res.json()["mode"] == "fallback"
            assert "dữ liệu VF5 và VF6" in fallback_chat_res.json()["reply"]

    print("\n--- 5. Global Exception Handler Test ---")
    # We test what happens if an uncaught exception is raised inside the endpoint itself
    # We patch handle_chat to raise an exception
    with patch("src.api.routes.chat.handle_chat", side_effect=RuntimeError("Database connection lost!")):
        err_res = client.post("/api/v1/chat", json={"user_id": user_id, "message": "hello"})
        print("Error Response Status (Expected 500):", err_res.status_code)
        print("Error Response Body:", err_res.json())
        assert err_res.status_code == 500
        assert err_res.json()["mode"] == "error"

    print("\nSUCCESS: All robustness and fallback test cases passed successfully!")

if __name__ == "__main__":
    test_flow()
