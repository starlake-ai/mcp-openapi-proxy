import os
from dotenv import load_dotenv
load_dotenv()
import pytest
import requests

BASE_URL = "http://localhost:3000"
TOKEN = os.environ.get("OPENWEBUI_API_KEY", "test_token_placeholder")

@pytest.fixture(scope="module")
def auth_header():
    return {"Authorization": f"Bearer {TOKEN}"}

@pytest.mark.skipif(os.environ.get("RUN_INTEGRATION_TESTS") is None, reason="Integration tests not enabled")
def test_models_and_chat_completion(auth_header):
    if auth_header["Authorization"] == "Bearer test_token_placeholder":
        pytest.skip("Valid token not provided for integration tests")
    # Retrieve list of models
    models_url = f"{BASE_URL}/api/models"
    r = requests.get(models_url, headers=auth_header)
    if r.status_code == 401:
        pytest.skip(f"Unauthorized access to {models_url}: {r.text}. Check your OPENWEBUI_API_KEY.")
    else:
        assert r.status_code == 200, f"GET {models_url} failed: {r.text}"
    models_data = r.json()
    # For simplicity, assume models_data is a list or dictionary containing models
    # This may require adjustment based on actual schema
    assert models_data, "No models returned"
    
    # Choose the first available model
    if isinstance(models_data, list) and models_data:
        chosen_model = models_data[0]
    elif isinstance(models_data, dict):
        # If the response uses the key "data" to hold model information, extract from it.
        if "data" in models_data and models_data["data"]:
            # Assume each model is an object with a "name" field; fallback to the raw object.
            chosen_model = models_data["data"][0].get("name", models_data["data"][0])
        else:
            pytest.fail("Unexpected models data structure: missing 'data' field")
    else:
        pytest.fail("Unexpected models data structure")
    print("DEBUG: Chosen model:", chosen_model)
    
    # Use the chosen model to construct a chat completion request
    chat_url = f"{BASE_URL}/api/chat/completions"
    payload = {
         "model": chosen_model,
         "messages": [
             {"role": "user", "content": "Hello, what's the meaning of life?"}
         ]
    }
    r2 = requests.post(chat_url, json=payload, headers=auth_header)
    assert r2.status_code == 200, f"POST {chat_url} failed: {r2.text}"
    completion_data = r2.json()
    # Check for some expected field in chat completion response.
    assert "choices" in completion_data, "No choices field in response"
    assert completion_data["choices"], "Empty choices field in response"
    first_choice = completion_data["choices"][0]
    assert "message" in first_choice, "No message field in first choice"
    assert "content" in first_choice["message"], "No content in message"
    print("DEBUG: Chat message content:", first_choice["message"]["content"])
