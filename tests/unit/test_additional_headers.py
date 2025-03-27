"""
Unit tests for additional headers functionality in mcp-openapi-proxy.
"""

import os
import json
import asyncio
import pytest
from unittest.mock import patch
from mcp_openapi_proxy.utils import get_additional_headers, setup_logging
from mcp_openapi_proxy.server_lowlevel import dispatcher_handler, tools, openapi_spec_data
from mcp_openapi_proxy.server_fastmcp import call_function
import requests
from types import SimpleNamespace

DUMMY_SPEC = {
    "servers": [{"url": "http://dummy.com"}],
    "paths": {
        "/test": {
            "get": {
                "summary": "Test",
                "operationId": "get_test"  # Match tool name
            }
        }
    }
}

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.delenv("EXTRA_HEADERS", raising=False)
    monkeypatch.delenv("OPENAPI_SPEC_URL", raising=False)
    monkeypatch.setenv("OPENAPI_SPEC_URL", "http://dummy.com")

@pytest.fixture
def mock_requests(monkeypatch):
    def mock_request(method, url, **kwargs):
        class MockResponse:
            def __init__(self):
                self.text = "Mocked response"
            def raise_for_status(self):
                pass
        return MockResponse()
    monkeypatch.setattr(requests, "request", mock_request)

def test_get_additional_headers_empty(mock_env):
    headers = get_additional_headers()
    assert headers == {}, "Expected empty headers when EXTRA_HEADERS not set"

def test_get_additional_headers_single(mock_env):
    os.environ["EXTRA_HEADERS"] = "X-Test: Value"
    headers = get_additional_headers()
    assert headers == {"X-Test": "Value"}, "Single header not parsed correctly"

def test_get_additional_headers_multiple(mock_env):
    os.environ["EXTRA_HEADERS"] = "X-Test: Value\nX-Another: More"
    headers = get_additional_headers()
    assert headers == {"X-Test": "Value", "X-Another": "More"}, "Multiple headers not parsed correctly"

@pytest.mark.asyncio
async def test_lowlevel_dispatcher_with_headers(mock_env, mock_requests, monkeypatch):
    os.environ["EXTRA_HEADERS"] = "X-Custom: Foo"
    tools.clear()
    monkeypatch.setattr("mcp_openapi_proxy.server_lowlevel.openapi_spec_data", DUMMY_SPEC)
    tools.append(SimpleNamespace(name="get_test", inputSchema={"type": "object", "properties": {}}))
    request = SimpleNamespace(params=SimpleNamespace(name="get_test", arguments={}))
    with patch('mcp_openapi_proxy.server_fastmcp.fetch_openapi_spec', return_value=DUMMY_SPEC):
        result = await dispatcher_handler(request)
    assert result.content[0].text == "Mocked response", "Dispatcher failed with headers"

from unittest.mock import patch
def test_fastmcp_call_function_with_headers(mock_env, mock_requests):
    os.environ["EXTRA_HEADERS"] = "X-Custom: Bar"
    os.environ["API_KEY"] = "dummy"
    from unittest.mock import patch
    from mcp_openapi_proxy import server_fastmcp
    # Patch the fetch_openapi_spec in server_fastmcp so it returns DUMMY_SPEC.
    with patch('mcp_openapi_proxy.server_fastmcp.fetch_openapi_spec', return_value=DUMMY_SPEC):
        from types import SimpleNamespace
        with patch('mcp_openapi_proxy.utils.normalize_tool_name', side_effect=lambda raw_name: "get_test"), \
             patch('mcp_openapi_proxy.server_fastmcp.requests.request', return_value=SimpleNamespace(text='"Mocked response"', raise_for_status=lambda: None)):
            result = server_fastmcp.call_function(function_name="get_test", parameters={}, env_key="OPENAPI_SPEC_URL")
            print(f"DEBUG: Call function result: {result}")
    assert json.loads(result) == "Mocked response", "Call function failed with headers"
