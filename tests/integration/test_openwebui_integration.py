import os
import json
import pytest
import logging

logger = logging.getLogger(__name__)

@pytest.mark.skipif(
    "OPENWEBUI_API_KEY" not in os.environ or os.environ["OPENWEBUI_API_KEY"] == "test_token_placeholder",
    reason="Valid OPENWEBUI_API_KEY not provided for integration tests"
)
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
def test_chat_completion_modes(test_mode, params, reset_env_and_module):
    env_key = reset_env_and_module
    # Set up auth and spec from environment
    api_key = os.environ.get("OPENWEBUI_API_KEY", "test_token_placeholder")
    os.environ["API_AUTH_BEARER"] = api_key
    os.environ[env_key] = "http://localhost:3000/openapi.json"
    os.environ["SERVER_URL_OVERRIDE"] = "http://localhost:3000"

    from mcp_openapi_proxy.server_fastmcp import list_functions, call_function

    logger.debug(f"Env before list_functions: {env_key}={os.environ.get(env_key)}")
    tools_json = list_functions(env_key=env_key)
    tools = json.loads(tools_json)
    assert len(tools) > 0, f"No tools generated from OpenWebUI spec: {tools_json}"

    chat_completion_func = next(
        (t["name"] for t in tools if "chat.completions" in t["name"] and t["method"] == "POST"),
        None
    )
    assert chat_completion_func, "No POST chat.completions function found in tools"

    logger.info(f"Calling chat completion function: {chat_completion_func} in {test_mode} mode")
    response_json = call_function(function_name=chat_completion_func, parameters=params, env_key=env_key)
    response = json.loads(response_json)

    if test_mode == "simple":
        assert "choices" in response, "Simple mode response missing 'choices'"
        assert len(response["choices"]) > 0, "Simple mode response has no choices"
        assert "message" in response["choices"][0], "Simple mode response choice missing 'message'"
        assert "content" in response["choices"][0]["message"], "Simple mode response choice missing 'content'"
    elif test_mode == "complex":
        assert isinstance(response, dict), "Complex mode (streaming) response should be a dict"
        assert "error" not in response, f"Complex mode response contains error: {response.get('error')}"
