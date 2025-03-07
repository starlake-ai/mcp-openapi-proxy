import os
import json
import pytest

# Set OpenAPI configuration before importing server functions
os.environ["OPENAPI_SPEC_URL"] = "http://localhost:3000/openapi.json"
os.environ["SERVER_URL_OVERRIDE"] = "http://localhost:3000"

from mcp_openapi_proxy.server_fastmcp import list_functions, call_function

@pytest.mark.parametrize("test_mode,params", [
    ("simple", {
        "model": os.environ.get("OPENWEBUI_MODEL", "litellm.llama3.2"),
        "messages": [{
            "role": "user",
            "content": "Hello, what's the meaning of life?"
        }]
    }),
    ("complex", {
        "model": os.environ.get("OPENWEBUI_MODEL", "litellm.llama3.2"),
        "messages": [{
            "role": "user",
            "content": "Explain quantum computing in 3 paragraphs",
            "name": "physics_student"
        }, {
            "role": "system",
            "content": "You are a physics professor"
        }],
        "temperature": 0.7,
        "max_tokens": 300,
        "top_p": 0.9,
        "stream": True
    })
])
def test_chat_completion_modes(test_mode, params):
    # Set up auth from environment
    api_key = os.environ.get("OPENWEBUI_API_KEY", "test_token_placeholder")
    if api_key == "test_token_placeholder":
        pytest.skip("Valid OPENWEBUI_API_KEY not provided for integration tests")
    
    os.environ["API_AUTH_BEARER"] = api_key
    
    # Verify model availability
    models_response = call_function(function_name="GET /api/models", parameters={})
    models_data = json.loads(models_response)
    
    if isinstance(models_data, dict) and "error" in models_data:
        import pytest
        pytest.skip(f"Model check skipped due to access restriction: {models_data['error']}")
    
    model_names = models_data if isinstance(models_data, list) else \
                 [m.get("name", m) for m in models_data.get("data", [])]
    assert params["model"] in model_names, f"Model {params['model']} not available"
    
    # Execute chat completion with mode-specific parameters
    chat_response = call_function(
        function_name="POST /api/chat/completions",
        parameters=params
    )
    # Mode-specific handling
    if test_mode == "complex":  # Streaming response
        completion = {}
        full_content = ""
        for chunk in chat_response.split("\n"):
            if chunk.strip().startswith(""):
                try:
                    chunk_data = json.loads(chunk.strip()[5:])
                    if "choices" in chunk_data and chunk_data["choices"]:
                        delta = chunk_data["choices"][0].get("delta", {})
                        if "content" in delta:
                            full_content += delta["content"]
                        if "finish_reason" in chunk_data["choices"][0] and chunk_data["choices"][0]["finish_reason"] is not None:
                            completion["choices"] = [{"finish_reason" : chunk_data["choices"][0]["finish_reason"]}]
                except json.JSONDecodeError:
                    pass  # Ignore incomplete JSON chunks

        completion["choices"][0]["message"] = {"content": full_content, "role": "assistant"}

        # Assertions for complex mode
        assert len(full_content) > 100, "Short response in complex mode"
        assert "finish_reason" in completion["choices"][0], "Missing finish reason"

    else:  # Non-streaming response
        completion = json.loads(chat_response)

        # Common validation
        assert "choices" in completion, "Missing choices field"
        assert len(completion["choices"]) > 0, "Empty choices array"

        first_choice = completion["choices"][0]
        message = first_choice.get("message", {})
        assert "content" in message, "Missing content in simple mode"
        assert any(c in message["content"].lower()
                   for c in ["life", "meaning", "42"]), "Unexpected simple response"
