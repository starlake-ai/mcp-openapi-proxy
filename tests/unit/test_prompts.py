import os
import json
import pytest
from mcp_openapi_proxy.server_lowlevel import list_prompts, get_prompt
from mcp_openapi_proxy.server_fastmcp import list_functions, call_function
from types import SimpleNamespace

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.delenv("OPENAPI_SPEC_URL", raising=False)
    monkeypatch.setenv("OPENAPI_SPEC_URL", "http://dummy.com")

def test_lowlevel_list_prompts(mock_env):
    request = SimpleNamespace(params=SimpleNamespace())
    result = asyncio.run(list_prompts(request))
    assert len(result.root.prompts) == 1, "Expected one prompt"
    assert result.root.prompts[0].name == "summarize_spec", "Expected summarize_spec prompt"

def test_lowlevel_get_prompt_valid(mock_env):
    request = SimpleNamespace(params=SimpleNamespace(name="summarize_spec", arguments={}))
    result = asyncio.run(get_prompt(request))
    assert len(result.root.messages) == 1, "Expected one message"
    assert "blueprint" in result.root.messages[0]["content"]["text"], "Expected 'blueprint' in prompt response"

def test_fastmcp_list_prompts(mock_env):
    tools_json = list_functions(env_key="OPENAPI_SPEC_URL")
    tools = json.loads(tools_json)
    assert any(t["name"] == "list_prompts" for t in tools), "list_prompts not found"
    result = call_function(function_name="list_prompts", parameters={}, env_key="OPENAPI_SPEC_URL")
    prompts = json.loads(result)
    assert len(prompts) == 1, "Expected one prompt"
    assert prompts[0]["name"] == "summarize_spec", "Expected summarize_spec prompt"

def test_fastmcp_get_prompt_valid(mock_env):
    result = call_function(function_name="get_prompt", parameters={"name": "summarize_spec"}, env_key="OPENAPI_SPEC_URL")
    messages = json.loads(result)
    assert len(messages) == 1, "Expected one message"
    assert "blueprint" in messages[0]["content"]["text"], "Expected 'blueprint' in prompt response"
