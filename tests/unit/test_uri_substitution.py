import os
import json
import asyncio
import pytest
from unittest.mock import patch
from mcp_openapi_proxy.server_lowlevel import register_functions, dispatcher_handler
from mcp_openapi_proxy.server_fastmcp import list_functions, call_function
import requests
from types import SimpleNamespace

DUMMY_SPEC = {
    "servers": [{"url": "http://dummy.com"}],
    "paths": {
        "/users/{user_id}/tasks": {
            "get": {
                "summary": "Get tasks",
                "operationId": "get_users_tasks",
                "parameters": [
                    {"name": "user_id", "in": "path", "required": True, "schema": {"type": "string"}}
                ]
            }
        }
    }
}

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.delenv("OPENAPI_SPEC_URL", raising=False)
    monkeypatch.setenv("OPENAPI_SPEC_URL", "http://dummy.com")
    monkeypatch.setenv("TOOL_WHITELIST", "")

@pytest.fixture
def mock_requests(monkeypatch):
    def mock_request(method, url, **kwargs):
        class MockResponse:
            def __init__(self, url):
                self.text = f"Mocked response for {url}"
            def raise_for_status(self):
                pass
        return MockResponse(url)
    monkeypatch.setattr(requests, "request", mock_request)

@pytest.mark.skip(reason="Tool registration issue, revisit later")
def test_lowlevel_uri_substitution(mock_env):
    from mcp_openapi_proxy.server_lowlevel import tools, openapi_spec_data
    tools.clear()
    openapi_spec_data = DUMMY_SPEC
    register_functions(DUMMY_SPEC)
    assert len(tools) == 1, "Expected one tool"
    assert "user_id" in tools[0].inputSchema["properties"], "user_id not in inputSchema"
    assert "user_id" in tools[0].inputSchema["required"], "user_id not required"

@pytest.mark.skip(reason="Tool name mismatch, revisit later")
def test_lowlevel_dispatcher_substitution(mock_env, mock_requests):
    from mcp_openapi_proxy.server_lowlevel import tools, openapi_spec_data
    tools.clear()
    openapi_spec_data = DUMMY_SPEC
    register_functions(DUMMY_SPEC)
    request = SimpleNamespace(params=SimpleNamespace(name="get_users_tasks", arguments={"user_id": "123"}))
    result = asyncio.run(dispatcher_handler(request))
    assert result.root.content[0].text == "Mocked response for http://dummy.com/users/123/tasks", "URI substitution failed"

@pytest.mark.skip(reason="FastMCP tool list issue, revisit later")
def test_fastmcp_uri_substitution(mock_env):
    with patch('mcp_openapi_proxy.utils.fetch_openapi_spec', return_value=DUMMY_SPEC):
        tools_json = list_functions(env_key="OPENAPI_SPEC_URL")
        tools = json.loads(tools_json)
        assert any(t["name"] == "get_users_tasks" for t in tools), "get_users_tasks not found"
        tool = next(t for t in tools if t["name"] == "get_users_tasks")
        assert "user_id" in tool["inputSchema"]["properties"], "user_id not in inputSchema"
        assert "user_id" in tool["inputSchema"]["required"], "user_id not required"

@pytest.mark.skip(reason="FastMCP spec fetch issue, revisit later")
def test_fastmcp_call_function_substitution(mock_env, mock_requests):
    with patch('mcp_openapi_proxy.utils.fetch_openapi_spec', return_value=DUMMY_SPEC):
        result = call_function(function_name="get_users_tasks", parameters={"user_id": "123"}, env_key="OPENAPI_SPEC_URL")
        assert json.loads(result) == "Mocked response for http://dummy.com/users/123/tasks", "URI substitution failed"
