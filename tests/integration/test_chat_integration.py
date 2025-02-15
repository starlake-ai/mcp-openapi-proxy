import os
import json
import pytest

# Set OpenAPI configuration before importing server functions
os.environ["OPENAPI_SPEC_URL"] = "http://localhost:3000/openapi.json"
os.environ["SERVER_URL_OVERRIDE"] = "http://localhost:3000"

from mcp_openapi_proxy.server_fastmcp import list_functions, call_function

@pytest.mark.skipif(os.environ.get("RUN_INTEGRATION_TESTS") is None,
                   reason="Integration tests require RUN_INTEGRATION_TESTS environment variable")
def test_models_and_chat_completion():
    # Set up auth from environment
    api_key = os.environ.get("OPENWEBUI_API_KEY", "test_token_placeholder")
    if api_key == "test_token_placeholder":
        pytest.skip("Valid OPENWEBUI_API_KEY not provided for integration tests")
    
    os.environ["API_AUTH_BEARER"] = api_key  # Align with server_fastmcp config
    
    # 1. Test list_functions tool
    functions_json = list_functions()
    functions = json.loads(functions_json)
    
    if isinstance(functions, dict) and "error" in functions:
        pytest.fail(f"Failed to list functions: {functions['error']}")
    
    # Verify expected functions are present
    function_names = [f["name"] for f in functions]
    assert "GET /api/models" in function_names
    assert "POST /api/chat/completions" in function_names
    
    # 2. Test models endpoint through call_function
    models_response = call_function(
        function_name="GET /api/models",
        parameters={}
    )
    models_data = json.loads(models_response)
    
    if isinstance(models_data, dict) and "error" in models_data:
        pytest.fail(f"Failed to get models: {models_data['error']}")
    
    # Extract model names based on response structure
    if isinstance(models_data, list):
        model_names = models_data
    elif isinstance(models_data, dict) and "data" in models_data:
        model_names = [m.get("name", m) for m in models_data["data"]]
    else:
        pytest.fail(f"Unexpected models data structure: {type(models_data)}")
    
    assert model_names, "No models returned from API"
    
    # 3. Test chat completion with default model
    chosen_model = os.environ.get("OPENWEBUI_MODEL", "litellm.llama3.2")
    assert chosen_model in model_names, f"Model {chosen_model} not in available models: {model_names}"
    
    chat_response = call_function(
        function_name="POST /api/chat/completions",
        parameters={
            "model": chosen_model,
            "messages": [{
                "role": "user",
                "content": "Hello, what's the meaning of life?"
            }]
        }
    )
    completion = json.loads(chat_response)
    
    if isinstance(completion, dict) and "error" in completion:
        pytest.fail(f"Chat completion failed: {completion['error']}")
    
    # Validate response structure
    assert "choices" in completion, "Missing choices field in completion response"
    assert len(completion["choices"]) > 0, "Empty choices array in completion response"
    
    first_choice = completion["choices"][0]
    assert "message" in first_choice, "Missing message in completion choice"
    assert "content" in first_choice["message"], "Missing content in completion message"
